"""
PDF Service — Handles PDF file validation and text extraction.
Uses pdfplumber for reliable text extraction from PDF documents.
"""

import pdfplumber
from io import BytesIO
from fastapi import HTTPException


# Maximum file size: 20 MB
MAX_FILE_SIZE = 20 * 1024 * 1024
ALLOWED_CONTENT_TYPES = [
    "application/pdf",
]


def validate_pdf(file_bytes: bytes, content_type: str, filename: str) -> None:
    """
    Validate that the uploaded file is a legitimate PDF within size limits.
    Raises HTTPException on validation failure.
    """
    # Check content type
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{content_type}'. Only PDF files are accepted."
        )

    # Check file extension
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file extension. Only .pdf files are accepted."
        )

    # Check file size
    if len(file_bytes) > MAX_FILE_SIZE:
        size_mb = len(file_bytes) / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum size is 20 MB."
        )

    # Check PDF magic bytes
    if not file_bytes[:5] == b"%PDF-":
        raise HTTPException(
            status_code=400,
            detail="File does not appear to be a valid PDF."
        )


def extract_text_from_pdf(file_bytes: bytes) -> dict:
    """
    Extract text from a PDF file using pdfplumber.
    Returns a dict with extracted text, page count, and per-page text.
    """
    try:
        pages_text = []
        full_text = ""

        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            page_count = len(pdf.pages)

            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                pages_text.append({
                    "page_number": i + 1,
                    "text": text.strip(),
                    "char_count": len(text.strip())
                })
                full_text += text + "\n\n"

        full_text = full_text.strip()

        if not full_text or len(full_text) < 10:
            raise HTTPException(
                status_code=422,
                detail="Could not extract meaningful text from the PDF. "
                       "The file may be scanned/image-based or empty."
            )

        # Calculate word count and reading time
        word_count = len(full_text.split())
        reading_time_minutes = max(1, round(word_count / 200))  # avg 200 wpm

        return {
            "text": full_text,
            "page_count": page_count,
            "word_count": word_count,
            "reading_time_minutes": reading_time_minutes,
            "pages": pages_text
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(e)}"
        )
