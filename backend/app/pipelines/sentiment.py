"""
App Reviewer AI - Sentiment & Emotion Pipeline

Detects emotional tone beyond star ratings.
"""

from typing import List, Dict, Any
import logging

from app.pipelines.base import BasePipeline

logger = logging.getLogger(__name__)


class SentimentPipeline(BasePipeline):
    """
    Sentiment and emotion analysis pipeline.
    
    Output:
    {
        "overall_sentiment": "positive|neutral|negative",
        "sentiment_breakdown": {
            "positive": percentage,
            "neutral": percentage,
            "negative": percentage
        },
        "emotions": [
            {"emotion": "frustration", "frequency": 0.25},
            {"emotion": "satisfaction", "frequency": 0.40}
        ]
    }
    """
    
    VERSION = "1.0"
    
    @property
    def name(self) -> str:
        return "sentiment"
    
    @property
    def system_prompt(self) -> str:
        return """You are a sentiment and emotion analysis system for app reviews.

TASK:
Analyze the provided app reviews and classify sentiment and emotional tones.

OUTPUT FORMAT (strict JSON):
{
    "overall_sentiment": "positive" | "neutral" | "negative",
    "sentiment_breakdown": {
        "positive": <percentage 0-100>,
        "neutral": <percentage 0-100>,
        "negative": <percentage 0-100>
    },
    "emotions": [
        {
            "emotion": "<emotion name>",
            "frequency": <0.0-1.0 indicating how common>
        }
    ]
}

RULES:
1. Percentages must sum to 100
2. Consider context, not just keywords
3. Detect emotions: frustration, confusion, satisfaction, excitement, disappointment, anger, appreciation
4. Only output valid JSON, no explanations
5. Be objective and data-driven"""
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "overall_sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
                "sentiment_breakdown": {
                    "type": "object",
                    "properties": {
                        "positive": {"type": "number"},
                        "neutral": {"type": "number"},
                        "negative": {"type": "number"}
                    }
                },
                "emotions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "emotion": {"type": "string"},
                            "frequency": {"type": "number"}
                        }
                    }
                }
            }
        }
    
    async def analyze(self, reviews: List[str]) -> Dict[str, Any]:
        """
        Analyze sentiment and emotions in reviews.
        
        Args:
            reviews: List of review texts
            
        Returns:
            Sentiment analysis result
        """
        if not reviews:
            return {
                "overall_sentiment": "neutral",
                "sentiment_breakdown": {"positive": 33, "neutral": 34, "negative": 33},
                "emotions": []
            }
        
        # Process in chunks for large datasets
        chunks = self._chunk_reviews(reviews)
        all_results = []
        
        for chunk in chunks:
            reviews_text = "\n---\n".join(chunk)
            prompt = f"Analyze the sentiment and emotions in these {len(chunk)} app reviews:\n\n{reviews_text}"
            
            result = await self._call_openai(
                prompt,
                response_format={"type": "json_object"}
            )
            all_results.append(result)
        
        # Aggregate results if multiple chunks
        if len(all_results) == 1:
            return all_results[0]
        
        # Merge sentiment breakdowns
        total_positive = sum(r.get("sentiment_breakdown", {}).get("positive", 0) for r in all_results)
        total_neutral = sum(r.get("sentiment_breakdown", {}).get("neutral", 0) for r in all_results)
        total_negative = sum(r.get("sentiment_breakdown", {}).get("negative", 0) for r in all_results)
        
        count = len(all_results)
        
        # Merge emotions
        emotion_freq = {}
        for result in all_results:
            for emotion in result.get("emotions", []):
                name = emotion.get("emotion", "")
                freq = emotion.get("frequency", 0)
                if name:
                    emotion_freq[name] = emotion_freq.get(name, 0) + freq
        
        # Normalize emotion frequencies
        emotions = [
            {"emotion": name, "frequency": round(freq / count, 2)}
            for name, freq in sorted(emotion_freq.items(), key=lambda x: -x[1])
        ]
        
        # Determine overall sentiment
        avg_positive = total_positive / count
        avg_negative = total_negative / count
        
        if avg_positive > avg_negative + 10:
            overall = "positive"
        elif avg_negative > avg_positive + 10:
            overall = "negative"
        else:
            overall = "neutral"
        
        return {
            "overall_sentiment": overall,
            "sentiment_breakdown": {
                "positive": round(total_positive / count, 1),
                "neutral": round(total_neutral / count, 1),
                "negative": round(total_negative / count, 1)
            },
            "emotions": emotions[:10]  # Top 10 emotions
        }
