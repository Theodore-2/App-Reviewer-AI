"""
App Reviewer AI - Insight Aggregator

Merges all pipeline outputs into a unified insight object.
"""

from typing import List, Dict, Any
from datetime import datetime
import logging

from app.api.schemas import (
    InsightResult, SentimentBreakdown, TopIssue, FeatureRequest,
    MonetizationRisk, RecommendedAction, Platform, Severity, Priority
)

logger = logging.getLogger(__name__)


class InsightAggregator:
    """
    Aggregates outputs from all AI pipelines into a final insight object.
    
    Applies deterministic conflict resolution using frequency and severity weighting.
    """
    
    def aggregate(
        self,
        app_id: str,
        platform: Platform,
        reviews_analyzed: int,
        analysis_version: str,
        sentiment: Dict[str, Any],
        issues: List[Dict[str, Any]],
        features: List[Dict[str, Any]],
        monetization: Dict[str, Any],
        actions: List[Dict[str, Any]]
    ) -> InsightResult:
        """
        Aggregate all pipeline results into final insight.
        
        Args:
            app_id: App identifier
            platform: Platform (ios/android)
            reviews_analyzed: Number of reviews processed
            analysis_version: Version of analysis
            sentiment: Sentiment pipeline output
            issues: Issues pipeline output
            features: Features pipeline output
            monetization: Monetization pipeline output
            actions: Actions pipeline output
            
        Returns:
            Complete InsightResult object
        """
        logger.info(f"Aggregating results for app {app_id}")
        
        # Build sentiment breakdown
        sentiment_breakdown = self._build_sentiment_breakdown(sentiment)
        
        # Build top issues
        top_issues = self._build_top_issues(issues)
        
        # Build feature requests
        feature_requests = self._build_feature_requests(features)
        
        # Build monetization risks
        monetization_risks = self._build_monetization_risks(monetization)
        
        # Build recommended actions
        recommended_actions = self._build_recommended_actions(actions)
        
        # Generate executive summary
        summary = self._generate_summary(
            reviews_analyzed=reviews_analyzed,
            sentiment=sentiment,
            issues_count=len(top_issues),
            features_count=len(feature_requests),
            monetization=monetization
        )
        
        return InsightResult(
            summary=summary,
            sentiment_breakdown=sentiment_breakdown,
            top_issues=top_issues,
            feature_requests=feature_requests,
            monetization_risks=monetization_risks,
            recommended_actions=recommended_actions,
            app_id=app_id,
            platform=platform,
            reviews_analyzed=reviews_analyzed,
            analysis_version=analysis_version,
            generated_at=datetime.utcnow()
        )
    
    def _build_sentiment_breakdown(self, sentiment: Dict[str, Any]) -> SentimentBreakdown:
        """Build sentiment breakdown from pipeline output."""
        breakdown = sentiment.get("sentiment_breakdown", {})
        
        positive = breakdown.get("positive", 33.3)
        neutral = breakdown.get("neutral", 33.3)
        negative = breakdown.get("negative", 33.3)
        
        # Ensure percentages sum to ~100
        total = positive + neutral + negative
        if total > 0:
            positive = round(positive / total * 100, 1)
            neutral = round(neutral / total * 100, 1)
            negative = round(100 - positive - neutral, 1)
        
        return SentimentBreakdown(
            positive=positive,
            neutral=neutral,
            negative=negative
        )
    
    def _build_top_issues(self, issues: List[Dict[str, Any]]) -> List[TopIssue]:
        """Build top issues list with proper schema."""
        result = []
        
        for issue in issues[:10]:  # Top 10
            severity_str = issue.get("severity", "medium").lower()
            try:
                severity = Severity(severity_str)
            except ValueError:
                severity = Severity.MEDIUM
            
            result.append(TopIssue(
                issue=issue.get("issue", "Unknown issue"),
                frequency=issue.get("frequency", 1),
                severity=severity
            ))
        
        return result
    
    def _build_feature_requests(self, features: List[Dict[str, Any]]) -> List[FeatureRequest]:
        """Build feature requests list."""
        result = []
        
        for feature in features[:10]:  # Top 10
            result.append(FeatureRequest(
                feature=feature.get("feature", "Unknown feature"),
                count=feature.get("count", 1)
            ))
        
        return result
    
    def _build_monetization_risks(self, monetization: Dict[str, Any]) -> List[MonetizationRisk]:
        """Build monetization risks list."""
        result = []
        risks = monetization.get("risks", []) if monetization else []
        
        for risk in risks[:5]:  # Top 5
            confidence_str = risk.get("confidence", "medium").lower()
            try:
                confidence = Severity(confidence_str)
            except ValueError:
                confidence = Severity.MEDIUM
            
            result.append(MonetizationRisk(
                risk=risk.get("risk", "Unknown risk"),
                confidence=confidence
            ))
        
        return result
    
    def _build_recommended_actions(self, actions: List[Dict[str, Any]]) -> List[RecommendedAction]:
        """Build recommended actions list."""
        result = []
        
        for action in actions[:10]:  # Top 10
            priority_str = action.get("priority", "medium").lower()
            # Map "critical" to "high"
            if priority_str == "critical":
                priority_str = "high"
            
            try:
                priority = Priority(priority_str)
            except ValueError:
                priority = Priority.MEDIUM
            
            result.append(RecommendedAction(
                action=action.get("action", "Unknown action"),
                priority=priority,
                expected_impact=action.get("expected_impact", "")
            ))
        
        return result
    
    def _generate_summary(
        self,
        reviews_analyzed: int,
        sentiment: Dict[str, Any],
        issues_count: int,
        features_count: int,
        monetization: Dict[str, Any]
    ) -> str:
        """Generate executive summary."""
        overall_sentiment = sentiment.get("overall_sentiment", "neutral")
        monetization_risk = monetization.get("overall_risk", "low") if monetization else "low"
        
        # Build summary
        parts = [
            f"Analysis of {reviews_analyzed} reviews reveals {overall_sentiment} overall sentiment."
        ]
        
        if issues_count > 0:
            parts.append(f"{issues_count} key issues were identified.")
        
        if features_count > 0:
            parts.append(f"Users requested {features_count} new features.")
        
        if monetization_risk in ["medium", "high"]:
            parts.append(f"Monetization risk is {monetization_risk}; review pricing strategy.")
        
        return " ".join(parts)
