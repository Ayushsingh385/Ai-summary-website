"""
Summarize Router — API endpoints for PDF upload, summarization,
keyword extraction, and summary download.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from services.pdf_service import validate_pdf, extract_text_from_pdf
from services.nlp_service import summarize_text, extract_keywords, compute_text_stats
from services.download_service import generate_summary_pdf, generate_summary_txt

router = APIRouter(prefix="/api", tags=["Summarizer"])


# ──────────────────────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────────────────────

class SummarizeRequest(BaseModel):
    """Request body for the /summarize endpoint."""
    text: str
    length: Optional[str] = "medium"  # short | medium | long


class KeywordsRequest(BaseModel):
    """Request body for the /keywords endpoint."""
    text: str
    top_n: Optional[int] = 15


class DownloadRequest(BaseModel):
    """Request body for the /download endpoint."""
    summary: str
    original_word_count: int = 0
    summary_word_count: int = 0
    format: str = "txt"  # pdf | txt


# ──────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file and extract its text content.

    Returns:
        - Extracted full text
        - Page count, word count, reading time
        - Per-page text breakdown
    """
    file_bytes = await file.read()

    # Validate the uploaded file
    validate_pdf(file_bytes, file.content_type, file.filename)

    # Extract text
    result = extract_text_from_pdf(file_bytes)
    result["filename"] = file.filename
    return result


@router.post("/summarize")
async def summarize(request: SummarizeRequest):
    """
    Summarize the provided text using BART NLP model.

    Request body:
        - text:   The text to summarize
        - length: 'short', 'medium', or 'long'

    Returns:
        - Generated summary
        - Word counts and compression ratio
    """
    if not request.text or len(request.text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Text is too short to summarize. Please provide at least 50 characters."
        )

    result = summarize_text(request.text, request.length)
    stats = compute_text_stats(request.text)
    result["original_stats"] = stats
    return result


@router.post("/keywords")
async def keywords(request: KeywordsRequest):
    """
    Extract keywords from the provided text.

    Request body:
        - text:   The text to analyze
        - top_n:  Number of keywords to return (default: 15)

    Returns:
        List of keywords with relevance scores.
    """
    if not request.text or len(request.text.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Text is too short for keyword extraction."
        )

    result = extract_keywords(request.text, request.top_n)
    return {"keywords": result}


@router.post("/download")
async def download_summary(request: DownloadRequest):
    """
    Download the summary as a PDF or TXT file.

    Request body:
        - summary:             The summary text
        - original_word_count: Word count of the original text
        - summary_word_count:  Word count of the summary
        - format:              'pdf' or 'txt'

    Returns:
        File download response.
    """
    if request.format == "pdf":
        pdf_bytes = generate_summary_pdf(
            request.summary,
            request.original_word_count,
            request.summary_word_count,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=summary.pdf"}
        )

    elif request.format == "txt":
        txt_content = generate_summary_txt(
            request.summary,
            request.original_word_count,
            request.summary_word_count,
        )
        return Response(
            content=txt_content.encode("utf-8"),
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=summary.txt"}
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid format. Use 'pdf' or 'txt'."
        )
