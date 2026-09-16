# app.py
import streamlit as st
import os
import tempfile
import uuid
import re
from src.audio_processor import transcribe_audio_groq, download_youtube_audio
from src.rag_pipeline import index_audio_segments, query_audio_rag

st.set_page_config(page_title="Indic Audio RAG", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_files_registry" not in st.session_state:
    st.session_state.uploaded_files_registry = {}  
if "active_audio" not in st.session_state:
    st.session_state.active_audio = None

st.title("🎙️ Indian Language Audio Knowledge Engine")

with st.sidebar:
    st.header("1. Add Audio Context")
    tab1, tab2 = st.tabs(["Upload Local File", "YouTube URL"])
    
    with tab1:
        uploaded_file = st.file_uploader("Choose an audio file", type=['mp3', 'wav', 'm4a'])
        if st.button("Process Local File") and uploaded_file:
            if uploaded_file.name not in st.session_state.uploaded_files_registry:
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                        file_bytes = uploaded_file.getvalue()
                        tmp_file.write(file_bytes)
                        temp_path = tmp_file.name
                    try:
                        segments = transcribe_audio_groq(temp_path)
                        index_audio_segments(segments, uploaded_file.name)
                        st.session_state.uploaded_files_registry[uploaded_file.name] = file_bytes
                        st.success(f"{uploaded_file.name} indexed successfully!")
                    except Exception as e:
                        st.error(f"Error processing audio: {e}")
                    finally:
                        os.remove(temp_path)
            else:
                st.warning("File already processed.")
                
    with tab2:
        youtube_url = st.text_input("Enter YouTube Video URL")
        if st.button("Process YouTube") and youtube_url:
            source_name = f"YouTube: {youtube_url.split('v=')[-1][:11]}"
            if source_name not in st.session_state.uploaded_files_registry:
                with st.spinner("Delegating download and processing audio..."):
                    
                    temp_dir = tempfile.gettempdir()
                    unique_id = uuid.uuid4().hex
                    base_path = os.path.join(temp_dir, f"yt_audio_{unique_id}")
                    final_audio_path = f"{base_path}.m4a"
                    
                    try:
                        download_youtube_audio(youtube_url, base_path)
                        
                        with open(final_audio_path, "rb") as f:
                            file_bytes = f.read()
                        
                        segments = transcribe_audio_groq(final_audio_path)
                        index_audio_segments(segments, source_name)
                        
                        st.session_state.uploaded_files_registry[source_name] = file_bytes
                        st.success(f"YouTube audio indexed successfully!")
                    except Exception as e:
                        st.error(f"Error processing YouTube audio: {e}")
                    finally:
                        if os.path.exists(final_audio_path):
                            os.remove(final_audio_path)
            else:
                st.warning("This YouTube URL is already processed.")

    st.divider()
    st.header("2. Context Selection")
    available_files = list(st.session_state.uploaded_files_registry.keys())
    
    if available_files:
        selected_files = st.multiselect(
            "Select sources for the AI to search:",
            options=available_files,
            default=available_files
        )
        st.header("3. Audio Player")
        st.session_state.active_audio = st.selectbox("Select file to play:", options=available_files)
        
        if st.session_state.active_audio:
            audio_bytes = st.session_state.uploaded_files_registry[st.session_state.active_audio]
            if audio_bytes:
                st.audio(audio_bytes)
    else:
        selected_files = []
        st.info("Add audio sources to begin.")

st.header("Ask Questions")
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("E.g., What did the speaker say about consideration?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not selected_files:
            st.warning("Please add and select at least one audio context.")
        else:
            with st.spinner("Searching audio context..."):
                try:
                    response = query_audio_rag(prompt, selected_sources=selected_files)
                    answer = response["answer"]
                    sources = response["source_documents"]
                    
                    formatted_answer = re.sub(r'\[([\d\.]+)s\]', r'**[\1s]** ⏱️', answer)
                    st.markdown(formatted_answer)
                    
                    with st.expander("View Source Transcripts"):
                        for i, doc in enumerate(sources):
                            start = doc.metadata.get('start_time', 0)
                            end = doc.metadata.get('end_time', 0)
                            source_file = doc.metadata.get('source', 'Unknown File')
                            st.caption(f"**Source {i+1}: {source_file}** ({start}s - {end}s)")
                            st.write(f"*{doc.page_content}*")
                            
                    st.session_state.messages.append({"role": "assistant", "content": formatted_answer})
                    
                except Exception as e:
                    st.error(f"Error querying the database: {e}")