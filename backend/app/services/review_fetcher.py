"""
App Reviewer AI - Review Fetcher Service

Orchestrates review fetching across multiple adapters.
"""

from typing import List, Optional
import logging
import re
from datetime import datetime

from app.api.schemas import Review
from app.adapters.appstore import AppStoreAdapter
from app.adapters.playstore import PlayStoreAdapter
from app.core.cache import get_cache_manager
from app.config import get_settings

logger = logging.getLogger(__name__)


class ReviewFetcher:
    """
    Unified review fetcher with adapter selection and caching.
    """
    
    CACHE_PREFIX = "reviews:"
    
    def __init__(self):
        self.appstore = AppStoreAdapter()
        self.playstore = PlayStoreAdapter()
        self.cache = get_cache_manager()
        self.settings = get_settings()
    
    def _cache_key(self, app_id: str, locale: str) -> str:
        """Generate cache key for reviews."""
        return f"{self.CACHE_PREFIX}{app_id}:{locale}"
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize review text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Normalize unicode
        text = text.encode("utf-8", errors="ignore").decode("utf-8")
        
        return text.strip()
    
    def _detect_language(self, text: str) -> str:
        """
        Simple language detection based on character analysis.
        For production, consider using langdetect or fasttext.
        """
        if not text:
            return "en"
        
        # Check for CJK characters
        cjk_pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]')
        if cjk_pattern.search(text):
            return "cjk"
        
        # Check for Cyrillic
        cyrillic_pattern = re.compile(r'[\u0400-\u04ff]')
        if cyrillic_pattern.search(text):
            return "ru"
        
        # Check for Arabic
        arabic_pattern = re.compile(r'[\u0600-\u06ff]')
        if arabic_pattern.search(text):
            return "ar"
        
        return "en"
    
    def _process_reviews(self, reviews: List[Review]) -> List[Review]:
        """Clean and process fetched reviews."""
        processed = []
        seen_ids = set()
        
        for review in reviews:
            # Skip duplicates
            if review.review_id in seen_ids:
                continue
            seen_ids.add(review.review_id)
            
            # Clean text
            review.body_cleaned = self._clean_text(review.body)
            if review.title:
                review.title = self._clean_text(review.title)
            
            # Detect language
            review.detected_language = self._detect_language(review.body_cleaned)
            
            # Skip empty reviews
            if not review.body_cleaned:
                continue
            
            processed.append(review)
        
        return processed
    
    async def fetch_reviews(
        self,
        app_id: str,
        platform: str = "ios",
        locale: str = "en-US",
        limit: int = 500
    ) -> List[Review]:
        """
        Fetch reviews from the appropriate adapter.
        
        Args:
            app_id: App identifier
            platform: 'ios' or 'android'
            locale: Locale code
            limit: Maximum reviews to fetch
            
        Returns:
            List of processed Review objects
        """
        cache_key = self._cache_key(app_id, locale)
        
        # Check cache
        cached = await self.cache.get_json(cache_key)
        if cached:
            logger.info(f"Using cached reviews for {app_id}")
            reviews = [Review(**r) for r in cached]
            return reviews[:limit]
        
        # Select adapter
        if platform == "ios":
            adapter = self.appstore
        elif platform == "android":
            adapter = self.playstore
        else:
            logger.error(f"Unknown platform: {platform}")
            return []
        
        # Fetch reviews
        reviews = await adapter.fetch_reviews(
            app_id=app_id,
            locale=locale,
            limit=limit
        )
        
        if not reviews:
            logger.warning(f"No reviews fetched for {app_id}")
            return []
        
        # Process reviews
        processed = self._process_reviews(reviews)
        
        # Cache results
        await self.cache.set_json(
            cache_key,
            [r.model_dump(mode="json") for r in processed],
            ttl=self.settings.review_cache_ttl
        )
        
        logger.info(f"Fetched and cached {len(processed)} reviews for {app_id}")
        return processed[:limit]
