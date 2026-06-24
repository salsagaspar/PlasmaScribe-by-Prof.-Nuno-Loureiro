import re
import json

def clean_text(text):
    # Remove XML/HTML tags and timestamp tags like <00:00:03.280>
    text = re.sub(r'<[^>]+>', '', text)
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_time(time_str):
    # Format: HH:MM:SS.mmm
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds

def main():
    filepath = "backend/auto_sub.en.vtt"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by double newline to separate cue blocks
    blocks = content.split('\n\n')
    
    raw_segments = []
    for block in blocks:
        lines = block.strip().split('\n')
        if not lines or '-->' not in lines[0]:
            continue
            
        time_line = lines[0]
        match = re.match(r'(\d+:\d+:\d+\.\d+) --> (\d+:\d+:\d+\.\d+)', time_line)
        if not match:
            continue
            
        start_time = parse_time(match.group(1))
        end_time = parse_time(match.group(2))
        
        # Extract and clean text lines
        text_lines = []
        for line in lines[1:]:
            cleaned = clean_text(line)
            if cleaned:
                text_lines.append(cleaned)
                
        if not text_lines:
            continue
            
        # The new text is always the last line in the block (YouTube auto-caption scrolling pattern)
        new_text = text_lines[-1]
        
        raw_segments.append({
            "text": new_text,
            "start": start_time,
            "end": end_time
        })
        
    if not raw_segments:
        print("No segments found.")
        return
        
    # 1. Merge consecutive segments with the same text
    merged_same = []
    current = raw_segments[0].copy()
    
    for next_seg in raw_segments[1:]:
        if next_seg["text"] == current["text"]:
            current["end"] = next_seg["end"]
        else:
            merged_same.append(current)
            current = next_seg.copy()
    merged_same.append(current)
    
    # 2. Group into sentences/chunks (around 15-20 words or 8-10 seconds)
    grouped = []
    acc_text = []
    acc_start = None
    acc_end = None
    
    for seg in merged_same:
        text = seg["text"]
        if acc_start is None:
            acc_start = seg["start"]
        acc_end = seg["end"]
        
        # Avoid duplicate words at transitions
        # Sometimes YouTube repeats the last word(s) of the previous line at the start of the next line
        # Let's do a simple check to deduplicate consecutive words
        words = text.split()
        for w in words:
            if not acc_text or acc_text[-1].lower() != w.lower():
                acc_text.append(w)
        
        combined_text = " ".join(acc_text)
        word_count = len(acc_text)
        duration = acc_end - acc_start
        
        # Split condition: 15 words or 8.0 seconds duration
        if word_count >= 15 or duration >= 8.0:
            final_text = combined_text.strip()
            if final_text:
                final_text = final_text[0].upper() + final_text[1:]
                # Add punctuation if missing (let's just capitalize and let LLM add punctuation during translation)
                grouped.append({
                    "text": final_text,
                    "start": round(acc_start, 2),
                    "duration": round(duration, 2)
                })
            acc_text = []
            acc_start = None
            acc_end = None
            
    # Flush remaining
    if acc_text and acc_start is not None:
        combined_text = " ".join(acc_text)
        final_text = combined_text.strip()
        if final_text:
            final_text = final_text[0].upper() + final_text[1:]
            grouped.append({
                "text": final_text,
                "start": round(acc_start, 2),
                "duration": round(acc_end - acc_start, 2)
            })
            
    # Print statistics
    print(f"Original segments: {len(raw_segments)}")
    print(f"Merged same-text segments: {len(merged_same)}")
    print(f"Grouped sentence segments: {len(grouped)}")
    
    print("\nFirst 10 grouped segments:")
    for seg in grouped[:10]:
        print(f"[{seg['start']}s, dur={seg['duration']}s]: {seg['text']}")
        
    output_path = "backend/transcript_raw_0hiy7hxjZ5s.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(grouped, f, ensure_ascii=False, indent=2)
    print(f"Saved grouped segments to {output_path}")

if __name__ == "__main__":
    main()
