"""
Vector Store Service using ChromaDB
Manages document storage and retrieval
"""
import logging
import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from .config import rag_config
from .embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Service for managing ChromaDB vector store"""
    
    def __init__(self, persist_directory: str = None, collection_name: str = None):
        """
        Initialize ChromaDB client
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection
        """
        self.persist_directory = persist_directory or rag_config.CHROMA_PERSIST_DIRECTORY
        self.collection_name = collection_name or rag_config.COLLECTION_NAME
        
        # Create persist directory if not exists
        os.makedirs(self.persist_directory, exist_ok=True)
        
        logger.info(f"Initializing ChromaDB (mode: {rag_config.CHROMA_MODE})")
        
        try:
            # Initialize ChromaDB client based on mode
            if rag_config.CHROMA_MODE == "remote":
                # Remote ChromaDB server
                logger.info(f"Connecting to remote ChromaDB at: {rag_config.CHROMA_HOST}:{rag_config.CHROMA_PORT}")
                
                # Prepare headers
                headers = {}
                if rag_config.CHROMA_USERNAME and rag_config.CHROMA_PASSWORD:
                    import base64
                    credentials = f"{rag_config.CHROMA_USERNAME}:{rag_config.CHROMA_PASSWORD}"
                    encoded = base64.b64encode(credentials.encode()).decode()
                    headers["Authorization"] = f"Basic {encoded}"
                
                self.client = chromadb.HttpClient(
                    host=rag_config.CHROMA_HOST,
                    port=rag_config.CHROMA_PORT,
                    ssl=rag_config.CHROMA_SSL,
                    headers=headers,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=False,
                        chroma_client_auth_provider="chromadb.auth.basic.BasicAuthClientProvider",
                        chroma_client_auth_credentials=f"{rag_config.CHROMA_USERNAME}:{rag_config.CHROMA_PASSWORD}"
                    )
                )
            else:
                # Local ChromaDB with persistence
                logger.info(f"Using local ChromaDB at: {self.persist_directory}")
                os.makedirs(self.persist_directory, exist_ok=True)
                
                self.client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
            
            # Test connection first
            try:
                self.client.heartbeat()
                logger.info(f"✅ ChromaDB connection successful")
            except Exception as e:
                logger.error(f"❌ ChromaDB heartbeat failed: {str(e)}")
                raise ConnectionError(f"Cannot connect to ChromaDB server: {str(e)}")
            
            # Get or create collection
            self.embedding_service = get_embedding_service()
            
            try:
                # Try to get existing collection first
                self.collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"✅ Found existing collection: {self.collection_name}")
            except Exception:
                # Collection doesn't exist, create it
                logger.info(f"Creating new collection: {self.collection_name}")
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
            
            logger.info(f"✅ ChromaDB initialized successfully. Collection: {self.collection_name}")
            
            try:
                doc_count = self.collection.count()
                logger.info(f"   Total documents: {doc_count}")
            except Exception as e:
                logger.warning(f"   Could not get document count: {str(e)}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize ChromaDB: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """Test ChromaDB connection"""
        try:
            self.client.heartbeat()
            logger.info("✅ ChromaDB heartbeat OK")
            return True
        except Exception as e:
            logger.error(f"❌ ChromaDB heartbeat failed: {str(e)}")
            return False
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """
        Add documents to the vector store
        
        Args:
            documents: List of document texts
            metadatas: List of metadata dictionaries
            ids: List of unique IDs for each document
        """
        try:
            logger.info(f"Adding {len(documents)} documents to ChromaDB...")
            
            # Generate embeddings
            embeddings = self.embedding_service.embed_texts(documents)
            
            # Add to ChromaDB
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"✅ Added {len(documents)} documents successfully")
            logger.info(f"   Total documents in collection: {self.collection.count()}")
            
        except Exception as e:
            logger.error(f"❌ Error adding documents: {e}")
            raise
    
    def query(
        self,
        query_text: str,
        n_results: int = None,
        where: Dict[str, Any] = None,
        where_document: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Query the vector store
        
        Args:
            query_text: Query text
            n_results: Number of results to return
            where: Metadata filters
            where_document: Document content filters
            
        Returns:
            Query results with documents, metadatas, distances
        """
        try:
            n_results = n_results or rag_config.TOP_K
            
            # Generate query embedding
            query_embedding = self.embedding_service.embed_text(query_text)
            
            # Query ChromaDB - remove empty filters to avoid operator errors
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": n_results,
                "include": ["documents", "metadatas", "distances"]
            }
            
            # Only add filters if they are not empty
            if where and len(where) > 0:
                query_params["where"] = where
            if where_document and len(where_document) > 0:
                query_params["where_document"] = where_document
            
            results = self.collection.query(**query_params)
            
            logger.info(f"Query returned {len(results['documents'][0])} results")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error querying vector store: {e}")
            raise
    
    def delete_documents(self, ids: List[str]) -> None:
        """
        Delete documents by IDs
        
        Args:
            ids: List of document IDs to delete
        """
        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents")
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            raise
    
    def update_documents(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """
        Update existing documents
        
        Args:
            ids: List of document IDs to update
            documents: Updated document texts
            metadatas: Updated metadata
        """
        try:
            # Generate new embeddings
            embeddings = self.embedding_service.embed_texts(documents)
            
            self.collection.update(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info(f"Updated {len(ids)} documents")
        except Exception as e:
            logger.error(f"Error updating documents: {e}")
            raise
    
    def get_document_count(self) -> int:
        """Get total number of documents in collection"""
        return self.collection.count()
    
    def reset_collection(self) -> None:
        """Delete all documents in the collection (use with caution!)"""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.warning(f"⚠️ Collection {self.collection_name} has been reset")
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            raise
    
    def get_all_documents(self) -> Dict[str, Any]:
        """Get all documents in the collection (for debugging/export)"""
        try:
            results = self.collection.get(
                include=["documents", "metadatas"]
            )
            return results
        except Exception as e:
            logger.error(f"Error getting all documents: {e}")
            raise


# Global instance
_vector_store_service = None


def get_vector_store_service() -> VectorStoreService:
    """Get or create the global vector store service instance"""
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = VectorStoreService()
    return _vector_store_service
