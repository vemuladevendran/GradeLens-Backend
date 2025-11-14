
from agno.agent import Agent
from agno.models.anthropic import Claude
from dotenv import load_dotenv
import os
from agno.tools.reasoning import ReasoningTools
import json



BASEDIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASEDIR, '.env'))

class Grader:

    def create_grader_agent(self):
        return Agent(
    model=Claude(
        api_key=os.getenv('ANTHROPIC_API_KEY'),
        id=os.getenv('ANTHROPIC_MODEL'),
        max_tokens=int(os.getenv('ANTHROPIC_MAX_TOKENS')),
        temperature=float(os.getenv('ANTHROPIC_TEMPERATURE')),
        top_p=float(os.getenv('ANTHROPIC_TOP_P'))
    ),
    instructions=["You are a grader and you will be grading a student's answer.",
                  "You will be provided with the rubrics for grading, context about the question and actual question",
                  f"Here are the Rubrics:\n{self.rubrics}",
                  f"Here is the question:{self.question}",
                  f"Here is the context: {self.context}",
                  f"The student's answer should be of minimum {self.minimum_word_count} words.",
                  "Score each criterion separately on a scale of 0 to 1.",
                  "Provide reasoning for each score.",
                  f"If you deduct marks, explain why you deducted. For Example: Deducted marks for: \n 1. Deducted marks for not giving an example.\n 2. Deducted marks for grammatical mistakes"
                  f"Compute the weighted final score out of {self.overall_score}.",
                  "If something is wrong or missing, explain why.",
                  self.leniency_description,
                  "OUTPUT FORMAT RULES: ",
                  "Return *only* a valid JSON object that starts with '{' and ends with '}'.",
                  "Do not include markdown formatting, triple quotes, or backticks.",
                  "Do not wrap the JSON inside any text, explanations, or comments.",
                  "Do not say anything like 'Here is the JSON:' — just output the JSON directly.",
                  f"The JSON must strictly follow the schema shown below: \n\n {self.output_format}"],

    tools=[
        ReasoningTools(add_instructions=True)
    ]
)

    
    def __init__(self, rubric_path, relevent_chunks, question, minimum_word_count, overall_score, strictness = 1):
        
        # self.rubrics = generateRubrics.rubric_generation(os.path.join(os.path.dirname(BASEDIR), rubric_path))
        self.rubrics = rubric_path

        self.question = question
        self.context = relevent_chunks
        self.minimum_word_count = minimum_word_count
        self.overall_score = overall_score
        self.strictness = strictness
        self.output_format = '''
        {{
        "criteria": [
            {{
            "criterion": "{'{criterion_name}'}",
            "weight": "{'{weight}'}",
            "feedback": "{'{feedback}'}",
            "score_received": "{'{score_received}'}",
            "result_calculation": "{'{score_received} * {weight}'}",
            "result": "{'{calculated_result}'}"
            }}
        ],
        "total_score": {{
            "calculation": "{'{calculated_result_1} + {calculated_result_2} + ... + {calculated_result_n}'}",
            "result": "{'{total_score}'}",
            "out_of": "{'{overall_score}'}",
        }},
        "overall_feedback": "{'{overall_feedback}'}"
        }}
        '''
        leniency_level = (1 - self.strictness)
        self.leniency_description = (
            f"The grader strictness level is set to {self.strictness}. "
            # f"This means you should be {'very forgiving' if leniency_level > 0.5 else 'moderately forgiving'} — "
            f"This means you should be {leniency_level * 100:.0f}% forgiving"
            # f"allow partial answers to still receive proportionally higher scores. "
            f"If the student meets roughly {self.strictness * 100:.0f}% of the rubric expectations, "
            f"they can still receive generous marks. "
            f"Apply this leniency consistently when scoring."
        )
        self.agent = self.create_grader_agent()

    def grade_answer(self, answer):
        if answer == "" or answer == None or answer.lower() == "not answered":
            word_count = 0
        else:
            word_count = len(answer.split())
        response_prompt = f'''Grade the following answer based on the provided rubrics, context, and question. 
        The word count of the answer is: {word_count}\n
        Answer:\n\n{answer}'''
        # self.agent.print_response(response_prompt, 
        #              stream=True,
        #              show_full_reasoning=True,
        #              stream_intermediate_steps=True)

        # return self.agent
        # return self.agent
        response_json = self.convert_to_json(self.agent.run(response_prompt))
        i = 0
        while(response_json == None):
            if(i>=5):
                print("Tried 5 times, yet it failed! Skipping question!")
                break
            response_json = self.convert_to_json(self.agent.run(response_prompt))
            print("Object was on not a valid json! Retrying...")
            i += 1

        return response_json


    def convert_to_json(self, response):
        try:
            return json.loads(response.get_content_as_string())
        except:
            return None