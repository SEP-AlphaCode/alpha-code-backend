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

    async def get_recent(self, serial: str, k: int = 5) -> List[Dict[str, Any]]:
        """Return the most recent k conversation messages for a robot serial.

        We use metadata filter robot_serial + type=conversation then sort by
        timestamp locally because Chroma may not provide ordering guarantees.
        """
        if not self.collection:
            logger.debug("Vector store not initialized; get_recent returns empty list")
            return []

        try:
            # Chroma expects a single top-level operator when combining filters.
            # Use $and with explicit $eq operators for each field to be safe.
            where_filter = {
                "$and": [
                    {"robot_serial": {"$eq": serial}},
                    {"type": {"$eq": "conversation"}}
                ]
            }
            # collection.get is synchronous in the installed Chroma client; call directly.
            # Note: some Chroma versions don't accept 'ids' in the include list.
            # Request only documents/metadatas/distances and build ids locally if missing.
            results = self.collection.get(where=where_filter, include=["documents", "metadatas"])

            # Chroma get() may return nested lists; normalize
            documents = results.get("documents") or []
            metadatas = results.get("metadatas") or []
            ids = results.get("ids") or []

            # If Chroma didn't return ids (some backends/versions omit it),
            # synthesize stable ids from metadata or generate new ones.
            if not ids:
                ids = []
                for i, md in enumerate(metadatas):
                    # prefer an existing id-like field in metadata
                    candidate = None
                    if isinstance(md, dict):
                        candidate = md.get("id") or md.get("_id") or md.get("uuid")
                    if candidate:
                        ids.append(str(candidate))
                    else:
                        ids.append(self._make_id())

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
            # Log full exception for easier debugging in deploy logs
            logger.warning(f"Failed to fetch recent conversation context for {serial}: {e}")
            logger.debug("Exception details:", exc_info=True)
            return []

    def prune_messages(self, serial: str = None, keep_last: int = 200, older_than_days: int = None) -> int:
        """Prune conversation messages for a serial (or all serials if serial=None).

        - keep_last: keep this many most-recent messages (per-serial). If None, don't prune by count.
        - older_than_days: also delete messages older than this many days (UTC). If None, don't prune by age.

        Returns number of deleted documents (best-effort; some chorma clients may not support delete(ids=...)).
        """
        if not self.collection:
            logger.debug("Vector store not initialized; skipping prune_messages")
            return 0

        try:
            # Build a list of serials to operate on
            serials = [serial] if serial else []
            if not serials:
                try:
                    # try to enumerate distinct robot_serial values by scanning metadatas
                    results = self.collection.get(include=["metadatas"]) or {}
                    metadatas = results.get("metadatas") or []
                    if len(metadatas) == 1 and isinstance(metadatas[0], list):
                        metadatas = metadatas[0]
                    for md in metadatas:
                        if isinstance(md, dict):
                            rs = md.get("robot_serial")
                            if rs:
                                serials.append(rs)
                except Exception:
                    # fallback: operate only on provided serial (none)
                    serials = []

            total_deleted = 0
            from datetime import datetime, timedelta

            for s in serials:
                try:
                    where_filter = {"$and": [{"robot_serial": {"$eq": s}}, {"type": {"$eq": "conversation"}}]}
                    results = self.collection.get(where=where_filter, include=["ids", "metadatas"]) or {}
                    ids = results.get("ids") or []
                    metadatas = results.get("metadatas") or []

                    # normalize
                    if len(ids) == 1 and isinstance(ids[0], list):
                        ids = ids[0]
                    if len(metadatas) == 1 and isinstance(metadatas[0], list):
                        metadatas = metadatas[0]

                    items = []
                    for i, mid in enumerate(ids):
                        md = metadatas[i] if i < len(metadatas) else {}
                        ts = md.get("timestamp") or ""
                        items.append({"id": mid, "timestamp": ts})

                    # sort newest-first
                    items_sorted = sorted(items, key=lambda x: x.get("timestamp") or "", reverse=True)

                    # collect ids to delete by keep_last
                    to_delete = []
                    if keep_last is not None and len(items_sorted) > keep_last:
                        to_delete.extend([it["id"] for it in items_sorted[keep_last:]])

                    # collect ids to delete by age
                    if older_than_days is not None:
                        cutoff = (datetime.utcnow() - timedelta(days=older_than_days)).isoformat()
                        older_ids = [it["id"] for it in items_sorted if (it.get("timestamp") or "") < cutoff]
                        to_delete.extend(older_ids)

                    # dedupe
                    to_delete = list(dict.fromkeys(to_delete))

                    if not to_delete:
                        continue

                    # Attempt deletion: prefer ids-based delete, fallback to where-based delete
                    deleted_count = 0
                    try:
                        if hasattr(self.collection, "delete"):
                            try:
                                # many chroma clients support delete(ids=...)
                                self.collection.delete(ids=to_delete)
                            except TypeError:
                                # fallback: delete by where clause (id in ...)
                                try:
                                    where_ids = {"$and": [{"id": {"$in": to_delete}}]}
                                    self.collection.delete(where=where_ids)
                                except Exception:
                                    # as a last resort, attempt deleting individually
                                    for did in to_delete:
                                        try:
                                            self.collection.delete(ids=[did])
                                        except Exception:
                                            pass
                        else:
                            logger.warning("Collection does not support delete; cannot prune")
                            continue

                        deleted_count = len(to_delete)
                        total_deleted += deleted_count
                        logger.info(f"Pruned {deleted_count} conversation messages for serial={s}")
                    except Exception as e:
                        logger.warning(f"Failed to delete/prune messages for {s}: {e}")
                        logger.debug("Exception details:", exc_info=True)

                except Exception as e:
                    logger.warning(f"Error while preparing prune for serial={s}: {e}")
                    logger.debug("Exception details:", exc_info=True)

            return total_deleted

        except Exception as e:
            logger.warning(f"Error while preparing prune messages: {e}")
            logger.debug("Exception details:", exc_info=True)
            return 0

    def prune_all(self, keep_last: int = 200, older_than_days: int = None) -> int:
        """Convenience to prune all serials. Returns total deleted."""
        return self.prune_messages(serial=None, keep_last=keep_last, older_than_days=older_than_days)

_context_service = None


def get_conversation_context_service() -> ConversationContextService:
    global _context_service
    if _context_service is None:
        _context_service = ConversationContextService()
    return _context_service
