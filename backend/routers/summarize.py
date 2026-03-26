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
from services.download_service import generate_summary_pdf, generate_summary_txt, generate_original_pdf
from services.vector_service import vector_service

from database import get_db
from models import CaseDocument
from sqlalchemy.orm import Session
from fastapi import Depends

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


class DownloadOriginalRequest(BaseModel):
    """Request body for the /download_original endpoint."""
    original_text: str
    original_word_count: int = 0


class SaveCaseRequest(BaseModel):
    """Request body for the /save_case endpoint."""
    filename: str
    original_text: str
    summary_text: str
    keywords: list
    stats: dict


class SearchRequest(BaseModel):
    """Request body for the /search endpoint."""
    query: str
    top_k: Optional[int] = 1


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


@router.post("/download_original")
async def download_original(request: DownloadOriginalRequest):
    """
    Download the properly aligned original case text as a PDF.
    """
    pdf_bytes = generate_original_pdf(
        request.original_text,
        request.original_word_count,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=original_case.pdf"}
    )


@router.post("/save_case")
async def save_case(request: SaveCaseRequest, db: Session = Depends(get_db)):
    """
    Save the generated case summary to the SQLite database and FAISS vector store.
    """
    new_case = CaseDocument(
        filename=request.filename,
        original_text=request.original_text,
        summary_text=request.summary_text,
        keywords=request.keywords,
        stats=request.stats
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    # Add to FAISS index (using the original_text as the representation)
    vector_service.add_document(new_case.id, request.original_text)

    return {"message": "Case saved successfully", "case_id": new_case.id}


@router.get("/history")
async def get_history(db: Session = Depends(get_db)):
    """
    Retrieve all saved cases, ordered by newest first.
    Returns metadata only to save bandwidth.
    """
    cases = db.query(
        CaseDocument.id, 
        CaseDocument.filename, 
        CaseDocument.created_at,
        CaseDocument.stats
    ).order_by(CaseDocument.created_at.desc()).all()
    
    return [
        {
            "id": c.id,
            "filename": c.filename,
            "created_at": c.created_at,
            "stats": c.stats
        } 
        for c in cases
    ]


@router.post("/search")
async def search_cases(request: SearchRequest, db: Session = Depends(get_db)):
    """
    Semantic search through saved cases using the FAISS vector store.
    """
    results = vector_service.find_similar(request.query, top_k=request.top_k)
    
    if not results:
        return {"results": []}
        
    case_ids = [res[0] for res in results]
    scores = {res[0]: res[1] for res in results}
    
    cases = db.query(CaseDocument).filter(CaseDocument.id.in_(case_ids)).all()
    
    # Format and sort by score
    formatted_results = []
    for case in cases:
        formatted_results.append({
            "id": case.id,
            "filename": case.filename,
            "original_text": case.original_text,
            "summary_text": case.summary_text,
            "keywords": case.keywords,
            "stats": case.stats,
            "created_at": case.created_at,
            "score": scores.get(case.id, 0)
        })
        
    formatted_results.sort(key=lambda x: x["score"], reverse=True)
    return {"results": formatted_results}


@router.delete("/delete_case/{case_id}")
async def delete_case(case_id: int, db: Session = Depends(get_db)):
    """
    Delete a specific case from the database and FAISS vector store.
    """
    case = db.query(CaseDocument).filter(CaseDocument.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    # Delete from DB
    db.delete(case)
    db.commit()
    
    # Delete from FAISS
    vector_service.remove_document(case_id)
    
    return {"message": f"Case {case_id} deleted successfully"}

