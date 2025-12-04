
from agno.agent import Agent
from agno.models.anthropic import Claude
from dotenv import load_dotenv
import os
from generate_ruberics import GenerateRubrics
from get_context import get_relevant_chunks
from agno.tools.reasoning import ReasoningTools

generateRubrics = GenerateRubrics()

BASEDIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASEDIR, '.env'))


def create_grader_agent():
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
                f"Here are the Rubrics:\n{rubrics}",
                f"Here is the question:{question}",
                f"Here is the context: {context}",
                f"The student's answer should be of minimum {minimum_word_count} words.",
                "Score each criterion separately on a scale of 0 to 1.",
                "Provide reasoning for each score.",
                f"Compute the weighted final score out of {overall_score}.",
                "If something is wrong or missing, explain why.",
                f"The grading output strictly in JSON format as shown below:\n\n {output_format}"],

tools=[
    ReasoningTools(add_instructions=True)
]
)


def grade_answer(answer, agent):
    response_prompt = f'''Grade the following answer based on the provided rubrics, context, and question. 
    The word count of the answer is: {len(answer.split())}\n
    Answer:\n\n{answer}'''
    agent.print_response(response_prompt, 
                    stream=True,
                    show_full_reasoning=True,
                    stream_intermediate_steps=True)

 

rubrics = generateRubrics.rubric_generation(os.path.join(os.path.dirname(BASEDIR), "data/rubric.csv"))
question = "Why is land considered central to the religion and cultural identity of the Dakota people?"
context = get_relevant_chunks(os.path.join(os.path.dirname(BASEDIR), "data/Lecture Native American Cosmologies.pdf"), question)
minimum_word_count = 50
overall_score = 25
output_format = '''
{{
"criteria": [
    {{
    "criterion": "{'{criterion_name}'}",
    "weight": "{'{weight}'}",
    "feedback": "{'{feedback}'}",
    "score_received": "{'{score_received}'}"
    }}
],
"final_weighted_score_calculation": [
    {{
    "criterion": "{'{criterion_name}'}",
    "calculation": "{'{score_received} * {weight}'}",
    "result": "{'{calculation_result}'}"
    }}
],
"total_score": {{
    "calculation": "{'{score1} + {score2} + ... + {scoreN}'}",
    "result": "{'{total_score}'}"
}},
"final_score": {{
    "out_of": "{'{overall_score}'}",
    "score": "{'{final_score}'}"
}},
"overall_feedback": "{'{overall_feedback}'}"
}}
'''

agent = create_grader_agent()

answer = '''Land is central to the Dakota people’s religion and cultural identity because it represents the very foundation of their cosmology, memory, and way of life. For the Dakota, Mni Sota Makoce—“the land where the water reflects the sky”—is not just a physical space but the place of human origin and the center of the world. Their religion is inseparable from geography; the rivers, rocks, and landforms are all sacred markers that tell stories of their ancestors and spiritual connections. The land is where the earthly and spiritual realms meet, forming the axis of Dakota existence—what could be called their Prime Meridian of life and meaning.

Losing this land through deceitful treaties and forced relocation was not just a political or economic loss—it was a spiritual dismemberment. Being removed from sacred places disrupted rituals, ceremonies, and the ability to maintain ancestral connections, effectively breaking the link between religion, culture, and identity. For the Dakota, religion isn’t about belief or doctrine but about being in relationship with the land—a living entity that remembers stories, embodies sacred power, and connects generations through memory and ceremony.

Even today, reclaiming and protecting ancestral land remains a sacred act of remembrance and resistance. It restores not only physical space but also the collective spiritual identity of the Dakota people, affirming that “land is memory, and land remembers.”'''

grade_answer(answer, agent)