"""
Generation Service for RAG System
Handles LLM-based answer generation
"""
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from .config import rag_config
from .retrieval_service import RetrievedDocument

logger = logging.getLogger(__name__)


class GenerationService:
    """Service for generating answers using LLM"""
    
    def __init__(
        self,
        provider: str = None,
        model: str = None,
        temperature: float = None
    ):
        """
        Initialize generation service
        
        Args:
            provider: LLM provider ('openai' or 'anthropic')
            model: Model name
            temperature: Generation temperature
        """
        self.provider = provider or rag_config.LLM_PROVIDER
        self.model = model or rag_config.LLM_MODEL
        self.temperature = temperature or rag_config.LLM_TEMPERATURE
        
        logger.info(f"Initializing generation service: {self.provider}/{self.model}")
        
        # Initialize Gemini API client
        if self.provider == "gemini":
            if not rag_config.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not found in environment")
            genai.configure(api_key=rag_config.GEMINI_API_KEY)
            self.client = genai.GenerativeModel(self.model)
        else:
            raise ValueError(f"Only 'gemini' provider is supported. Got: {self.provider}")
        
        logger.info("✅ Generation service initialized")
    
    def generate(
        self,
        query: str,
        context: str,
        system_prompt: str = None
    ) -> Dict[str, Any]:
        """
        Generate answer using LLM
        
        Args:
            query: User question
            context: Retrieved context from documents
            system_prompt: Custom system prompt (optional)
            
        Returns:
            Dictionary with answer and metadata
        """
        try:
            system_prompt = system_prompt or rag_config.SYSTEM_PROMPT
            
            # Format the prompt
            full_prompt = system_prompt.format(
                context=context,
                question=query
            )
            
            logger.info(f"Generating answer for query: '{query[:50]}...'")
            logger.info(f"Context length: {len(context)} chars")
            
            # Generate using Gemini
            response = self._generate_gemini(full_prompt)
            
            logger.info(f"Generated answer ({len(response['answer'])} chars)")
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise
    
    def _generate_gemini(self, prompt: str) -> Dict[str, Any]:
        """Generate using Google Gemini API"""
        try:
            generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": rag_config.LLM_MAX_TOKENS,
            }
            
            response = self.client.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            answer = response.text
            
            return {
                "answer": answer,
                "model": self.model,
                "provider": "gemini",
                "tokens_used": {
                    "prompt": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                    "completion": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                    "total": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    def generate_with_fallback(
        self,
        query: str,
        documents: List[RetrievedDocument]
    ) -> Dict[str, Any]:
        """
        Generate answer with automatic fallback if no relevant documents
        
        Args:
            query: User question
            documents: Retrieved documents
            
        Returns:
            Generated answer with metadata
        """
        # Check if we have relevant documents
        if not documents:
            logger.warning("No relevant documents found, returning fallback message")
            return {
                "answer": rag_config.NO_ANSWER_MESSAGE,
                "model": None,
                "provider": None,
                "has_answer": False,
                "documents_used": 0
            }
        
        # Format context from documents
        from .retrieval_service import get_retrieval_service
        retrieval_service = get_retrieval_service()
        context = retrieval_service.format_context(documents)
        
        # Generate answer
        result = self.generate(query, context)
        result.update({
            "has_answer": True,
            "documents_used": len(documents),
            "avg_score": sum(d.score for d in documents) / len(documents)
        })
        
        return result
    
    def validate_answer(self, answer: str, context: str) -> Dict[str, Any]:
        """
        Validate if answer is grounded in context (basic heuristics)
        
        Args:
            answer: Generated answer
            context: Context used for generation
            
        Returns:
            Validation results
        """
        # Basic validation checks
        checks = {
            "not_empty": len(answer.strip()) > 0,
            "reasonable_length": 10 < len(answer) < 5000,
            "contains_vietnamese": any(ord(c) > 127 for c in answer),
            "not_generic_fallback": "không có thông tin" not in answer.lower()
        }
        
        is_valid = all(checks.values())
        
        return {
            "is_valid": is_valid,
            "checks": checks
        }


# Global instance
_generation_service = None


def get_generation_service() -> GenerationService:
    """Get or create the global generation service instance"""
    global _generation_service
    if _generation_service is None:
        _generation_service = GenerationService()
    return _generation_service
