# GradeLens – AI-Powered Auto-Grading Platform

GradeLens is an end-to-end AI auto-grading system designed to help instructors evaluate student answers quickly, accurately, and consistently. It uses a powerful Retrieval-Augmented Generation (RAG) pipeline, LLMs, and a scalable FastAPI backend to grade student responses based on reference materials, rubrics, and course content.

The platform supports complete academic workflows—course creation, student management, assessment setup, note uploads, exam submissions, grading, feedback generation, and more—automated using AI and backed by robust SQL data models.

---

## 🚀 Key Features
- **AI-Driven Auto-Grading** using RAG, embeddings, and LLM reasoning  
- **PDF Ingestion + Chunking** for course materials  
- **Rubric-Based Evaluation** with customizable parameters  
- **Parallel Grading Engine** that evaluates multiple answers simultaneously  
- **Complete API Suite** for courses, students, assessments, submissions, and grading  
- **Secure Authentication + User Management**  
- **Full CRUD Support** for all major entities (courses, notes, exams, assessments, submissions)

---

## 🛠️ Technologies Used
- **Python** – core backend logic  
- **FastAPI** – REST API framework  
- **RAG (Retrieval-Augmented Generation)** – grading intelligence layer  
- **LLMs** – experimented with GPT, OpenAI models, LLaMA, and finally **Claude** (selected for best accuracy)  
- **PostgreSQL** – database  
- **SQL + Migrations** – Alembic for schema versioning  
- **Vector Search** – document embeddings for retrieval  
- **Parallel Processing** – multi-RAG inference for faster grading  
- **Auth + Token Management** – JWT/Auth workflows  

---

# 📘 Project Overview

GradeLens aims to automate grading by comparing student answers with instructor-provided materials and rubrics. The system ingests PDFs, converts them into embedding-based vector stores, retrieves relevant content, and evaluates student responses using LLMs combined with rubric rules.

This ensures:
- fast grading  
- unbiased scoring  
- detailed feedback  
- scalable performance with parallel grading  

---

# GradeLens — Grader Engine Development Journey

This document explains the full engineering evolution of the GradeLens AI Grader, from early prototypes to the final scalable architecture. Five different approaches were explored, evaluated, and refined. Only the fifth approach proved stable, consistent, and efficient enough for real-world use.  
At the end, this document also includes the Pi-Scorer model evaluation step that helped determine the best-performing LLM settings.

---

# 1. Approach 1 — Strictness Prompt Adder

<img src="RAG DEVELOPMENT\images\approach1.png" width="650"/>

### Idea
Inject strictness as plain text into the grader prompt alongside:
- Question
- Student Response
- Rubrics
- Retrieved Context

### Problems
- Strictness was not understood; the LLM gave inconsistent scoring.
- Lenient sometimes produced lower marks than moderate.
- Strictness text was too weak to control behavior.

### Verdict
Not reliable or consistent.

---

# 2. Approach 2 — Add Strictness Criteria to the Prompt

<img src="RAG DEVELOPMENT\images\approach2.png" width="650"/>

### Idea
Include detailed strictness rules, strictness value, and all grading inputs.

### Outcome
Slight improvement over Approach 1.

### Problems
- Still unstable between strictness levels.
- LLM did not reliably map rules into scoring behavior.

### Verdict
Better than Approach 1, but still unpredictable.

---

# 3. Approach 3 — Strictness-Based Rubrics Agent

<img src="RAG DEVELOPMENT\images\approach3.png" width="700"/>

### Idea
Split the system into:
- A Rubrics Agent that generates strictness-based rubrics.
- A Grader Agent that grades using those generated rubrics.

### Strengths
- Strict and lenient grading were more aligned.
- Moderate grading was reasonably stable.

### Problems
1. Very resource-heavy.
2. Fairness issue: new rubrics were generated for each student.
3. No guarantee the generated rubric quality was optimal.
4. Reusing generated rubrics still did not solve reliability problems.

### Verdict
Promising concept, but impractical for production.

---

# 4. Approach 4 — Multiple Dedicated Strictness Agents

<img src="RAG DEVELOPMENT\images\approach4.png" width="700"/>

### Idea
Create three separate agents:
- Lenient Grader
- Moderate Grader
- Strict Grader

Select agent based on input strictness.

### Outcome
More predictable than the previous approaches.

### Problems
- Repeated recomputation of context and prompts.
- Expensive for multi-question exams.
- Some variation persisted between strictness levels.

### Verdict
Reasonable isolation, but not scalable.

---

# 5. Approach 5 — Final Architecture (Working and Efficient)

<img src="RAG DEVELOPMENT\images\approach5.png" width="700"/>

### Core Idea
Pre-build a dedicated grader for each exam question, save it, and reuse it for all student submissions.

### How It Works
1. Professor creates the exam.
2. Grader Initializer creates one grader per question, containing:
   - Retrieved context chunks
   - Rubrics
   - Question text
   - Strictness logic
3. All graders are saved as a pickle file.
4. Parallel Executor loads the graders and grades each student answer concurrently.
5. The output is consistent JSON with score and feedback.

### Why This Works
- No recomputation of context or rubrics.
- Consistent strictness behavior.
- Same grader used for all students (fairness).
- Very fast for multi-question exams.
- Supports parallelization.
- Lower token usage after initialization.
- Reproducible and stable.

