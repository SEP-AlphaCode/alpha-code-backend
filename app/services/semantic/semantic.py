from dataclasses import dataclass
import base64
import threading
import chromadb
import requests
from typing import Optional, Dict, Any, List
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions
from config.config import settings

@dataclass
class TaskPrediction:
    """Represents a single task classification prediction from ChromaDB"""
    task_type: str
    distance: float
    metadata: Dict[str, Any]



class TaskClassifier:
    """Task classifier using ChromaDB for semantic search (Singleton)"""

    _instance: Optional["TaskClassifier"] = None
    _lock = threading.Lock()
    _initialized = False

    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="intfloat/multilingual-e5-large",
        normalize_embeddings=True
    )

    def __new__(cls, *args, **kwargs):
        """Thread-safe singleton instance creation"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TaskClassifier, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize ChromaDB client and collection (runs once)"""
        if TaskClassifier._initialized:
            return

        self.settings = settings
        self.headers: Dict[str, str] = {}
        self.client: Optional[chromadb.HttpClient] = None
        self.collection: Optional[Collection] = None
        self.base_url: str = ""

        self._initialize()
        TaskClassifier._initialized = True

    def _initialize(self):
        """Setup ChromaDB connection and create tenant/database if needed"""

        credentials = f"{self.settings.CHROMA_USERNAME}:{self.settings.CHROMA_PASSWORD}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json"
        }

        self.base_url = f"{'https' if self.settings.CHROMA_SSL else 'http'}://{self.settings.CHROMA_HOST}:{self.settings.CHROMA_PORT}"

        # Create tenant if not exists
        try:
            print("Trying to create tenant")
            requests.post(
                f"{self.base_url}/api/v2/tenants",
                headers=self.headers,
                json={"name": self.settings.CHROMA_COMMAND_TENANT},
                timeout=10
            )
            print(f"Tenant created: {self.settings.CHROMA_COMMAND_TENANT}")
        except Exception as e:
            print(f"Tenant already exists or error: {e}")

        # Create database if not exists
        try:
            print("Trying to create database")
            requests.post(
                f"{self.base_url}/api/v2/tenants/{self.settings.CHROMA_COMMAND_TENANT}/databases",
                headers=self.headers,
                json={"name": self.settings.CHROMA_COMMAND_DB},
                timeout=10
            )
            print(f"Database created: {self.settings.CHROMA_COMMAND_DB}")
        except Exception as e:
            print(f"Database already exists or error: {e}")

        # Connect to ChromaDB
        self.client = chromadb.HttpClient(
            host=self.settings.CHROMA_HOST,
            ssl=self.settings.CHROMA_SSL,
            port=self.settings.CHROMA_PORT,
            headers=self.headers,
            tenant=self.settings.CHROMA_COMMAND_TENANT,
            database=self.settings.CHROMA_COMMAND_DB
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            self.settings.CHROMA_COMMAND_COLLECTION,
            embedding_function=self.embed_fn,
            metadata={"hnsw:space": "cosine"}
        )

        print(f"Collection ready: {self.settings.CHROMA_COMMAND_COLLECTION}")

    def classify_task(self, text: str, k: int = 3) -> List["TaskPrediction"]:
        """Classify input text into task types using semantic search"""

        results = self.collection.query(
            query_texts=["query:" + text],
            n_results=k,
            include=["distances", "metadatas"]
        )

        predictions = []

        if results.get("metadatas") and results["metadatas"][0]:
            for i in range(len(results["metadatas"][0])):
                predictions.append(TaskPrediction(
                    task_type=results["ids"][0][i],
                    distance=results["distances"][0][i],
                    metadata=results["metadatas"][0][i]
                ))

        return predictions

    def reload_tasks(self, json_path: Optional[str] = None) -> int:
        """Clear collection and reload all tasks from JSON"""

        existing_ids = self.collection.get()["ids"]
        if existing_ids:
            self.collection.delete(ids=existing_ids)
            print(f"Deleted {len(existing_ids)} existing tasks")

        return self.load_tasks_from_json(json_path)

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the current collection"""

        return {
            "name": self.settings.CHROMA_COMMAND_COLLECTION,
            "count": self.collection.count(),
            "tenant": self.settings.CHROMA_COMMAND_TENANT,
            "database": self.settings.CHROMA_COMMAND_DB
        }

