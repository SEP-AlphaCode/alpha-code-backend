"""
Task Classifier using Semantic Search
Classifies input text into task types and returns top-k results
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import base64
from config.config import settings
import chromadb

headers = {}

credentials = f"{settings.CHROMA_USERNAME}:{settings.CHROMA_PASSWORD}"
encoded = base64.b64encode(credentials.encode()).decode()
headers["Authorization"] = f"Basic {encoded}"

client = chromadb.HttpClient(host=settings.CHROMA_HOST, ssl=settings.CHROMA_SSL, port=settings.CHROMA_PORT,
                             headers=headers, tenant=settings.CHROMA_COMMAND_TENANT,
                             database=settings.CHROMA_COMMAND_DB)


collection = client.get_or_create_collection(
    settings.CHROMA_COMMAND_COLLECTION
)


@dataclass
class TaskPrediction:
    """Represents a single task classification prediction from ChromaDB"""
    task_type: str
    distance: float
    metadata: Dict[str, Any]


def classify_task(
        text: str,
        k: int,
) -> List[TaskPrediction]:
    """
    Classify input text into task types using semantic search

    Args:
        text: Input text to classify
        k: Number of top predictions to return
        collection: ChromaDB collection object

    Returns:
        List of TaskPrediction objects from ChromaDB results

    Example:
    """
    
    results = collection.query(
        query_texts=['query:' + text],
        n_results=k,
        include=['distances', 'metadatas']
    )
    
    predictions = []
    
    if results['metadatas'] and results['metadatas'][0]:
        for i in range(len(results['metadatas'][0])):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            task_type = results['ids'][0][i]
            
            predictions.append(TaskPrediction(
                task_type=task_type,
                distance=distance,
                metadata=metadata
            ))
    
    return predictions