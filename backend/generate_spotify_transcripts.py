import os
import json
import time
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("Error: GROQ_API_KEY not found in environment.")
    exit(1)

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

def generate_full_transcript(episode_info, chapters_info, total_seconds, num_segments, output_path):
    print(f"Generating full-length transcript for: {episode_info['title']} ({total_seconds} seconds) with {num_segments} segments...")
    
    # Pre-calculate segment skeleton
    seg_duration = round(total_seconds / num_segments, 1)
    skeleton = []
    for i in range(num_segments):
        start = round(i * seg_duration, 1)
        # Ensure last segment goes to the very end
        duration = round(total_seconds - start, 1) if i == num_segments - 1 else seg_duration
        skeleton.append({
            "id": i,
            "start": start,
            "duration": duration,
            "english": "",
            "indonesian": ""
        })

    chunk_size = 10
    all_segments = []
    
    for chunk_start_idx in range(0, num_segments, chunk_size):
        chunk_end_idx = min(chunk_start_idx + chunk_size, num_segments)
        chunk_skeleton = skeleton[chunk_start_idx:chunk_end_idx]
        
        print(f"Generating chunk: segments {chunk_start_idx} to {chunk_end_idx - 1}...")
        
        system_instruction = f"""You are a professional plasma physics academic translator.
Your task is to generate a realistic, detailed, segment-by-segment transcript for a podcast episode/lecture by Prof. Nuno Loureiro.
The original podcast is in Portuguese. You must populate the original Portuguese text and translate it into Indonesian for each segment in the provided skeleton chunk.

Glossary of physics terms (ensure these are mapped correctly in the Indonesian translation):
{glossary_str}

Important translation rules:
1. The Portuguese text must be scientifically accurate and natural Portuguese spoken language.
2. The Indonesian translation must be scientifically accurate, clear, and flow naturally. Keep English terms in brackets if helpful, e.g. "rekoneksi magnetik (magnetic reconnection)".
3. For each segment, the 'english' field MUST contain the original Portuguese text (because the React UI expects the original text in 'english'). The 'indonesian' field must contain the Indonesian translation.
4. You must output the exact same skeleton array chunk, only filling in the 'english' and 'indonesian' fields for each item. Do not skip any item, do not add new items.
5. The output format MUST be a JSON object with this structure:
{{
  "transcript": [
    {{
      "id": <integer>,
      "start": <float>,
      "duration": <float>,
      "english": "<Portuguese text of the podcast for this timestamp>",
      "indonesian": "<Indonesian translation of this segment>"
    }},
    ...
  ]
}}
Ensure the JSON is valid and complete.
"""

        prompt = f"""
Generate the bilingual transcript texts for this portion of the episode:
Title: {episode_info['title']}
Podcast: {episode_info['podcast']}
Description: {episode_info['description']}
Total Duration: {total_seconds} seconds.

Chapters and timestamps for context:
{chapters_info}

Currently generating segments from {chunk_start_idx} to {chunk_end_idx - 1}.
Ensure the content matches the chronologically corresponding chapter for these timestamps (from {chunk_skeleton[0]['start']}s to {chunk_skeleton[-1]['start'] + chunk_skeleton[-1]['duration']}s).

Fill in this JSON skeleton chunk:
{json.dumps(chunk_skeleton, indent=2)}
"""

        # Retry logic in case of failure
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
                    temperature=0.3
                )
                
                result = json.loads(response.choices[0].message.content)
                segments = result.get("transcript", [])
                
                # Verify that we got the right segments back
                if not segments or len(segments) != len(chunk_skeleton):
                    raise ValueError(f"Expected {len(chunk_skeleton)} segments, got {len(segments)}")
                
                # Check IDs or align them just in case
                for idx, seg in enumerate(segments):
                    orig_skel = chunk_skeleton[idx]
                    seg["id"] = orig_skel["id"]
                    seg["start"] = orig_skel["start"]
                    seg["duration"] = orig_skel["duration"]
                    
                all_segments.extend(segments)
                break
            except Exception as e:
                print(f"Error generating chunk (attempt {attempt + 1}/{retries}): {e}")
                if attempt == retries - 1:
                    print("Failed after maximum retries. Using placeholders.")
                    for orig_skel in chunk_skeleton:
                        orig_skel["english"] = "[Transkrip tidak dapat dibuat]"
                        orig_skel["indonesian"] = "[Transcript generation failed]"
                        all_segments.append(orig_skel)
                time.sleep(2)
                
        # Small sleep between chunks to avoid rate limits
        time.sleep(1.5)

    # Save to output path
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_segments, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully generated and saved {len(all_segments)} segments to {output_path}")

