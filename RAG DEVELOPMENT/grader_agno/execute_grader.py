from grader import Grader
from Models.Exam import Exam
from Models.AssessmentQuestion import AssessmentQuestion
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

class ExecuteGrader:
    
    def __init__(self, 
                 rubric_path: str, 
                 context_path: str, 
                 assessments: AssessmentQuestion,
                 strictness = 1):
        
        self.rubrics_path = rubric_path
        self.context_path = context_path

        self.graders = {}
        for asmt in assessments:
            self.graders[asmt.question] = Grader(rubric_path, 
                                                 context_path, 
                                                 asmt.question, 
                                                 asmt.min_words, 
                                                 asmt.question_weight,
                                                 strictness = strictness)


    # def grade_exams(self, exam: Exam):
    #     assessments = exam.get_assessment()
    #     for asmt in assessments:
    #         grader = self.graders.get(asmt.question)
    #         if grader == None:
    #             asmt.feedback = None
    #             continue
    #         asmt.feedback = grader.grade_answer(asmt.response)

    #     exam.set_assessment(assessments)
    #     return exam

    def grade_exams(self, exam: Exam):
        assessments = exam.get_assessment()
        results = []

        def grade_single(asmt):
            grader = self.graders.get(asmt.question)
            if grader is None:
                asmt.feedback = None
                return asmt
            asmt.set_feedback(grader.grade_answer(asmt.response))
            return asmt

        # Run grading in parallel threads
        with ThreadPoolExecutor(max_workers=min(8, len(assessments))) as executor:
            future_to_asmt = {executor.submit(grade_single, asmt): asmt for asmt in assessments}

            for future in as_completed(future_to_asmt):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    asmt = future_to_asmt[future]
                    print(f"Error grading question '{asmt.question}': {e}")
                    asmt.feedback = None
                    results.append(asmt)

        exam.set_assessment(results)
        return exam
