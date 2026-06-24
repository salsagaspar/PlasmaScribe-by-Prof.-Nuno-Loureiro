import os
import json
import sys
import uuid
import re
import time
from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
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
doc_collection = None
groq_client = None
transcript_data = []

# Data paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BILINGUAL_PATH = os.path.join(BASE_DIR, "transcript_bilingual.json")
CHROMA_DB_PATH = os.path.join(BASE_DIR, "chroma_db")
DOCUMENTS_REGISTRY_PATH = os.path.join(BASE_DIR, "uploaded_documents.json")

def format_timestamp(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

@app.on_event("startup")
def startup_event():
    global embedding_model, chroma_client, collection, doc_collection, groq_client, transcript_data
    
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
        
    try:
        doc_collection = chroma_client.get_or_create_collection(name="document_segments")
    except Exception as e:
        print(f"Could not load or create ChromaDB doc_collection: {e}")
        
    # 4. Initialize Groq Client
    groq_client = Groq()
    print("Startup complete. API is ready.")

# Media Catalog
MEDIA_CATALOG = [
    {
        "id": "youtube_nuno_lecture",
        "title": "Modern Perspectives and Challenges in Magnetic Reconnection",
        "type": "youtube",
        "url": "https://www.youtube.com/watch?v=n6DQvrfaFKY",
        "speaker": "Prof. Nuno Loureiro",
        "embed_id": "n6DQvrfaFKY",
        "language": "en"
    },
    {
        "id": "youtube_plancks_2021",
        "title": "Plasma Physics: from fusion energy to cosmic magnetogenesis (PLANCKS 2021)",
        "type": "youtube",
        "url": "https://www.youtube.com/watch?v=0hiy7hxjZ5s",
        "speaker": "Prof. Nuno Loureiro (PLANCKS 2021)",
        "embed_id": "0hiy7hxjZ5s",
        "language": "en"
    },
    {
        "id": "spotify_45graus_119",
        "title": "Nuno Loureiro - Chegou finalmente o tempo da energia de fusão?",
        "type": "spotify",
        "url": "https://open.spotify.com/episode/3hRwQaK1wDpfU8izp6pJeR",
        "speaker": "Nuno Loureiro (45 Graus #119)",
        "embed_id": "3hRwQaK1wDpfU8izp6pJeR",
        "language": "pt"
    },
    {
        "id": "spotify_descobertas_03",
        "title": "Física de Plasmas - Nuno Loureiro",
        "type": "spotify",
        "url": "https://open.spotify.com/episode/0VI1BBJo9YNnX3A0t2UbT2",
        "speaker": "Nuno Loureiro (Descobertas da Física Moderna #03)",
        "embed_id": "0VI1BBJo9YNnX3A0t2UbT2",
        "language": "pt"
    }
]

# Chapters for all media sources
CHAPTERS_DATA = {
    "youtube_nuno_lecture": [
        {
            "id": 1,
            "title": "Pengenalan Prof. Nuno Loureiro & MIT PSFC",
            "start": 0.0,
            "end": 35.0,
            "timestamp": "00:00",
            "description": "Prof. Nuno Loureiro memperkenalkan diri, perannya di MIT sebagai profesor teknik nuklir dan fisika, serta sebagai direktur Plasma Science and Fusion Center (PSFC).",
            "formulas": []
        },
        {
            "id": 2,
            "title": "Konsep Dasar Rekoneksi Magnetik",
            "start": 35.0,
            "end": 61.0,
            "timestamp": "00:35",
            "description": "Penjelasan mengenai definisi rekoneksi magnetik sebagai proses non-linier pelepasan energi magnetik akibat pengaturan ulang medan magnet (seperti pada solar flare).",
            "formulas": [
                {
                    "latex": "\\frac{\\partial \\mathbf{B}}{\\partial t} = \\nabla \\times (\\mathbf{u} \\times \\mathbf{B}) + \\eta \\nabla^2 \\mathbf{B}",
                    "description": "Persamaan Induksi Magnetohidrodinamika (MHD)"
                }
            ]
        },
        {
            "id": 3,
            "title": "Sifat Plasma & Pentingnya Turbulensi",
            "start": 61.0,
            "end": 131.0,
            "timestamp": "01:01",
            "description": "Bagaimana gerakan partikel plasma menciptakan arus yang memodifikasi medan magnet secara self-consistent, dan pentingnya memprediksi konversi energi turbulensi menjadi panas (solar wind).",
            "formulas": [
                {
                    "latex": "S = \\frac{L v_A}{\\eta}",
                    "description": "Bilangan Lundquist (Rasio skala waktu difusi magnetik)"
                }
            ]
        },
        {
            "id": 4,
            "title": "Fusi Kurungan Magnetis (Tokamak)",
            "start": 131.0,
            "end": 205.0,
            "timestamp": "02:11",
            "description": "Menjelaskan tantangan pengungkungan plasma di reaktor Tokamak, turbulensi amplitudo rendah, serta peran riset rekoneksi dalam mengontrol kestabilan fusi magnetik.",
            "formulas": [
                {
                    "latex": "E_y \\sim \\frac{v_A}{c} S^{-1/2}",
                    "description": "Laju rekoneksi model Sweet-Parker"
                },
                {
                    "latex": "\\gamma \\sim \\frac{v_A}{L}",
                    "description": "Laju pertumbuhan instabilitas plasmoid"
                }
            ]
        },
        {
            "id": 5,
            "title": "Ambisi Akademis & Nasihat Mahasiswa",
            "start": 205.0,
            "end": 232.0,
            "timestamp": "03:25",
            "description": "Dukungan moral bagi mahasiswa pascasarjana untuk berani memecahkan masalah fisika plasma yang sangat menantang dan menjauhi masalah yang terlalu mudah.",
            "formulas": []
        }
    ],
    "spotify_45graus_119": [
        {
            "id": 1,
            "title": "Pendahuluan & Latar Belakang Nuno Loureiro",
            "start": 0.0,
            "end": 456.0,
            "timestamp": "00:00",
            "description": "Perkenalan episode, latar belakang Prof. Nuno Loureiro di MIT e o seu percurso no MIT.",
            "formulas": []
        },
        {
            "id": 2,
            "title": "Bagaimana Energi Fusi Nuklir Bekerja?",
            "start": 456.0,
            "end": 897.0,
            "timestamp": "07:36",
            "description": "Penjelasan tentang reaksi fusi menggunakan isotop hidrogen: deuterium e trítio.",
            "formulas": [
                {
                    "latex": "\\mathrm{D} + \\mathrm{T} \\rightarrow \\mathrm{^{4}He} + \\mathrm{n} + 17.6\\text{ MeV}",
                    "description": "Reaksi Fusi Deuterium-Tritium"
                }
            ]
        },
        {
            "id": 3,
            "title": "Kesulitan Menghasilkan Fusi di Bumi & Peran Simulasi Komputasi",
            "start": 897.0,
            "end": 1720.0,
            "timestamp": "14:57",
            "description": "Mengapa mengendalikan plasma bersuhu ekstrem sangat menantang, serta peran penting simulasi komputer (simulação computacional).",
            "formulas": []
        },
        {
            "id": 4,
            "title": "Kemajuan Penelitian Terbaru (NIF & JET)",
            "start": 1720.0,
            "end": 3030.0,
            "timestamp": "28:40",
            "description": "Pencapaian rekor energi baru di National Ignition Facility (NIF) e JET, serta perbedaan kurungan magnetis versus inercial.",
            "formulas": []
        },
        {
            "id": 5,
            "title": "Stellarator & Investasi Swasta",
            "start": 3030.0,
            "end": 3884.0,
            "timestamp": "50:30",
            "description": "Keterlibatan perusahaan swasta dan pengembangan desain reaktor Stellarator seperti Wendelstein 7-X di Jerman.",
            "formulas": []
        }
    ],
    "spotify_descobertas_03": [
        {
            "id": 1,
            "title": "Pendahuluan Fisika Plasma",
            "start": 0.0,
            "end": 600.0,
            "timestamp": "00:00",
            "description": "Pengantar tentang keadaan materi keempat (plasma) dan pentingnya dalam fisika modern.",
            "formulas": []
        },
        {
            "id": 2,
            "title": "Perilaku Plasma Turbulen & Pemodelan (MHD)",
            "start": 600.0,
            "end": 1800.0,
            "timestamp": "10:00",
            "description": "Membahas sifat chaotic plasma turbulen (plasmas turbulentos) dan pemodelan makroskopis menggunakan persamaan magnetohidrodinamika (MHD).",
            "formulas": [
                {
                    "latex": "\\rho \\left(\\frac{\\partial \\mathbf{u}}{\\partial t} + \\mathbf{u} \\cdot \\nabla \\mathbf{u}\\right) = -\\nabla p + \\mathbf{J} \\times \\mathbf{B}",
                    "description": "Persamaan Momentum Magnetohidrodinamika (MHD)"
                }
            ]
        },
        {
            "id": 3,
            "title": "Vento Solar (Angin Surya) & Astrofisika",
            "start": 1800.0,
            "end": 2700.0,
            "timestamp": "30:00",
            "description": "Analisis angin surya (vento solar), disipasi energi, dan plasma di sekitar lubang hitam (buracos negros).",
            "formulas": []
        },
        {
            "id": 4,
            "title": "Tantangan Kestabilan Reaktor Fusi",
            "start": 2700.0,
            "end": 3600.0,
            "timestamp": "45:00",
            "description": "Mengatasi instabilitas dan turbulência untuk menjaga plasma tetap terkurung cukup lama di dalam Tokamak.",
            "formulas": []
        },
        {
            "id": 5,
            "title": "Masa Depan Energi Fusi Bersih",
            "start": 3600.0,
            "end": 4440.0,
            "timestamp": "01:00:00",
            "description": "Langkah-langkah berikutnya menuju komersialiasi fusi nuklir sebagai energi bersih masa depan.",
            "formulas": []
        }
    ],
    "youtube_plancks_2021": [
        {
            "id": 1,
            "title": "Pendahuluan & Selamat Datang",
            "start": 0.0,
            "end": 118.0,
            "timestamp": "00:00",
            "description": "Pembukaan ceramah tamu oleh Prof. Nuno Loureiro dalam acara PLANCKS 2021.",
            "formulas": []
        },
        {
            "id": 2,
            "title": "Apa itu Plasma?",
            "start": 118.0,
            "end": 204.0,
            "timestamp": "01:58",
            "description": "Penjelasan mendasar mengenai definisi plasma sebagai gas terionisasi yang merupakan keadaan materi keempat.",
            "formulas": []
        },
        {
            "id": 3,
            "title": "Efek Relativitas dalam Plasma",
            "start": 204.0,
            "end": 409.0,
            "timestamp": "03:24",
            "description": "Membahas kapan efek relativistik menjadi signifikan dan penting dalam kajian fisika plasma.",
            "formulas": []
        },
        {
            "id": 4,
            "title": "Mengapa Fisika Plasma Penting?",
            "start": 409.0,
            "end": 595.0,
            "timestamp": "06:49",
            "description": "Pentingnya mempelajari fisika plasma dalam kehidupan sehari-hari, riset energi fusi, dan fenomena astrofisika.",
            "formulas": []
        },
        {
            "id": 5,
            "title": "Pengantar Fisika Plasma",
            "start": 595.0,
            "end": 651.0,
            "timestamp": "09:55",
            "description": "Penjelasan kerangka teoretis dasar fisika plasma.",
            "formulas": []
        },
        {
            "id": 6,
            "title": "Masalah N-Tubuh (N-Body Problem)",
            "start": 651.0,
            "end": 783.0,
            "timestamp": "10:51",
            "description": "Tantangan dalam memodelkan interaksi antara miliaran partikel bermuatan secara individual.",
            "formulas": []
        },
        {
            "id": 7,
            "title": "Persamaan Boltzmann",
            "start": 783.0,
            "end": 1059.0,
            "timestamp": "13:03",
            "description": "Penggunaan deskripsi statistik melalui Persamaan Boltzmann untuk memodelkan fungsi distribusi partikel plasma.",
            "formulas": []
        },
        {
            "id": 8,
            "title": "Persamaan Magnetohidrodinamika (MHD)",
            "start": 1059.0,
            "end": 1109.0,
            "timestamp": "17:39",
            "description": "Penyederhanaan makroskopis plasma sebagai cairan konduktif menggunakan persamaan MHD.",
            "formulas": [
                {
                    "latex": "\\frac{\\partial \\mathbf{B}}{\\partial t} = \\nabla \\times (\\mathbf{u} \\times \\mathbf{B}) + \\eta \\nabla^2 \\mathbf{B}",
                    "description": "Persamaan Induksi Magnetohidrodinamika (MHD)"
                }
            ]
        },
        {
            "id": 9,
            "title": "Perspektif Ekstrem tentang Plasma",
            "start": 1109.0,
            "end": 1405.0,
            "timestamp": "18:29",
            "description": "Membandingkan pendekatan partikel tunggal, statistik (kinetik), dan pendekatan fluida makroskopis (MHD).",
            "formulas": []
        },
        {
            "id": 10,
            "title": "Reaksi Fusi Mandiri (Self-Sustaining Reaction)",
            "start": 1405.0,
            "end": 1886.0,
            "timestamp": "23:25",
            "description": "Kriteria Lawson dan bagaimana menjaga agar reaksi fusi nuklir dapat berjalan mandiri (ignition).",
            "formulas": []
        },
        {
            "id": 11,
            "title": "Koefisien Difusi Besi (Iron Diffusion Coefficient)",
            "start": 1886.0,
            "end": 1953.0,
            "timestamp": "31:26",
            "description": "Difusi partikel dan pengaruh impurities (seperti besi) dalam reaktor fusi.",
            "formulas": []
        },
        {
            "id": 12,
            "title": "Solar Flares (Suar Surya) & Rekoneksi",
            "start": 1953.0,
            "end": 2052.0,
            "timestamp": "32:33",
            "description": "Bagaimana rekoneksi magnetik mendorong pelepasan energi luar biasa pada suar surya.",
            "formulas": []
        },
        {
            "id": 13,
            "title": "Fusi Kurungan Inersia (Inertial Confinement Fusion)",
            "start": 2052.0,
            "end": 2464.0,
            "timestamp": "34:12",
            "description": "Membahas pendekatan alternatif fusi menggunakan laser kuat untuk mengompresi target bahan bakar.",
            "formulas": []
        },
        {
            "id": 14,
            "title": "Evolusi Medan Magnet dalam Plasma",
            "start": 2464.0,
            "end": 2549.0,
            "timestamp": "41:04",
            "description": "Mempelajari persamaan induksi yang mengatur bagaimana medan magnet berkembang dan berinteraksi dengan aliran plasma.",
            "formulas": []
        },
        {
            "id": 15,
            "title": "Masalah Dinamo (Dynamo Problem)",
            "start": 2549.0,
            "end": 2699.0,
            "timestamp": "42:29",
            "description": "Bagaimana gerakan plasma membangkitkan dan memperkuat medan magnet kosmik secara alami.",
            "formulas": []
        },
        {
            "id": 16,
            "title": "Dinamo dalam Plasma Tanpa Tabrakan (Collisionless)",
            "start": 2699.0,
            "end": 3148.0,
            "timestamp": "44:59",
            "description": "Proses dinamo pada skala astrofisika di mana kerapatan plasma sangat rendah sehingga tabrakan partikel dapat diabaikan.",
            "formulas": []
        },
        {
            "id": 17,
            "title": "Bilangan Reynolds",
            "start": 3148.0,
            "end": 3217.0,
            "timestamp": "52:28",
            "description": "Peran bilangan Reynolds mekanis dan magnetis dalam memprediksi turbulensi plasma.",
            "formulas": [
                {
                    "latex": "Re = \\frac{L U}{\\nu}",
                    "description": "Bilangan Reynolds Mekanis"
                },
                {
                    "latex": "R_m = \\frac{L U}{\\eta}",
                    "description": "Bilangan Reynolds Magnetik"
                }
            ]
        },
        {
            "id": 18,
            "title": "Pembangkitan Medan Magnet dari Gradien Tekanan dan Suhu",
            "start": 3217.0,
            "end": 3597.0,
            "timestamp": "53:37",
            "description": "Mekanisme baterai Biermann di mana ketidakselarasan gradien suhu dan kerapatan menghasilkan medan magnet awal.",
            "formulas": [
                {
                    "latex": "\\frac{\\partial \\mathbf{B}}{\\partial t} \\propto \\nabla T_e \\times \\nabla n_e",
                    "description": "Pembangkitan Medan Magnet Baterai Biermann"
                }
            ]
        },
        {
            "id": 19,
            "title": "Transformasi Matematika Panjang & Tanya Jawab",
            "start": 3597.0,
            "end": 3689.0,
            "timestamp": "59:57",
            "description": "Penutup teoretis dan sesi tanya jawab dengan peserta PLANCKS 2021.",
            "formulas": []
        }
    ]
}

# API Models
class SearchQuery(BaseModel):
    query: str
    limit: Optional[int] = 5
    media_id: Optional[str] = "youtube_nuno_lecture"

class ChatMessage(BaseModel):
    role: str # 'user' or 'model' / 'assistant'
    content: str

class ChatQuery(BaseModel):
    query: str
    media_id: Optional[str] = "youtube_nuno_lecture"
    history: Optional[List[ChatMessage]] = []

@app.get("/media")
def get_media_catalog():
    """Retrieve the catalog of available media sources."""
    return MEDIA_CATALOG

@app.get("/transcript")
def get_transcript(media_id: str = "youtube_nuno_lecture"):
    """Retrieve the full bilingual transcript for a given media source."""
    path_map = {
        "youtube_nuno_lecture": BILINGUAL_PATH,
        "youtube_plancks_2021": os.path.join(BASE_DIR, "transcript_bilingual_0hiy7hxjZ5s.json"),
        "spotify_45graus_119": os.path.join(BASE_DIR, "transcript_bilingual_spotify_45graus_119.json"),
        "spotify_descobertas_03": os.path.join(BASE_DIR, "transcript_bilingual_spotify_descobertas_03.json")
    }
    path = path_map.get(media_id)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Transcript not found for media: {media_id}")
        
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load transcript: {str(e)}")

@app.post("/search")
def search_transcript(payload: SearchQuery):
    """Perform a semantic search across the transcript segments for a specific media source."""
    if not collection or not embedding_model:
        raise HTTPException(status_code=500, detail="Search engine or index is not initialized.")
        
    try:
        # Generate query embedding
        query_embedding = embedding_model.encode(payload.query).tolist()
        
        # Query ChromaDB with media_id filter
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=payload.limit,
            where={"media_id": payload.media_id}
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
    """Chat with a specific media transcript using RAG."""
    if not collection or not embedding_model or not groq_client:
        raise HTTPException(status_code=500, detail="RAG system components are not initialized.")
        
    try:
        # 1. Embed query and search ChromaDB for context of the current media
        query_embedding = embedding_model.encode(payload.query).tolist()
        search_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=6,
            where={"media_id": payload.media_id}
        )
        
        # Get active media info
        media_info = next((m for m in MEDIA_CATALOG if m["id"] == payload.media_id), MEDIA_CATALOG[0])
        
        # 2. Extract and format context segments
        context_parts = []
        source_segments = []
        
        if search_results and search_results["metadatas"] and len(search_results["metadatas"]) > 0:
            sorted_metadata = sorted(search_results["metadatas"][0], key=lambda x: x["id"])
            
            for metadata in sorted_metadata:
                timestamp_str = format_timestamp(metadata["start"])
                context_parts.append(
                    f"[{timestamp_str}] (Start: {metadata['start']}s)\n"
                    f"Original ({media_info['language'].upper()}): {metadata['english']}\n"
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
        
        # Check active documents for RAG context
        active_docs = []
        if os.path.exists(DOCUMENTS_REGISTRY_PATH):
            with open(DOCUMENTS_REGISTRY_PATH, 'r', encoding='utf-8') as f:
                docs = json.load(f)
                active_docs = [d for d in docs if d.get("active", True)]
        
        doc_context_parts = []
        if active_docs and doc_collection:
            try:
                if len(active_docs) == 1:
                    where_filter = {"doc_id": active_docs[0]["id"]}
                else:
                    where_filter = {"doc_id": {"$in": [d["id"] for d in active_docs]}}
                
                doc_results = doc_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=4,
                    where=where_filter
                )
                if doc_results and doc_results["metadatas"] and len(doc_results["metadatas"]) > 0:
                    for metadata in doc_results["metadatas"][0]:
                        doc_context_parts.append(
                            f"[Dokumen: {metadata['doc_name']}]\n"
                            f"Kutipan Teks: {metadata['text']}\n"
                        )
            except Exception as e:
                print(f"Error querying doc_collection: {e}")
                
        doc_context_text = "\n---\n".join(doc_context_parts)
        
        document_instruction = ""
        if doc_context_text:
            document_instruction = f"""
Berikut adalah tambahan referensi dokumen pendukung (riset/jurnal fisika plasma) yang relevan dengan pertanyaan:
{doc_context_text}

Aturan Tambahan untuk Dokumen Pendukung:
1. Anda diperbolehkan menggunakan informasi dari dokumen pendukung di atas untuk memperkaya jawaban Anda.
2. Setiap kali Anda menggunakan fakta atau informasi dari dokumen pendukung, Anda harus menuliskan sitasi dalam format `[Dokumen: NamaFile]` (misal: `[Dokumen: paper_nuno_2024.pdf]`).
"""
        
        # 3. Formulate prompt for Groq
        system_instruction = f"""Anda adalah 'PlasmaScribe AI Assistant', seorang ahli fisika plasma. 
Tugas Anda adalah menjawab pertanyaan pengguna mengenai isi media: "{media_info['title']}" oleh {media_info['speaker']}.

Anda HARUS menggunakan transkrip media berikut sebagai sumber kebenaran utama Anda:
{context_text}
{document_instruction}

Aturan Penting:
1. Jawablah dalam Bahasa Indonesia yang ramah, informatif, dan jelas.
2. Setiap kali Anda merujuk ke fakta atau kutipan dari media, Anda wajib menyertakan tombol timestamp dalam format markdown `[MM:SS]` (misal: `[12:34]`) yang menunjuk ke detik mulai segmen tersebut agar pengguna bisa mengklik dan memutar media di detik tersebut.
3. Untuk informasi yang berasal dari dokumen pendukung (jika disediakan), gunakan sitasi `[Dokumen: NamaFile.pdf]` (atau format extensão lainnya).
4. Jika pertanyaan pengguna tidak dapat dijawab berdasarkan informasi transkrip media atau dokumen pendukung yang diberikan, katakan secara jujur dan sopan bahwa informasi tersebut tidak dibahas di media atau dokumen rujukan Anda.
5. Gunakan list markdown, cetak tebal (bold), atau tabel jika membantu menstrukturkan penjelasan ilmiah Anda.
6. Gunakan format LaTeX untuk penulisan rumus fisika atau matematika. Gunakan $$...$$ untuk rumus pada baris baru (block math) dan $...$ untuk rumus yang berada di tengah teks (inline math).
"""

        # Compile chat history for Groq
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

