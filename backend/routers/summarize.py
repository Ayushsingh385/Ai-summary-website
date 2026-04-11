"""
Summarize Router — API endpoints for PDF upload, summarization,
keyword extraction, and summary download.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List, Any, Dict

from services.pdf_service import validate_pdf, extract_text_from_pdf
from services.nlp_service import summarize_text, extract_keywords, compute_text_stats, extract_citations, compare_documents
from services.download_service import generate_summary_pdf, generate_summary_txt, generate_summary_docx, generate_original_pdf
from services.vector_service import vector_service
from services.difference_engine import compare_documents_semantic, get_comparison_summary

from database import get_db
from models import CaseDocument, CaseComparison
from sqlalchemy.orm import Session
from fastapi import Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api", tags=["Summarizer"])


# ──────────────────────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────────────────────

class SummarizeRequest(BaseModel):
    """Request body for the /summarize endpoint."""
    text: str
    length: Optional[str] = "medium"  # short | medium | long
    language: Optional[str] = "en"


class KeywordsRequest(BaseModel):
    """Request body for the /keywords endpoint."""
    text: str
    top_n: Optional[int] = 15

class CompareRequest(BaseModel):
    """Request body for the /compare endpoint."""
    text1: str
    text2: str
    language: Optional[str] = "en"


class DownloadRequest(BaseModel):
    """Request body for the /download endpoint."""
    summary: str
    original_word_count: int = 0
    summary_word_count: int = 0
    format: str = "txt"  # pdf | txt | docx
    filename: Optional[str] = "summary"
    keywords: Optional[list] = []


class DownloadOriginalRequest(BaseModel):
    """Request body for the /download_original endpoint."""
    original_text: str
    original_word_count: int = 0


class SaveCaseRequest(BaseModel):
    """Request body for saving a case locally."""
    filename: str
    original_text: str
    summary_text: str
    keywords: list
    stats: dict


class SaveComparisonRequest(BaseModel):
    """Request body for saving a document comparison."""
    filename1: str
    filename2: str
    text1: str
    text2: str
    comparison_summary: str
    shared_entities: List[Any]
    similarities: Optional[List[Any]] = []
    differences: Optional[List[Any]] = []
    shared_blocks: Optional[List[Any]] = []


class SearchRequest(BaseModel):
    """Request body for the /search endpoint."""
    query: str
    top_k: Optional[int] = 1


class SemanticCompareRequest(BaseModel):
    """Request body for the /compare_semantic endpoint."""
    text1: str
    text2: str


# ──────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────

@router.post("/compare")
@limiter.limit("10/minute")
async def compare_documents(request: Request, body_request: CompareRequest):
    """
    Compare two Zilla Parishad/administrative documents using semantic embeddings.
    Primary comparison engine for the application.
    """
    if len(body_request.text1.strip()) < 50 or len(body_request.text2.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Both texts must be at least 50 characters."
        )

    try:
        # Use the specialized semantic engine
        result = compare_documents_semantic(body_request.text1, body_request.text2, debug=True)
        
        # Add human-readable summary
        summary = get_comparison_summary(result)
        result["comparison_summary"] = summary
        
        # Ensure backward compatibility with existing frontend expectations if any
        # (Though we are primarily improving the results)
        result["document_1_summary"] = summarize_text(body_request.text1, "short", body_request.language)["summary"]
        result["document_2_summary"] = summarize_text(body_request.text2, "short", body_request.language)["summary"]
        result["shared_entities"] = result.get("stats", {}).get("identical_count", 0) # rough proxy
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Comparison failed: {str(e)}"
        )



@router.post("/upload")
@limiter.limit("20/minute")
async def upload_pdf(request: Request, file: UploadFile = File(...)):
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
@limiter.limit("10/minute")
async def summarize(request: Request, body_request: SummarizeRequest):
    """
    Summarize the provided text using BART NLP model.

    Request body:
        - text:   The text to summarize
        - length: 'short', 'medium', or 'long'

    Returns:
        - Generated summary
        - Word counts and compression ratio
    """
    if not body_request.text or len(body_request.text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Text is too short to summarize. Please provide at least 50 characters."
        )

    result = summarize_text(body_request.text, body_request.length, body_request.language)
    stats = compute_text_stats(body_request.text)
    result["original_stats"] = stats
    return result


@router.post("/keywords")
@limiter.limit("20/minute")
async def keywords(request: Request, body_request: KeywordsRequest):
    """
    Extract keywords from the provided text.

    Request body:
        - text:   The text to analyze
        - top_n:  Number of keywords to return (default: 15)

    Returns:
        List of keywords with relevance scores.
    """
    if not body_request.text or len(body_request.text.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Text is too short for keyword extraction."
        )

    result = extract_keywords(body_request.text, body_request.top_n)
    citations = extract_citations(body_request.text)
    return {"keywords": result, "citations": citations}


# Consolidated with /api/compare above


@router.post("/compare_semantic")
@limiter.limit("10/minute")
async def compare_semantic(request: Request, body_request: SemanticCompareRequest):
    """
    Semantic document comparison using sentence embeddings.

    Compares two documents at the sentence/clause level using cosine similarity
    on embeddings from sentence-transformers/all-MiniLM-L6-v2.

    Classification thresholds:
        - similarity >= 0.90 -> Identical (unchanged)
        - 0.75 <= similarity < 0.90 -> Modified (changed)
        - similarity < 0.75 -> Different (added/removed)

    Returns:
        - identical: List of unchanged segments
        - modified: List of {original, updated, similarity} objects
        - added: List of new segments in document B
        - removed: List of deleted segments from document A
        - stats: Summary statistics
    """
    if len(body_request.text1.strip()) < 50 or len(body_request.text2.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Both texts must be at least 50 characters."
        )

    try:
        result = compare_documents_semantic(body_request.text1, body_request.text2)
        summary = get_comparison_summary(result)
        result["human_readable_summary"] = summary
        return result
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Embedding model not available: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Comparison failed: {str(e)}"
        )

@router.post("/download")
@limiter.limit("20/minute")
async def download_summary(request: Request, body_request: DownloadRequest):
    """
    Download the summary as a PDF, TXT, or DOCX file.

    Request body:
        - summary:             The summary text
        - original_word_count: Word count of the original text
        - summary_word_count:  Word count of the summary
        - format:              'pdf', 'txt', or 'docx'
        - filename:            Optional filename (without extension)
        - keywords:            Optional list of keywords for DOCX

    Returns:
        File download response.
    """
    if body_request.format == "pdf":
        pdf_bytes = generate_summary_pdf(
            body_request.summary,
            body_request.original_word_count,
            body_request.summary_word_count,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=summary.pdf"}
        )

    elif body_request.format == "txt":
        txt_content = generate_summary_txt(
            body_request.summary,
            body_request.original_word_count,
            body_request.summary_word_count,
        )
        return Response(
            content=txt_content.encode("utf-8"),
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=summary.txt"}
        )

    elif body_request.format == "docx":
        docx_bytes = generate_summary_docx(
            body_request.summary,
            body_request.original_word_count,
            body_request.summary_word_count,
            filename=body_request.filename,
            keywords=body_request.keywords,
        )
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": "attachment; filename=summary.docx"}
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid format. Use 'pdf', 'txt', or 'docx'."
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


@router.post("/save_comparison")
async def save_comparison(request: SaveComparisonRequest, db: Session = Depends(get_db)):
    """
    Save a document comparison to the database.
    """
    new_comparison = CaseComparison(
        filename1=request.filename1,
        filename2=request.filename2,
        text1=request.text1,
        text2=request.text2,
        comparison_summary=request.comparison_summary,
        shared_entities=request.shared_entities,
        similarities=request.similarities,
        differences=request.differences,
        shared_blocks=request.shared_blocks
    )
    db.add(new_comparison)
    db.commit()
    db.refresh(new_comparison)
    
    return {"message": "Comparison saved successfully", "comparison_id": new_comparison.id}


@router.get("/history/comparisons")
async def get_comparison_history(db: Session = Depends(get_db)):
    """
    Retrieve all saved comparisons.
    """
    comparisons = db.query(
        CaseComparison.id, 
        CaseComparison.filename1,
        CaseComparison.filename2,
        CaseComparison.created_at
    ).order_by(CaseComparison.created_at.desc()).all()
    
    return [
        {
            "id": c.id,
            "filename1": c.filename1,
            "filename2": c.filename2,
            "created_at": c.created_at
        } 
        for c in comparisons
    ]


@router.get("/history/comparisons/{comparison_id}")
async def get_comparison_detail(comparison_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific comparison by ID.
    """
    comparison = db.query(CaseComparison).filter(CaseComparison.id == comparison_id).first()
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")
        
    return comparison
