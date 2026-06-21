import os
import sys
import json
import subprocess
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("Warning: GROQ_API_KEY not found in environment. Please make sure it is set.", file=sys.stderr)

def get_groq_client():
    if GROQ_API_KEY:
        return Groq(api_key=GROQ_API_KEY)
    else:
        return Groq()

def download_audio(video_id, output_dir):
    out_tmpl = os.path.join(output_dir, "audio.%(ext)s")
    print(f"Downloading audio for video {video_id} using yt-dlp...")
    try:
        subprocess.run([
            sys.executable, "-m", "yt_dlp",
            "-f", "ba",
            "-o", out_tmpl,
            f"https://www.youtube.com/watch?v={video_id}"
        ], check=True)
        print("Audio download complete.")
    except Exception as e:
        print(f"Error downloading audio: {e}", file=sys.stderr)
        raise e

def find_audio_file(output_dir):
    for f in os.listdir(output_dir):
        if f.startswith("audio.") and not f.endswith(".part"):
            return os.path.join(output_dir, f)
    return None

def transcribe_audio(audio_path, output_json_path):
    print(f"Transcribing audio file: {audio_path} using Groq Whisper API...")
    
    client = get_groq_client()
    
    try:
        with open(audio_path, "rb") as file:
            # Call Groq Audio Transcription API with verbose_json format for timestamps
            response = client.audio.transcriptions.create(
                file=(os.path.basename(audio_path), file.read()),
                model="whisper-large-v3",
                response_format="verbose_json",
                language="en"
            )
            
        # Parse output segments
        segments = []
        # Response is an object containing a list of segments
        raw_segments = getattr(response, 'segments', [])
        
        for idx, seg in enumerate(raw_segments):
            start = float(seg.get('start', 0.0))
            end = float(seg.get('end', 0.0))
            text = seg.get('text', '').strip()
            
            segments.append({
                "text": text,
                "start": start,
                "duration": round(end - start, 2)
            })
            
        # Save to JSON
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)
            
        print(f"Successfully transcribed audio. Saved to: {output_json_path}")
        print(f"Total segments: {len(segments)}")
        return True
    except Exception as e:
        print(f"Error during Groq Whisper transcription: {e}", file=sys.stderr)
        return False

def main():
    video_id = "n6DQvrfaFKY"
    output_dir = "backend"
    output_json = os.path.join(output_dir, "transcript_raw.json")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Download audio if not present
    audio_file = find_audio_file(output_dir)
    if not audio_file:
        download_audio(video_id, output_dir)
        audio_file = find_audio_file(output_dir)
        
    if not audio_file:
        print("Could not find downloaded audio file.", file=sys.stderr)
        sys.exit(1)
        
    # 2. Transcribe using Groq Whisper API
    transcribe_audio(audio_file, output_json)

if __name__ == "__main__":
    main()
