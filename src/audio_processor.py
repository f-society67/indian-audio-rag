# src/audio_processor.py
import os
import requests
import yt_dlp
import streamlit as st
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
    Downloads the best audio stream from YouTube and compresses to 64 kbps MP3.
    Uses browser cookies from Streamlit secrets to bypass data center IP blocks.
    """
    cookie_path = f"{output_base_path}_cookies.txt"
    
    # Safely pull the cookie block from Streamlit Secrets or local .env
    youtube_cookies = None
    try:
        if "YOUTUBE_COOKIES" in st.secrets:
            youtube_cookies = st.secrets["YOUTUBE_COOKIES"]
    except Exception:
        youtube_cookies = os.getenv("YOUTUBE_COOKIES")
        
    # If cookies exist, write them to a temporary file
    if youtube_cookies:
        with open(cookie_path, "w") as f:
            f.write(youtube_cookies)
            
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f"{output_base_path}.%(ext)s",
        'js_runtimes': {'node': {}},
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '64',
        }],
        'quiet': True,
        'nocheckcertificate': True
    }
    
    # Tell yt-dlp to use the cookie file we just generated
    if youtube_cookies:
        ydl_opts['cookiefile'] = cookie_path
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
    finally:
        # Immediately delete the sensitive cookie file after the download finishes
        if os.path.exists(cookie_path):
            os.remove(cookie_path)
    
    return f"{output_base_path}.mp3"