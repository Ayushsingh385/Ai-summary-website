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
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)

# ──────────────────────────────────────────────────────────────
# Create FastAPI app
# ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="PDF Summarizer API",
    description="Upload PDFs, extract text, and generate NLP-powered summaries.",
    version="1.0.0",
)

# ──────────────────────────────────────────────────────────────
# CORS — allow the React frontend to connect
# ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
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
