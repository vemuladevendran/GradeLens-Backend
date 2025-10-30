from rest_framework import serializers
from .models import *
from django.db import transaction

from .models import StudentExamSubmission, StudentAnswer
from rest_framework import serializers

class CourseNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseNote
        fields = ['id', 'note_name', 'file', 'uploaded_at']

class AssessmentQuestionPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentQuestion
        fields = ['id', 'question', 'question_weight', 'min_words']

class QuestionInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentQuestion
        fields = ["id", "question", "question_weight", "min_words"]


class StudentAnswerDetailSerializer(serializers.ModelSerializer):
    question = serializers.CharField(source="question.question")

    class Meta:
        model = StudentAnswer
        fields = ["question", "question_weight", "answer_text", "received_weight"]

    question_weight = serializers.FloatField(source="question.question_weight")


class StudentSubmissionDetailSerializer(serializers.Serializer):
    student_name = serializers.CharField()
    is_submitted = serializers.BooleanField()
    submission_timestamp = serializers.DateTimeField(allow_null=True)
    is_graded = serializers.BooleanField()
    answers = StudentAnswerDetailSerializer(many=True)

class ProfessorExamSummarySerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.course_name", read_only=True)
    num_questions = serializers.SerializerMethodField()
    num_enrolled_students = serializers.SerializerMethodField()
    num_students_submitted = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            "id",
            "exam_name",
            "course_name",
            "overall_score",
            "num_questions",
            "num_enrolled_students",
            "num_students_submitted",
        ]

    def get_num_questions(self, obj):
        return obj.assessment_questions.count()

    def get_num_enrolled_students(self, obj):
        return obj.course.enrollments.count()

    def get_num_students_submitted(self, obj):
        return obj.submissions.count()


class StudentExamListSerializer(serializers.ModelSerializer):
    is_taken = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            'id',
            'exam_name',
            'rubrics',
            'overall_score',
            'is_taken'
        ]

    def get_is_taken(self, obj):
        """
        Returns True if the current student has already submitted this exam.
        """
        student = self.context.get('student')
        if not student:
            return False
        return StudentExamSubmission.objects.filter(student=student, exam=obj).exists()
    
class StudentAnswerSerializer(serializers.ModelSerializer):
    question_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = StudentAnswer
        fields = ['question_id', 'answer_text']


class StudentExamSubmissionSerializer(serializers.ModelSerializer):
    answers = StudentAnswerSerializer(many=True, write_only=True)

    class Meta:
        model = StudentExamSubmission
        fields = ['id', 'exam', 'answers']

    def create(self, validated_data):
        answers_data = validated_data.pop('answers')
        submission = StudentExamSubmission.objects.create(**validated_data)
        for answer_data in answers_data:
            question_id = answer_data.pop('question_id')
            StudentAnswer.objects.create(submission=submission, question_id=question_id, **answer_data)
        return submission

class EnrolledCourseSerializer(serializers.ModelSerializer):
    professor_name = serializers.CharField(source="professor.full_name", read_only=True)
    institution_name = serializers.CharField(source="professor.institution_name", read_only=True)

    class Meta:
        model = Course
        fields = [
            'id',
            'course_name',
            'course_code',
            'course_description',
            'professor_name',
            'institution_name'
        ]

class AssessmentQuestionUpdateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = AssessmentQuestion
        fields = [
            'id',
            'question',
            'question_weight',
            'min_words'
        ]


class ExamUpdateSerializer(serializers.ModelSerializer):
    assessment_questions = AssessmentQuestionUpdateSerializer(many=True, required=False)

    class Meta:
        model = Exam
        fields = [
            'id',
            'exam_name',
            'rubrics',
            'overall_score',
            'assessment_questions'
        ]

    @transaction.atomic
    def update(self, instance, validated_data):
        # Extract nested questions
        questions_data = validated_data.pop('assessment_questions', None)

        # Update exam fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If no question updates, return now
        if questions_data is None:
            return instance

        existing_qs = {q.id: q for q in instance.assessment_questions.all()}
        updated_ids = []

        for q_data in questions_data:
            q_id = q_data.get('id')
            if q_id and q_id in existing_qs:
                # Update existing question
                question = existing_qs[q_id]
                question.question = q_data.get('question', question.question)
                question.question_weight = q_data.get('question_weight', question.question_weight)
                question.min_words = q_data.get('min_words', question.min_words)
                question.save()
                updated_ids.append(q_id)
            else:
                # Create new question
                AssessmentQuestion.objects.create(exam=instance, **q_data)

        # Delete removed questions (not in updated list)
        for old_id, old_q in existing_qs.items():
            if old_id not in updated_ids:
                old_q.delete()

        return instance

class AssessmentQuestionReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentQuestion
        fields = [
            'id', 'question', 'question_weight', 'min_words',
            'response', 'received_weight', 'feedback', 'is_graded'
        ]


class ExamReadSerializer(serializers.ModelSerializer):
    assessment_questions = AssessmentQuestionReadSerializer(many=True, read_only=True)

    class Meta:
        model = Exam
        fields = [
            'id',
            'exam_name',
            'rubrics',
            'overall_score',
            'received_score',
            'overall_feedback',
            'assessment_questions'
        ]

class AssessmentQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentQuestion
        fields = [
            'id',
            'question',
            'question_weight',
            'min_words',
            'response',
            'received_weight',
            'feedback',
            'is_graded'
        ]

class ExamSerializer(serializers.ModelSerializer):
    assessment_questions = AssessmentQuestionSerializer(many=True, required=False)
    course = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Exam
        fields = [
            'id',
            'exam_name',
            'rubrics',
            'overall_score',
            'received_score',
            'overall_feedback',
            'course',
            'assessment_questions'
        ]

    # override create so DRF never tries to validate course itself
    def create(self, validated_data):
        validated_data.pop('course', None)
        return super().create(validated_data)

class StudentSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = Student
        fields = ['id', 'full_name', 'email', 'student_id', 'password', 'confirm_password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        raw_password = validated_data.pop('password')
        student = Student(**validated_data)
        student.set_password(raw_password)
        student.save()
        return student


class ProfessorSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = Professor
        fields = ['id', 'full_name', 'email', 'institution_name', 'password', 'confirm_password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        raw_password = validated_data.pop('password')
        prof = Professor(**validated_data)
        prof.set_password(raw_password)
        prof.save()
        return prof


class AssessmentQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentQuestion
        fields = '__all__'


class ExamSerializer(serializers.ModelSerializer):
    assessment_questions = AssessmentQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Exam
        fields = '__all__'


class CourseSerializer(serializers.ModelSerializer):
    exams = ExamSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'course_name', 'course_code', 'course_description', 'exams']