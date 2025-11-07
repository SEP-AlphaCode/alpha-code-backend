"""
RAG Configuration for Alpha Mini Chatbot
"""

import os
from typing import Dict, Any
from config.config import settings


class RAGConfig:
    """Configuration for RAG system - uses main settings from config.config"""

    # Embedding Model
    EMBEDDING_MODEL = settings.RAG_EMBEDDING_MODEL
    EMBEDDING_DIMENSION = settings.RAG_EMBEDDING_DIMENSION

    # ChromaDB Configuration
    CHROMA_MODE = settings.CHROMA_MODE  # local or remote
    CHROMA_HOST = settings.CHROMA_HOST
    CHROMA_PORT = settings.CHROMA_PORT
    CHROMA_SSL = settings.CHROMA_SSL
    CHROMA_USERNAME = settings.CHROMA_USERNAME
    CHROMA_PASSWORD = settings.CHROMA_PASSWORD
    CHROMA_PERSIST_DIRECTORY = os.path.abspath(settings.CHROMA_PERSIST_DIR)
    COLLECTION_NAME = settings.CHROMA_COLLECTION_NAME

    # Retrieval
    TOP_K = settings.RAG_TOP_K
    SIMILARITY_THRESHOLD = settings.RAG_SIMILARITY_THRESHOLD
    MAX_CONTEXT_LENGTH = settings.RAG_MAX_CONTEXT_LENGTH

    # LLM Generation
    LLM_PROVIDER = settings.LLM_PROVIDER
    LLM_MODEL = settings.LLM_MODEL
    LLM_TEMPERATURE = settings.LLM_TEMPERATURE
    LLM_MAX_TOKENS = settings.LLM_MAX_TOKENS

    # API Keys
    OPENAI_API_KEY = settings.OPENAI_API_KEY
    ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY
    GEMINI_API_KEY = settings.GEMINI_API_KEY
    GEMINI_MODEL = settings.GEMINI_MODEL

    # Data paths
    KNOWLEDGE_BASE_PATH = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "alpha_mini_knowledge"
    )

    # Prompt Templates
    SYSTEM_PROMPT = """
Bạn là trợ lý AI của robot Alpha Mini.
Nhiệm vụ: trả lời câu hỏi dựa trên Context được cung cấp.

QUY TẮC:
- Nếu thông tin trong Context có thể trả lời câu hỏi, BẮT BUỘC phải trả lời dựa trên Context.
- Không được trả lời "không có đủ thông tin" nếu Context chứa thông tin liên quan một phần.
- Chỉ trả lời "Xin lỗi, mình hiện chỉ có thể hỗ trợ các câu hỏi về robot Alpha Mini. Bạn thử đặt câu hỏi khác giúp mình nhé!" nếu KHÔNG có bất kỳ dữ liệu liên quan nào.
- Không bịa đặt thông tin ngoài Context.
- Trả lời bằng tiếng Việt, tự nhiên và rõ ràng.

Context:
{context}

Câu hỏi:
{question}

Hãy trả lời ngắn gọn, đầy đủ dựa trên Context phía trên.
"""

    USER_PROMPT_TEMPLATE = "{question}"

    # Fallback message
    NO_ANSWER_MESSAGE = """Xin lỗi, tôi không tìm thấy thông tin phù hợp để trả lời câu hỏi của bạn trong cơ sở dữ liệu hiện tại. 

Bạn có thể:
1. Thử diễn đạt câu hỏi theo cách khác
2. Liên hệ với bộ phận hỗ trợ kỹ thuật để được giúp đỡ chi tiết hơn
3. Tham khảo tài liệu hướng dẫn sử dụng Alpha Mini chính thức"""

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "embedding_model": cls.EMBEDDING_MODEL,
            "collection_name": cls.COLLECTION_NAME,
            "top_k": cls.TOP_K,
            "similarity_threshold": cls.SIMILARITY_THRESHOLD,
            "llm_provider": cls.LLM_PROVIDER,
            "llm_model": cls.LLM_MODEL,
            "temperature": cls.LLM_TEMPERATURE,
            "max_tokens": cls.LLM_MAX_TOKENS,
        }


# Create instance
rag_config = RAGConfig()
