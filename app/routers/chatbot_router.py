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
    
    Args:
        query: ChatbotQuery with question and optional parameters
        
    Returns:
        ChatbotResponse with answer and metadata
    """
    try:
        logger.info(f"Received chatbot query: '{query.question}'")
        
        # Get services
        retrieval_service = get_retrieval_service()
        generation_service = get_generation_service()
        
        # Retrieve relevant documents
        documents = retrieval_service.retrieve(
            query=query.question,
            top_k=query.top_k,
            filters=query.filters
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
        
        vector_store = get_vector_store_service()
        
        # Get all documents to analyze
        all_docs = vector_store.get_all_documents()
        
        # Analyze by category
        categories = {}
        if all_docs.get('metadatas'):
            for metadata in all_docs['metadatas']:
                category = metadata.get('category', 'unknown')
                categories[category] = categories.get(category, 0) + 1
        
        return JSONResponse(
            content={
                "total_documents": vector_store.get_document_count(),
                "collection_name": vector_store.collection_name,
                "categories": categories,
                "persist_directory": vector_store.persist_directory
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting stats: {str(e)}"
        )
