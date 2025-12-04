import faiss
import numpy as np
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import pandas as pd

from get_content_from_app_prop import read_properties
props = read_properties('application.properties')

embedder = SentenceTransformer("all-MiniLM-L6-v2")

class Grader():

    def __init__(self, llms):
        self.llms = llms

    def load_pdf_text(self, pdf_path):
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

    def chunk_text(self, text, chunk_size=550, overlap=50):
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunks.append(" ".join(words[i:i+chunk_size]))
        return chunks

    def create_faiss_index(self, chunks):
        embeddings = embedder.encode(chunks, convert_to_numpy=True)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings.astype("float32"))
        return index, embeddings

    def rubric_generation(self, rubric_file_csv):
        rubric = pd.read_csv(rubric_file_csv)

        criterion = rubric["Criterion"].unique().tolist()
        levels = rubric["Level"].unique().tolist()
        
        rubric_prompt = ""

        for c in criterion:
            weight = rubric[rubric["Criterion"]==c]["Weight"].values[0]
            rubric_prompt += f"- Criterion: {c} (Weight: {weight})"
            for l in levels:
                rubric[(rubric["Criterion"] == c) & (rubric["Level"] == l)]["Description"].values
                rubric_prompt += f"\n  - Level => {l}: {rubric[(rubric["Criterion"] == c) & (rubric["Level"] == l)]['Description'].values[0]}"
            rubric_prompt += "\n\n"

        return rubric_prompt

    def evaluate_with_rubric(self, 
                            question, 
                            student_answer, 
                            chunks, index, 
                            rubric_path,
                            minimum_word_requirement, 
                            overall_score,
                            llm, 
                            k=3):


        q_embedding = embedder.encode(question, convert_to_numpy=True)

        # retrieve relevant context
        D, I = index.search(np.array([q_embedding]).astype("float32"), k)
        retrieved_chunks = [chunks[i] for i in I[0]]

        context = "\n\n".join(retrieved_chunks)

        # build rubric text
        rubric = self.rubric_generation(rubric_path)

        prompt = f"""
    You are grading a student's answer using the following rubric:

    Rubric:
    {rubric}

    Minimum word requirement for the answer: {minimum_word_requirement} words.

    Context from notes:
    {context}

    Question: {question}
    Student Answer: {student_answer}

    Student's Answer Length: {len(student_answer.split())} words.

    Instructions:
    - Score each criterion separately on a scale of 0 to 1.
    - Provide reasoning for each score.
    - Compute the weighted final score out of {overall_score}.
    - If something is wrong or missing, explain why.

    I want you to give the output in a JSON format only. I want you to follow the following template strictly:

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
    """
        if llm == "gpt":
            return context, prompt, self.llms.autograder_openai(prompt)
        if llm == "claude":
            return  context, prompt, self.llms.autograder_anthropic(prompt)
        if llm == "ollama":
            return  context, prompt, self.llms.autograder_llama(prompt)
    
    def execute_grader(self, 
                       question, 
                       student_response,
                       llm="gpt",
                       minimum_word_requirement=50,
                       overall_score=100,
                       context_path="data/Lecture Native American Cosmologies.pdf", 
                       rubric_path="data/rubric.csv"):
        pdf_path = context_path
        text = self.load_pdf_text(pdf_path)
        chunks = self.chunk_text(text)
        index, embeddings = self.create_faiss_index(chunks)
        return self.evaluate_with_rubric(question, 
                                         student_response, 
                                         chunks, 
                                         index, 
                                         rubric_path, 
                                         minimum_word_requirement, 
                                         overall_score, llm)
