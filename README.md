# 🌌 PlasmaScribe

Interactive Physics Lecture Transcript & AI RAG Assistant (Bilingual: English - Indonesian) for Prof. Nuno Loureiro's lectures and podcasts.

PlasmaScribe is a complete AI Engineering application that downloads, transcribes, translates, indexes, and enables interactive AI Chat (RAG) in Indonesian for specialized plasma physics lectures. It features a custom premium dark-themed UI (plasma color scheme) with glassmorphic visuals, interactive quizzes, video notebooks, and on-the-fly document reference ingestion.

---

## 🌟 Core Features

- **Multi-Media Lecture Catalog**: Support for multiple lectures and podcasts, including:
  - MIT Lecture: *"Modern Perspectives and Challenges in Magnetic Reconnection"* (YouTube)
  - Guest Lecture: *"Plasma Physics: from fusion energy to cosmic magnetogenesis"* (PLANCKS 2021 YouTube)
  - Podcast episode: *"Nuno Loureiro - Chegou finalmente o tempo da energia de fusão?"* (45 Graus #119 Spotify)
  - Podcast episode: *"Física de Plasmas - Nuno Loureiro"* (Descobertas da Física Moderna #03 Spotify)
- **Dynamic Player & Transcript Sync**: Integrates the YouTube Iframe Player API to synchronize the active transcript segment with the current playback time. The transcript automatically scrolls into view as the video plays.
- **Interactive Time Seeking**: Click on any transcript row to jump the video directly to that timestamp.
- **Cross-Lingual Semantic Search**: Search terms semantically in both English/Portuguese and Indonesian (e.g., searching for "tokamak" or "rekoneksi" returns matching segments instantly).
- **Indonesian RAG Chat Assistant**: Chat with the video content using a dedicated sidebar. The AI (Llama 3.3) responds in Indonesian and generates clickable timestamp links (e.g., `[02:14]`) allowing users to easily seek the player.
- **Advanced Document RAG Upload**: Ingest and index PDF or TXT reference papers/documents on-the-fly. The AI Assistant integrates active documents into its context and automatically cites them (e.g. `[Dokumen: paper_name.pdf]`) in its response.
- **AI Quiz Mode**: Dynamically generates a 5-question multiple-choice quiz based on the selected transcript. Features immediate feedback, explanations, and timestamp links to watch the relevant explanation in the video.
- **Video Notebook**: Take personal notes synchronized with the current video playback time, edit/delete notes, and export notes as a Markdown (`.md`) file.
- **Physics-Specific Glossary Integration**: Auto-scans transcripts for 24+ advanced plasma physics terms (e.g., *magnetic reconnection*, *plasmoid instability*, *stellarator*) mapping to their Indonesian translations and timestamps.

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **AI Services**: Groq Cloud API (`whisper-large-v3` for audio transcription, `llama-3.3-70b-versatile` for translation, quiz generation, and chat)
- **Vector DB**: ChromaDB (Local SQLite-based persistent store)
- **Embeddings**: Local `Sentence-Transformers` (`all-MiniLM-L6-v2`)
- **Document Parser**: `pypdf` for parsing user-uploaded PDF papers

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

1. **Download & Transcribe Audio (YouTube)**:
   ```bash
   python backend/download_transcript.py
   ```
   Downloads the YouTube lecture audio stream (`.webm` via `yt-dlp`) and transcribes it into `backend/transcript_raw.json` using Groq Whisper.

2. **Generate Spotify Transcripts**:
   ```bash
   python backend/generate_spotify_transcripts.py
   ```
   Downloads and processes Portuguese Spotify audio transcripts using Groq.

3. **Translate to Indonesian**:
   ```bash
   python backend/translate_groq.py
   ```
   Translates English transcript segments into Indonesian via Llama 3.3 and maps physics terminology based on `backend/glossary.json`, saving the output to `backend/transcript_bilingual.json`.

4. **Build Semantic Index**:
   ```bash
   python backend/build_index.py
   ```
   Generates local embeddings using Sentence-Transformers and indexes all transcript files into a ChromaDB database inside `backend/chroma_db/`.
