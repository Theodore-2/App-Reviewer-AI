"""
App Reviewer AI - API Schemas

Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from enum import Enum
from datetime import datetime
import re


# ============================================================================
# Enums
# ============================================================================

class Platform(str, Enum):
    """Supported platforms."""
    IOS = "ios"
    ANDROID = "android"


class JobStatus(str, Enum):
    """Job lifecycle states."""
    CREATED = "created"
    FETCHING_REVIEWS = "fetching"
    ANALYZING_REVIEWS = "analyzing"
    AGGREGATING_RESULTS = "aggregating"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(str, Enum):
    """Severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Priority(str, Enum):
    """Priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ErrorCode(str, Enum):
    """Error codes as specified in directive."""
    INVALID_INPUT = "ERR_INVALID_INPUT"
    REVIEW_FETCH_FAILED = "ERR_REVIEW_FETCH_FAILED"
    AI_TIMEOUT = "ERR_AI_TIMEOUT"
    SCHEMA_VALIDATION_FAILED = "ERR_SCHEMA_VALIDATION_FAILED"
    COST_LIMIT_EXCEEDED = "ERR_COST_LIMIT_EXCEEDED"


# ============================================================================
# Request Models
# ============================================================================

class AnalysisOptions(BaseModel):
    """Options for analysis request."""
    review_limit: int = Field(
        default=500,
        ge=1,
        le=1000,
        description="Maximum number of reviews to analyze"
    )
    locale: Optional[str] = Field(
        default=None,
        description="Locale filter (e.g., 'en-US')"
    )
    analysis_version: str = Field(
        default="v1",
        description="Analysis pipeline version"
    )


class AnalyzeRequest(BaseModel):
    """Request model for POST /analyze endpoint."""
    app_url: str = Field(
        ...,
        description="App Store or Play Store URL",
        min_length=10
    )
    platform: Platform = Field(
        default=Platform.IOS,
        description="Platform (ios or android)"
    )
    options: Optional[AnalysisOptions] = Field(
        default_factory=AnalysisOptions,
        description="Analysis options"
    )
    
    @field_validator("app_url")
    @classmethod
    def validate_app_url(cls, v: str) -> str:
        """Validate that URL is from supported app stores."""
        ios_pattern = r"https?://apps\.apple\.com/.+/app/.+"
        android_pattern = r"https?://play\.google\.com/store/apps/details\?id=.+"
        
        if not (re.match(ios_pattern, v) or re.match(android_pattern, v)):
            raise ValueError(
                "URL must be a valid App Store or Play Store URL"
            )
        return v


# ============================================================================
# Response Models
# ============================================================================

class AnalyzeResponse(BaseModel):
    """Response model for POST /analyze endpoint."""
    analysis_id: str = Field(..., description="Unique analysis job ID")
    status: JobStatus = Field(..., description="Current job status")
    estimated_time_sec: int = Field(..., description="Estimated processing time")
    cached: bool = Field(default=False, description="Whether result was cached")


class StatusResponse(BaseModel):
    """Response model for GET /status/{analysis_id} endpoint."""
    analysis_id: str = Field(..., description="Unique analysis job ID")
    status: JobStatus = Field(..., description="Current job status")
    progress: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Progress percentage (0-100)"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[ErrorCode] = Field(default=None, description="Error code if failed")


# ============================================================================
# Insight Result Models (Final Output Schema)
# ============================================================================

class SentimentBreakdown(BaseModel):
    """Sentiment distribution."""
    positive: float = Field(..., ge=0, le=100, description="Positive percentage")
    neutral: float = Field(..., ge=0, le=100, description="Neutral percentage")
    negative: float = Field(..., ge=0, le=100, description="Negative percentage")


class TopIssue(BaseModel):
    """Issue/bug entry."""
    issue: str = Field(..., description="Issue description")
    frequency: int = Field(..., ge=1, description="Occurrence count")
    severity: Severity = Field(..., description="Issue severity")


class FeatureRequest(BaseModel):
    """Feature request entry."""
    feature: str = Field(..., description="Requested feature")
    count: int = Field(..., ge=1, description="Request count")


class MonetizationRisk(BaseModel):
    """Monetization risk entry."""
    risk: str = Field(..., description="Risk description")
    confidence: Severity = Field(..., description="Confidence level")


class RecommendedAction(BaseModel):
    """Recommended action entry."""
    action: str = Field(..., description="Action description")
    priority: Priority = Field(..., description="Action priority")
    expected_impact: str = Field(..., description="Expected impact")


class InsightResult(BaseModel):
    """Final aggregated insight result."""
    summary: str = Field(..., description="Executive summary")
    sentiment_breakdown: SentimentBreakdown = Field(..., description="Sentiment distribution")
    top_issues: List[TopIssue] = Field(default_factory=list, description="Top issues")
    feature_requests: List[FeatureRequest] = Field(default_factory=list, description="Feature requests")
    monetization_risks: List[MonetizationRisk] = Field(default_factory=list, description="Monetization risks")
    recommended_actions: List[RecommendedAction] = Field(default_factory=list, description="Recommended actions")
    
    # Metadata
    app_id: str = Field(..., description="App identifier")
    platform: Platform = Field(..., description="Platform")
    reviews_analyzed: int = Field(..., description="Number of reviews analyzed")
    analysis_version: str = Field(..., description="Analysis version used")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Generation timestamp")


class ResultResponse(BaseModel):
    """Response model for GET /result/{analysis_id} endpoint."""
    analysis_id: str = Field(..., description="Unique analysis job ID")
    result: InsightResult = Field(..., description="Analysis result")


# ============================================================================
# Error Response Model
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error message")
    error_code: ErrorCode = Field(..., description="Error code")
    details: Optional[str] = Field(default=None, description="Additional details")


# ============================================================================
# Internal Models (for job processing)
# ============================================================================

class Review(BaseModel):
    """Normalized review model."""
    review_id: str = Field(..., description="Unique review ID")
    rating: int = Field(..., ge=1, le=5, description="Star rating")
    date: datetime = Field(..., description="Review date")
    locale: str = Field(..., description="Review locale")
    title: Optional[str] = Field(default=None, description="Review title")
    body: str = Field(..., description="Review body")
    
    # Cleaned fields
    body_cleaned: Optional[str] = Field(default=None, description="Cleaned body text")
    detected_language: Optional[str] = Field(default=None, description="Detected language")


class JobData(BaseModel):
    """Internal job data model."""
    analysis_id: str
    app_url: str
    app_id: str
    platform: Platform
    options: AnalysisOptions
    request_hash: str
    status: JobStatus = JobStatus.CREATED
    progress: int = 0
    error: Optional[str] = None
    error_code: Optional[ErrorCode] = None
    reviews: List[Review] = Field(default_factory=list)
    result: Optional[InsightResult] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tokens_used: int = 0
