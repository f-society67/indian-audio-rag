# src/audio_processor.py
import os
import requests
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
        files = {"file": (os.path.basename(file_path), f, "audio/mpeg")}
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
    Directly uses the Cobalt API for audio extraction.
    Bypasses datacenter IP bans natively without relying on pytubefix.
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "url": youtube_url,
        "isAudioOnly": True,
        "downloadMode": "audio",
        "aFormat": "mp3"
    }
    
    # Pool of active Cobalt instances
    endpoints = [
        "https://api.cobalt.tools/api/json",
        "https://co.wuk.sh/api/json",
        "https://cobalt.qewertyy.dev/api/json"
    ]
    
    download_link = None
    for api_url in endpoints:
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") != "error" and data.get("url"):
                    download_link = data["url"]
                    break
        except Exception:
            continue
            
    if not download_link:
        raise ValueError("All Cobalt API endpoints failed or timed out.")
        
    # Download the extracted MP3 file
    audio_data = requests.get(download_link)
    final_path = f"{output_base_path}.mp3"
    
    with open(final_path, "wb") as f:
        f.write(audio_data.content)
        
    return final_path