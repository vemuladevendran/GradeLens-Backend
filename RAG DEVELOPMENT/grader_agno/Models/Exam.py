from Models.AssessmentQuestion import AssessmentQuestion
class Exam:

    def set_overall_score(self):
        score = 0
        for a in self.__assessment_questions:
            score += a.question_weight
        self.overall_score = score

    def set_received_score(self):
        score = 0
        for a in self.__assessment_questions:
            score += a.received_weight
        self.received_score = score

    def __init__(self, 
                 exam_id:int, 
                 exam_name:str, 
                 assessment_questions:list):
        
        self.exam_id = exam_id
        self.exams_name = exam_name
        self.__assessment_questions = assessment_questions
        self.set_overall_score()
        self.received_score = 0
        self.overall_feedback = None

    def set_assessment(self, assessment_questions:list):
        self.__assessment_questions = assessment_questions
        self.set_overall_score()
        self.set_received_score()

    def get_assessment(self):
        return self.__assessment_questions
    
    def get_all_questions(self):
        return [i.question for i in self.__assessment_questions]
