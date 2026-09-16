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
    Bulletproof YouTube downloader using Invidious API with rotating servers.
    Bypasses the current global Piped API outages.
    """
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", youtube_url)
    video_id = match.group(1) if match else None
    
    if not video_id:
        raise ValueError("Could not extract a valid YouTube video ID.")
        
    # Pool of active Invidious instances
    invidious_instances = [
        "https://invidious.nerdvpn.de",
        "https://inv.tux.pizza",
        "https://invidious.perennialte.ch",
        "https://invidious.privacydev.net",
        "https://inv.nadeko.net"
    ]
    
    stream_url = None
    
    # Cycle through servers until one successfully returns the data
    for instance in invidious_instances:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if "adaptiveFormats" in data:
                # Find the highest compressed audio-only stream (m4a/webm)
                for stream in data["adaptiveFormats"]:
                    if stream.get("type", "").startswith("audio/"):
                        stream_url = stream["url"]
                        break
            
            if stream_url:
                break # We got the URL, exit the loop
        except Exception:
            continue
            
    if not stream_url:
        raise ValueError("All Invidious backup servers failed or no audio stream found. YouTube might be blocking them.")
        
    # Download the actual audio data directly to the Streamlit server
    audio_data = requests.get(stream_url)
    final_path = f"{output_base_path}.m4a"
    
    with open(final_path, "wb") as f:
        f.write(audio_data.content)
        
    return final_path