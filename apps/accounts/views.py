from rest_framework import viewsets
from .models import Student, Professor, Course, Exam, AssessmentQuestion, Enrollment
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth.hashers import check_password
from .models import Professor, Student
import uuid
from .models import UserToken
from .serializers import *
from django.db import transaction
from django.utils.timezone import localtime
from rest_framework.parsers import MultiPartParser, FormParser
import os
import numpy as np
import faiss
import pickle
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from .models import CourseNote, DocumentChunk
from .grader_utils.execute_grader import ExecuteGrader
from .grader_utils.grader import Grader
from django.db.models import Prefetch
import pickle

embedder = SentenceTransformer("all-MiniLM-L6-v2")


def retrieve_relevant_chunks(query, course_id, top_k=3):
    """
    Retrieve the most relevant text chunks for a given query from ALL notes under a specific course.
    """
    # Gather all chunks across all notes in the course
    chunks = DocumentChunk.objects.filter(note__course_id=course_id)

    if not chunks.exists():
        return []

    texts = []
    embeddings = []

    # Deserialize embeddings
    for c in chunks:
        try:
            emb = pickle.loads(c.embedding)
            embeddings.append(emb)
            texts.append(c.chunk_text)
        except Exception as e:
            print(f"Skipping corrupt embedding for chunk {c.id}: {e}")

    if not embeddings:
        return []

    embeddings = np.array(embeddings).astype("float32")

    # Build FAISS index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # Encode query
    q_emb = embedder.encode(query, convert_to_numpy=True).astype("float32")

    # Search
    D, I = index.search(np.array([q_emb]), top_k)
    retrieved = [texts[i] for i in I[0]]

    return retrieved


embedder = SentenceTransformer("all-MiniLM-L6-v2")

