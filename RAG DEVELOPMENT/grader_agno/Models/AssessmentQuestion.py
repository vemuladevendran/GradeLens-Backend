class AssessmentQuestion:

    def __init__(self, question:str, question_weight:int, min_words:int = None):
        self.question = question
        self.question_weight = question_weight
        self.min_words = min_words
        self.response = None
        self.received_weight = 0
        self.feedback = None
        self.is_graded = False
        
    def set_feedback(self, feedback):
        self.received_weight = float(feedback["total_score"]["result"])
        self.is_graded = True
        output_text = ""

        for c in feedback["criteria"]:
            # Convert scores and weights to numeric values
            score_received = float(c["score_received"])
            weight = float(c["weight"])
            total = round(score_received * weight * 100, 2)  # e.g., 0.9 * 0.35 * 100 = 31.5
            out_of = int(weight * 100)                       # e.g., 0.35 * 100 = 35

            # Build formatted block
            block = (
                f"Criteria: {c['criterion']}\n\n"
                f"Feedback: {c['feedback']}\n\n"
                f"Score: {total}/{out_of}\n\n"
            )

            output_text += block

        self.feedback = output_text