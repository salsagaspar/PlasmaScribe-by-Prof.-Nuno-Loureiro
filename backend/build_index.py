import os
import json
import sys
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

def main():
    bilingual_path = "backend/transcript_bilingual.json"
    db_path = "backend/chroma_db"
    
    if not os.path.exists(bilingual_path):
        print(f"Bilingual transcript file not found: {bilingual_path}. Run translate_gemini.py first.")
        sys.exit(1)
        
    print("Loading bilingual transcript...")
    with open(bilingual_path, 'r', encoding='utf-8') as f:
        segments = json.load(f)
        
    print("Initializing Sentence-Transformer model (all-MiniLM-L6-v2)...")
    # This downloads the model (~90MB) on the first run and caches it locally
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print(f"Initializing persistent ChromaDB client at: {db_path}")
    chroma_client = chromadb.PersistentClient(path=db_path)
    
    # Reset or get the collection
    collection_name = "transcript_segments"
    try:
        chroma_client.delete_collection(name=collection_name)
        print(f"Deleted existing collection: {collection_name}")
    except Exception:
        pass
        
    collection = chroma_client.create_collection(name=collection_name)
    
    print(f"Indexing {len(segments)} segments...")
    
    documents = []
    ids = []
    metadatas = []
    
    for seg in segments:
        # We index a combined string of Indonesian and English to allow search in both
        doc_text = f"English: {seg['english']}\nIndonesian: {seg['indonesian']}"
        documents.append(doc_text)
        ids.append(str(seg['id']))
        metadatas.append({
            "id": seg["id"],
            "start": float(seg["start"]),
            "duration": float(seg["duration"]),
            "english": seg["english"],
            "indonesian": seg["indonesian"]
        })
        
    # Generate embeddings
    print("Generating embeddings (this may take a minute)...")
    embeddings = model.encode(documents, show_progress_bar=True).tolist()
    
    # Add to ChromaDB
    print("Adding vectors to ChromaDB...")
    # Batch add in chunks of 200 to avoid limits
    batch_size = 200
    for i in range(0, len(ids), batch_size):
        end_idx = min(i + batch_size, len(ids))
        collection.add(
            ids=ids[i:end_idx],
            embeddings=embeddings[i:end_idx],
            metadatas=metadatas[i:end_idx],
            documents=documents[i:end_idx]
        )
        
    print("Indexing completed successfully!")
    print(f"Total indexed items: {collection.count()}")

if __name__ == "__main__":
    main()
