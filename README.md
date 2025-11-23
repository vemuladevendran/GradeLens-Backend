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