def load_pdf_text(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"
    return text

def chunk_text(text, chunk_size=550, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunks.append(" ".join(words[i:i + chunk_size]))
    return chunks

def create_and_save_grader(exam: Exam, course_id):
    # Fetch questions for context
    questions = AssessmentQuestion.objects.filter(exam=exam)

    retrived_chunks = {}
    for q in questions:
        retrived_chunks[q] = retrieve_relevant_chunks(q.question, course_id)

    grader_executor = ExecuteGrader(
        rubrics=exam.rubrics,
        retrived_chunks=retrived_chunks,
        assessments=questions,
        strictness=1
    )

    save_dir = "graders"
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, f"exam_{exam.id}_graders.pkl")

    with open(filepath, "wb") as file_handler:
        pickle.dump(grader_executor, file_handler)

    print("Grader saved successfully!")

def load_grader(exam_id):
    save_dir = "graders"
    filepath = os.path.join(save_dir, f"exam_{exam_id}_graders.pkl")

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No saved grader found for exam {exam_id}")

    with open(filepath, "rb") as file_handler:
        grader = pickle.load(file_handler)

    return grader


class StudentExamAnswersView(APIView):
    """
    Get all answers of a specific student for a specific exam in a specific course.
    """

    def get(self, request, course_id, exam_id, student_id):
        # Token validation
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        if token_obj.user_type != "professor":
            return Response({"error": "Only professors can access this endpoint"}, status=403)

        # Validate professor and course
        try:
            professor = Professor.objects.get(id=token_obj.user_id)
        except Professor.DoesNotExist:
            return Response({"error": "Professor not found"}, status=404)

        try:
            course = Course.objects.get(id=course_id, professor=professor)
        except Course.DoesNotExist:
            return Response({"error": "Course not found or unauthorized"}, status=404)

        # Validate exam
        try:
            exam = Exam.objects.get(id=exam_id, course=course)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found for this course"}, status=404)

        # Validate student and submission
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        try:
            submission = StudentExamSubmission.objects.prefetch_related(
                Prefetch("answers", queryset=StudentAnswer.objects.select_related("question"))
            ).get(student=student, exam=exam)
        except StudentExamSubmission.DoesNotExist:
            return Response({"error": "Student has not submitted this exam"}, status=404)

        # Fetch questions for context
        questions = AssessmentQuestion.objects.filter(exam=exam)

        # Build response
        answers_data = []
        retrived_chunks = {}
        for q in questions:

            # retrived_chunks[q] = retrieve_relevant_chunks(q.question, course_id)    

            answer_obj = next((a for a in submission.answers.all() if a.question_id == q.id), None)
            answers_data.append({
                "question_id": q.id,
                "question_text": q.question,
                "question_weight": q.question_weight,
                "min_words": q.min_words,
                "answer_text": answer_obj.answer_text if answer_obj else None,
                "is_graded": answer_obj.is_graded if answer_obj else False,
                "received_weight": answer_obj.received_weight if answer_obj else 0.0,
                "feedback": answer_obj.feedback if answer_obj else ""
            })
        # grader_executor = ExecuteGrader(
        #         rubrics=exam.rubrics,
        #         retrived_chunks=retrived_chunks,
        #         assessments=questions,
        #         strictness=1) 

        try:
            grader_executor = load_grader(exam_id)
        except:
            create_and_save_grader(exam=exam, course_id=course_id)
            grader_executor = load_grader(exam_id)

        grader_executor.grade_exams(answers_data)
        print("Grading Done!")   


        # Return JSON response
        return Response({
            "course": course.course_name,
            "exam": exam.exam_name,
            "student_id": student.id,
            "student_name": student.full_name,
            "student_email": student.email,
            "submitted_at": submission.submitted_at,
            "overall_received_score": submission.overall_received_score,
            "overall_feedback": submission.overall_feedback or "",
            "total_questions": len(questions),
            "answers": answers_data
        }, status=200)
    

class DeleteCourseNoteView(APIView):
    """
    Allows a professor to delete one of their uploaded notes.
    Deletes:
      - The CourseNote record
      - All DocumentChunk entries related to it
      - The file from the filesystem
    """

    def delete(self, request, note_id):
        # Token validation
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        if token_obj.user_type != "professor":
            return Response({"error": "Only professors can delete notes"}, status=403)

        # Get professor and note
        try:
            professor = Professor.objects.get(id=token_obj.user_id)
        except Professor.DoesNotExist:
            return Response({"error": "Professor not found"}, status=404)

        try:
            note = CourseNote.objects.get(id=note_id, professor=professor)
        except CourseNote.DoesNotExist:
            return Response({"error": "Note not found or unauthorized"}, status=404)

        #  Perform deletion atomically
        try:
            with transaction.atomic():
                # Delete chunks
                chunk_count = DocumentChunk.objects.filter(note=note).delete()[0]

                # Delete file from disk
                if note.file and os.path.exists(note.file.path):
                    os.remove(note.file.path)

                # Delete note record
                note.delete()

                return Response(
                    {
                        "message": f"Note deleted successfully. {chunk_count} chunks removed.",
                        "note_id": note_id
                    },
                    status=200
                )

        except Exception as e:
            return Response({"error": f"Failed to delete note: {str(e)}"}, status=500)


class UploadCourseNoteView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    def post(self, request, course_id):
        # --- Token Validation ---
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        if token_obj.user_type != "professor":
            return Response({"error": "Only professors can upload notes"}, status=403)

        # --- Professor and Course Validation ---
        professor = Professor.objects.get(id=token_obj.user_id)
        try:
            course = Course.objects.get(id=course_id, professor=professor)
        except Course.DoesNotExist:
            return Response({"error": "Course not found or unauthorized"}, status=404)

        file = request.FILES.get("file")
        note_name = request.data.get("note_name")

        if not file or not note_name:
            return Response({"error": "Both 'note_name' and 'file' are required."}, status=400)

        valid_extensions = ['.pdf', '.docx']
        if not any(file.name.lower().endswith(ext) for ext in valid_extensions):
            return Response({"error": "Only PDF or DOCX files are allowed."}, status=400)

        try:
            with transaction.atomic():
                # Step 1: Save the file record (not committed yet)
                course_note = CourseNote.objects.create(
                    course=course,
                    professor=professor,
                    note_name=note_name,
                    file=file
                )

                # Step 2: Process PDF
                if file.name.lower().endswith(".pdf"):
                    pdf_path = course_note.file.path
                    try:
                        text = load_pdf_text(pdf_path)
                        if not text.strip():
                            raise ValueError("No text extracted from the PDF.")

                        chunks = chunk_text(text)
                        if not chunks:
                            raise ValueError("Chunking failed or produced empty chunks.")

                        embeddings = embedder.encode(chunks, convert_to_numpy=True)

                        # Step 3: Save chunks
                        for chunk_text_item, emb in zip(chunks, embeddings):
                            binary_emb = pickle.dumps(emb.astype(np.float32))
                            DocumentChunk.objects.create(
                                note=course_note,
                                chunk_text=chunk_text_item,
                                embedding=binary_emb
                            )

                    except Exception as e:
                        # Rollback and delete file if chunking fails
                        if os.path.exists(course_note.file.path):
                            os.remove(course_note.file.path)
                        raise e

                # Step 4: Return successful response
                serializer = CourseNoteSerializer(course_note)
                return Response(serializer.data, status=201)

        except Exception as e:
            print(e)
            return Response({"error": f"Failed to process and save file: {str(e)}"}, status=500)

class GetCourseNotesView(APIView):
    """
    Returns all notes for a given course.
    Accessible to both professors and students.
    """

    def get(self, request, course_id):
        notes = CourseNote.objects.filter(course_id=course_id)
        serializer = CourseNoteSerializer(notes, many=True)
        return Response(serializer.data, status=200)
    


class ProfessorExamSubmissionsView(APIView):
    """
    Shows all submissions of a particular exam for the professor who created it.
    Includes:
    - Exam info (name, course, enrolled/submitted counts)
    - All questions
    - Each student's submission details (answers, grading status, etc.)
    """

    def get(self, request, exam_id):
        # Validate token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        # Ensure only professors can access
        if token_obj.user_type != "professor":
            return Response({"error": "Only professors can access this endpoint"}, status=403)

        # Get professor
        try:
            professor = Professor.objects.get(id=token_obj.user_id)
        except Professor.DoesNotExist:
            return Response({"error": "Professor not found"}, status=404)

        # Get exam (ensure it belongs to this professor)
        try:
            exam = Exam.objects.select_related("course").get(id=exam_id, course__professor=professor)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found or unauthorized"}, status=404)

        course = exam.course

        # Collect metadata
        enrolled_students = Student.objects.filter(enrollments__course=course).distinct()
        submissions = StudentExamSubmission.objects.filter(exam=exam).select_related("student")

        # Build per-student submission data
        student_submission_data = []
        for student in enrolled_students:
            submission = submissions.filter(student=student).first()

            if submission:
                answers = StudentAnswer.objects.filter(submission=submission)
                answers_serialized = [
                    {
                        "question_id": ans.question.id,
                        "question": ans.question.question,
                        "question_weight": ans.question.question_weight,
                        "answer_text": ans.answer_text,
                        "received_weight": ans.received_weight,
                        "feedback": ans.feedback
                    }
                    for ans in answers
                ]
                student_submission_data.append({
                    "student_id": student.id,
                    "student_name": student.full_name,
                    "is_submitted": True,
                    "submission_timestamp": localtime(submission.submitted_at) if submission.submitted_at else None,
                    "is_graded": all(a.is_graded for a in answers),
                    "answers": answers_serialized
                })
            else:
                student_submission_data.append({
                    "student_id": student.id,
                    "student_name": student.full_name,
                    "is_submitted": False,
                    "submission_timestamp": None,
                    "is_graded": False,
                    "answers": []
                })

        # Serialize questions
        questions = exam.assessment_questions.all()
        question_serializer = QuestionInfoSerializer(questions, many=True)

        # Build final response
        response_data = {
            "exam_name": exam.exam_name,
            "course_name": course.course_name,
            "num_enrolled_students": enrolled_students.count(),
            "num_students_submitted": submissions.count(),
            "questions": question_serializer.data,
            "student_submissions": student_submission_data,
        }

        return Response(response_data, status=200)

class UpdateSubmissionView(APIView):
    """
    PATCH: Update overall score/feedback and/or per-question grading for a student's submission.
    Endpoint:
      PATCH /api/courses/<course_id>/exams/<exam_id>/students/<student_id>/submission/
    Body (partial allowed), e.g.:
    {
      "overall_received_score": 42.5,
      "overall_feedback": "Good depth.",
      "answers": [
        {"question_id": 11, "received_weight": 9.5, "feedback": "Sharper."},
        {"question_id": 12, "is_graded": true}
      ]
    }
    """

    def patch(self, request, course_id, exam_id, student_id):
        # Auth: professor only
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)
        token_value = auth_header.split(" ")[1]
        try:
            token = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)
        if token.user_type != "professor":
            return Response({"error": "Only professors can update grades"}, status=403)

        # Entities & ownership
        try:
            professor = Professor.objects.get(id=token.user_id)
        except Professor.DoesNotExist:
            return Response({"error": "Professor not found"}, status=404)

        try:
            course = Course.objects.get(id=course_id, professor=professor)
        except Course.DoesNotExist:
            return Response({"error": "Course not found or unauthorized"}, status=404)

        try:
            exam = Exam.objects.get(id=exam_id, course=course)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found for this course"}, status=404)

        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        try:
            submission = StudentExamSubmission.objects.get(student=student, exam=exam)
        except StudentExamSubmission.DoesNotExist:
            return Response({"error": "Submission not found for this student/exam"}, status=404)

        # Validate payload
        serializer = UpdateSubmissionSerializer(data=request.data, partial=True)
        print(request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        data = serializer.validated_data

        # Update atomically
        try:
            with transaction.atomic():
                # Per-question updates (optional)
                updated_answers = 0
                if "answers" in data and data["answers"]:
                    # Ensure questions belong to this exam
                    valid_qids = set(
                        AssessmentQuestion.objects.filter(exam=exam).values_list("id", flat=True)
                    )
                    for item in data["answers"]:
                        qid = item["question_id"]
                        if qid not in valid_qids:
                            return Response(
                                {"error": f"question_id {qid} does not belong to this exam"},
                                status=400
                            )
                        # Upsert StudentAnswer
                        sa, _ = StudentAnswer.objects.get_or_create(
                            submission=submission,
                            question_id=qid,
                            defaults={"answer_text": ""}  # keep/default if not present
                        )
                        if "received_weight" in item:
                            sa.received_weight = item["received_weight"]
                        if "feedback" in item:
                            sa.feedback = item["feedback"] or ""
                        if "is_graded" in item:
                            sa.is_graded = bool(item["is_graded"])
                        sa.save()
                        updated_answers += 1

                # Overall updates (optional)
                if "overall_received_score" in data:
                    submission.overall_received_score = data["overall_received_score"]
                if "overall_feedback" in data:
                    submission.overall_feedback = data["overall_feedback"] or ""
                submission.save()

            return Response(
                {
                    "message": "Submission updated",
                    "submission_id": submission.id,
                    "answers_updated": updated_answers,
                    "overall_received_score": submission.overall_received_score,
                    "overall_feedback": submission.overall_feedback or ""
                },
                status=200
            )
        except Exception as e:
            return Response({"error": f"Failed to update submission: {str(e)}"}, status=500)

class ProfessorAllExamsView(APIView):
    """
    Returns all exams created by the authenticated professor.
    Includes course name, number of enrolled students in that course,
    number of submissions, number of questions, and overall score.
    """

    def get(self, request):
        #  Validate token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response(
                {"error": "Missing or invalid Authorization header"}, status=401
            )

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        # Check professor type
        if token_obj.user_type != "professor":
            return Response(
                {"error": "Only professors can access this endpoint"}, status=403
            )

        #  Fetch professor
        try:
            professor = Professor.objects.get(id=token_obj.user_id)
        except Professor.DoesNotExist:
            return Response({"error": "Professor not found"}, status=404)

        # Fetch all exams created by this professor
        exams = Exam.objects.filter(course__professor=professor).select_related("course")

        # Serialize results
        serializer = ProfessorExamSummarySerializer(exams, many=True)
        return Response(serializer.data, status=200)

