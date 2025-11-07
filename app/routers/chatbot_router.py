"""
Chatbot Router - RAG-based Q&A API
"""
import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.models.chatbot_models import ChatbotQuery, ChatbotResponse, RetrievedDocumentResponse
from app.services.rag.retrieval_service import get_retrieval_service
from app.services.rag.generation_service import get_generation_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ask", response_model=ChatbotResponse)
async def ask_chatbot(query: ChatbotQuery):
    """
    Ask the Alpha Mini chatbot a question
    
    This endpoint uses RAG (Retrieval-Augmented Generation) to:
    1. Retrieve relevant documents from ChromaDB
    2. Generate an answer using LLM based on retrieved context
    
    Request Body:
        {
            "question": "Your question here"
        }
    
    Example:
        POST /chatbot/ask
        {
            "question": "Alpha Mini có thể làm gì?"
        }
        
    Returns:
        ChatbotResponse with answer, sources, and metadata
    """
    try:
        logger.info(f"Received chatbot query: '{query.question}'")
        
        # Get services
        retrieval_service = get_retrieval_service()
        generation_service = get_generation_service()
        
        # Retrieve relevant documents with default settings
        documents = retrieval_service.retrieve(
            query=query.question
            # top_k and filters use defaults from config
        )
        
        logger.info(f"Retrieved {len(documents)} documents")
        
        # Get retrieval statistics
        retrieval_stats = retrieval_service.get_retrieval_stats(documents)
        
        # Generate answer with fallback
        result = generation_service.generate_with_fallback(
            query=query.question,
            documents=documents
        )
        
        # Format response
        response = ChatbotResponse(
            question=query.question,
            answer=result["answer"],
            has_answer=result["has_answer"],
            documents_used=result["documents_used"],
            documents=[
                RetrievedDocumentResponse(
                    id=doc.id,
                    content=doc.content,
                    metadata=doc.metadata,
                    score=doc.score
                )
                for doc in documents
            ],
            model=result.get("model"),
            provider=result.get("provider"),
            tokens_used=result.get("tokens_used"),
            retrieval_stats=retrieval_stats
        )
        
        logger.info(f"Generated answer successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error processing chatbot query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )


@router.get("/health")
async def chatbot_health():
    """
    Check chatbot system health
    
    Returns status of:
    - Vector store (ChromaDB)
    - Embedding service
    - LLM service
    """
    try:
        from app.services.rag.vector_store_service import get_vector_store_service
        from app.services.rag.embedding_service import get_embedding_service
        
        vector_store = get_vector_store_service()
        embedding_service = get_embedding_service()
        generation_service = get_generation_service()
        
        doc_count = vector_store.get_document_count()
        embedding_dim = embedding_service.get_dimension()
        
        return JSONResponse(
            content={
                "status": "healthy",
                "components": {
                    "vector_store": {
                        "status": "ok",
                        "document_count": doc_count,
                        "collection": vector_store.collection_name
                    },
                    "embedding_service": {
                        "status": "ok",
                        "model": embedding_service.model_name,
                        "dimension": embedding_dim
                    },
                    "generation_service": {
                        "status": "ok",
                        "provider": generation_service.provider,
                        "model": generation_service.model
                    }
                }
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@router.get("/stats")
async def get_knowledge_base_stats():
    """
    Get statistics about the knowledge base
    
    Returns:
        Statistics about documents in ChromaDB
    """
    try:
        from app.services.rag.vector_store_service import get_vector_store_service
        from app.services.rag.config import rag_config
        
        vector_store = get_vector_store_service()
        
        # Test connection first
        if not vector_store.test_connection():
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "Cannot connect to ChromaDB server",
                    "mode": rag_config.CHROMA_MODE,
                    "host": rag_config.CHROMA_HOST if rag_config.CHROMA_MODE == "remote" else "local"
                }
            )
        
        # Get document count safely
        try:
            doc_count = vector_store.get_document_count()
        except Exception as e:
            logger.warning(f"Could not get document count: {str(e)}")
            doc_count = 0
        
        # Try to get all documents to analyze
        categories = {}
        try:
            if doc_count > 0:
                all_docs = vector_store.get_all_documents()
                
                # Analyze by category
                if all_docs.get('metadatas'):
                    for metadata in all_docs['metadatas']:
                        category = metadata.get('category', 'unknown')
                        categories[category] = categories.get(category, 0) + 1
        except Exception as e:
            logger.warning(f"Could not analyze categories: {str(e)}")
        
        return JSONResponse(
            content={
                "status": "connected",
                "mode": rag_config.CHROMA_MODE,
                "collection_name": vector_store.collection_name,
                "total_documents": doc_count,
                "categories": categories,
                "server": f"{rag_config.CHROMA_HOST}:{rag_config.CHROMA_PORT}" if rag_config.CHROMA_MODE == "remote" else "local"
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Error getting stats",
                "detail": str(e),
                "mode": rag_config.CHROMA_MODE if 'rag_config' in locals() else "unknown"
            }
        )


@router.post("/query")
async def query_chatbot(query: ChatbotQuery):
    """
    Simple query endpoint for frontend integration
    
    Returns only the answer that frontend needs.
    
    Request Body:
        {
            "question": "Câu hỏi của bạn"
        }
    
    Example:
        POST /chatbot/query
        {
            "question": "Robot có thể làm gì?"
        }
        
    Returns:
        {
            "answer": "Tôi là trợ lý AI của robot Alpha Mini..."
        }
    """
    try:
        logger.info(f"Frontend query: '{query.question}'")
        
        retrieval_service = get_retrieval_service()
        generation_service = get_generation_service()
        
        # Retrieve documents
        documents = retrieval_service.retrieve(query=query.question)
        logger.info(f"Retrieved {len(documents)} documents")
        
        # Generate answer
        result = generation_service.generate_with_fallback(
            query=query.question,
            documents=documents
        )
        
        # Only return answer for frontend
        return JSONResponse(content={"answer": result["answer"]})
        
    except Exception as e:
        logger.error(f"Error in frontend query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )


@router.get("/categories")
async def get_categories():
    """
    Get all available categories in the knowledge base
    
    Returns:
        List of categories with document counts
        
    Example Response:
        {
            "categories": [
                {"name": "features", "count": 10},
                {"name": "faq", "count": 15},
                {"name": "user_guide", "count": 8}
            ],
            "total": 33
        }
    """
    try:
        from app.services.rag.vector_store_service import get_vector_store_service
        
        vector_store = get_vector_store_service()
        doc_count = vector_store.get_document_count()
        
        categories_dict = {}
        if doc_count > 0:
            all_docs = vector_store.get_all_documents()
            
            if all_docs.get('metadatas'):
                for metadata in all_docs['metadatas']:
                    category = metadata.get('category', 'unknown')
                    categories_dict[category] = categories_dict.get(category, 0) + 1
        
        categories_list = [
            {"name": cat, "count": count}
            for cat, count in sorted(categories_dict.items())
        ]
        
        return JSONResponse(
            content={
                "categories": categories_list,
                "total": doc_count
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting categories: {str(e)}"
        )
