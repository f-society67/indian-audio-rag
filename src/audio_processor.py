# src/audio_processor.py
import os
import requests
from pytubefix import YouTube
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def transcribe_audio_groq(file_path: str):
    """
    Sends the audio to Groq's Whisper endpoint.
    Returns segments with start and end timestamps.
    """
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
    Downloads audio using pytubefix to completely bypass 
    YouTube's datacenter IP bans and 403 errors on Streamlit Cloud.
    """
    # pytubefix automatically handles PoToken bypasses under the hood
    yt = YouTube(youtube_url)
    
    # Grab the best audio-only stream
    audio_stream = yt.streams.get_audio_only()
    
    # Download directly to the expected temp path
    final_path = f"{output_base_path}.mp3"
    audio_stream.download(filename=final_path)
    
    return final_path