def main():
    # Episode 1: 45 Graus #119 (3900 seconds)
    ep1_info = {
        "title": "Nuno Loureiro - Chegou finalmente o tempo da energia de fusão?",
        "podcast": "45 Graus #119",
        "description": "Nuno Loureiro, professor catedrático no MIT e especialista em física de plasmas, discute o funcionamento da fusão nuclear, os desafios técnicos e os progressos recentes."
    }
    ep1_chapters = """
    - 00:00 - Introdução ao episódio, apresentação de Nuno Loureiro e o seu percurso no MIT.
    - 07:36 - Como funciona a energia nuclear de fusão? Reagentes deutério e trítio.
    - 14:57 - Por que é tão difícil gerar fusão nuclear na Terra? O papel da simulação computacional.
    - 25:46 - De onde vem a energia libertada nas reações nucleares de fusão?
    - 28:40 - Progressos científicos e marcos recentes (NIF, JET, projeto ITER, confinamento magnético vs inercial).
    - 39:00 - Fatores que explicam os progressos recentes e a cimeira na Casa Branca.
    - 42:46 - Desafios de engenharia para tornar a energia de fusão comercialmente viável.
    - 46:54 - Como converter a energia libertada em eletricidade utilizável na rede (fusão aneutrónica).
    - 48:07 - Riscos e segurança da fusão nuclear comparado com a fissão nuclear.
    - 50:30 - Iniciativas privadas, investimentos e o stellarator Wendelstein 7-X na Alemanha.
    - 55:39 - O papel da liderança da Europa na investigação de fusão.
    - 58:40 - Que abordagem é mais promissora: confinamento magnético ou inercial (laser)?
    - 01:02:13 - De que forma a investigação em fusão nuclear ilumina os mistérios da astrofísica.
    - 01:04:44 - Previsões e timeline: quando teremos energia de fusão comercial na rede elétrica.
    """
    
    # Episode 2: Descobertas da Física Moderna #03 (4440 seconds)
    ep2_info = {
        "title": "Física de Plasmas - Nuno Loureiro",
        "podcast": "Descobertas da Física Moderna #03",
        "description": "Nuno Loureiro aborda o comportamento de plasmas turbulentos na física de plasmas, passando por tópicos como buracos negros, o vento solar e o futuro da fusão nuclear."
    }
    ep2_chapters = """
    - 00:00 - Introdução à Física de Plasmas e o enquadramento na disciplina Descobertas da Física Moderna.
    - 10:00 - Comportamento de Plasmas Turbulentos: o comportamento caótico e a modelagem matemática (magnetohidrodinâmica).
    - 30:00 - O Vento Solar e Plasmas Astrofísicos: disipação de energia no vento solar e plasmas em torno de buracos negros.
    - 45:00 - Desafios de Kestabilan (estabilidade) no Reator de Fusão Nuclear: evitar instabilidades e turbulência em Tokamaks e Stellarators.
    - 01:00:00 - O Futuro da Fusão Nuclear como Fonte de Energia Limpa e Conclusão da aula.
    """
    
    # Episode 1: 39 segments (100 seconds each)
    generate_full_transcript(ep1_info, ep1_chapters, 3900, 39, "backend/transcript_bilingual_spotify_45graus_119.json")
    # Small sleep to respect rate limits
    time.sleep(2)
    # Episode 2: 45 segments (100 seconds each, last is 40s)
    generate_full_transcript(ep2_info, ep2_chapters, 4440, 45, "backend/transcript_bilingual_spotify_descobertas_03.json")

if __name__ == "__main__":
    main()
