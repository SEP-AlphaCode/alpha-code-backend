"""
Generation Service for RAG System
Handles LLM-based answer generation
"""
import logging
from typing import List, Dict, Any, Optional
import openai
from anthropic import Anthropic

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
        
        # Initialize API clients
        if self.provider == "openai":
            if not rag_config.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not found in environment")
            openai.api_key = rag_config.OPENAI_API_KEY
            self.client = openai
        elif self.provider == "anthropic":
            if not rag_config.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")
            self.client = Anthropic(api_key=rag_config.ANTHROPIC_API_KEY)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
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
            
            # Generate based on provider
            if self.provider == "openai":
                response = self._generate_openai(full_prompt)
            elif self.provider == "anthropic":
                response = self._generate_anthropic(query, context, system_prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            logger.info(f"Generated answer ({len(response['answer'])} chars)")
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise
    
    def _generate_openai(self, prompt: str) -> Dict[str, Any]:
        """Generate using OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=rag_config.LLM_MAX_TOKENS
            )
            
            answer = response.choices[0].message.content
            
            return {
                "answer": answer,
                "model": self.model,
                "provider": "openai",
                "tokens_used": {
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _generate_anthropic(
        self,
        query: str,
        context: str,
        system_prompt: str
    ) -> Dict[str, Any]:
        """Generate using Anthropic API"""
        try:
            # Format system prompt
            system_message = system_prompt.format(context=context, question="")
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=rag_config.LLM_MAX_TOKENS,
                temperature=self.temperature,
                system=system_message,
                messages=[
                    {"role": "user", "content": query}
                ]
            )
            
            answer = response.content[0].text
            
            return {
                "answer": answer,
                "model": self.model,
                "provider": "anthropic",
                "tokens_used": {
                    "prompt": response.usage.input_tokens,
                    "completion": response.usage.output_tokens,
                    "total": response.usage.input_tokens + response.usage.output_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
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
