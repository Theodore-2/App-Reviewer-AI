"""
App Reviewer AI - Background Worker

Handles async job processing through the analysis pipeline.
"""

import asyncio
import logging
from typing import List

from app.api.schemas import (
    JobStatus, ErrorCode, Review, InsightResult,
    SentimentBreakdown, TopIssue, FeatureRequest,
    MonetizationRisk, RecommendedAction
)
from app.core.job_manager import get_job_manager
from app.services.review_fetcher import ReviewFetcher
from app.pipelines.sentiment import SentimentPipeline
from app.pipelines.issues import IssuePipeline
from app.pipelines.features import FeaturePipeline
from app.pipelines.monetization import MonetizationPipeline
from app.pipelines.actions import ActionPipeline
from app.aggregation.aggregator import InsightAggregator
from app.config import get_settings

logger = logging.getLogger(__name__)


async def process_job(analysis_id: str) -> None:
    """
    Main job processing function.
    
    Lifecycle:
    CREATED → FETCHING_REVIEWS → ANALYZING_REVIEWS → AGGREGATING_RESULTS → COMPLETED | FAILED
    """
    job_manager = get_job_manager()
    settings = get_settings()
    total_tokens = 0
    
    try:
        # Get job data
        job = await job_manager.get_job(analysis_id)
        if not job:
            logger.error(f"Job not found: {analysis_id}")
            return
        
        # ===== PHASE 1: FETCHING REVIEWS =====
        await job_manager.update_status(
            analysis_id, 
            JobStatus.FETCHING_REVIEWS, 
            progress=5
        )
        
        fetcher = ReviewFetcher()
        reviews = await fetcher.fetch_reviews(
            app_id=job.app_id,
            platform=job.platform.value,
            locale=job.options.locale or "en-US",
            limit=job.options.review_limit
        )
        
        if not reviews:
            await job_manager.fail_job(
                analysis_id,
                "Failed to fetch reviews from app store",
                ErrorCode.REVIEW_FETCH_FAILED
            )
            return
        
        await job_manager.set_reviews(analysis_id, reviews)
        await job_manager.update_status(
            analysis_id, 
            JobStatus.FETCHING_REVIEWS, 
            progress=20
        )
        
        logger.info(f"Job {analysis_id}: Fetched {len(reviews)} reviews")
        
        # ===== PHASE 2: ANALYZING REVIEWS =====
        await job_manager.update_status(
            analysis_id, 
            JobStatus.ANALYZING_REVIEWS, 
            progress=25
        )
        
        # Check cost limits
        if len(reviews) > settings.max_review_count:
            await job_manager.fail_job(
                analysis_id,
                f"Review count ({len(reviews)}) exceeds limit ({settings.max_review_count})",
                ErrorCode.COST_LIMIT_EXCEEDED
            )
            return
        
        # Prepare review texts
        review_texts = [r.body for r in reviews]
        
        # Run pipelines in parallel
        sentiment_pipeline = SentimentPipeline()
        issue_pipeline = IssuePipeline()
        feature_pipeline = FeaturePipeline()
        monetization_pipeline = MonetizationPipeline()
        
        pipeline_results = await asyncio.gather(
            sentiment_pipeline.analyze(review_texts),
            issue_pipeline.analyze(review_texts),
            feature_pipeline.analyze(review_texts),
            monetization_pipeline.analyze(review_texts),
            return_exceptions=True
        )
        
        # Check for pipeline errors
        for i, result in enumerate(pipeline_results):
            if isinstance(result, Exception):
                logger.error(f"Pipeline {i} failed: {result}")
                await job_manager.fail_job(
                    analysis_id,
                    f"AI pipeline failed: {str(result)}",
                    ErrorCode.AI_TIMEOUT
                )
                return
        
        sentiment_result, issues_result, features_result, monetization_result = pipeline_results
        
        # Track tokens
        total_tokens += sentiment_pipeline.tokens_used
        total_tokens += issue_pipeline.tokens_used
        total_tokens += feature_pipeline.tokens_used
        total_tokens += monetization_pipeline.tokens_used
        
        # Check token budget
        if total_tokens > settings.max_token_budget_per_job:
            await job_manager.fail_job(
                analysis_id,
                f"Token usage ({total_tokens}) exceeds budget ({settings.max_token_budget_per_job})",
                ErrorCode.COST_LIMIT_EXCEEDED
            )
            return
        
        await job_manager.update_status(
            analysis_id, 
            JobStatus.ANALYZING_REVIEWS, 
            progress=70
        )
        
        # Run action pipeline (depends on other results)
        action_pipeline = ActionPipeline()
        actions_result = await action_pipeline.analyze(
            issues=issues_result,
            features=features_result,
            monetization=monetization_result
        )
        total_tokens += action_pipeline.tokens_used
        
        await job_manager.update_status(
            analysis_id, 
            JobStatus.ANALYZING_REVIEWS, 
            progress=85
        )
        
        # ===== PHASE 3: AGGREGATING RESULTS =====
        await job_manager.update_status(
            analysis_id, 
            JobStatus.AGGREGATING_RESULTS, 
            progress=90
        )
        
        # Aggregate all pipeline outputs
        aggregator = InsightAggregator()
        result = aggregator.aggregate(
            app_id=job.app_id,
            platform=job.platform,
            reviews_analyzed=len(reviews),
            analysis_version=job.options.analysis_version,
            sentiment=sentiment_result,
            issues=issues_result,
            features=features_result,
            monetization=monetization_result,
            actions=actions_result
        )
        
        # ===== PHASE 4: COMPLETED =====
        await job_manager.set_result(analysis_id, result, total_tokens)
        
        logger.info(f"Job {analysis_id} completed successfully. Tokens: {total_tokens}")
        
    except Exception as e:
        logger.exception(f"Job {analysis_id} failed with error: {e}")
        await job_manager.fail_job(
            analysis_id,
            str(e),
            ErrorCode.SCHEMA_VALIDATION_FAILED
        )