class StudentGetCourseExamsView(APIView):
    """
    Allows a student to view all exams in a specific course.
    Requires: Authorization: Token <token_value>
    """

    def get(self, request, course_id):
        # Validate token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        # Only students allowed
        if token_obj.user_type != "student":
            return Response({"error": "Only students can access this endpoint"}, status=403)

        # Validate student existence
        try:
            student = Student.objects.get(id=token_obj.user_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        # Validate course
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=404)


        # Fetch exams
        exams = Exam.objects.filter(course=course).order_by('id')

        # Pass student into serializer context
        serializer = StudentExamListSerializer(exams, many=True, context={'student': student})
        return Response(serializer.data, status=200)

class TakeExamView(APIView):
    """
    Allows a student to fetch an exam with all questions before taking it.
    """

    def get(self, request, course_id, exam_id):
        # Validate token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        if token_obj.user_type != "student":
            return Response({"error": "Only students can take exams"}, status=403)

        # Validate exam ownership within course
        try:
            exam = Exam.objects.get(id=exam_id, course_id=course_id)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found in this course"}, status=404)

        # Fetch questions
        questions = exam.assessment_questions.all().values('id', 'question', 'question_weight', 'min_words')

        return Response({
            "exam_id": exam.id,
            "exam_name": exam.exam_name,
            "rubrics": exam.rubrics,
            "overall_score": exam.overall_score,
            "questions": list(questions)
        }, status=200)


