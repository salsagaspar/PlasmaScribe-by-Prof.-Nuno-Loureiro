# 🌌 PlasmaScribe

Interactive Physics Lecture Transcript & AI RAG Assistant (Bilingual: English - Indonesian) for Prof. Nuno Loureiro's lecture: *"Modern Perspectives and Challenges in Magnetic Reconnection"*.

PlasmaScribe is a complete AI Engineering application that downloads, transcribes, translates, indexes, and enables interactive AI Chat (RAG) in Indonesian for specialized plasma physics lectures. It features a custom premium dark-themed UI (plasma color scheme) with glassmorphic visuals and smooth scroll interactions.

---

## 🌟 Core Features

- **Dynamic Video & Transcript Sync**: Integrates the YouTube Iframe Player API to synchronize the active transcript segment with the current playback time. The transcript automatically scrolls into view as the video plays.
- **Interactive Time Seeking**: Click on any transcript row to jump the video directly to that timestamp.
- **Cross-Lingual Semantic Search**: Search terms semantically in both English and Indonesian (e.g., searching for "tokamak" or "rekoneksi" returns matching segments instantly, even if searched in the opposite language).
- **Indonesian RAG Chat Assistant**: Chat with the video content using a dedicated sidebar. The AI (Llama 3.3) responds in Indonesian and generates clickable timestamp links (e.g., `[02:14]`) allowing users to easily seek the player.
- **Physics-Specific Glossary Integration**: Transcripts are translated using a domain-specific glossary (`glossary.json`) to map advanced scientific terms correctly (e.g., *magnetic reconnection* -> rekoneksi magnetik, *magnetic islands* -> pulau magnetik).

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **AI Services**: Groq Cloud API (Whisper-large-v3 for audio transcription, Llama-3.3-70b-versatile for translation and chat)
- **Vector DB**: ChromaDB (Local SQLite-based persistent store)
- **Embeddings**: Local `Sentence-Transformers` (`all-MiniLM-L6-v2`)

### Frontend
- **Framework**: Vite + React
- **Icons**: Lucide React
- **Styling**: Pure Custom Vanilla CSS (Dark Space/Plasma theme, Glassmorphism, Micro-interactions)

### Containerization
- **Docker Compose** (Multi-container architecture for frontend and backend integration)

---

## 🐳 Getting Started (Docker Compose - Recommended)

Docker Compose compiles and mounts all directories with *hot-reloading* active.

### 1. Prerequisites
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
- Get your free API key from the [Groq Console](https://console.groq.com/).

### 2. Configure Environment Variables
Create a `.env` file inside the `backend/` directory:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Spin Up Containers
In the project root folder, run:
```bash
docker-compose up -d
```

- **Frontend Interface** is available at: `http://localhost:5173/`
- **FastAPI API Documentation** is available at: `http://localhost:8000/docs`

---

## 💻 Manual Local Setup

If you prefer to run the components directly on your host machine:

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the API server:
   ```bash
   python -m uvicorn main:app --reload
   ```
   The API will listen at `http://127.0.0.1:8000`.

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Launch Vite development server:
   ```bash
   npm run dev
   ```
   Open the app at `http://localhost:5173/`.

---

## 🗄️ Data Pipeline Generation (Optional)

All transcript assets, translations, and vector indices have already been generated and committed. If you need to re-run the pipeline from scratch:

1. **Download & Transcribe Audio**:
   ```bash
   python backend/download_transcript.py
   ```
   Downloads the YouTube lecture audio stream (`.webm` via `yt-dlp`) and transcribes it into `backend/transcript_raw.json` using Groq Whisper.

2. **Translate to Indonesian**:
   ```bash
   python backend/translate_groq.py
   ```
   Translates English transcript segments into Indonesian via Llama 3.3 and maps physics terminology based on `backend/glossary.json`, saving the output to `backend/transcript_bilingual.json`.

3. **Build Semantic Index**:
   ```bash
   python backend/build_index.py
   ```
   Generates local embeddings using Sentence-Transformers and indexes the data into a ChromaDB database inside `backend/chroma_db/`.

---

## Frontend
![alt text](<Screenshot 2026-06-22 003241.png>)

## Backend
![alt text](<Screenshot 2026-06-22 004854.png>)

---
