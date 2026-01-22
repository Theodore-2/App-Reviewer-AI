"""
App Reviewer AI - API Routes

FastAPI route handlers for all endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional
import hashlib
import uuid
import io
import json
import os
from pathlib import Path

from app.api.schemas import (
    AnalyzeRequest, AnalyzeResponse, StatusResponse, ResultResponse,
    ErrorResponse, JobStatus, ErrorCode, Platform
)
from app.core.job_manager import JobManager, get_job_manager
from app.core.worker import process_job
from app.services.pdf_generator import generate_pdf_report
from app.services.review_fetcher import ReviewFetcher
from app.config import get_settings

router = APIRouter()


def generate_request_hash(request: AnalyzeRequest) -> str:
    """Generate deterministic hash for request caching."""
    data = f"{request.app_url}|{request.options.review_limit}|{request.options.locale}|{request.options.analysis_version}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]


def extract_app_id(app_url: str, platform: str) -> str:
    """Extract app ID from store URL."""
    import re
    
    if platform == "ios":
        # iOS App Store URL: https://apps.apple.com/us/app/app-name/id123456789
        match = re.search(r"/id(\d+)", app_url)
        if match:
            return match.group(1)
    else:
        # Google Play URL: https://play.google.com/store/apps/details?id=com.example.app
        match = re.search(r"id=([^&]+)", app_url)
        if match:
            return match.group(1)
    
    raise ValueError(f"Could not extract app ID from URL: {app_url}")


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Create analysis job",
    description="Submit an app URL for review analysis. Returns a job ID for tracking."
)
async def create_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    job_manager: JobManager = Depends(get_job_manager)
) -> AnalyzeResponse:
    """Create a new analysis job or return cached result."""
    settings = get_settings()
    
    # Validate locale if provided
    if request.options.locale and request.options.locale not in settings.locales_list:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=f"Unsupported locale: {request.options.locale}",
                error_code=ErrorCode.INVALID_INPUT,
                details=f"Supported locales: {settings.locales_list}"
            ).model_dump()
        )
    
    # Extract app ID
    try:
        app_id = extract_app_id(request.app_url, request.platform.value)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=str(e),
                error_code=ErrorCode.INVALID_INPUT
            ).model_dump()
        )
    
    # Generate request hash for caching
    request_hash = generate_request_hash(request)
    
    # Check if cached result exists
    cached_job = await job_manager.get_by_hash(request_hash)
    if cached_job and cached_job.status == JobStatus.COMPLETED:
        return AnalyzeResponse(
            analysis_id=cached_job.analysis_id,
            status=cached_job.status,
            estimated_time_sec=0,
            cached=True
        )
    
    # Create new job
    analysis_id = str(uuid.uuid4())
    await job_manager.create_job(
        analysis_id=analysis_id,
        app_url=request.app_url,
        app_id=app_id,
        platform=request.platform,
        options=request.options,
        request_hash=request_hash
    )
    
    # Start background processing
    background_tasks.add_task(process_job, analysis_id)
    
    # Estimate processing time based on review limit
    estimated_time = 30 + (request.options.review_limit // 100) * 10
    
    return AnalyzeResponse(
        analysis_id=analysis_id,
        status=JobStatus.CREATED,
        estimated_time_sec=estimated_time,
        cached=False
    )


@router.get(
    "/status/{analysis_id}",
    response_model=StatusResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get job status",
    description="Check the status and progress of an analysis job."
)
async def get_status(
    analysis_id: str,
    job_manager: JobManager = Depends(get_job_manager)
) -> StatusResponse:
    """Get current status of an analysis job."""
    job = await job_manager.get_job(analysis_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=f"Analysis job not found: {analysis_id}",
                error_code=ErrorCode.INVALID_INPUT
            ).model_dump()
        )
    
    return StatusResponse(
        analysis_id=job.analysis_id,
        status=job.status,
        progress=job.progress,
        error=job.error,
        error_code=job.error_code
    )


@router.get(
    "/result/{analysis_id}",
    response_model=ResultResponse,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse}
    },
    summary="Get analysis result",
    description="Retrieve the completed analysis result."
)
async def get_result(
    analysis_id: str,
    job_manager: JobManager = Depends(get_job_manager)
) -> ResultResponse:
    """Get the result of a completed analysis job."""
    job = await job_manager.get_job(analysis_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=f"Analysis job not found: {analysis_id}",
                error_code=ErrorCode.INVALID_INPUT
            ).model_dump()
        )
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=f"Analysis not yet completed. Current status: {job.status.value}",
                error_code=ErrorCode.INVALID_INPUT
            ).model_dump()
        )
    
    if not job.result:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Result not available despite completed status",
                error_code=ErrorCode.SCHEMA_VALIDATION_FAILED
            ).model_dump()
        )
    
    return ResultResponse(
        analysis_id=job.analysis_id,
        result=job.result
    )


@router.get(
    "/export/pdf/{analysis_id}",
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse}
    },
    summary="Export PDF report",
    description="Download the analysis result as a PDF report."
)
async def export_pdf(
    analysis_id: str,
    job_manager: JobManager = Depends(get_job_manager)
) -> StreamingResponse:
    """Export analysis result as PDF."""
    job = await job_manager.get_job(analysis_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=f"Analysis job not found: {analysis_id}",
                error_code=ErrorCode.INVALID_INPUT
            ).model_dump()
        )
    
    if job.status != JobStatus.COMPLETED or not job.result:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Analysis must be completed before exporting PDF",
                error_code=ErrorCode.INVALID_INPUT
            ).model_dump()
        )
    
    # Generate PDF
    pdf_buffer = generate_pdf_report(job.result)
    
    return StreamingResponse(
        io.BytesIO(pdf_buffer),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="app_review_analysis_{analysis_id[:8]}.pdf"'
        }
    )


@router.get(
    "/health",
    summary="Health check",
    description="Check if the API is running."
)
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy", 
        "service": "app-reviewer-ai",
        "model": settings.openai_model
    }


@router.post(
    "/fetch-reviews",
    summary="Fetch and save reviews",
    description="Fetch reviews from app store and save to JSON file (no AI analysis)."
)
async def fetch_reviews(
    app_url: str,
    platform: str = "ios",
    locale: str = "en-US",
    limit: int = 100
):
    """Fetch reviews and save to JSON file for inspection."""
    import re
    import httpx
    
    # Extract app ID from various URL formats
    # Handles: /id123, /id/123, id=123
    # Also handles country codes like /tr/, /us/, /gb/ in URLs
    if platform == "ios":
        # Try multiple patterns for iOS App Store URLs
        patterns = [
            r"/id(\d+)",           # Standard: /id389801252
            r"/id/(\d+)",          # Alternative: /id/389801252
            r"[?&]id=(\d+)",       # Query param: ?id=389801252
        ]
        app_id = None
        for pattern in patterns:
            match = re.search(pattern, app_url)
            if match:
                app_id = match.group(1)
                break
        
        if not app_id:
            raise HTTPException(status_code=400, detail="Invalid iOS App Store URL. Could not extract app ID.")
    else:
        match = re.search(r"id=([^&]+)", app_url)
        if match:
            app_id = match.group(1)
        else:
            raise HTTPException(status_code=400, detail="Invalid Play Store URL")
    
    # Get app name from App Store API
    app_name = app_id  # fallback
    try:
        async with httpx.AsyncClient() as client:
            # Use the locale's country code for lookup
            country = locale.split("-")[-1].lower() if "-" in locale else "us"
            lookup_url = f"https://itunes.apple.com/lookup?id={app_id}&country={country}"
            response = await client.get(lookup_url)
            if response.status_code == 200:
                data = response.json()
                if data.get("resultCount", 0) > 0:
                    app_name = data["results"][0].get("trackName", app_id)
    except Exception:
        pass  # Use app_id as fallback
    
    # Clean app name for filename (remove special characters)
    safe_name = re.sub(r'[^\w\s-]', '', app_name).strip().replace(' ', '_').lower()
    
    # Fetch reviews
    fetcher = ReviewFetcher()
    reviews = await fetcher.fetch_reviews(
        app_id=app_id,
        platform=platform,
        locale=locale,
        limit=limit
    )
    
    if not reviews:
        raise HTTPException(status_code=404, detail="No reviews found for this app")
    
    # Save to JSON file
    data_dir = Path(__file__).parent.parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    filename = f"{safe_name}_reviews.json"
    filepath = data_dir / filename
    
    reviews_data = {
        "app_name": app_name,
        "app_id": app_id,
        "platform": platform,
        "locale": locale,
        "total_reviews": len(reviews),
        "reviews": [r.model_dump(mode="json") for r in reviews]
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(reviews_data, f, indent=2, ensure_ascii=False, default=str)
    
    # Return ALL reviews, not just sample
    return {
        "message": f"Saved {len(reviews)} reviews",
        "app_name": app_name,
        "file": str(filepath),
        "app_id": app_id,
        "locale": locale,
        "total_reviews": len(reviews),
        "reviews": [
            {
                "rating": r.rating,
                "title": r.title,
                "body": r.body,
                "date": r.date.isoformat() if r.date else None
            }
            for r in reviews
        ]
    }