@app.get("/glossary")
def get_glossary(media_id: str = "youtube_nuno_lecture"):
    """Retrieve glossary terms with associated timestamps where they are mentioned in the active media."""
    glossary_path = os.path.join(BASE_DIR, "glossary.json")
    if not os.path.exists(glossary_path):
        raise HTTPException(status_code=404, detail="Glossary file not found.")
        
    with open(glossary_path, 'r', encoding='utf-8') as f:
        glossary = json.load(f)
        
    try:
        active_transcript = get_transcript(media_id)
    except Exception:
        active_transcript = []
        
    result = []
    # Scan active transcript for timestamps of each glossary item
    for eng_term, indo_term in glossary.items():
        timestamps = []
        eng_pat = re.compile(r'\b' + re.escape(eng_term) + r'\b', re.IGNORECASE)
        indo_pat = re.compile(r'\b' + re.escape(indo_term) + r'\b', re.IGNORECASE)
        
        for seg in active_transcript:
            eng_match = eng_pat.search(seg["english"])
            indo_match = indo_pat.search(seg["indonesian"])
            if eng_match or indo_match:
                ts_str = format_timestamp(seg["start"])
                if not any(t["seconds"] == seg["start"] for t in timestamps):
                    timestamps.append({
                        "timestamp": ts_str,
                        "seconds": seg["start"]
                    })
        
        definitions = {
            "magnetic reconnection": "Proses di mana garis-garis medan magnet dalam plasma ber-reorientasi dan melepaskan energi magnetik dalam jumlah besar menjadi energi kinetik dan panas.",
            "magnetic field lines": "Garis imajiner yang digunakan untuk memvisualisasikan kekuatan dan arah medan magnet.",
            "plasmoid instability": "Instabilitas lembar arus (current sheet) yang pecah menjadi pulau-pulau magnetik kecil (plasmoid) dan mempercepat laju rekoneksi magnetik.",
            "turbulence": "Gerakan plasma yang tidak teratur, chaotic, dan non-linier yang mentransfer energi dari skala makroskopis ke disipasi mikroskopis.",
            "plasma physics": "Cabang fisika yang mempelajari gas terionisasi (plasma), keadaan materi keempat yang sangat responsif terhadap medan elektromagnetik.",
            "magnetic confinement fusion": "Pendekatan fusi nuklir menggunakan medan magnet kuat untuk mengurung plasma panas di dalam reaktor (seperti Tokamak).",
            "resistivity": "Hambatan listrik intrinsik plasma yang memungkinkan garis medan magnet berdifusi dan bertabrakan untuk melakukan rekoneksi.",
            "magnetic field": "Medan gaya tak terlihat yang dihasilkan oleh muatan listrik bergerak (arus) dalam plasma.",
            "hydrodynamics": "Studi tentang dinamika fluida konvensional (non-konduktif).",
            "magnetohydrodynamics": "Model fluida makroskopis yang menggambarkan dinamika plasma sebagai cairan konduktor listrik yang berinteraksi dengan medan magnet.",
            "tokamak": "Perangkat kurungan magnetis berbentuk donat (toroida) yang digunakan untuk meneliti fusi nuklir terkendali.",
            "stellarator": "Perangkat kurungan magnetis dengan bentuk melintir rumit yang menstabilkan plasma tanpa membutuhkan arus plasma internal yang besar.",
            "shear flow": "Variasi kecepatan aliran plasma di berbagai posisi, yang dapat menstabilkan atau memicu ketidakstabilan.",
            "dissipation scale": "Skala spasial yang sangat kecil di mana energi turbulensi plasma diubah menjadi panas akibat resistivitas atau viskositas.",
            "diffusion": "Proses perataan konsentrasi partikel atau medan magnet akibat gerakan acak atau resistivitas.",
            "kinetic scale": "Skala ukuran di mana efek gerakan partikel individu (bukan perilaku fluida rata-rata) mulai mendominasi dinamika plasma.",
            "gyroviscosity": "Efek viskositas dalam plasma akibat gerakan melingkar (giro) ion di sekitar garis medan magnet.",
            "macroscopic": "Skala besar atau global dari sistem plasma di mana pendekatan fluida (MHD) sangat valid.",
            "microscopic": "Skala kecil partikel di mana fisika kinetik dan interaksi partikel-medan magnet individu mendominasi.",
            "plasmoid": "Gelembung plasma koheren yang dikelilingi oleh garis medan magnet lucratif (pulau magnetik).",
            "reconnection rate": "Laju kecepatan garis-garis medan magnet masuk dan bergabung kembali di wilayah rekoneksi.",
            "current sheet": "Lembaran tipis konsentrasi arus listrik tinggi yang terbentuk di antara wilayah medan magnet yang berlawanan arah.",
            "resistive MHD": "Teori magnetohidrodinamika yang menyertakan efek resistivitas listrik plasma untuk memungkinkan terjadinya rekoneksi magnetik.",
            "collisionless": "Kondisi plasma dengan kerapatan rendah dan suhu tinggi di mana partikel jarang saling bertabrakan secara fisik."
        }
        
        result.append({
            "term": eng_term,
            "indonesian": indo_term,
            "definition": definitions.get(eng_term.lower(), f"Istilah fisika plasma yang merujuk pada '{indo_term}'."),
            "timestamps": timestamps[:6]
        })
        
    return result

