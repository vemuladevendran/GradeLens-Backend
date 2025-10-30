from .grader import Grader
from ..models import Exam
from ..models import AssessmentQuestion
from concurrent.futures import ThreadPoolExecutor, as_completed
import json


class ExecuteGrader:
    
    def __init__(self, 
                 rubrics: str,
                 retrived_chunks: dict,
                 assessments,
                 strictness = 1):
        
        self.rubrics_path = rubrics

        self.graders = {}
        for asmt in assessments:
            self.graders[asmt.question] = Grader(rubrics, 
                                                 retrived_chunks.get(asmt.question), 
                                                 asmt.question, 
                                                 asmt.min_words, 
                                                 asmt.question_weight,
                                                 strictness = strictness)


    # def grade_exams(self, answerdata):
    #     print("assessment", answerdata)
    #     for asmt in answerdata:
    #         grader = self.graders.get(asmt.get("question_text"))
    #         if grader == None:
    #             asmt["feedback"] = None
    #             continue
    #         print("response", asmt.get("answer_text"))
    #         feedback = grader.grade_answer(asmt.get("answer_text"))
    #         asmt["feedback"] = feedback
    #         print(feedback)

    #     return answerdata

    def grade_exams(self, answerdata):

        def process(asmt):
            grader = self.graders.get(asmt.get("question_text"))
            if grader is None:
                asmt["feedback"] = None
                return asmt

            feedback = grader.grade_answer(asmt.get("answer_text"))
            asmt["feedback"] = feedback
            return asmt

        # use up to min(10, len(answerdata)) threads to avoid overwhelming system
        with ThreadPoolExecutor(max_workers=min(10, len(answerdata))) as executor:
            futures = [executor.submit(process, asmt) for asmt in answerdata]
            results = [f.result() for f in as_completed(futures)]

        return results
