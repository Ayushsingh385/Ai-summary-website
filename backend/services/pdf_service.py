"""
PDF Service — Handles PDF file validation and text extraction.
Uses pypdfium2 for high-performance text extraction.
"""

import pypdfium2 as pdfium
from io import BytesIO
from fastapi import HTTPException
import pytesseract
from pdf2image import convert_from_bytes
import logging

logger = logging.getLogger(__name__)

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
    Extract text from a PDF file using pypdfium2 (high performance).
    Returns a dict with extracted text, page count, and per-page text.
    """
    try:
        pages_text = []
        full_text_list = []

        # Load document from bytes
        pdf = pdfium.PdfDocument(file_bytes)
        page_count = len(pdf)

        for i in range(page_count):
            page = pdf.get_page(i)
            text_page = page.get_textpage()
            text = text_page.get_text_range() or ""
            
            clean_text = text.strip()
            pages_text.append({
                "page_number": i + 1,
                "text": clean_text,
                "char_count": len(clean_text)
            })
            full_text_list.append(clean_text)
            
            # Close page resources
            text_page.close()
            page.close()
        
        pdf.close()
        full_text = "\n\n".join(full_text_list).strip()

        if not full_text or len(full_text) < 10:
            logger.info("PDF text extraction failed or text is too short. Attempting OCR fallback...")
            try:
                # Convert PDF to list of images
                images = convert_from_bytes(file_bytes)
                pages_text = []
                full_text_list = []
                
                for i, img in enumerate(images):
                    text = pytesseract.image_to_string(img)
                    clean_text = text.strip()
                    pages_text.append({
                        "page_number": i + 1,
                        "text": clean_text,
                        "char_count": len(clean_text)
                    })
                    full_text_list.append(clean_text)
                
                full_text = "\n\n".join(full_text_list).strip()
                page_count = len(images)
                
            except Exception as ocr_err:
                logger.error(f"OCR fallback failed: {ocr_err}")
                raise HTTPException(
                    status_code=422,
                    detail="Could not extract meaningful text from the PDF. "
                           "The file may be scanned/image-based or empty, and OCR failed."
                )

        if not full_text or len(full_text) < 10:
            raise HTTPException(
                status_code=422,
                detail="Even with OCR, could not extract meaningful text from the PDF."
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
