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
        # Whisper natively supports m4a format
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
    Delegates YouTube extraction to the public Piped API network.
    100% free, no API keys, no billing info.
    """
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", youtube_url)
    video_id = match.group(1) if match else None
    
    if not video_id:
        raise ValueError("Could not extract a valid YouTube video ID.")
        
    # Hit the free Piped API network
    api_url = f"https://pipedapi.kavin.rocks/streams/{video_id}"
    response = requests.get(api_url)
    response.raise_for_status()
    
    # Piped returns a list of audio streams. 
    audio_streams = response.json().get("audioStreams", [])
    if not audio_streams:
        raise ValueError("No audio streams found for this video.")
        
    # Find an m4a stream (highly compressed, fast to download)
    stream_url = next((stream['url'] for stream in audio_streams if stream['format'] == 'M4A'), audio_streams[0]['url'])
    
    # Download the actual audio data directly to the Streamlit server
    audio_data = requests.get(stream_url)
    
    final_path = f"{output_base_path}.m4a"
    with open(final_path, "wb") as f:
        f.write(audio_data.content)
        
    return final_path