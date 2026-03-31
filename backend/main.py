"""
PDF Summarizer — FastAPI Application Entry Point.

This server provides API endpoints for:
  • PDF upload and text extraction
  • NLP-powered text summarization (BART)
  • Keyword extraction
  • Summary download (PDF / TXT)
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings
from routers.summarize import router as summarize_router
from routers.auth import router as auth_router
from routers.chat import router as chat_router
from database import engine
import models

# Initialize database tables
models.Base.metadata.create_all(bind=engine)


# ──────────────────────────────────────────────────────────────
# Configure logging
# ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Log startup configuration
logger.info(f"Starting in {settings.environment} mode")
logger.info(f"CORS origins: {settings.get_cors_origins_list()}")

# ──────────────────────────────────────────────────────────────
# Create FastAPI app
# ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="PDF Summarizer API",
    description="Upload PDFs, extract text, and generate NLP-powered summaries.",
    version="1.0.0",
)

# ──────────────────────────────────────────────────────────────
# Rate Limiting
# ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ──────────────────────────────────────────────────────────────
# CORS — allow configured frontend origins
# ──────────────────────────────────────────────────────────────
# In development, allow localhost origins
# In production, use strict CORS from environment
cors_origins = settings.get_cors_origins_list()

# Validate CORS origins in production
if settings.environment == "production":
    if "*" in cors_origins:
        logger.warning(
            "WARNING: Wildcard CORS origin detected in production mode. "
            "Set CORS_ORIGINS environment variable to your frontend domain."
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
# Register routers
# ──────────────────────────────────────────────────────────────
app.include_router(summarize_router)
app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    """Health check / welcome endpoint."""
    return {
        "message": "PDF Summarizer API is running",
        "docs": "/docs",
        "version": "1.0.0",
    }
