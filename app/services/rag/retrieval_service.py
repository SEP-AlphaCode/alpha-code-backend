"""
Retrieval Service for RAG System
Handles document retrieval and ranking
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .config import rag_config
from .vector_store_service import get_vector_store_service

logger = logging.getLogger(__name__)


@dataclass
class RetrievedDocument:
    """Container for a retrieved document"""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float  # Similarity score (higher is better)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "score": self.score
        }


class RetrievalService:
    """Service for retrieving relevant documents"""
    
    def __init__(self):
        """Initialize retrieval service"""
        self.vector_store = get_vector_store_service()
        self.similarity_threshold = rag_config.SIMILARITY_THRESHOLD
        self.top_k = rag_config.TOP_K
        logger.info("Retrieval service initialized")
    
    def retrieve(
        self,
        query: str,
        top_k: int = None,
        filters: Dict[str, Any] = None,
        similarity_threshold: float = None
    ) -> List[RetrievedDocument]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: User query
            top_k: Number of documents to retrieve
            filters: Metadata filters (e.g., {"category": "features"})
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of retrieved documents
        """
        try:
            top_k = top_k or self.top_k
            similarity_threshold = similarity_threshold or self.similarity_threshold
            
            logger.info(f"Retrieving documents for query: '{query[:50]}...'")
            logger.info(f"  top_k={top_k}, threshold={similarity_threshold}")
            
            # Query vector store - only pass filters if not None and not empty
            query_params = {
                "query_text": query,
                "n_results": top_k
            }
            
            if filters and len(filters) > 0:
                query_params["where"] = filters
            
            results = self.vector_store.query(**query_params)
            
            # Parse results
            documents = []
            if results['documents'] and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    # Convert distance to similarity score (1 - distance for cosine)
                    distance = results['distances'][0][i]
                    similarity = 1 - distance
                    
                    # Filter by threshold
                    if similarity >= similarity_threshold:
                        doc = RetrievedDocument(
                            id=results['ids'][0][i] if 'ids' in results else f"doc_{i}",
                            content=results['documents'][0][i],
                            metadata=results['metadatas'][0][i] if 'metadatas' in results else {},
                            score=similarity
                        )
                        documents.append(doc)
            
            logger.info(f"Retrieved {len(documents)} documents above threshold")
            
            # Sort by score descending
            documents.sort(key=lambda x: x.score, reverse=True)
            
            return documents
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            raise
    
    def format_context(
        self,
        documents: List[RetrievedDocument],
        max_length: int = None
    ) -> str:
        """
        Format retrieved documents into context string for LLM
        
        Args:
            documents: List of retrieved documents
            max_length: Maximum context length in characters
            
        Returns:
            Formatted context string
        """
        if not documents:
            return "Không tìm thấy thông tin liên quan."
        
        max_length = max_length or rag_config.MAX_CONTEXT_LENGTH
        
        context_parts = []
        current_length = 0
        
        for idx, doc in enumerate(documents, 1):
            # Format each document with metadata
            category = doc.metadata.get('category', 'unknown')
            source = doc.metadata.get('source', 'N/A')
            
            doc_text = f"""[Tài liệu {idx} - {category}]
Nguồn: {source}
Nội dung: {doc.content}
Điểm liên quan: {doc.score:.2f}

"""
            
            # Check if adding this document exceeds max length
            if current_length + len(doc_text) > max_length:
                logger.warning(f"Context truncated at {idx-1} documents (length: {current_length})")
                break
            
            context_parts.append(doc_text)
            current_length += len(doc_text)
        
        return "\n".join(context_parts)
    
    def rerank_documents(
        self,
        documents: List[RetrievedDocument],
        query: str
    ) -> List[RetrievedDocument]:
        """
        Rerank documents using additional scoring (placeholder for future enhancement)
        
        Args:
            documents: List of retrieved documents
            query: Original query
            
        Returns:
            Reranked list of documents
        """
        # For now, just return documents sorted by score
        # Future: Implement cross-encoder reranking, BM25, etc.
        return sorted(documents, key=lambda x: x.score, reverse=True)
    
    def get_retrieval_stats(self, documents: List[RetrievedDocument]) -> Dict[str, Any]:
        """
        Get statistics about retrieved documents
        
        Args:
            documents: List of retrieved documents
            
        Returns:
            Dictionary with statistics
        """
        if not documents:
            return {
                "total_documents": 0,
                "avg_score": 0.0,
                "categories": []
            }
        
        scores = [doc.score for doc in documents]
        categories = list(set(doc.metadata.get('category', 'unknown') for doc in documents))
        
        return {
            "total_documents": len(documents),
            "avg_score": sum(scores) / len(scores),
            "max_score": max(scores),
            "min_score": min(scores),
            "categories": categories
        }


# Global instance
_retrieval_service = None


def get_retrieval_service() -> RetrievalService:
    """Get or create the global retrieval service instance"""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
