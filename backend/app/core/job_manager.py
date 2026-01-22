"""
App Reviewer AI - Job Manager

Manages job lifecycle, state transitions, and persistence.
"""

from typing import Optional, Dict
from datetime import datetime
import logging

from app.api.schemas import (
    JobData, JobStatus, Platform, AnalysisOptions, 
    ErrorCode, InsightResult, Review
)
from app.core.cache import get_cache_manager
from app.config import get_settings

logger = logging.getLogger(__name__)


class JobManager:
    """Manages analysis job lifecycle."""
    
    # Cache key prefixes
    JOB_PREFIX = "job:"
    HASH_PREFIX = "hash:"
    
    def __init__(self):
        self.cache = get_cache_manager()
        self.settings = get_settings()
    
    def _job_key(self, analysis_id: str) -> str:
        """Generate cache key for job."""
        return f"{self.JOB_PREFIX}{analysis_id}"
    
    def _hash_key(self, request_hash: str) -> str:
        """Generate cache key for request hash."""
        return f"{self.HASH_PREFIX}{request_hash}"
    
    async def create_job(
        self,
        analysis_id: str,
        app_url: str,
        app_id: str,
        platform: Platform,
        options: AnalysisOptions,
        request_hash: str
    ) -> JobData:
        """Create a new analysis job."""
        job = JobData(
            analysis_id=analysis_id,
            app_url=app_url,
            app_id=app_id,
            platform=platform,
            options=options,
            request_hash=request_hash,
            status=JobStatus.CREATED,
            progress=0
        )
        
        # Store job data
        await self.cache.set_json(
            self._job_key(analysis_id),
            job.model_dump(mode="json"),
            ttl=self.settings.result_cache_ttl
        )
        
        # Store hash -> analysis_id mapping
        await self.cache.set_json(
            self._hash_key(request_hash),
            {"analysis_id": analysis_id},
            ttl=self.settings.result_cache_ttl
        )
        
        logger.info(f"Created job {analysis_id} for app {app_id}")
        return job
    
    async def get_job(self, analysis_id: str) -> Optional[JobData]:
        """Get job by analysis ID."""
        data = await self.cache.get_json(self._job_key(analysis_id))
        if data:
            return JobData(**data)
        return None
    
    async def get_by_hash(self, request_hash: str) -> Optional[JobData]:
        """Get job by request hash (for cache lookup)."""
        mapping = await self.cache.get_json(self._hash_key(request_hash))
        if mapping and "analysis_id" in mapping:
            return await self.get_job(mapping["analysis_id"])
        return None
    
    async def update_status(
        self,
        analysis_id: str,
        status: JobStatus,
        progress: Optional[int] = None,
        error: Optional[str] = None,
        error_code: Optional[ErrorCode] = None
    ) -> Optional[JobData]:
        """Update job status."""
        job = await self.get_job(analysis_id)
        if not job:
            return None
        
        job.status = status
        job.updated_at = datetime.utcnow()
        
        if progress is not None:
            job.progress = progress
        
        if error:
            job.error = error
            job.error_code = error_code
        
        await self.cache.set_json(
            self._job_key(analysis_id),
            job.model_dump(mode="json"),
            ttl=self.settings.result_cache_ttl
        )
        
        logger.info(f"Job {analysis_id} status: {status.value} ({progress}%)")
        return job
    
    async def set_reviews(
        self,
        analysis_id: str,
        reviews: list[Review]
    ) -> Optional[JobData]:
        """Store fetched reviews for job."""
        job = await self.get_job(analysis_id)
        if not job:
            return None
        
        job.reviews = reviews
        job.updated_at = datetime.utcnow()
        
        await self.cache.set_json(
            self._job_key(analysis_id),
            job.model_dump(mode="json"),
            ttl=self.settings.result_cache_ttl
        )
        
        logger.info(f"Job {analysis_id}: stored {len(reviews)} reviews")
        return job
    
    async def set_result(
        self,
        analysis_id: str,
        result: InsightResult,
        tokens_used: int = 0
    ) -> Optional[JobData]:
        """Store final analysis result."""
        job = await self.get_job(analysis_id)
        if not job:
            return None
        
        job.result = result
        job.tokens_used = tokens_used
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.updated_at = datetime.utcnow()
        
        await self.cache.set_json(
            self._job_key(analysis_id),
            job.model_dump(mode="json"),
            ttl=self.settings.result_cache_ttl
        )
        
        logger.info(f"Job {analysis_id} completed (tokens: {tokens_used})")
        return job
    
    async def fail_job(
        self,
        analysis_id: str,
        error: str,
        error_code: ErrorCode
    ) -> Optional[JobData]:
        """Mark job as failed."""
        return await self.update_status(
            analysis_id,
            JobStatus.FAILED,
            error=error,
            error_code=error_code
        )


# Global instance
_job_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """Get job manager singleton."""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