class SubmitExamView(APIView):
    """
    Allows a student to submit answers for an exam.
    """

    def post(self, request, course_id, exam_id):
        # Validate token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        if token_obj.user_type != "student":
            return Response({"error": "Only students can submit exams"}, status=403)

        # Fetch student and exam
        try:
            student = Student.objects.get(id=token_obj.user_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        try:
            exam = Exam.objects.get(id=exam_id, course_id=course_id)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found"}, status=404)

        # Check if already submitted
        if StudentExamSubmission.objects.filter(student=student, exam=exam).exists():
            return Response({"message": "You have already submitted this exam."}, status=200)

        # Create submission
        data = request.data.copy()
        data['exam'] = exam.id
        serializer = StudentExamSubmissionSerializer(data=data)
        if serializer.is_valid():
            serializer.save(student=student, exam=exam)
            return Response({"message": "Exam submitted successfully."}, status=201)
        return Response(serializer.errors, status=400)

class UnenrollCourseView(APIView):
    """
    Allows a student to unenroll (remove) themselves from a course.
    Requires header: Authorization: Token <token_value>
    """

    def delete(self, request, course_id):
        # Validate token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=status.HTTP_401_UNAUTHORIZED)

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)

        # Ensure student user
        if token_obj.user_type != "student":
            return Response({"error": "Only students can unenroll from courses"}, status=status.HTTP_403_FORBIDDEN)

        # Find student and course
        try:
            student = Student.objects.get(id=token_obj.user_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check enrollment
        try:
            enrollment = Enrollment.objects.get(student=student, course=course)
        except Enrollment.DoesNotExist:
            return Response({"error": "You are not enrolled in this course"}, status=status.HTTP_400_BAD_REQUEST)

        # Unenroll (delete record)
        enrollment.delete()
        return Response(
            {"message": f"You have been unenrolled from {course.course_name} successfully."},
            status=status.HTTP_200_OK
        )

class StudentEnrolledCoursesView(APIView):
    """
    Returns all courses the authenticated student is enrolled in.
    Requires header: Authorization: Token <token_value>
    """

    def get(self, request):
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        # Ensure it's a student
        if token_obj.user_type != "student":
            return Response({"error": "Only students can view enrolled courses"}, status=403)

        # Fetch student and enrolled courses
        try:
            student = Student.objects.get(id=token_obj.user_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        enrolled_courses = Course.objects.filter(enrollments__student=student)
        serializer = EnrolledCourseSerializer(enrolled_courses, many=True)
        return Response(serializer.data, status=200)


class EnrollCourseView(APIView):
    """
    Allows a student to enroll in a course.
    Requires header: Authorization: Token <token_value>
    """

    def post(self, request, course_id):
        # Validate token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        # Ensure it's a student
        if token_obj.user_type != "student":
            return Response({"error": "Only students can enroll in courses"}, status=403)

        # Find student and course
        try:
            student = Student.objects.get(id=token_obj.user_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=404)

        # Check if already enrolled
        if Enrollment.objects.filter(student=student, course=course).exists():
            return Response({"message": "Already enrolled in this course"}, status=200)

        # Enroll the student
        Enrollment.objects.create(student=student, course=course)
        return Response(
            {"message": f"Enrolled successfully in {course.course_name}"},
            status=201
        )

class EditExamView(APIView):
    """
    Allows professor to edit an existing exam and its questions.
    Requires: Authorization: Token <token_value>
    """

    @transaction.atomic
    def put(self, request, course_id, exam_id):
        # Authenticate professor
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        if token_obj.user_type != "professor":
            return Response({"error": "Only professors can edit exams"}, status=403)

        # Verify professor and ownership
        try:
            professor = Professor.objects.get(id=token_obj.user_id)
        except Professor.DoesNotExist:
            return Response({"error": "Professor not found"}, status=404)

        try:
            course = Course.objects.get(id=course_id, professor=professor)
        except Course.DoesNotExist:
            return Response({"error": "Course not found or not owned by professor"}, status=404)

        try:
            exam = Exam.objects.get(id=exam_id, course=course)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found for this course"}, status=404)

        # Delete all submissions (and their StudentAnswer rows via CASCADE) for this exam
        StudentExamSubmission.objects.filter(exam=exam).delete()

        # Validate and update exam
        serializer = ExamUpdateSerializer(exam, data=request.data, partial=True)

        try:
            # whatever this does in your flow (rebuild grader, etc.)
            create_and_save_grader(exam=exam, course_id=course_id)
        except Exception:
            return Response({"error": "Error in updating exam"}, status=404)

        if serializer.is_valid():
            updated_exam = serializer.save()
            return Response(
                {
                    "message": "Exam updated successfully",
                    "exam": ExamUpdateSerializer(updated_exam).data,
                },
                status=200,
            )

        return Response(serializer.errors, status=400)

class GetCourseExamsView(APIView):
    """
    Returns all exams for a given course (professor only).
    Requires: Authorization: Token <token_value>
    """

    def get(self, request, course_id):
        # Validate token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        # Ensure professor
        if token_obj.user_type != "professor":
            return Response({"error": "Only professors can view exams"}, status=403)

        # Verify professor and course ownership
        try:
            professor = Professor.objects.get(id=token_obj.user_id)
        except Professor.DoesNotExist:
            return Response({"error": "Professor not found"}, status=404)

        try:
            course = Course.objects.get(id=course_id, professor=professor)
        except Course.DoesNotExist:
            return Response({"error": "Course not found or not owned by professor"}, status=404)

        # Fetch exams for that course
        exams = Exam.objects.filter(course=course).order_by('-id')
        serializer = ExamReadSerializer(exams, many=True)

        return Response(serializer.data, status=200)

class CreateExamView(APIView):
    """
    Allows a professor to create an exam for a specific course.
    Professors can also include multiple assessment questions.
    Requires header: Authorization: Token <token_value>
    """

    def post(self, request, course_id):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response(
                {"error": "Missing or invalid Authorization header"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        #  Ensure it's a professor
        if token_obj.user_type != "professor":
            return Response({"error": "Only professors can create exams"}, status=403)

        #  Validate professor and course ownership
        try:
            professor = Professor.objects.get(id=token_obj.user_id)
        except Professor.DoesNotExist:
            return Response({"error": "Professor not found"}, status=404)

        try:
            course = Course.objects.get(id=course_id, professor=professor)
        except Course.DoesNotExist:
            return Response(
                {"error": "Course not found or does not belong to this professor"},
                status=404
            )

        #  Extract exam data and nested questions
        exam_data = request.data
        questions_data = exam_data.pop("assessment_questions", [])

        exam_serializer = ExamSerializer(data=exam_data)
        if not exam_serializer.is_valid():
            print("Exam serializer errors:", exam_serializer.errors)
            return Response(exam_serializer.errors, status=400)

        exam = exam_serializer.save(course=course)

        #  Create associated questions
        created_questions = []
        for q in questions_data:
            q["exam"] = exam.id
            question_serializer = AssessmentQuestionSerializer(data=q)
            if question_serializer.is_valid():
                question_serializer.save(exam=exam)
                created_questions.append(question_serializer.data)
            else:
                # rollback exam if invalid question
                exam.delete()
                return Response(
                    {"error": "Invalid question data", "details": question_serializer.errors},
                    status=400
                )

        # Return combined response
        response_data = ExamSerializer(exam).data
        response_data["assessment_questions"] = created_questions
        create_and_save_grader(exam=exam, course_id=course_id)
        return Response(response_data, status=201)


class ProfessorCoursesView(APIView):
    """
    Returns all courses for the authenticated professor.
    Requires header: Authorization: Token <token_value>
    """

    def get(self, request):
        #  Extract token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response(
                {"error": "Missing or invalid Authorization header"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        #  Only professors allowed
        if token_obj.user_type != "professor":
            return Response(
                {"error": "Only professors can view their courses"},
                status=status.HTTP_403_FORBIDDEN
            )

        #  Fetch professor
        try:
            professor = Professor.objects.get(id=token_obj.user_id)
        except Professor.DoesNotExist:
            return Response(
                {"error": "Professor not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        #  Fetch all courses for that professor
        courses = Course.objects.filter(professor=professor).order_by('-id')

        #  Serialize and return
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CreateCourseView(APIView):

    def post(self, request):
        #  Extract and validate token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response(
                {"error": "Missing or invalid Authorization header"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Only professors can create courses
        if token_obj.user_type != "professor":
            return Response(
                {"error": "Only professors can create courses"},
                status=status.HTTP_403_FORBIDDEN
            )

        #  Fetch professor record
        try:
            professor = Professor.objects.get(id=token_obj.user_id)
        except Professor.DoesNotExist:
            return Response(
                {"error": "Professor not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        #  Validate and save course
        serializer = CourseSerializer(data=request.data)
        if serializer.is_valid():
            course = serializer.save(professor=professor)
            return Response(
                {
                    "message": "Course created successfully",
                    "course": CourseSerializer(course).data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from .serializers import (
    StudentSerializer,
    ProfessorSerializer,
    CourseSerializer,
    ExamSerializer,
    AssessmentQuestionSerializer,
)

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

class ProfessorViewSet(viewsets.ModelViewSet):
    queryset = Professor.objects.all()
    serializer_class = ProfessorSerializer

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer

class AssessmentQuestionViewSet(viewsets.ModelViewSet):
    queryset = AssessmentQuestion.objects.all()
    serializer_class = AssessmentQuestionSerializer



class LoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": "Email and password required."}, status=400)

        # Check professor
        try:
            prof = Professor.objects.get(email=email)
            if check_password(password, prof.password):
                token = UserToken.objects.create(
                    token=str(uuid.uuid4()),
                    user_type="professor",
                    user_id=prof.id
                )
                return Response({
                    "token": token.token,
                    "user_type": "professor",
                    "id": prof.id,
                    "full_name": prof.full_name,
                    "email": prof.email,
                    "institution": prof.institution_name
                }, status=200)
        except Professor.DoesNotExist:
            pass

        # Check student
        try:
            stu = Student.objects.get(email=email)
            if check_password(password, stu.password):
                token = UserToken.objects.create(
                    token=str(uuid.uuid4()),
                    user_type="student",
                    user_id=stu.id
                )
                return Response({
                    "token": token.token,
                    "user_type": "student",
                    "id": stu.id,
                    "full_name": stu.full_name,
                    "email": stu.email,
                    "institution": stu.student_id
                }, status=200)
        except Student.DoesNotExist:
            pass

        return Response({"error": "Invalid credentials"}, status=401)
    

class SaveGradesView(APIView):
    """
    Persist grading results for a student's exam.
    Expected JSON:
    {
      "overall_received_score": 42.0,
      "overall_feedback": "Solid work.",
      "answers": [
        {"question_id": 11, "received_weight": 9.0, "feedback": "Good.", "is_graded": true},
        {"question_id": 12, "received_weight": 8.5, "feedback": "Tidy.", "is_graded": true}
      ]
    }
    """

    def post(self, request, course_id, exam_id, student_id):
        #  Auth: professor only
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)
        token_value = auth_header.split(" ")[1]
        try:
            token = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)
        if token.user_type != "professor":
            return Response({"error": "Only professors can save grades"}, status=403)

        # Ownership & entities
        try:
            professor = Professor.objects.get(id=token.user_id)
        except Professor.DoesNotExist:
            return Response({"error": "Professor not found"}, status=404)

        try:
            course = Course.objects.get(id=course_id, professor=professor)
        except Course.DoesNotExist:
            return Response({"error": "Course not found or unauthorized"}, status=404)

        try:
            exam = Exam.objects.get(id=exam_id, course=course)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found for this course"}, status=404)

        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        try:
            submission = StudentExamSubmission.objects.get(student=student, exam=exam)
        except StudentExamSubmission.DoesNotExist:
            return Response({"error": "Submission not found for this student/exam"}, status=404)

        # Validate payload
        serializer = SaveGradeInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        data = serializer.validated_data

        #Save atomically
        try:
            with transaction.atomic():
                # Update per-question grades
                # Ensure the question belongs to this exam
                valid_qids = set(
                    AssessmentQuestion.objects.filter(exam=exam).values_list("id", flat=True)
                )

                updated = 0
                for ans in data["answers"]:
                    qid = ans["question_id"]
                    if qid not in valid_qids:
                        return Response(
                            {"error": f"question_id {qid} does not belong to this exam"},
                            status=400
                        )

                    qa, _ = StudentAnswer.objects.get_or_create(
                        submission=submission,
                        question_id=qid,
                        defaults={
                            "answer_text": "",  # keep existing if already created elsewhere
                        }
                    )
                    qa.received_weight = ans["received_weight"]
                    qa.feedback = ans.get("feedback", "") or ""
                    qa.is_graded = ans.get("is_graded", True)
                    qa.save()
                    updated += 1

                # Update overall scores/feedback
                submission.overall_received_score = data["overall_received_score"]
                submission.overall_feedback = data.get("overall_feedback", "") or ""
                submission.save()

            return Response(
                {
                    "message": "Grades saved successfully",
                    "submission_id": submission.id,
                    "answers_updated": updated,
                    "overall_received_score": submission.overall_received_score,
                    "overall_feedback": submission.overall_feedback or ""
                },
                status=200
            )
        except Exception as e:
            return Response({"error": f"Failed to save grades: {str(e)}"}, status=500)
        

class ProfessorStudentExamGradesView(APIView):
    """
    GET /api/professor/exams/<exam_id>/students/<student_id>/grades/

    Returns graded data for ONE student in ONE exam:
    - overall_received_score, overall_feedback
    - per-question answer_text, received_weight, feedback, is_graded (+ question metadata)
    Reads directly from StudentExamSubmission + StudentAnswer.
    """

    def get(self, request, exam_id, student_id):
        # Auth: professor only
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)
        token_value = auth.split(" ", 1)[1]

        try:
            token = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)
        if token.user_type != "professor":
            return Response({"error": "Only professors can access this endpoint"}, status=403)

        # Scope exam to this professor
        try:
            professor = Professor.objects.get(id=token.user_id)
        except Professor.DoesNotExist:
            return Response({"error": "Professor not found"}, status=404)

        try:
            exam = Exam.objects.select_related("course").get(id=exam_id, course__professor=professor)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found or unauthorized"}, status=404)

        # Resolve student + submission; prefetch all answers with their question
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        try:
            submission = (
                StudentExamSubmission.objects
                .select_related("exam__course", "student")
                .prefetch_related(
                    Prefetch(
                        "answers",
                        queryset=StudentAnswer.objects.select_related("question").only(
                            "id", "submission_id", "question_id",
                            "answer_text", "is_graded", "received_weight", "feedback",
                            "question__question", "question__question_weight", "question__min_words"
                        )
                    )
                )
                .get(exam=exam, student=student)
            )
        except StudentExamSubmission.DoesNotExist:
            return Response({"error": "Submission not found for this student/exam"}, status=404)

        answers_out = []
        for a in submission.answers.all().order_by("question_id", "id"):
            q = a.question  # may be None only if data inconsistent
            answers_out.append({
                "question_id": a.question_id,
                "question_text": getattr(q, "question", ""),
                "question_weight": float(getattr(q, "question_weight", 0.0)),
                "min_words": int(getattr(q, "min_words", 0) or 0),
                "answer_text": a.answer_text,
                "is_graded": bool(a.is_graded),
                "received_weight": float(a.received_weight),
                "feedback": a.feedback or ""
            })

        return Response({
            "exam_id": exam.id,
            "exam_name": exam.exam_name,
            "course_id": exam.course.id,
            "course_name": exam.course.course_name,
            "student_id": student.id,
            "student_name": student.full_name,
            "student_email": student.email,
            "submitted_at": submission.submitted_at,
            "overall_received_score": float(submission.overall_received_score),
            "overall_feedback": submission.overall_feedback or "",
            "answers_count": len(answers_out),
            "answers": answers_out
        }, status=200)

class StudentAllGradesView(APIView):
    """
    GET /api/student/exams/grades/
    Returns all exams for the authenticated student with overall and per-question grades/feedback.
    Student-only endpoint (UserToken.user_type == 'student').
    Optional query params:
      - only_graded=true|false  (default false) -> when true, show only submissions that have any graded answers or nonzero overall score.
    """

    def get(self, request):
        # 1) Auth: student only
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)
        token_value = auth_header.split(" ")[1]
        try:
            token = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)
        if token.user_type != "student":
            return Response({"error": "Only students can access this endpoint"}, status=403)

        # 2) Get student
        try:
            student = Student.objects.get(id=token.user_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        # 3) Fetch all submissions for this student (with exam, course, answers, questions)
        submissions_qs = (
            StudentExamSubmission.objects
            .filter(student=student)
            .select_related("exam", "exam__course")
            .prefetch_related(
                Prefetch("answers", queryset=StudentAnswer.objects.select_related("question"))
            )
            .order_by("-submitted_at")
        )

        # Optional filter: only_graded=true
        only_graded = str(request.query_params.get("only_graded", "false")).lower() == "true"
        if only_graded:
            submissions_qs = [s for s in submissions_qs
                              if (s.overall_received_score and s.overall_received_score > 0)
                              or any(a.is_graded for a in s.answers.all())]

        if not submissions_qs:
            return Response({"exams": []}, status=200)

        # 4) Build response
        payload = []
        for sub in submissions_qs:
            exam = sub.exam
            course = exam.course
            answers = sub.answers.all()

            # Map per question
            questions = AssessmentQuestion.objects.filter(exam=exam).only(
                "id", "question", "question_weight", "min_words"
            )
            q_map = {q.id: q for q in questions}

            per_question = []
            graded_count = 0
            for ans in answers:
                q = q_map.get(ans.question_id)
                if not q:
                    # stale or deleted question; skip safely
                    continue
                per_question.append({
                    "question_id": q.id,
                    "question_text": q.question,
                    "question_weight": q.question_weight,
                    "min_words": q.min_words,
                    "answer_text": ans.answer_text,
                    "received_weight": ans.received_weight,
                    "feedback": ans.feedback or "",
                    "is_graded": bool(ans.is_graded),
                })
                if ans.is_graded:
                    graded_count += 1

            payload.append({
                "course_id": course.id,
                "course_name": course.course_name,
                "course_code": course.course_code,
                "exam_id": exam.id,
                "exam_name": exam.exam_name,
                "submitted_at": sub.submitted_at,
                "overall_received_score": sub.overall_received_score,
                "overall_feedback": sub.overall_feedback or "",
                "questions_count": questions.count(),
                "graded_answers_count": graded_count,
                "answers": per_question
            })

        return Response({"exams": payload}, status=200)
    

class DeleteExamView(APIView):
    """
    Allows a professor to delete an exam and everything related to it:
    - AssessmentQuestion rows for that exam
    - StudentExamSubmission rows for that exam
    - StudentAnswer rows (via CASCADE from submission)
    - Any other FK with on_delete=CASCADE pointing to Exam
    """

    @transaction.atomic
    def delete(self, request, course_id, exam_id):
        # Auth: must be professor
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        if token_obj.user_type != "professor":
            return Response({"error": "Only professors can delete exams"}, status=403)

        # Verify professor and course ownership
        try:
            professor = Professor.objects.get(id=token_obj.user_id)
        except Professor.DoesNotExist:
            return Response({"error": "Professor not found"}, status=404)

        try:
            course = Course.objects.get(id=course_id, professor=professor)
        except Course.DoesNotExist:
            return Response({"error": "Course not found or not owned by professor"}, status=404)

        # Get exam
        try:
            exam = Exam.objects.get(id=exam_id, course=course)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found for this course"}, status=404)

        exam_name = exam.exam_name

        # Delete exam + cascades
        # This will delete:
        # - AssessmentQuestion(exam=exam)
        # - StudentExamSubmission(exam=exam)
        # - StudentAnswer(submission in deleted submissions)
        exam.delete()

        return Response(
            {
                "message": "Exam and all related data deleted successfully",
                "exam_id": exam_id,
                "exam_name": exam_name,
                "course_id": course.id,
                "course_name": course.course_name,
            },
            status=200,
        )
    

class DeleteCourseView(APIView):
    """
    DELETE /api/courses/<course_id>/delete-course/
    Deletes a course and ALL related data:
      - Exams
      - StudentExamSubmission + StudentAnswer (via CASCADE)
      - Enrollments (via CASCADE)
      - CourseNotes + files
      - DocumentChunks (via CASCADE)
    Only the owning professor can perform this.
    """

    @transaction.atomic
    def delete(self, request, course_id):
        # 1) Auth: professor only
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            return Response({"error": "Missing or invalid Authorization header"}, status=401)

        token_value = auth_header.split(" ")[1]
        try:
            token_obj = UserToken.objects.get(token=token_value)
        except UserToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=401)

        if token_obj.user_type != "professor":
            return Response({"error": "Only professors can delete courses"}, status=403)

        # 2) Get professor and course
        try:
            professor = Professor.objects.get(id=token_obj.user_id)
        except Professor.DoesNotExist:
            return Response({"error": "Professor not found"}, status=404)

        try:
            course = Course.objects.get(id=course_id, professor=professor)
        except Course.DoesNotExist:
            return Response({"error": "Course not found or unauthorized"}, status=404)

        # 3) Pre-delete cleanup

        # 3a) Delete any grader files if you're using exam_<id>_graders.pkl pattern
        exams = list(course.exams.all())
        for exam in exams:
            grader_path = os.path.join("graders", f"exam_{exam.id}_graders.pkl")
            if os.path.exists(grader_path):
                try:
                    os.remove(grader_path)
                except OSError:
                    # If removing fails, still continue – DB will roll back on exception
                    pass

        # 3b) Delete note files on disk, then notes (DocumentChunk will CASCADE)
        notes = course.notes.all()
        for note in notes:
            if note.file and note.file.name:
                try:
                    if os.path.exists(note.file.path):
                        os.remove(note.file.path)
                except (ValueError, OSError):
                    # ValueError if file.path is invalid; OSError if removal fails.
                    pass

        # 3c) Delete submissions explicitly (answers CASCADE via FK)
        StudentExamSubmission.objects.filter(exam__in=exams).delete()

        # 4) Delete the course itself (will CASCADE: exams, enrollments, notes, chunks, etc.)
        course.delete()

        return Response(
            {
                "message": "Course and all related data deleted successfully",
                "course_id": course_id,
            },
            status=200,
        )