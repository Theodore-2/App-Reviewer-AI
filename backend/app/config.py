"""
App Reviewer AI - Configuration Module

Handles all environment-based configuration with validation.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4-turbo-preview", description="OpenAI model to use")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    
    # Cost Control
    max_token_budget_per_job: int = Field(default=50000, description="Maximum tokens per job")
    max_review_count: int = Field(default=1000, description="Maximum reviews to process")
    default_review_limit: int = Field(default=500, description="Default review limit")
    
    # Cache TTL (seconds)
    result_cache_ttl: int = Field(default=86400, description="Result cache TTL (24 hours)")
    review_cache_ttl: int = Field(default=3600, description="Review cache TTL (1 hour)")
    
    # Supported Locales
    supported_locales: str = Field(default="en-US,en-GB", description="Comma-separated locales")
    
    @property
    def locales_list(self) -> List[str]:
        """Get supported locales as a list."""
        return [loc.strip() for loc in self.supported_locales.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Cached settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get settings instance (reload on each server start)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
