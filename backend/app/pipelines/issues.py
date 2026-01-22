"""
App Reviewer AI - Issue & Bug Extraction Pipeline

Identifies recurring technical or UX problems.
"""

from typing import List, Dict, Any
import logging

from app.pipelines.base import BasePipeline

logger = logging.getLogger(__name__)


class IssuePipeline(BasePipeline):
    """
    Issue and bug extraction pipeline.
    
    Output:
    [
        {
            "issue": "Login fails after update",
            "frequency": 34,
            "severity": "high"
        }
    ]
    """
    
    VERSION = "1.0"
    
    @property
    def name(self) -> str:
        return "issues"
    
    @property
    def system_prompt(self) -> str:
        return """You are an issue and bug extraction system for app reviews.

TASK:
Extract and categorize technical issues, bugs, and UX problems from app reviews.

OUTPUT FORMAT (strict JSON):
{
    "issues": [
        {
            "issue": "<clear description of the issue>",
            "frequency": <estimated count across reviews>,
            "severity": "low" | "medium" | "high",
            "category": "<bug|crash|performance|ux|content|other>"
        }
    ]
}

RULES:
1. Group similar issues together
2. Severity based on impact: high=crashes/data loss, medium=broken features, low=minor annoyances
3. Be specific but concise in issue descriptions
4. Only extract actual problems, not feature requests
5. Only output valid JSON, no explanations"""
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "issue": {"type": "string"},
                            "frequency": {"type": "integer"},
                            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                            "category": {"type": "string"}
                        }
                    }
                }
            }
        }
    
    async def analyze(self, reviews: List[str]) -> List[Dict[str, Any]]:
        """
        Extract issues from reviews.
        
        Args:
            reviews: List of review texts
            
        Returns:
            List of issue objects
        """
        if not reviews:
            return []
        
        # Process in chunks
        chunks = self._chunk_reviews(reviews)
        all_issues = []
        
        for chunk in chunks:
            reviews_text = "\n---\n".join(chunk)
            prompt = f"Extract issues and bugs from these {len(chunk)} app reviews:\n\n{reviews_text}"
            
            result = await self._call_openai(
                prompt,
                response_format={"type": "json_object"}
            )
            
            issues = result.get("issues", [])
            all_issues.extend(issues)
        
        # Aggregate and deduplicate issues
        issue_map = {}
        for issue in all_issues:
            name = issue.get("issue", "").lower().strip()
            if not name:
                continue
            
            if name in issue_map:
                # Merge: add frequency, keep highest severity
                issue_map[name]["frequency"] += issue.get("frequency", 1)
                if self._severity_level(issue.get("severity", "low")) > \
                   self._severity_level(issue_map[name]["severity"]):
                    issue_map[name]["severity"] = issue.get("severity", "low")
            else:
                issue_map[name] = {
                    "issue": issue.get("issue", name),
                    "frequency": issue.get("frequency", 1),
                    "severity": issue.get("severity", "medium"),
                    "category": issue.get("category", "other")
                }
        
        # Sort by frequency and severity
        sorted_issues = sorted(
            issue_map.values(),
            key=lambda x: (x["frequency"] * self._severity_level(x["severity"])),
            reverse=True
        )
        
        return sorted_issues[:20]  # Top 20 issues
    
    def _severity_level(self, severity: str) -> int:
        """Convert severity to numeric level."""
        return {"low": 1, "medium": 2, "high": 3}.get(severity, 1)
