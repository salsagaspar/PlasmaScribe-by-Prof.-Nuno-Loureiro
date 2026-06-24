import os
import json
import sys
import chromadb
from sentence_transformers import SentenceTransformer

def main():
    db_path = "backend/chroma_db"
    
    # List of all transcripts to index
    transcripts_config = [
        {"media_id": "youtube_nuno_lecture", "path": "backend/transcript_bilingual.json"},
        {"media_id": "youtube_plancks_2021", "path": "backend/transcript_bilingual_0hiy7hxjZ5s.json"},
        {"media_id": "spotify_45graus_119", "path": "backend/transcript_bilingual_spotify_45graus_119.json"},
        {"media_id": "spotify_descobertas_03", "path": "backend/transcript_bilingual_spotify_descobertas_03.json"}
    ]
    
    print("Initializing Sentence-Transformer model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print(f"Initializing persistent ChromaDB client at: {db_path}")
    chroma_client = chromadb.PersistentClient(path=db_path)
    
    collection_name = "transcript_segments"
    try:
        chroma_client.delete_collection(name=collection_name)
        print(f"Deleted existing collection: {collection_name}")
    except Exception:
        pass
        
    collection = chroma_client.create_collection(name=collection_name)
    
    for config in transcripts_config:
        media_id = config["media_id"]
        filepath = config["path"]
        
        if not os.path.exists(filepath):
            print(f"Transcript file not found: {filepath}. Skipping.")
            continue
            
        print(f"Loading transcript for {media_id} from {filepath}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            segments = json.load(f)
            
        print(f"Indexing {len(segments)} segments for {media_id}...")
        
        documents = []
        ids = []
        metadatas = []
        
        for seg in segments:
            # We index a combined string of Original and Indonesian to allow search in both
            doc_text = f"Original: {seg['english']}\nIndonesian: {seg['indonesian']}"
            documents.append(doc_text)
            ids.append(f"{media_id}_{seg['id']}")
            metadatas.append({
                "id": seg["id"],
                "media_id": media_id,
                "start": float(seg["start"]),
                "duration": float(seg["duration"]),
                "english": seg["english"],
                "indonesian": seg["indonesian"]
            })
            
        # Generate embeddings
        print(f"Generating embeddings for {media_id}...")
        embeddings = model.encode(documents, show_progress_bar=True).tolist()
        
        # Add to ChromaDB in batches
        print(f"Adding vectors for {media_id} to ChromaDB...")
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
