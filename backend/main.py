import os
import json
import sys
from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from groq import Groq
import chromadb
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="PlasmaScribe API (Groq)", description="Backend API for Bilingual Transcript Search and Chat RAG using Groq")

# Enable CORS for the frontend Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for models and DB
embedding_model = None
chroma_client = None
collection = None
groq_client = None
transcript_data = []

# Data paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BILINGUAL_PATH = os.path.join(BASE_DIR, "transcript_bilingual.json")
CHROMA_DB_PATH = os.path.join(BASE_DIR, "chroma_db")

def format_timestamp(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

@app.on_event("startup")
def startup_event():
    global embedding_model, chroma_client, collection, groq_client, transcript_data
    
    # 1. Load bilingual transcript JSON
    if not os.path.exists(BILINGUAL_PATH):
        print(f"Bilingual transcript not found at: {BILINGUAL_PATH}. Please generate it first.")
    else:
        with open(BILINGUAL_PATH, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
            
    # 2. Initialize Sentence-Transformer
    print("Loading Sentence-Transformer (all-MiniLM-L6-v2) for API query encoding...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # 3. Initialize ChromaDB
    print("Connecting to ChromaDB...")
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    try:
        collection = chroma_client.get_collection(name="transcript_segments")
    except Exception as e:
        print(f"Could not load ChromaDB collection: {e}. Run build_index.py first.")
        
    # 4. Initialize Groq Client
    groq_client = Groq()
    print("Startup complete. API is ready.")

# API Models
class SearchQuery(BaseModel):
    query: str
    limit: Optional[int] = 5

class ChatMessage(BaseModel):
    role: str # 'user' or 'model' / 'assistant'
    content: str

class ChatQuery(BaseModel):
    query: str
    history: Optional[List[ChatMessage]] = []

@app.get("/transcript")
def get_transcript():
    """Retrieve the full bilingual transcript."""
    if not transcript_data:
        raise HTTPException(status_code=404, detail="Bilingual transcript not loaded.")
    return transcript_data

@app.post("/search")
def search_transcript(payload: SearchQuery):
    """Perform a semantic search across the transcript segments."""
    if not collection or not embedding_model:
        raise HTTPException(status_code=500, detail="Search engine or index is not initialized.")
        
    try:
        # Generate query embedding
        query_embedding = embedding_model.encode(payload.query).tolist()
        
        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=payload.limit
        )
        
        # Format results
        formatted_results = []
        if results and results["metadatas"] and len(results["metadatas"]) > 0:
            for idx, metadata in enumerate(results["metadatas"][0]):
                distance = results["distances"][0][idx] if results["distances"] else 0
                similarity = 1.0 / (1.0 + distance)
                
                formatted_results.append({
                    "id": metadata["id"],
                    "start": metadata["start"],
                    "duration": metadata["duration"],
                    "timestamp": format_timestamp(metadata["start"]),
                    "english": metadata["english"],
                    "indonesian": metadata["indonesian"],
                    "similarity": similarity
                })
        
        return formatted_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/chat")
def chat_rag(payload: ChatQuery):
    """Chat with the video transcript using RAG."""
    if not collection or not embedding_model or not groq_client:
        raise HTTPException(status_code=500, detail="RAG system components are not initialized.")
        
    try:
        # 1. Embed query and search ChromaDB for context
        query_embedding = embedding_model.encode(payload.query).tolist()
        search_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=6
        )
        
        # 2. Extract and format context segments
        context_parts = []
        source_segments = []
        
        if search_results and search_results["metadatas"] and len(search_results["metadatas"]) > 0:
            sorted_metadata = sorted(search_results["metadatas"][0], key=lambda x: x["id"])
            
            for metadata in sorted_metadata:
                timestamp_str = format_timestamp(metadata["start"])
                context_parts.append(
                    f"[{timestamp_str}] (Start: {metadata['start']}s)\n"
                    f"English: {metadata['english']}\n"
                    f"Indonesian: {metadata['indonesian']}\n"
                )
                source_segments.append({
                    "id": metadata["id"],
                    "start": metadata["start"],
                    "timestamp": timestamp_str,
                    "english": metadata["english"],
                    "indonesian": metadata["indonesian"]
                })
                
        context_text = "\n---\n".join(context_parts)
        
        # 3. Formulate prompt for Groq
        system_instruction = f"""Anda adalah 'PlasmaScribe AI Assistant', seorang ahli fisika plasma. 
Tugas Anda adalah menjawab pertanyaan pengguna mengenai isi video presentasi Prof. Nuno Loureiro tentang rekoneksi magnetik.

Anda HARUS menggunakan transkrip video berikut sebagai satu-satunya sumber kebenaran (source of truth) Anda:
{context_text}

Aturan Penting:
1. Jawablah dalam Bahasa Indonesia yang ramah, informatif, dan jelas.
2. Setiap kali Anda merujuk ke fakta atau kutipan dari video, Anda wajib menyertakan tombol timestamp dalam format markdown `[MM:SS]` (misal: `[12:34]`) yang menunjuk ke detik mulai segmen tersebut. Ini sangat krusial agar pengguna bisa mengklik dan memutar video di detik tersebut!
3. Jika pertanyaan pengguna tidak dapat dijawab berdasarkan informasi transkrip yang diberikan, katakan secara jujur dan sopan bahwa informasi tersebut tidak dibahas di video ini. Jangan mengarang informasi di luar transkrip.
4. Gunakan list markdown, cetak tebal (bold), atau tabel jika membantu menstrukturkan penjelasan ilmiah Anda.
"""

        # Compile chat history for Groq (expects 'user' and 'assistant')
        messages = [
            {"role": "system", "content": system_instruction}
        ]
        
        for msg in payload.history:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})
            
        # Add the current user query
        messages.append({"role": "user", "content": payload.query})
        
        # Generate answer from Groq
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        
        return {
            "answer": answer,
            "sources": source_segments
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG Chat failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
