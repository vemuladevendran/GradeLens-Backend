from agno.agent import Agent
from agno.models.anthropic import Claude
from dotenv import load_dotenv
import os
import json
from agno.tools.reasoning import ReasoningTools

BASEDIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASEDIR, '.env'))

class FeedbackAgent:
    def __init__(self):
        self.agent = self._create_agent()

    def _create_agent(self):
        return Agent(
            model=Claude(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                id=os.getenv("ANTHROPIC_MODEL"),
                max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS")),
                temperature=float(os.getenv("ANTHROPIC_TEMPERATURE")),
                top_p=float(os.getenv("ANTHROPIC_TOP_P")),
            ),
            instructions=[
                "You are a meta-grader who reviews feedback from multiple graded questions.",
                "Each question’s feedback JSON includes the rubric evaluations, total scores, and per-question comments.",
                "Your job is to summarize patterns across all feedback:",
                "- Identify common strengths (themes the student did well on).",
                "- Identify recurring weaknesses or areas of improvement.",
                "- Suggest 2–3 specific, actionable ways the student can improve future answers.",
                "Keep tone professional, constructive, and clear.",
                "Respond strictly in the following JSON format:\n\n"
                """{
                    "overall_feedback": "A short paragraph summarizing general performance.",
                    "key_strengths": ["point 1", "point 2", ...],
                    "improvement_areas": ["point 1", "point 2", ...]
                }"""
            ],
            tools=[ReasoningTools(add_instructions=True)]
        )

    def generate_overall_feedback(self, graded_results_json):
        
        if isinstance(graded_results_json, list):
            formatted_input = json.dumps(graded_results_json, indent=2)
        elif isinstance(graded_results_json, dict):
            formatted_input = json.dumps([graded_results_json], indent=2)
        else:
            raise TypeError("graded_results_json must be list or dict")

        prompt = f"""
        Review the following graded results for multiple questions and produce an overall evaluation:

        {formatted_input}
        """

        response = self.agent.run(prompt)
        try:
            return json.loads(response.get_content_as_string())
        except Exception:
            raise ValueError("FeedbackAgent: model response was not valid JSON.")
