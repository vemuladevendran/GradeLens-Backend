from django.urls import path, include
from .views import *

from rest_framework.routers import DefaultRouter
from . import views

from .views import (
    EnrollCourseView,
    StudentEnrolledCoursesView,
)

router = DefaultRouter()
router.register(r'students', views.StudentViewSet)
router.register(r'professors', views.ProfessorViewSet)
router.register(r'courses', views.CourseViewSet)
router.register(r'exams', views.ExamViewSet)
router.register(r'questions', views.AssessmentQuestionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login'),  
    path('create-course/', CreateCourseView.as_view(), name='create-course'),

    path('get-courses/', ProfessorCoursesView.as_view(), name='professor-courses'),
    path('courses/<int:course_id>/create-exam/', CreateExamView.as_view(), name='create-exam'),
    path('courses/<int:course_id>/exams/', GetCourseExamsView.as_view(), name='get-course-exams'),
    path('courses/<int:course_id>/exams/<int:exam_id>/edit/', EditExamView.as_view(), name='edit-exam'),
    path('courses/<int:course_id>/enroll/', EnrollCourseView.as_view(), name='enroll-course'),
    path('courses/<int:course_id>/unenroll/', UnenrollCourseView.as_view(), name='unenroll-course'),
    path('courses/<int:course_id>/exams/<int:exam_id>/take/', TakeExamView.as_view(), name='take-exam'),
    path('courses/<int:course_id>/exams/<int:exam_id>/submit/', SubmitExamView.as_view(), name='submit-exam'),
    path('courses/<int:course_id>/upload-note/', UploadCourseNoteView.as_view(), name='upload-course-note'),
    path('courses/<int:course_id>/notes/', GetCourseNotesView.as_view(), name='get-course-notes'),
    path('courses/<int:course_id>/exams/<int:exam_id>/students/<int:student_id>/grade/', StudentExamAnswersView.as_view(), name='student-exam-answers'),
    path('courses/<int:course_id>/exams/<int:exam_id>/students/<int:student_id>/save-grades/', SaveGradesView.as_view(), name='save-grades'),
    path('courses/<int:course_id>/exams/<int:exam_id>/students/<int:student_id>/update-grades/',UpdateSubmissionView.as_view(),name='update-submission'),
    path('courses/<int:course_id>/exams/<int:exam_id>/delete/',DeleteExamView.as_view(),name='delete-exam'),
    path('courses/<int:course_id>/delete-course/',DeleteCourseView.as_view(),name='delete-course'),

    path('student/enrolled-courses/', StudentEnrolledCoursesView.as_view(), name='student-enrolled-courses'),
    path('student/courses/<int:course_id>/exams/', StudentGetCourseExamsView.as_view(), name='student-get-course-exams'),
    path('student/exams/grades/', StudentAllGradesView.as_view(), name='student-all-grades'),

    path('professor/exams/', ProfessorAllExamsView.as_view(), name='professor-all-exams'),
    path('professor/exams/<int:exam_id>/submissions/', ProfessorExamSubmissionsView.as_view(), name='professor-exam-submissions'),
    path("professor/exams/<int:exam_id>/students/<int:student_id>/grades/", ProfessorStudentExamGradesView.as_view(),name="professor-student-exam-grades"),

    path('notes/<int:note_id>/delete/', DeleteCourseNoteView.as_view(), name='delete-course-note'),
]
