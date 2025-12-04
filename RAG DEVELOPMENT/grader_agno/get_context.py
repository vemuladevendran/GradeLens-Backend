import faiss
import numpy as np
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer

embedder = SentenceTransformer("all-MiniLM-L6-v2")

def load_pdf_text(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def chunk_text(text, chunk_size=550, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunks.append(" ".join(words[i:i+chunk_size]))
    return chunks

def create_faiss_index(chunks):
    embeddings = embedder.encode(chunks, convert_to_numpy=True)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings.astype("float32"))
    return index, embeddings

def get_relevant_chunks(pdf_path, query, k=3):
    text = load_pdf_text(pdf_path)
    chunks = chunk_text(text)
    index, embeddings = create_faiss_index(chunks)

    q_embedding = embedder.encode(query, convert_to_numpy=True)
        # retrieve relevant context
    D, I = index.search(np.array([q_embedding]).astype("float32"), k)
    retrieved_chunks = [chunks[i] for i in I[0]]

    return "\n\n".join(retrieved_chunks)