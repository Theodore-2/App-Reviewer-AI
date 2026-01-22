"""
App Reviewer AI - Main Application

FastAPI application entry point with middleware and route configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api.routes import router
from app.core.cache import get_redis_client
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    logger.info("Starting App Reviewer AI Backend...")
    settings = get_settings()
    logger.info(f"OpenAI Model: {settings.openai_model}")
    logger.info(f"Supported Locales: {settings.locales_list}")
    
    # Initialize Redis connection
    redis = await get_redis_client()
    if redis:
        logger.info("Redis connection established")
    else:
        logger.warning("Redis not available, using in-memory storage")
    
    yield
    
    # Shutdown
    logger.info("Shutting down App Reviewer AI Backend...")
    redis = await get_redis_client()
    if redis:
        await redis.close()


# Create FastAPI application
app = FastAPI(
    title="App Reviewer AI",
    description="Automated App Store Review Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, tags=["Analysis"])


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs."""
    return {
        "service": "App Reviewer AI",
        "version": "1.0.0",
        "docs": "/docs"
    }