@app.get("/chapters")
def get_chapters(media_id: str = "youtube_nuno_lecture"):
    """Retrieve structured chapters for the active media source."""
    chapters = CHAPTERS_DATA.get(media_id)
    if not chapters:
        raise HTTPException(status_code=404, detail=f"Chapters not found for media_id: {media_id}")
    return chapters

@app.post("/quiz/generate")
def generate_quiz(media_id: str = "youtube_nuno_lecture"):
    """Generate 5 multiple-choice quiz questions based on the transcript of the active media."""
    if not groq_client:
        raise HTTPException(status_code=500, detail="Groq client is not initialized.")
        
    try:
        active_transcript = get_transcript(media_id)
        transcript_text = "\n".join([f"[{format_timestamp(s['start'])}] {s['english']}" for s in active_transcript])
        
        system_instruction = """Anda adalah ahli fisika plasma dan asisten pembuat kuis edukatif. 
Tugas Anda adalah membuat kuis pilihan ganda berisi 5 soal yang mendalam berdasarkan materi kuliah/podcast fisika plasma yang disediakan.

Soal kuis harus mencakup konsep penting dari transkrip seperti:
1. Rekoneksi magnetik
2. Tokamak dan fusi kurungan magnetis
3. Turbulensi plasma dan transfer energi (solar wind)

Aturan Output:
1. Kembalikan respons dalam format JSON object.
2. Respons harus mengikuti skema berikut secara persis:
{
  "quiz": [
    {
      "id": 1,
      "question": "<pertanyaan ilmiah dalam Bahasa Indonesia>",
      "options": {
        "A": "<pilihan jawaban A>",
        "B": "<pilihan jawaban B>",
        "C": "<pilihan jawaban C>",
        "D": "<pilihan jawaban D>"
      },
      "correct_answer": "A", // Pilihan jawaban yang benar (A, B, C, atau D)
      "explanation": "<penjelasan lengkap mengapa jawaban tersebut benar dalam Bahasa Indonesia, harus menyertakan timestamp rujukan dalam format [MM:SS] seperti [01:23]>",
      "seconds": 83.0 // Detik mulai dari bagian media yang bersesuaian dengan penjelasan tersebut
    },
    ...
  ]
}
Pastikan data numerik 'seconds' adalah float/integer yang valid dan menunjukkan detik mulainya segmen media tersebut (misal jika timestampnya [01:23], maka seconds adalah 83.0).
"""
        
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Berikut adalah transkrip untuk membuat kuis:\n{transcript_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        quiz_data = json.loads(response.choices[0].message.content)
        return quiz_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")

# Helper to read document registry
def read_documents_registry() -> List[dict]:
    if not os.path.exists(DOCUMENTS_REGISTRY_PATH):
        return []
    try:
        with open(DOCUMENTS_REGISTRY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

# Helper to write document registry
def write_documents_registry(registry: List[dict]):
    with open(DOCUMENTS_REGISTRY_PATH, 'w', encoding='utf-8') as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

@app.get("/documents")
def list_documents():
    """List all uploaded documents and their active states."""
    return read_documents_registry()

@app.post("/documents/{doc_id}/toggle")
def toggle_document(doc_id: str):
    """Toggle the active state of a document for RAG search."""
    registry = read_documents_registry()
    updated = False
    for doc in registry:
        if doc["id"] == doc_id:
            doc["active"] = not doc.get("active", True)
            updated = True
            break
            
    if not updated:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    write_documents_registry(registry)
    return {"status": "success", "registry": registry}

@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    """Delete a document and its indexed vectors from ChromaDB."""
    global doc_collection
    if not doc_collection:
        raise HTTPException(status_code=500, detail="ChromaDB document collection not initialized.")
        
    registry = read_documents_registry()
    doc_to_delete = None
    for doc in registry:
        if doc["id"] == doc_id:
            doc_to_delete = doc
            break
            
    if not doc_to_delete:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    try:
        doc_collection.delete(where={"doc_id": doc_id})
    except Exception as e:
        print(f"Error deleting vectors from ChromaDB: {e}")
        
    registry = [d for d in registry if d["id"] != doc_id]
    write_documents_registry(registry)
    
    return {"status": "success", "registry": registry}

@app.post("/document/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF or TXT document, extract text, embed, and store in ChromaDB."""
    global doc_collection, embedding_model
    if not doc_collection or not embedding_model:
        raise HTTPException(status_code=500, detail="Embedding model or ChromaDB collection not initialized.")
        
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
        
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".pdf", ".txt"]:
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported.")
        
    contents = await file.read()
    text_content = ""
    
    if ext == ".txt":
        try:
            text_content = contents.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text_content = contents.decode("latin-1")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read TXT file: {str(e)}")
    elif ext == ".pdf":
        try:
            import pypdf
            import io
            pdf_file = io.BytesIO(contents)
            reader = pypdf.PdfReader(pdf_file)
            pages_text = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
            text_content = "\n\n".join(pages_text)
            if not text_content.strip():
                raise Exception("PDF file has no extractable text.")
        except ImportError:
            raise HTTPException(status_code=500, detail="pypdf library is not installed in the backend.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF file: {str(e)}")
            
    if not text_content.strip():
        raise HTTPException(status_code=400, detail="The uploaded file contains no readable text content.")
        
    chunk_size = 750
    overlap = 150
    chunks = []
    
    start_idx = 0
    while start_idx < len(text_content):
        end_idx = start_idx + chunk_size
        chunk = text_content[start_idx:end_idx]
        chunks.append(chunk)
        start_idx += (chunk_size - overlap)
        
    doc_id = str(uuid.uuid4())
    
    documents_list = []
    ids_list = []
    metadatas_list = []
    
    for idx, chunk_text in enumerate(chunks):
        chunk_id = f"{doc_id}_{idx}"
        documents_list.append(chunk_text)
        ids_list.append(chunk_id)
        metadatas_list.append({
            "doc_id": doc_id,
            "doc_name": filename,
            "chunk_index": idx,
            "text": chunk_text
        })
        
    try:
        embeddings = embedding_model.encode(documents_list).tolist()
        doc_collection.add(
            ids=ids_list,
            embeddings=embeddings,
            metadatas=metadatas_list,
            documents=documents_list
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation or ChromaDB storage failed: {str(e)}")
        
    registry = read_documents_registry()
    size_str = f"{len(contents) / 1024:.1f} KB" if len(contents) < 1024*1024 else f"{len(contents) / (1024*1024):.1f} MB"
    
    new_doc = {
        "id": doc_id,
        "name": filename,
        "size": size_str,
        "type": ext[1:],
        "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "active": True
    }
    
    registry.append(new_doc)
    write_documents_registry(registry)
    
    return {"status": "success", "document": new_doc, "registry": registry}

if __name__ == "__main__":
    import uvicorn
    # Trigger reload for ChromaDB collection update
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
