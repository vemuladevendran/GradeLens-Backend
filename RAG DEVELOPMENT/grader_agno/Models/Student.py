from Exam import Exam

class Student:
    def __init__(self, 
                 name:str, 
                 id:int):
        
        self.name = name
        self.id = id
        self.exams = []
        self.enrolled_courses = []
    
    def add_exam(self,
                 exam:Exam):
        self.exams.append(exam)
        

    def get_exams(self):
        return self.exams