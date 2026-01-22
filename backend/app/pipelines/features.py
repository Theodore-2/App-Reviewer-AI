"""
App Reviewer AI - Feature Request Detection Pipeline

Separates complaints from feature requests.
"""

from typing import List, Dict, Any
import logging

from app.pipelines.base import BasePipeline

logger = logging.getLogger(__name__)


class FeaturePipeline(BasePipeline):
    """
    Feature request detection pipeline.
    
    Output:
    [
        {
            "feature": "Dark mode",
            "count": 18,
            "category": "<ui|functionality|integration|content|other>"
        }
    ]
    """
    
    VERSION = "1.0"
    
    @property
    def name(self) -> str:
        return "features"
    
    @property
    def system_prompt(self) -> str:
        return """You are a feature request detection system for app reviews.

TASK:
Identify and categorize feature requests from app reviews. Distinguish between complaints about existing features and requests for new features.

OUTPUT FORMAT (strict JSON):
{
    "features": [
        {
            "feature": "<clear description of requested feature>",
            "count": <estimated number of requests>,
            "category": "ui" | "functionality" | "integration" | "content" | "accessibility" | "other"
        }
    ]
}

RULES:
1. Only include genuine feature REQUESTS, not bug reports
2. Group similar requests together
3. Be specific about what the user wants
4. Categorize accurately
5. Only output valid JSON, no explanations"""
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "features": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "feature": {"type": "string"},
                            "count": {"type": "integer"},
                            "category": {"type": "string"}
                        }
                    }
                }
            }
        }
    
    async def analyze(self, reviews: List[str]) -> List[Dict[str, Any]]:
        """
        Extract feature requests from reviews.
        
        Args:
            reviews: List of review texts
            
        Returns:
            List of feature request objects
        """
        if not reviews:
            return []
        
        # Process in chunks
        chunks = self._chunk_reviews(reviews)
        all_features = []
        
        for chunk in chunks:
            reviews_text = "\n---\n".join(chunk)
            prompt = f"Extract feature requests from these {len(chunk)} app reviews:\n\n{reviews_text}"
            
            result = await self._call_openai(
                prompt,
                response_format={"type": "json_object"}
            )
            
            features = result.get("features", [])
            all_features.extend(features)
        
        # Aggregate and deduplicate
        feature_map = {}
        for feature in all_features:
            name = feature.get("feature", "").lower().strip()
            if not name:
                continue
            
            if name in feature_map:
                feature_map[name]["count"] += feature.get("count", 1)
            else:
                feature_map[name] = {
                    "feature": feature.get("feature", name),
                    "count": feature.get("count", 1),
                    "category": feature.get("category", "other")
                }
        
        # Sort by count
        sorted_features = sorted(
            feature_map.values(),
            key=lambda x: x["count"],
            reverse=True
        )
        
        return sorted_features[:15]  # Top 15 feature requests
