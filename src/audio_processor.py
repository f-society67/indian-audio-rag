# src/audio_processor.py
import os
import requests
import yt_dlp
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
        # Whisper supports m4a files encoded as mp4
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
    Downloads the native M4A stream using yt-dlp with Chrome impersonation.
    curl-cffi handles the TLS fingerprinting to bypass YouTube 403 IP blocks natively.
    """
    final_path = f"{output_base_path}.m4a"
    
    ydl_opts = {
        'format': '140',  # 140 is YouTube's native M4A audio stream (no ffmpeg needed)
        'outtmpl': final_path,
        'impersonate': 'chrome',
        'quiet': True,
        'no_warnings': True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
        
    if not os.path.exists(final_path):
        raise FileNotFoundError(f"Failed to download audio to {final_path}")
        
    return final_path