"""
PDF Service — Handles PDF file validation and text extraction.
Uses pypdfium2 for high-performance text extraction.
"""

import pypdfium2 as pdfium
from io import BytesIO
from fastapi import HTTPException
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import logging
import os
import asyncio

# Check for Tesseract path on Windows
if os.name == 'nt':
    tesseract_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Users\USER\AppData\Local\Tesseract-OCR\tesseract.exe'
    ]
    for path in tesseract_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break

logger = logging.getLogger(__name__)

# Maximum file size: 20 MB
MAX_FILE_SIZE = 20 * 1024 * 1024
ALLOWED_CONTENT_TYPES = [
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg"
]



def validate_pdf(file_bytes: bytes, content_type: str, filename: str) -> None:
    """
    Validate that the uploaded file is a legitimate PDF within size limits.
    Raises HTTPException on validation failure.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{content_type}'. Supported types: PDF, JPG, PNG."
        )

    # Check file extension
    ext = filename.lower().split('.')[-1]
    if ext not in ['pdf', 'jpg', 'jpeg', 'png', 'webp']:
        raise HTTPException(
            status_code=400,
            detail="Invalid file extension. Supported extensions: .pdf, .jpg, .jpeg, .png, .webp"
        )


    # Check file size
    if len(file_bytes) > MAX_FILE_SIZE:
        size_mb = len(file_bytes) / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum size is 20 MB."
        )

    # Check PDF magic bytes if it's a PDF
    if filename.lower().endswith(".pdf") and not file_bytes[:5] == b"%PDF-":
        raise HTTPException(
            status_code=400,
            detail="File does not appear to be a valid PDF."
        )



async def extract_text_from_pdf(file_bytes: bytes) -> dict:
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

        # If average text per page is very low (< 50 chars), it's likely a scanned PDF needing OCR
        avg_chars_per_page = len(full_text) / max(1, page_count)
        
        if not full_text or avg_chars_per_page < 50:
            logger.info(f"PDF text extraction yielded low text (avg {avg_chars_per_page:.1f} chars/page). Attempting parallel OCR fallback...")
            try:
                # Load document with pdfium for faster rendering than Poppler
                pdf = pdfium.PdfDocument(file_bytes)
                page_count = len(pdf)
                
                async def ocr_page(page_idx):
                    # Render page to PIL image
                    page = pdf.get_page(page_idx)
                    # 300 DPI is standard for OCR
                    bitmap = page.render(scale=300/72) 
                    pil_image = bitmap.to_pil()
                    
                    # Use asyncio.to_thread for blocking Tesseract calls
                    text = await asyncio.to_thread(pytesseract.image_to_string, pil_image)
                    clean_text = text.strip()
                    
                    page.close()
                    return {
                        "page_number": page_idx + 1,
                        "text": clean_text,
                        "char_count": len(clean_text)
                    }

                # Run OCR on all pages in parallel
                ocr_results = await asyncio.gather(*[ocr_page(i) for i in range(page_count)])
                pdf.close()
                
                # Sort by page number to maintain order
                ocr_results.sort(key=lambda x: x["page_number"])
                
                pages_text = ocr_results
                full_text_list = [res["text"] for res in ocr_results]
                full_text = "\n\n".join(full_text_list).strip()
                page_count = len(ocr_results)
                
            except Exception as ocr_err:
                logger.error(f"Parallel OCR fallback failed: {ocr_err}")
                raise HTTPException(
                    status_code=422,
                    detail="Could not extract meaningful text from the PDF using Parallel OCR."
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

def extract_text_from_image(file_bytes: bytes) -> dict:
    """
    Extract text from an image file using pytesseract.
    Returns a dict with extracted text, page count (1), and word count.
    """
    try:
        # Load image from bytes
        img = Image.open(BytesIO(file_bytes))
        
        # Perform OCR
        full_text = pytesseract.image_to_string(img).strip()
        
        if not full_text:
            raise HTTPException(
                status_code=422,
                detail="Could not extract any meaningful text from the image using OCR."
            )
            
        # Standardize return format
        word_count = len(full_text.split())
        reading_time_minutes = max(1, round(word_count / 200))
        
        return {
            "text": full_text,
            "page_count": 1,
            "word_count": word_count,
            "reading_time_minutes": reading_time_minutes,
            "pages": [{
                "page_number": 1,
                "text": full_text,
                "char_count": len(full_text)
            }]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image OCR failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error performing OCR on image: {str(e)}"
        )

