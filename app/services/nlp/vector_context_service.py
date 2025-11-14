"""
Conversation context store using existing ChromaDB VectorStoreService.

Stores chat history embeddings with metadata including `robot_serial` so
we can retrieve conversation context per robot.

This module intentionally reuses the project's existing RAG VectorStoreService
to avoid duplicating Chroma configuration.
"""
from datetime import datetime
import logging
import uuid
from typing import List, Dict, Any

from app.services.rag.vector_store_service import get_vector_store_service

logger = logging.getLogger(__name__)


class ConversationContextService:
    def __init__(self):
        try:
            self.vs = get_vector_store_service()
            self.collection = self.vs.collection
            self.embedding_service = self.vs.embedding_service
        except Exception as e:
            logger.warning(f"ConversationContextService: failed to initialize vector store: {e}")
            self.vs = None
            self.collection = None
            self.embedding_service = None

    def _make_id(self) -> str:
        return uuid.uuid4().hex

    def upsert_messages(self, serial: str, messages: List[Dict[str, Any]]) -> None:
        """Upsert a list of message dicts into the vector store.

        Each message should have at least a 'text' and 'role' (user/assistant).
        Optional fields: 'id', 'timestamp', 'extra' (dict) for additional metadata.
        """
        if not self.collection or not self.embedding_service:
            logger.debug("Vector store not initialized; skipping upsert_messages")
            return

        ids = []
        docs = []
        metadatas = []

        for m in messages:
            mid = m.get("id") or f"{serial}_{self._make_id()}"
            ids.append(mid)
            text = m.get("text", "")
            docs.append(text)
            ts = m.get("timestamp") or datetime.utcnow().isoformat()
            md = {
                "robot_serial": serial,
                "type": "conversation",
                "role": m.get("role", "user"),
                "timestamp": ts,
            }
            extra = m.get("extra") or {}
            # merge extra metadata
            for k, v in extra.items():
                md[k] = v
            metadatas.append(md)

        try:
            embeddings = self.embedding_service.embed_texts(docs)
        except Exception as e:
            logger.warning(f"Failed to embed texts for context upsert: {e}")
            return

        try:
            # prefer upsert if available
            if hasattr(self.collection, "upsert"):
                self.collection.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metadatas)
            else:
                # fallback to add (may error if ids already exist)
                self.collection.add(ids=ids, documents=docs, embeddings=embeddings, metadatas=metadatas)
            logger.debug(f"Upserted {len(docs)} conversation messages for serial={serial}")
        except Exception as e:
            logger.warning(f"Failed to add/upsert context messages: {e}")

    def get_recent(self, serial: str, k: int = 5) -> List[Dict[str, Any]]:
        """Return the most recent k conversation messages for a robot serial.

        We use metadata filter robot_serial + type=conversation then sort by
        timestamp locally because Chroma may not provide ordering guarantees.
        """
        if not self.collection:
            logger.debug("Vector store not initialized; get_recent returns empty list")
            return []

        try:
            results = self.collection.get(where={"robot_serial": serial, "type": "conversation"}, include=["documents", "metadatas", "ids"])

            # Chroma get() may return nested lists; normalize
            documents = results.get("documents") or []
            metadatas = results.get("metadatas") or []
            ids = results.get("ids") or []

            # normalize if wrapped in outer list
            if len(documents) == 1 and isinstance(documents[0], list):
                documents = documents[0]
            if len(metadatas) == 1 and isinstance(metadatas[0], list):
                metadatas = metadatas[0]
            if len(ids) == 1 and isinstance(ids[0], list):
                ids = ids[0]

            items = []
            for i, doc in enumerate(documents):
                md = metadatas[i] if i < len(metadatas) else {}
                item = {
                    "id": ids[i] if i < len(ids) else self._make_id(),
                    "text": doc,
                    "meta": md,
                    "timestamp": md.get("timestamp")
                }
                items.append(item)

            # sort by timestamp desc
            items_sorted = sorted(items, key=lambda x: x.get("timestamp") or "", reverse=True)
            return items_sorted[:k]

        except Exception as e:
            logger.warning(f"Failed to fetch recent conversation context for {serial}: {e}")
            return []


_context_service = None


def get_conversation_context_service() -> ConversationContextService:
    global _context_service
    if _context_service is None:
        _context_service = ConversationContextService()
    return _context_service
