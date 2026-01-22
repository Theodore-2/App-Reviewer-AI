"""
App Reviewer AI - Base Pipeline

Abstract base class for AI analysis pipelines with OpenAI integration.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json
import logging
from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


class BasePipeline(ABC):
    """
    Abstract base class for AI analysis pipelines.
    
    All pipelines must:
    - Have a fixed prompt template version
    - Enforce strict JSON output schema
    - Run with low temperature
    - Be independently executable
    """
    
    # Pipeline version for tracking
    VERSION = "1.0"
    
    # Model parameters
    TEMPERATURE = 0.1  # Low temperature for deterministic output
    MAX_TOKENS = 4000
    
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        self.tokens_used = 0
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Pipeline name for logging."""
        pass
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt defining the pipeline's role."""
        pass
    
    @property
    @abstractmethod
    def output_schema(self) -> Dict[str, Any]:
        """JSON schema for output validation."""
        pass
    
    def _chunk_reviews(self, reviews: List[str], chunk_size: int = 50) -> List[List[str]]:
        """Split reviews into chunks for processing."""
        return [reviews[i:i + chunk_size] for i in range(0, len(reviews), chunk_size)]
    
    def _validate_output(self, output: Any, schema: Dict[str, Any]) -> bool:
        """
        Basic schema validation.
        For production, use jsonschema library.
        """
        if not isinstance(output, (dict, list)):
            return False
        return True
    
    async def _call_openai(
        self,
        user_prompt: str,
        response_format: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make API call to OpenAI."""
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            kwargs = {
                "model": self.settings.openai_model,
                "messages": messages,
                "temperature": self.TEMPERATURE,
                "max_tokens": self.MAX_TOKENS,
            }
            
            # Use JSON mode if available
            if response_format:
                kwargs["response_format"] = response_format
            
            response = await self.client.chat.completions.create(**kwargs)
            
            # Track token usage
            if response.usage:
                self.tokens_used += response.usage.total_tokens
            
            # Parse response
            content = response.choices[0].message.content
            
            # Try to parse as JSON
            try:
                # Find JSON in response
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0]
                else:
                    json_str = content
                
                return json.loads(json_str.strip())
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from pipeline {self.name}")
                return {"raw": content}
                
        except Exception as e:
            logger.error(f"OpenAI API error in pipeline {self.name}: {e}")
            raise
    
    @abstractmethod
    async def analyze(self, *args, **kwargs) -> Any:
        """Run the analysis pipeline."""
        pass
