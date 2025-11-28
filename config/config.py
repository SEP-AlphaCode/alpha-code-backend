import os
from dotenv import load_dotenv

load_dotenv()  # load .env file

class Settings:
    TITLE = os.getenv("APP_TITLE", "My API")
    DESCRIPTION = os.getenv("APP_DESCRIPTION", "API description")
    VERSION = os.getenv("APP_VERSION", "0.0.1")
    CONTACT_NAME = os.getenv("APP_CONTACT_NAME", "")
    CONTACT_EMAIL = os.getenv("APP_CONTACT_EMAIL", "")
    LICENSE_NAME = os.getenv("APP_LICENSE_NAME", "")
    LICENSE_URL = os.getenv("APP_LICENSE_URL", "")

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

    # RAG Chatbot Configuration
    RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    RAG_EMBEDDING_DIMENSION = int(os.getenv("RAG_EMBEDDING_DIMENSION", 384))
    
    # ChromaDB Configuration
    CHROMA_MODE = os.getenv("CHROMA_MODE", "local")  # local or remote
    CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
    CHROMA_SSL = os.getenv("CHROMA_SSL", "false").lower() == "true"
    CHROMA_USERNAME = os.getenv("CHROMA_USERNAME", "")
    CHROMA_PASSWORD = os.getenv("CHROMA_PASSWORD", "")
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "alpha_mini_knowledge")
    
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", 5))
    RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", 0.7))
    RAG_MAX_CONTEXT_LENGTH = int(os.getenv("RAG_MAX_CONTEXT_LENGTH", 4000))
    
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.3))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 1000))
    
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

settings = Settings()

