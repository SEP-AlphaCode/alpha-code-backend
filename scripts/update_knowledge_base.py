"""
Update Knowledge Base
Add, update, or delete documents in ChromaDB
"""
import sys
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.rag.vector_store_service import get_vector_store_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def add_documents_from_json(json_file: str):
    """Add documents from a JSON file"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        vector_store = get_vector_store_service()
        
        documents = [item['content'] for item in data]
        metadatas = [item['metadata'] for item in data]
        ids = [item['id'] for item in data]
        
        logger.info(f"Adding {len(documents)} documents from {json_file}")
        vector_store.add_documents(documents, metadatas, ids)
        logger.info(f"✅ Successfully added {len(documents)} documents")
        
    except Exception as e:
        logger.error(f"❌ Error adding documents: {e}")


def update_documents_from_json(json_file: str):
    """Update existing documents from a JSON file"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        vector_store = get_vector_store_service()
        
        documents = [item['content'] for item in data]
        metadatas = [item['metadata'] for item in data]
        ids = [item['id'] for item in data]
        
        logger.info(f"Updating {len(documents)} documents from {json_file}")
        vector_store.update_documents(ids, documents, metadatas)
        logger.info(f"✅ Successfully updated {len(documents)} documents")
        
    except Exception as e:
        logger.error(f"❌ Error updating documents: {e}")


def delete_documents(doc_ids: List[str]):
    """Delete documents by IDs"""
    try:
        vector_store = get_vector_store_service()
        
        logger.info(f"Deleting {len(doc_ids)} documents")
        vector_store.delete_documents(doc_ids)
        logger.info(f"✅ Successfully deleted {len(doc_ids)} documents")
        
    except Exception as e:
        logger.error(f"❌ Error deleting documents: {e}")


def show_stats():
    """Show knowledge base statistics"""
    try:
        vector_store = get_vector_store_service()
        
        total = vector_store.get_document_count()
        all_docs = vector_store.get_all_documents()
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Knowledge Base Statistics")
        logger.info(f"{'=' * 80}")
        logger.info(f"Total documents: {total}")
        logger.info(f"Collection: {vector_store.collection_name}")
        logger.info(f"Persist directory: {vector_store.persist_directory}")
        
        # Count by category
        if all_docs.get('metadatas'):
            categories = {}
            for metadata in all_docs['metadatas']:
                category = metadata.get('category', 'unknown')
                categories[category] = categories.get(category, 0) + 1
            
            logger.info(f"\nDocuments by category:")
            for category, count in sorted(categories.items()):
                logger.info(f"  - {category}: {count}")
        
        logger.info(f"{'=' * 80}\n")
        
    except Exception as e:
        logger.error(f"❌ Error getting stats: {e}")


def interactive_mode():
    """Interactive mode for managing knowledge base"""
    logger.info("\n" + "=" * 80)
    logger.info("Alpha Mini Knowledge Base Manager")
    logger.info("=" * 80 + "\n")
    
    while True:
        print("\nOptions:")
        print("1. Add documents from JSON file")
        print("2. Update documents from JSON file")
        print("3. Delete documents by IDs")
        print("4. Show statistics")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            file_path = input("Enter JSON file path: ").strip()
            add_documents_from_json(file_path)
            
        elif choice == '2':
            file_path = input("Enter JSON file path: ").strip()
            update_documents_from_json(file_path)
            
        elif choice == '3':
            ids_str = input("Enter document IDs (comma-separated): ").strip()
            ids = [id.strip() for id in ids_str.split(',')]
            delete_documents(ids)
            
        elif choice == '4':
            show_stats()
            
        elif choice == '5':
            logger.info("Goodbye!")
            break
        else:
            logger.warning("Invalid choice. Please try again.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "add" and len(sys.argv) > 2:
            add_documents_from_json(sys.argv[2])
        elif command == "update" and len(sys.argv) > 2:
            update_documents_from_json(sys.argv[2])
        elif command == "delete" and len(sys.argv) > 2:
            ids = sys.argv[2].split(',')
            delete_documents(ids)
        elif command == "stats":
            show_stats()
        else:
            print("Usage:")
            print("  python update_knowledge_base.py add <json_file>")
            print("  python update_knowledge_base.py update <json_file>")
            print("  python update_knowledge_base.py delete <id1,id2,...>")
            print("  python update_knowledge_base.py stats")
            print("  python update_knowledge_base.py  (interactive mode)")
    else:
        interactive_mode()
