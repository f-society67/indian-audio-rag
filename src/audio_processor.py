# src/audio_processor.py
import re
from youtube_transcript_api import YouTubeTranscriptApi

def download_youtube_audio(youtube_url: str, output_base_path: str = None):
    """
    Instead of downloading audio, we extract the video ID and pass it along.
    This takes 0 seconds and bypasses all 403 data center blocks.
    """
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", youtube_url)
    video_id = match.group(1) if match else None
    
    if not video_id:
        raise ValueError("Could not extract a valid YouTube video ID from the URL.")
        
    return video_id 

def transcribe_audio_groq(video_id: str):
    """
    Bypasses Groq Whisper entirely and fetches YouTube's native transcript instantly.
    Formats the text to perfectly match the structure your Pinecone indexer expects.
    """
    # Updated to the new v1.2.4 syntax: initialize the class, then fetch
    ytt_api = YouTubeTranscriptApi()
    raw_transcript = ytt_api.fetch(video_id)
    
    all_segments = []
    for entry in raw_transcript:
        all_segments.append({
            "text": entry.get("text", ""),
            "start_time": float(entry.get("start", 0.0)),
            "end_time": float(entry.get("start", 0.0)) + float(entry.get("duration", 0.0))
        })
        
    return all_segments