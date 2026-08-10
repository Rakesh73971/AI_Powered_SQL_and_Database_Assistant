from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from app.db.config import settings

def get_llm():
    """
    Returns a configured ChatGoogleGenerativeAI instance for running chain steps.
    """
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0.0
    )

def get_embeddings():
    """
    Returns a configured GoogleGenerativeAIEmbeddings instance for ChromaDB schema embedding.
    """
    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=settings.google_api_key
    )
