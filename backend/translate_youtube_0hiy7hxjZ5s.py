import os
import json
import sys
import time
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("Error: GROQ_API_KEY not found in environment.", file=sys.stderr)
    sys.exit(1)

client = Groq(api_key=GROQ_API_KEY)

# Load glossary terms to pass to Groq
def load_glossary():
    path = os.path.join("backend", "glossary.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

glossary = load_glossary()
glossary_str = "\n".join([f"- {k} -> {v}" for k, v in glossary.items()])

def translate_batch(batch):
    system_instruction = f"""Anda adalah asisten penerjemah AI profesional yang ahli dalam bidang fisika plasma dan fusi nuklir.
Tugas Anda adalah menerjemahkan segmen transkrip kuliah ilmiah dari Bahasa Inggris ke Bahasa Indonesia.

Gunakan glosarium istilah fisika berikut untuk memastikan terjemahan teknis Anda akurat:
{glossary_str}

Aturan penting:
1. Terjemahan harus akurat secara ilmiah, tetapi tetap mengalir secara alami untuk bahasa lisan/ceramah.
2. Pertahankan istilah bahasa Inggris dalam tanda kurung jika dirasa perlu untuk kejelasan (misal: "rekoneksi magnetik (magnetic reconnection)", "kurungan magnetis (magnetic confinement)").
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

    retries = 3
    for attempt in range(retries):
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
            
            result = json.loads(response.choices[0].message.content)
            translated_items = result.get("translations", [])
            return {item["id"]: item["translation"] for item in translated_items}
        except Exception as e:
            print(f"API call or parsing failed for batch (attempt {attempt + 1}/{retries}): {e}", file=sys.stderr)
            if attempt == retries - 1:
                return {item["id"]: "[Terjemahan gagal]" for item in batch}
            time.sleep(2)

def main():
    raw_path = "backend/transcript_raw_0hiy7hxjZ5s.json"
    output_path = "backend/transcript_bilingual_0hiy7hxjZ5s.json"
    
    if not os.path.exists(raw_path):
        print(f"Raw transcript file not found: {raw_path}. Run parse_vtt.py first.", file=sys.stderr)
        sys.exit(1)
        
    with open(raw_path, 'r', encoding='utf-8') as f:
        raw_segments = json.load(f)
        
    print(f"Starting translation of {len(raw_segments)} segments...")
    
    batch_size = 20
    bilingual_segments = []
    
    for i in range(0, len(raw_segments), batch_size):
        chunk = raw_segments[i:i+batch_size]
        batch_input = [{"id": i + idx, "text": seg["text"]} for idx, seg in enumerate(chunk)]
        
        print(f"Translating segments {i} to {min(i + batch_size, len(raw_segments))}...")
        translations = translate_batch(batch_input)
        
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
            
        # Respect rate limits
        time.sleep(1.0)
        
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(bilingual_segments, f, ensure_ascii=False, indent=2)
        
    print(f"Translation completed successfully! Saved to {output_path}")

if __name__ == "__main__":
    main()
