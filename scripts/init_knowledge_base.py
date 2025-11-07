"""
Initialize Knowledge Base
Load data from JSON files into ChromaDB
"""
import sys
import os
import json
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.rag.vector_store_service import get_vector_store_service
from config.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_json_data(file_path: str):
    """Load data from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} documents from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return []


def init_knowledge_base(auto_mode=False, reset=False):
    """
    Initialize knowledge base with data from JSON files
    
    Args:
        auto_mode: If True, skip user prompts (for startup auto-init)
        reset: If True, reset existing data
    """
    try:
        logger.info("=" * 80)
        logger.info("Initializing Alpha Mini Knowledge Base")
        logger.info("=" * 80)
        
        # Get vector store service
        vector_store = get_vector_store_service()
        
        # Check current document count
        current_count = vector_store.get_document_count()
        logger.info(f"Current documents in ChromaDB: {current_count}")
        
        if current_count > 0:
            if auto_mode:
                # Auto mode: skip if already has data
                logger.info("✅ Knowledge base already initialized. Skipping.")
                return
            elif reset:
                logger.warning("Resetting collection...")
                vector_store.reset_collection()
            else:
                response = input("⚠️  Knowledge base already has documents. Reset? (y/N): ")
                if response.lower() == 'y':
                    logger.warning("Resetting collection...")
                    vector_store.reset_collection()
                else:
                    logger.info("Keeping existing documents. Will add new ones.")
        
        # Data directory
        data_dir = Path(__file__).parent.parent / "data" / "alpha_mini_knowledge"
        logger.info(f"Loading data from: {data_dir}")
        
        # Load all JSON files
        all_documents = []
        all_metadatas = []
        all_ids = []
        
        json_files = list(data_dir.glob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files")
        
        for json_file in json_files:
            logger.info(f"\nProcessing: {json_file.name}")
            data = load_json_data(str(json_file))
            for item in data:
                all_metadatas.append((item['content'], item['metadata'], item['id']))
        if not all_documents:
            logger.error("❌ No documents found to load!")
            return
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Total documents to add: {len(all_documents)}")
        logger.info(f"{'=' * 80}\n")
        
        # Add documents to vector store
        logger.info("Adding documents to ChromaDB...")
        vector_store.add_documents(
            documents=all_documents,
            metadatas=all_metadatas,
            ids=all_ids
        )
        
        # Verify
        final_count = vector_store.get_document_count()
        logger.info(f"\n{'=' * 80}")
        logger.info(f"✅ Knowledge base initialized successfully!")
        logger.info(f"Total documents in ChromaDB: {final_count}")
        logger.info(f"{'=' * 80}\n")
        
        # Show statistics
        logger.info("Statistics by category:")
        categories = {}
        for metadata in all_metadatas:
            category = metadata.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1
        
        for category, count in categories.items():
            logger.info(f"  - {category}: {count} documents")
        
        logger.info(f"\n{'=' * 80}")
        logger.info("You can now use the chatbot API!")
        logger.info(f"{'=' * 80}\n")
        
    except Exception as e:
        logger.error(f"❌ Error initializing knowledge base: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    init_knowledge_base()