### Verdict
This is the final and production-ready architecture for GradeLens.

---

# Model Evaluation With Pi-Scorer (Finding the Best Settings)

To avoid guesswork, multiple model configurations were evaluated using Pi Labs’ Pi-Scorer, which scores the model across:
- Balanced Evaluation
- Constructive Feedback
- Content Recognition
- Logical Alignment
- Rubric Coverage
- Schema Compliance
- Prompt Fulfillment
- Professional Tone
- Note Grounding and Referencing
- Consistency
- Relevance Enforcement

Each trial used identical:
- Questions
- Rubrics
- Student responses
- Retrieved context

Only model parameters changed.

---

## Best Model Settings (Empirically Verified)

After several experiments, the best-performing configuration was:


### Reasons
- Temperature 0.7 provides balanced flexibility without hallucinations.
- Top_p 1.0 avoids collapsing into deterministic behavior.
- max_tokens 10000 is required due to the large grader prompt.
- Produced the most consistent strictness behavior.
- Achieved the highest overall Pi-Scorer performance.

---

## Sample Pi-Scorer Output


This configuration was the strongest across repeated runs.

---

# Final Summary

| Approach | Result |
|----------|--------|
| Approach 1 | Failed; strictness ignored |
| Approach 2 | Still inconsistent |
| Approach 3 | Too heavy; fairness issues |
| Approach 4 | Better but not scalable |
| Approach 5 | Final architecture; consistent and efficient |

Pi-Scorer was essential in selecting the optimal LLM configuration to ensure consistent and accurate grading behavior.

---




# 📅 Weekly Progress Timeline

Below is a detailed, documented progression of the project from initial setup to final implementation.

---

## 🟦 Week 1–2: Core RAG Development
- Set up basic FastAPI structure  
- Built the **RAG pipeline prototype**  
- Added PDF ingestion  
- Implemented text splitting + chunking  
- Stored chunks in PostgreSQL / vector DB  
- Implemented retrieval logic for matching student answers with reference content  
- Verified correctness using small test documents  

---

## 🟩 Week 3–4: Enhancing RAG and Experimenting with LLMs
- Added processing steps:  
  - improved chunking  
  - better text cleaning  
  - metadata tagging of chunks  
- Started testing grading prompts  
- Experimented with **multiple LLMs**:  
  - GPT  
  - OpenAI models  
  - LLaMA  
  - **Claude (Anthropic)**  
- Tested different:  
  - temperatures  
  - max tokens  
  - formatting styles  
  - grading templates  
- Conclusion: **Claude performed the best** in accuracy and response consistency  

---

## 🟨 Week 5–6: Adding Rubrics + Question Management
- Added rubric evaluation logic  
- Created API and schema for:  
  - questions  
  - answer keys  
  - rubric templates  
- Implemented strictness levels (multiple attempts)  
  - After 2–3 weeks of trials, strictness logic was unstable → **temporarily removed**  
- Standardized grading prompt format  
- Improved RAG context retrieval  

---

## 🟧 Week 7–8: Database + Migrations + Full Backend Structure
- Set up **Alembic migration scripts**  
- Created tables for:  
  - users  
  - courses  
  - notes  
  - assessments  
  - exams  
  - student submissions  
  - grades  
- Added CRUD APIs:  
  - user creation + authentication  
  - course creation, update, delete  
  - uploading and editing notes  
  - creating assessments and exams  
  - student registration  
  - submission endpoints  

---

## 🟥 Week 9–10: Full Integration + RAG + API Workflow
- Connected all backend APIs to RAG pipeline  
- Implemented grading flow:  
  - student submits exam  
  - backend retrieves correct content  
  - RAG evaluates each answer  
  - feedback + score returned  
  - grades stored in DB  
- Added endpoints for:  
  - editing submissions  
  - viewing grades  
  - updating course/assessment/exam details  
  - deleting notes  
- Fixed multiple bugs related to:  
  - chunking issues  
  - retrieval mismatches  
  - token limits  
  - database joins  

---

## 🟪 Week 11–12: High-Performance Parallel Grading Engine
- Designed a **parallel RAG system**  
- If a student submits 4 questions → system runs **4 RAG processes simultaneously**  
- Result:  
  - huge reduction in grading time  
  - more scalability for large exams  
- Added performance logging  
- Final end-to-end testing completed  

---

## 🟫 Current Status & Future Work  
### ✅ Completed  
- End-to-end grading pipeline  
- Complete REST API suite  
- Course/notes/exam workflow  
- Parallel grading  
- Cloud LLM integration  
- Migrations + stable DB schema  

### 🔄 In Progress / Planned  
- Re-implement strictness level (more refined version)  
- Additional rubric customization  
- Plagiarism detection module  
- Multi-model fallback system  

---

# ▶️ How It Works
1. Instructor uploads **PDF notes**  
2. System chunks + embeds the content  
3. Students answer exam questions  
4. For each answer, RAG retrieves relevant context  
5. LLM grades based on rubric + reference materials  
6. Parallel processing speeds up grading  
7. Grades + feedback stored in DB  

---

# 📬 Contributors
- **Devendran Vemula** – Backend, Frontend
- **Srinivasan Poonkundran** – RAG development, Backend APIs Integration
- **Tejasree Nimmagadda** – Document Preparation, Data Analysis


