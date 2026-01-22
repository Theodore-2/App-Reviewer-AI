"""
App Reviewer AI - Action Recommendation Pipeline

Converts insights into recommended actions.
"""

from typing import List, Dict, Any
import logging

from app.pipelines.base import BasePipeline

logger = logging.getLogger(__name__)


class ActionPipeline(BasePipeline):
    """
    Action recommendation mapping pipeline.
    
    Takes outputs from other pipelines and generates prioritized action items.
    
    Output:
    [
        {
            "action": "Fix authentication regression",
            "priority": "high",
            "expected_impact": "Rating recovery, reduced churn"
        }
    ]
    """
    
    VERSION = "1.0"
    
    @property
    def name(self) -> str:
        return "actions"
    
    @property
    def system_prompt(self) -> str:
        return """You are an action recommendation system for product teams.

TASK:
Based on the analyzed issues, feature requests, and monetization risks, generate prioritized action recommendations.

INPUT: You will receive:
- Issues/bugs from the app
- Feature requests from users
- Monetization risks identified

OUTPUT FORMAT (strict JSON):
{
    "actions": [
        {
            "action": "<specific, actionable recommendation>",
            "priority": "low" | "medium" | "high" | "critical",
            "expected_impact": "<expected outcome if implemented>",
            "category": "bug_fix" | "feature" | "ux" | "monetization" | "performance" | "other",
            "effort": "low" | "medium" | "high"
        }
    ]
}

PRIORITIZATION RULES:
1. Critical: App crashes, data loss, security issues
2. High: Major functionality broken, significant user churn signals
3. Medium: Important features, common complaints
4. Low: Nice-to-have improvements

RULES:
1. Be specific and actionable
2. Consider effort vs impact
3. Group related items
4. Maximum 10 recommendations
5. Only output valid JSON, no explanations"""
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string"},
                            "priority": {"type": "string"},
                            "expected_impact": {"type": "string"},
                            "category": {"type": "string"},
                            "effort": {"type": "string"}
                        }
                    }
                }
            }
        }
    
    async def analyze(
        self,
        issues: List[Dict[str, Any]],
        features: List[Dict[str, Any]],
        monetization: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate action recommendations from analysis results.
        
        Args:
            issues: List of issues from IssuePipeline
            features: List of features from FeaturePipeline
            monetization: Result from MonetizationPipeline
            
        Returns:
            List of action recommendations
        """
        # Prepare context for the AI
        context_parts = []
        
        if issues:
            issues_text = "\n".join([
                f"- [{i.get('severity', 'medium').upper()}] {i.get('issue', '')} (frequency: {i.get('frequency', 0)})"
                for i in issues[:10]
            ])
            context_parts.append(f"ISSUES/BUGS:\n{issues_text}")
        
        if features:
            features_text = "\n".join([
                f"- {f.get('feature', '')} (requested {f.get('count', 0)} times)"
                for f in features[:10]
            ])
            context_parts.append(f"FEATURE REQUESTS:\n{features_text}")
        
        risks = monetization.get("risks", []) if monetization else []
        if risks:
            risks_text = "\n".join([
                f"- [{r.get('confidence', 'medium').upper()}] {r.get('risk', '')}"
                for r in risks[:5]
            ])
            overall_risk = monetization.get("overall_risk", "low")
            context_parts.append(f"MONETIZATION RISKS (Overall: {overall_risk}):\n{risks_text}")
        
        if not context_parts:
            return []
        
        context = "\n\n".join(context_parts)
        prompt = f"Based on the following analysis, generate prioritized action recommendations:\n\n{context}"
        
        result = await self._call_openai(
            prompt,
            response_format={"type": "json_object"}
        )
        
        actions = result.get("actions", [])
        
        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_actions = sorted(
            actions,
            key=lambda x: priority_order.get(x.get("priority", "low"), 4)
        )
        
        return sorted_actions[:10]  # Top 10 actions
