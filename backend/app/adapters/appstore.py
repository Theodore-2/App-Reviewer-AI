"""
App Reviewer AI - App Store Adapter

Fetches reviews from the iOS App Store.
"""

import httpx
from typing import List, Optional
from datetime import datetime
import logging
import xml.etree.ElementTree as ET
from tenacity import retry, stop_after_attempt, wait_exponential

from app.adapters.base import BaseAdapter
from app.api.schemas import Review

logger = logging.getLogger(__name__)


class AppStoreAdapter(BaseAdapter):
    """iOS App Store review adapter using RSS feed."""
    
    # RSS feed URL template
    RSS_URL = "https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/page={page}/xml"
    
    # Lookup API for validation
    LOOKUP_URL = "https://itunes.apple.com/lookup?id={app_id}&country={country}"
    
    # Country code mapping from locale
    LOCALE_TO_COUNTRY = {
        "en-US": "us",
        "en-GB": "gb",
        "de-DE": "de",
        "fr-FR": "fr",
        "ja-JP": "jp",
        "zh-CN": "cn",
        "es-ES": "es",
        "it-IT": "it",
        "pt-BR": "br",
        "ko-KR": "kr",
    }
    
    @property
    def platform(self) -> str:
        return "ios"
    
    def _get_country(self, locale: str) -> str:
        """Convert locale to country code."""
        return self.LOCALE_TO_COUNTRY.get(locale, "us")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _fetch_page(
        self,
        app_id: str,
        country: str,
        page: int
    ) -> List[Review]:
        """Fetch a single page of reviews."""
        url = self.RSS_URL.format(
            country=country,
            app_id=app_id,
            page=page
        )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            return self._parse_rss(response.text)
    
    def _parse_rss(self, xml_content: str) -> List[Review]:
        """Parse RSS XML into Review objects."""
        reviews = []
        
        try:
            # Define namespaces
            namespaces = {
                "atom": "http://www.w3.org/2005/Atom",
                "im": "http://itunes.apple.com/rss"
            }
            
            root = ET.fromstring(xml_content)
            
            # Find all entry elements (reviews)
            for entry in root.findall(".//atom:entry", namespaces):
                try:
                    # Extract review data
                    review_id = entry.find("atom:id", namespaces)
                    title = entry.find("atom:title", namespaces)
                    content = entry.find("atom:content[@type='text']", namespaces)
                    rating = entry.find("im:rating", namespaces)
                    updated = entry.find("atom:updated", namespaces)
                    
                    # Skip entries without content (like feed metadata)
                    if content is None or content.text is None:
                        continue
                    
                    # Parse date
                    date_str = updated.text if updated is not None else None
                    try:
                        review_date = datetime.fromisoformat(
                            date_str.replace("Z", "+00:00")
                        ) if date_str else datetime.utcnow()
                    except:
                        review_date = datetime.utcnow()
                    
                    review = Review(
                        review_id=review_id.text if review_id is not None else f"unknown_{len(reviews)}",
                        rating=int(rating.text) if rating is not None else 3,
                        date=review_date,
                        locale="en-US",  # Will be set by caller
                        title=title.text if title is not None else None,
                        body=content.text
                    )
                    
                    reviews.append(review)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse review entry: {e}")
                    continue
                    
        except ET.ParseError as e:
            logger.error(f"Failed to parse RSS XML: {e}")
        
        return reviews
    
    async def fetch_reviews(
        self,
        app_id: str,
        locale: str = "en-US",
        limit: int = 500
    ) -> List[Review]:
        """Fetch reviews from App Store RSS feed."""
        country = self._get_country(locale)
        all_reviews: List[Review] = []
        page = 1
        max_pages = 10  # RSS feed has max 10 pages
        
        logger.info(f"Fetching reviews for app {app_id} ({locale})")
        
        while len(all_reviews) < limit and page <= max_pages:
            try:
                page_reviews = await self._fetch_page(app_id, country, page)
                
                if not page_reviews:
                    break
                
                # Set locale for all reviews
                for review in page_reviews:
                    review.locale = locale
                
                all_reviews.extend(page_reviews)
                page += 1
                
            except Exception as e:
                logger.error(f"Failed to fetch page {page}: {e}")
                if page == 1:
                    # First page failed, no reviews available
                    return []
                break
        
        # Trim to limit
        all_reviews = all_reviews[:limit]
        
        logger.info(f"Fetched {len(all_reviews)} reviews for app {app_id}")
        return all_reviews
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def validate_app_id(self, app_id: str) -> bool:
        """Validate app ID exists in App Store."""
        url = self.LOOKUP_URL.format(app_id=app_id, country="us")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                return data.get("resultCount", 0) > 0
                
        except Exception as e:
            logger.error(f"Failed to validate app ID {app_id}: {e}")
            return False
