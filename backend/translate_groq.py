import os
import json
import sys
import time
from dotenv import load_dotenv
from groq import Groq

# Load env variables (GROQ_API_KEY)
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("Warning: GROQ_API_KEY not found in environment. Please make sure it is set.", file=sys.stderr)

def get_groq_client():
    if GROQ_API_KEY:
        return Groq(api_key=GROQ_API_KEY)
    else:
        return Groq()

def load_glossary(glossary_path):
    try:
        with open(glossary_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading glossary: {e}", file=sys.stderr)
        return {}

def translate_batch(client, batch, glossary):
    glossary_str = "\n".join([f"- {k}: {v}" for k, v in glossary.items()])
    
    system_instruction = f"""Anda adalah penerjemah AI profesional yang ahli dalam bidang fisika plasma dan fusi nuklir.
Tugas Anda adalah menerjemahkan segmen transkrip kuliah ilmiah dari Bahasa Inggris ke Bahasa Indonesia.

Gunakan glosarium istilah berikut untuk memastikan terjemahan teknis Anda akurat:
{glossary_str}

Aturan penting:
1. Terjemahan harus akurat secara ilmiah, tetapi tetap mengalir secara alami untuk bahasa lisan.
2. Pertahankan istilah bahasa Inggris dalam tanda kurung jika dirasa perlu untuk kejelasan (misal: "rekoneksi magnetik (magnetic reconnection)").
3. Output HARUS berupa JSON object dengan format:
   {{
     "translations": [
       {{"id": <integer>, "translation": "<terjemahan bahasa indonesia>"}},
       ...
     ]
   }}
Pastikan kunci 'id' yang Anda kembalikan persis sama dengan 'id' yang dikirimkan.
"""

    prompt = f"Terjemahkan segmen transkrip berikut:\n{json.dumps(batch, ensure_ascii=False, indent=2)}"

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        # Parse the JSON response
        result = json.loads(response.choices[0].message.content)
        translated_items = result.get("translations", [])
        return {item["id"]: item["translation"] for item in translated_items}
    except Exception as e:
        print(f"API call or parsing failed for batch: {e}", file=sys.stderr)
        return {item["id"]: "" for item in batch}

def main():
    raw_path = "backend/transcript_raw.json"
    glossary_path = "backend/glossary.json"
    output_path = "backend/transcript_bilingual.json"
    
    if not os.path.exists(raw_path):
        print(f"Raw transcript file not found: {raw_path}. Run download_transcript.py first.")
        sys.exit(1)
        
    with open(raw_path, 'r', encoding='utf-8') as f:
        raw_segments = json.load(f)
        
    glossary = load_glossary(glossary_path)
    client = get_groq_client()
    
    print(f"Starting translation of {len(raw_segments)} segments...")
    
    # Batch size (Llama 70B can easily handle larger batches, e.g., 30 items)
    batch_size = 20
    bilingual_segments = []
    
    for i in range(0, len(raw_segments), batch_size):
        chunk = raw_segments[i:i+batch_size]
        batch_input = [{"id": i + idx, "text": seg["text"]} for idx, seg in enumerate(chunk)]
        
        print(f"Translating segments {i} to {min(i + batch_size, len(raw_segments))}...")
        translations = translate_batch(client, batch_input, glossary)
        
        # Merge translations with original segment info
        for idx, seg in enumerate(chunk):
            seg_id = i + idx
            indonesian_text = translations.get(seg_id, "")
            
            bilingual_segments.append({
                "id": seg_id,
                "start": seg["start"],
                "duration": seg["duration"],
                "english": seg["text"],
                "indonesian": indonesian_text
            })
            
        # Small sleep to respect rate limits
        time.sleep(0.5)
        
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(bilingual_segments, f, ensure_ascii=False, indent=2)
        
    print(f"Translation completed successfully! Saved to {output_path}")

if __name__ == "__main__":
    main()
