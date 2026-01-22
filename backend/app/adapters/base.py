"""
App Reviewer AI - Base Adapter

Abstract base class for review source adapters.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from app.api.schemas import Review


class BaseAdapter(ABC):
    """Abstract base adapter for fetching reviews."""
    
    @property
    @abstractmethod
    def platform(self) -> str:
        """Return platform identifier."""
        pass
    
    @abstractmethod
    async def fetch_reviews(
        self,
        app_id: str,
        locale: str = "en-US",
        limit: int = 500
    ) -> List[Review]:
        """
        Fetch reviews for an app.
        
        Args:
            app_id: App identifier
            locale: Locale code (e.g., 'en-US')
            limit: Maximum number of reviews
            
        Returns:
            List of Review objects
        """
        pass
    
    @abstractmethod
    async def validate_app_id(self, app_id: str) -> bool:
        """
        Validate that app ID exists.
        
        Args:
            app_id: App identifier
            
        Returns:
            True if valid, False otherwise
        """
        pass
