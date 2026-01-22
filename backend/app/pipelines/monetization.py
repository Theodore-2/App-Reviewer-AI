"""
App Reviewer AI - Monetization Friction Pipeline

Detects revenue-blocking feedback.
"""

from typing import List, Dict, Any
import logging

from app.pipelines.base import BasePipeline

logger = logging.getLogger(__name__)


class MonetizationPipeline(BasePipeline):
    """
    Monetization friction analysis pipeline.
    
    Detects:
    - Subscription complaints
    - Paywall frustration
    - Pricing confusion
    - Ad-related issues
    
    Output:
    {
        "monetization_risk": "low|medium|high",
        "risks": [
            {
                "risk": "Forced subscription after free trial",
                "confidence": "high",
                "category": "subscription"
            }
        ]
    }
    """
    
    VERSION = "1.0"
    
    @property
    def name(self) -> str:
        return "monetization"
    
    @property
    def system_prompt(self) -> str:
        return """You are a monetization friction analysis system for app reviews.

TASK:
Identify monetization-related complaints and potential revenue risks from app reviews.

SIGNALS TO DETECT:
- Subscription complaints (too expensive, forced, unclear terms)
- Paywall frustration (features locked, too aggressive)
- Pricing confusion (unclear pricing, unexpected charges)
- Ad complaints (too many ads, intrusive ads)
- Refund requests
- Value perception issues

OUTPUT FORMAT (strict JSON):
{
    "overall_risk": "low" | "medium" | "high",
    "risks": [
        {
            "risk": "<clear description of monetization issue>",
            "confidence": "low" | "medium" | "high",
            "category": "subscription" | "pricing" | "paywall" | "ads" | "value" | "other",
            "impact": "<potential business impact>"
        }
    ]
}

RULES:
1. Focus only on monetization/revenue-related issues
2. Assess confidence based on frequency and clarity
3. Consider business impact
4. Only output valid JSON, no explanations"""
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "overall_risk": {"type": "string", "enum": ["low", "medium", "high"]},
                "risks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "risk": {"type": "string"},
                            "confidence": {"type": "string"},
                            "category": {"type": "string"},
                            "impact": {"type": "string"}
                        }
                    }
                }
            }
        }
    
    async def analyze(self, reviews: List[str]) -> Dict[str, Any]:
        """
        Analyze monetization friction in reviews.
        
        Args:
            reviews: List of review texts
            
        Returns:
            Monetization risk analysis
        """
        if not reviews:
            return {
                "overall_risk": "low",
                "risks": []
            }
        
        # Process in chunks
        chunks = self._chunk_reviews(reviews)
        all_risks = []
        risk_levels = []
        
        for chunk in chunks:
            reviews_text = "\n---\n".join(chunk)
            prompt = f"Analyze monetization friction in these {len(chunk)} app reviews:\n\n{reviews_text}"
            
            result = await self._call_openai(
                prompt,
                response_format={"type": "json_object"}
            )
            
            risks = result.get("risks", [])
            all_risks.extend(risks)
            
            overall = result.get("overall_risk", "low")
            risk_levels.append(self._risk_level(overall))
        
        # Aggregate risks
        risk_map = {}
        for risk in all_risks:
            name = risk.get("risk", "").lower().strip()
            if not name:
                continue
            
            if name in risk_map:
                # Keep higher confidence
                if self._risk_level(risk.get("confidence", "low")) > \
                   self._risk_level(risk_map[name]["confidence"]):
                    risk_map[name]["confidence"] = risk.get("confidence", "low")
            else:
                risk_map[name] = {
                    "risk": risk.get("risk", name),
                    "confidence": risk.get("confidence", "medium"),
                    "category": risk.get("category", "other"),
                    "impact": risk.get("impact", "")
                }
        
        # Calculate overall risk
        avg_risk = sum(risk_levels) / len(risk_levels) if risk_levels else 1
        if avg_risk >= 2.5:
            overall_risk = "high"
        elif avg_risk >= 1.5:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        # Sort by confidence
        sorted_risks = sorted(
            risk_map.values(),
            key=lambda x: self._risk_level(x["confidence"]),
            reverse=True
        )
        
        return {
            "overall_risk": overall_risk,
            "risks": sorted_risks[:10]  # Top 10 risks
        }
    
    def _risk_level(self, level: str) -> int:
        """Convert risk/confidence level to numeric."""
        return {"low": 1, "medium": 2, "high": 3}.get(level, 1)
