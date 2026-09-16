# src/audio_processor.py
import os
import requests
import re
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def transcribe_audio_groq(file_path: str):
    """Sends the audio to Groq's Whisper endpoint."""
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    
    data = {
        "model": "whisper-large-v3",
        "response_format": "verbose_json"
    }
    
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "audio/mp4")}
        response = requests.post(url, headers=headers, files=files, data=data)
        
    response.raise_for_status()
    response_data = response.json()
    
    all_segments = []
    for segment in response_data.get("segments", []):
        all_segments.append({
            "text": segment.get("text", ""),
            "start_time": float(segment.get("start", 0.0)),
            "end_time": float(segment.get("end", 0.0))
        })
        
    return all_segments

def download_youtube_audio(youtube_url: str, output_base_path: str):
    """
    Bulletproof YouTube downloader using a rotating list of Piped APIs.
    """
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", youtube_url)
    video_id = match.group(1) if match else None
    
    if not video_id:
        raise ValueError("Could not extract a valid YouTube video ID.")
        
    # Pool of active Piped instances to prevent single-node failure
    piped_instances = [
        "https://api.piped.private.coffee",
        "https://pipedapi.moomoo.me",
        "https://pipedapi.tokhmi.xyz",
        "https://pipedapi.phoenixthrush.com",
        "https://pipedapi.kavin.rocks"
    ]
    
    audio_streams = None
    
    # Cycle through servers until one works
    for instance in piped_instances:
        try:
            api_url = f"{instance}/streams/{video_id}"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if "audioStreams" in data and len(data["audioStreams"]) > 0:
                audio_streams = data["audioStreams"]
                break
        except Exception:
            continue
            
    if not audio_streams:
        raise ValueError("All backup Piped servers failed. YouTube might be blocking them globally.")
        
    stream_url = next((stream['url'] for stream in audio_streams if stream['format'] == 'M4A'), audio_streams[0]['url'])
    
    audio_data = requests.get(stream_url)
    final_path = f"{output_base_path}.m4a"
    
    with open(final_path, "wb") as f:
        f.write(audio_data.content)
        
    return final_path