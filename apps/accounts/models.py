from django.db import models
from django.contrib.auth.hashers import make_password
import uuid
from django.db import models
from django.utils import timezone



class UserToken(models.Model):
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    user_type = models.CharField(max_length=20)  # 'professor' or 'student'
    user_id = models.PositiveIntegerField()      # reference to professor.id or student.id
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_type} - {self.token[:8]}..."

class Student(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    student_id = models.CharField(max_length=50, blank=True, null=True)
    password = models.CharField(max_length=255)

    def set_password(self, raw_password: str):
        self.password = make_password(raw_password)

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class Professor(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    institution_name = models.CharField(max_length=255)
    password = models.CharField(max_length=255)

    def set_password(self, raw_password: str):
        self.password = make_password(raw_password)

    def __str__(self):
        return f"{self.full_name} - {self.institution_name}"


class Course(models.Model):
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, related_name="courses")
    course_name = models.CharField(max_length=255)
    course_code = models.CharField(max_length=50)
    course_description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"


class Exam(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="exams")
    exam_name = models.CharField(max_length=255)
    rubrics = models.TextField(blank=True, null=True)
    overall_score = models.FloatField(default=0.0)
    received_score = models.FloatField(default=0.0)
    overall_feedback = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.exam_name} ({self.course.course_code})"



class AssessmentQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="assessment_questions")
    question = models.TextField()
    question_weight = models.FloatField()
    min_words = models.IntegerField()
    response = models.TextField(blank=True, null=True)
    received_weight = models.FloatField(default=0.0)
    feedback = models.TextField(blank=True, null=True)
    is_graded = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.question[:60]}..."
    

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student.full_name} → {self.course.course_name}"
    

class StudentExamSubmission(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="submissions")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="submissions")
    submitted_at = models.DateTimeField(auto_now_add=True)
    overall_received_score = models.FloatField(default=0.0)
    overall_feedback = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('student', 'exam')

    def __str__(self):
        return f"{self.student.full_name} → {self.exam.exam_name}"
    

class StudentAnswer(models.Model):
    submission = models.ForeignKey(StudentExamSubmission, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(AssessmentQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField()
    received_weight = models.FloatField(default=0.0)
    feedback = models.TextField(blank=True, null=True)
    is_graded = models.BooleanField(default=False)

    def __str__(self):
        return f"Answer by {self.submission.student.full_name} for {self.question.question[:50]}"
    


class CourseNote(models.Model):
    course = models.ForeignKey("Course", on_delete=models.CASCADE, related_name="notes")
    professor = models.ForeignKey("Professor", on_delete=models.CASCADE, related_name="uploaded_notes")
    note_name = models.CharField(max_length=255)
    file = models.FileField(upload_to="course_notes/")
    uploaded_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.note_name} ({self.course.course_name})"
    

class DocumentChunk(models.Model):
    note = models.ForeignKey("CourseNote", on_delete=models.CASCADE, related_name="chunks")
    chunk_text = models.TextField()
    embedding = models.BinaryField()  # store numpy vector as bytes
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chunk {self.id} for note {self.note.note_name}"

