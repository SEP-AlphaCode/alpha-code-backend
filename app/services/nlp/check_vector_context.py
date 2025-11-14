"""Module to verify ConversationContextService initialization.

Run with: py -m app.services.nlp.check_vector_context
"""
import sys
import traceback

def main():
    try:
        from app.services.nlp.vector_context_service import get_conversation_context_service
        svc = get_conversation_context_service()
        coll_exists = hasattr(svc, 'collection') and svc.collection is not None
        print(f"ConversationContextService: {type(svc)}")
        print(f"Collection available: {coll_exists}")
        # try optional heartbeat via underlying vector store if available
        try:
            if hasattr(svc, 'vs') and svc.vs:
                ok = svc.vs.test_connection()
                print(f"Vector store heartbeat: {ok}")
        except Exception as e:
            print(f"Heartbeat check failed: {e}")
    except Exception:
        print("ERROR during initialization:")
        traceback.print_exc()
        sys.exit(2)

if __name__ == '__main__':
    main()
