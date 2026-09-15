# src/rag_pipeline.py
import os
from langchain_core.documents import Document
from langchain_cohere import CohereEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

def get_vector_store():
    """Initializes the Cohere embeddings and Pinecone vector store."""
    embeddings = CohereEmbeddings(
        model="embed-multilingual-v3.0",
        cohere_api_key=os.getenv("COHERE_API_KEY")
    )
    
    index_name = os.getenv("PINECONE_INDEX_NAME")
    
    vector_store = PineconeVectorStore(
        index_name=index_name, 
        embedding=embeddings,
        pinecone_api_key=os.getenv("PINECONE_API_KEY")
    )
    return vector_store

def index_audio_segments(segments: list, source_name: str):
    """Converts Groq utterances to Documents, groups them, and pushes to Pinecone."""
    
    # --- DIAGNOSTICS ---
    print(f"\n[DEBUG] --- PROCESSING NEW AUDIO ---")
    print(f"[DEBUG] Total utterances received: {len(segments)}")
    
    docs = []
    current_text = ""
    current_start = -1
    
    for seg in segments:
        if not seg.get("text", "").strip():
            continue
            
        if current_start == -1:
            current_start = seg.get("start_time", 0.0)
            
        current_text += seg["text"].strip() + " "
        
        if len(current_text) >= 600:
            doc = Document(
                page_content=current_text.strip(),
                metadata={
                    "start_time": round(current_start, 2),
                    "end_time": round(seg.get("end_time", 0.0), 2),
                    "source": source_name
                }
            )
            docs.append(doc)
            current_text = ""
            current_start = -1
            
    if current_text.strip():
        end_time = segments[-1].get("end_time", 0.0) if segments else 0.0
        doc = Document(
            page_content=current_text.strip(),
            metadata={
                "start_time": round(current_start, 2),
                "end_time": round(end_time, 2),
                "source": source_name
            }
        )
        docs.append(doc)
    
    print(f"[DEBUG] Total grouped chunks created: {len(docs)}")
    
    if docs:
        vector_store = get_vector_store()
        vector_store.add_documents(docs)
        print(f"[DEBUG] Successfully saved {len(docs)} chunks to Pinecone!")
    else:
        print("[DEBUG] WARNING: 0 chunks created. The audio is either completely silent, or the transcription failed.")
    print(f"[DEBUG] ----------------------------------\n")
        
    return True

def format_docs_with_timestamps(docs):
    """Extracts text AND timestamps so the LLM can actually see them."""
    formatted = []
    for doc in docs:
        start = doc.metadata.get('start_time', 'Unknown')
        end = doc.metadata.get('end_time', 'Unknown')
        formatted.append(f"[Start: {start}s, End: {end}s] {doc.page_content}")
    return "\n\n".join(formatted)

def query_audio_rag(user_query: str, selected_sources: list = None):
    """Retrieves context from Pinecone, filters by source, and generates an answer."""
    
    # Updated to the currently supported OpenAI GPT-OSS model on Groq's developer tier
    llm = ChatGroq(
        model="openai/gpt-oss-120b", 
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,
        max_retries=6
    )
    
    vector_store = get_vector_store()
    
    search_kwargs = {"k": 15}
    if selected_sources:
        search_kwargs["filter"] = {"source": {"$in": selected_sources}}
        
    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
    
    docs = retriever.invoke(user_query)
    formatted_context = format_docs_with_timestamps(docs)
    
    if not docs:
        return {
            "answer": "I couldn't find any relevant information in the provided audio context to answer your question.",
            "source_documents": []
        }
        
    prompt = ChatPromptTemplate.from_template(
        "You are an AI assistant answering questions based on an audio transcript. "
        "Use the provided context blocks to answer the user's question. "
        "Each context block includes a [Start Time] and [End Time]. "
        "You MUST cite the exact Start Time in your answer when referencing a fact, formatted exactly like this: [12.5s] or [145.2s].\n\n"
        "If the answer is not contained in the context, say so.\n\n"
        "Context:\n{context}\n\n"
        "Question: {question}"
    )
    
    chain = prompt | llm | StrOutputParser()
    
    answer = chain.invoke({
        "context": formatted_context,
        "question": user_query
    })
    
    return {
        "answer": answer,
        "source_documents": docs
    }