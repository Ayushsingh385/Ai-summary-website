"""
Summarize Router — API endpoints for PDF upload, summarization,
keyword extraction, and summary download.
"""

import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List, Any, Dict

from services.pdf_service import validate_pdf, extract_text_from_pdf, extract_text_from_image
from services.nlp_service import summarize_text, extract_keywords, compute_text_stats, extract_citations, compare_documents, classify_case_type, analyze_legal_document
from services.download_service import (
    generate_summary_pdf, generate_summary_txt, generate_summary_docx,
    generate_original_pdf, generate_original_docx, generate_comparison_docx,
)
from services.vector_service import vector_service
from services.difference_engine import compare_documents_semantic, get_comparison_summary
from services.brief_service import generate_brief_docx
from services.llm_service import get_llm_status

from database import get_db, SessionLocal
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

class ClassifyRequest(BaseModel):
    """Request body for the /classify endpoint."""
    text: str

class AnalyzeRequest(BaseModel):
    """Request body for the /analyze endpoint."""
    text: str

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
    template: Optional[str] = None  # zp_official | court_order | general


class DownloadOriginalRequest(BaseModel):
    """Request body for the /download_original endpoint."""
    original_text: str
    original_word_count: int = 0
    format: str = "pdf"  # pdf | docx
    filename: Optional[str] = "original_case"
    template: Optional[str] = None  # zp_official | court_order | general


class DownloadComparisonRequest(BaseModel):
    """Request body for the /download_comparison endpoint."""
    filename1: str = "Document 1"
    filename2: str = "Document 2"
    comparison_summary: str = ""
    similarities: Optional[list] = []
    differences: Optional[list] = []
    shared_blocks: Optional[list] = []
    shared_topics: Optional[list] = []
    unique_topics_doc1: Optional[list] = []
    unique_topics_doc2: Optional[list] = []
    format: str = "docx"  # docx
    template: Optional[str] = None  # zp_official | court_order | general


class SaveCaseRequest(BaseModel):
    """Request body for saving a case locally."""
    filename: str
    original_text: str
    summary_text: str
    keywords: list
    stats: dict
    tags: Optional[list] = []
    status: Optional[str] = "new"
    case_type: Optional[dict] = None


class BriefRequest(BaseModel):
    """Request body for generating a structured legal brief."""
    filename: str
    original_text: str
    summary: str
    keywords: list
    legal_analysis: Optional[dict] = None
    case_type: Optional[dict] = None
    brief_type: Optional[str] = "memo"
    template: Optional[str] = "general"


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
async def upload_file(request: Request, file: UploadFile = File(...)):
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

    # Extract text based on file type
    if file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
        result = await asyncio.to_thread(extract_text_from_image, file_bytes)
    else:
        result = await asyncio.to_thread(extract_text_from_pdf, file_bytes)

    result["filename"] = file.filename
    return result


@router.post("/batch_process")
@limiter.limit("5/minute")
async def batch_process_file(request: Request, file: UploadFile = File(...)):
    """
    Extract text, summarize, extract keywords, classify, and save — all in one call.
    Processes a single PDF file and returns extracted text + summary + keywords + classification.
    """
    file_bytes = await file.read()
    validate_pdf(file_bytes, file.content_type, file.filename)

    # 1. Extract text
    if file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
        extract_result = await asyncio.to_thread(extract_text_from_image, file_bytes)
    else:
        extract_result = await asyncio.to_thread(extract_text_from_pdf, file_bytes)

    text = extract_result.get("text", "")
    if len(text.strip()) < 50:
        return {"filename": file.filename, "error": "Too little text extracted"}

    # 2. Run summarize + keywords + classify in parallel threads
    summary_task = asyncio.to_thread(summarize_text, text, "medium", "en")
    keywords_task = asyncio.to_thread(extract_keywords, text, 10)
    classify_task = asyncio.to_thread(classify_case_type, text)
    summary_res, keywords_res, classify_res = await asyncio.gather(
        summary_task, keywords_task, classify_task
    )

    # 3. Save to database
    stats = compute_text_stats(text)
    new_case = CaseDocument(
        filename=file.filename,
        original_text=text,
        summary_text=summary_res.get("summary", ""),
        keywords=keywords_res,
        stats=stats,
        tags=[],
        status="new",
        case_type=classify_res,
    )
    db = SessionLocal()
    try:
        db.add(new_case)
        db.commit()
        db.refresh(new_case)
        case_id = new_case.id
        # Add to FAISS index
        vector_service.add_document(case_id, text)
    finally:
        db.close()

    return {
        "filename": file.filename,
        "text": text,
        "word_count": len(text.split()),
        "summary": summary_res,
        "keywords": keywords_res,
        "case_type": classify_res,
        "case_id": case_id,
        "success": True
    }


@router.post("/batch_upload")
@limiter.limit("5/minute")
async def batch_upload(request: Request, files: List[UploadFile] = File(...)):
    """
    Upload multiple PDF files at once and extract text from all of them.
    Returns a list of results, one per file.
    """
    results = []
    errors = []

    for file in files:
        try:
            file_bytes = await file.read()
            validate_pdf(file_bytes, file.content_type, file.filename)

            if file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                result = await asyncio.to_thread(extract_text_from_image, file_bytes)
            else:
                result = await asyncio.to_thread(extract_text_from_pdf, file_bytes)

            result["filename"] = file.filename
            results.append({"filename": file.filename, "success": True, **result})
        except Exception as e:
            errors.append({"filename": file.filename, "success": False, "error": str(e)})

    return {"results": results, "errors": errors, "total": len(files)}



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

    result = await asyncio.to_thread(summarize_text, body_request.text, body_request.length, body_request.language)
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

    result = await asyncio.to_thread(extract_keywords, body_request.text, body_request.top_n)
    citations = await asyncio.to_thread(extract_citations, body_request.text)
    return {"keywords": result, "citations": citations}


@router.post("/classify")
@limiter.limit("20/minute")
async def classify_case(request: Request, body_request: ClassifyRequest):
    """
    Classify the legal case type based on document content.

    Returns:
        - primary_type: The most likely case category
        - confidence: Confidence score (0-100)
        - all_scores: Top 5 category scores
        - matched_keywords: Keywords that triggered classification
    """
    if not body_request.text or len(body_request.text.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Text is too short for classification."
        )

    result = await asyncio.to_thread(classify_case_type, body_request.text)
    return result


@router.post("/analyze")
@limiter.limit("10/minute")
async def analyze_document(request: Request, body_request: AnalyzeRequest):
    """
    Comprehensive legal document analysis.

    Returns:
        - case_type: Case classification with confidence
        - legal_issues: Extracted legal questions
        - timeline: Chronological events from the document
        - monetary_claims: All monetary amounts mentioned
        - sections: Structured breakdown (Facts, Issues, Reasoning, Order)
        - citations: Legal citations with links
    """
    if not body_request.text or len(body_request.text.strip()) < 100:
        raise HTTPException(
            status_code=400,
            detail="Text is too short for analysis. Please provide at least 100 characters."
        )

    result = await asyncio.to_thread(analyze_legal_document, body_request.text)
    return result


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
            template=body_request.template,
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
    Download the original case text as PDF or DOCX.
    """
    if request.format == "docx":
        docx_bytes = generate_original_docx(
            request.original_text,
            request.original_word_count,
            filename=request.filename,
            template=request.template,
        )
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": "attachment; filename=original_case.docx"}
        )
    else:
        pdf_bytes = generate_original_pdf(
            request.original_text,
            request.original_word_count,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=original_case.pdf"}
        )


@router.post("/download_comparison")
@limiter.limit("20/minute")
async def download_comparison(request: Request, body_request: DownloadComparisonRequest):
    """
    Download a comparison report as a DOCX file.
    Supports legal document templates.
    """
    docx_bytes = generate_comparison_docx(
        filename1=body_request.filename1,
        filename2=body_request.filename2,
        comparison_summary=body_request.comparison_summary,
        similarities=body_request.similarities,
        differences=body_request.differences,
        shared_blocks=body_request.shared_blocks,
        shared_topics=body_request.shared_topics,
        unique_topics_doc1=body_request.unique_topics_doc1,
        unique_topics_doc2=body_request.unique_topics_doc2,
        template=body_request.template,
    )
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=comparison_report.docx"}
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
        stats=request.stats,
        tags=request.tags or [],
        status=request.status or "new",
        case_type=request.case_type,
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
    Retrieve all saved cases, deduplicated by filename, ordered by newest first.
    """
    cases = db.query(
        CaseDocument.id,
        CaseDocument.filename,
        CaseDocument.created_at,
        CaseDocument.stats,
        CaseDocument.tags,
        CaseDocument.status,
        CaseDocument.case_type,
    ).order_by(CaseDocument.created_at.desc()).all()

    # Deduplicate by filename (keeping the most recent)
    seen_filenames = set()
    unique_cases = []
    
    import json
    for c in cases:
        if c.filename not in seen_filenames:
            seen_filenames.add(c.filename)
            
            # Safety parse stats/tags if they are strings
            stats_val = c.stats
            if isinstance(stats_val, str):
                try: stats_val = json.loads(stats_val)
                except: stats_val = {}
                
            tags_val = c.tags
            if isinstance(tags_val, str):
                try: tags_val = json.loads(tags_val)
                except: tags_val = []
                
            case_type_val = c.case_type
            if isinstance(case_type_val, str):
                try: case_type_val = json.loads(case_type_val)
                except: case_type_val = {}

            unique_cases.append({
                "id": c.id,
                "filename": c.filename,
                "created_at": c.created_at,
                "stats": stats_val,
                "tags": tags_val or [],
                "status": c.status or "new",
                "case_type": case_type_val,
            })

    return unique_cases


@router.post("/search")
async def search_cases(request: SearchRequest, db: Session = Depends(get_db)):
    """
    Hybrid search: Semantic search through content (FAISS) + Keyword match on filenames.
    Results are deduplicated by filename.
    """
    # 1. Filename keyword match (SQL LIKE)
    filename_matches = db.query(CaseDocument).filter(
        CaseDocument.filename.ilike(f"%{request.query}%")
    ).all()
    filename_ids = {c.id for c in filename_matches}

    # 2. Semantic match (FAISS)
    semantic_results = vector_service.find_similar(request.query, top_k=request.top_k) or []
    semantic_ids = [res[0] for res in semantic_results]
    semantic_scores = {res[0]: res[1] for res in semantic_results}

    # 3. Combine and de-duplicate IDs
    all_case_ids = list(filename_ids.union(set(semantic_ids)))
    
    if not all_case_ids:
        return {"results": []}

    # 4. Fetch all matching cases
    cases = db.query(CaseDocument).filter(CaseDocument.id.in_(all_case_ids)).all()
    
    # 5. Format and score
    formatted_results = []
    for case in cases:
        score = semantic_scores.get(case.id, 0.0)
        if case.id in filename_ids:
            score = max(score, 1.5)

        formatted_results.append({
            "id": case.id,
            "filename": case.filename,
            "original_text": case.original_text,
            "summary_text": case.summary_text,
            "keywords": case.keywords,
            "stats": case.stats,
            "created_at": case.created_at,
            "case_type": case.case_type,
            "score": score,
            "tags": case.tags or []
        })
        
    # 6. Final deduplication by filename for the search results
    formatted_results.sort(key=lambda x: x["score"], reverse=True)
    
    seen_search_filenames = set()
    final_results = []
    for res in formatted_results:
        if res["filename"] not in seen_search_filenames:
            seen_search_filenames.add(res["filename"])
            final_results.append(res)

    return {"results": final_results}


class UpdateTagsRequest(BaseModel):
    tags: List[str]


@router.put("/case/{case_id}/tags")
async def update_case_tags(case_id: int, request: UpdateTagsRequest, db: Session = Depends(get_db)):
    """
    Update the tags for an existing case.
    """
    case = db.query(CaseDocument).filter(CaseDocument.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.tags = request.tags
    db.commit()

    return {"message": "Tags updated", "tags": case.tags}


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


@router.post("/brief")
@limiter.limit("10/minute")
async def generate_brief(request: Request, body_request: BriefRequest):
    """
    Generate a structured legal brief (memo, brief, opinion, summary)
    as a DOCX document with formal sections: Issues, Facts, Analysis, Prayer, Authorities.
    """
    try:
        docx_bytes = generate_brief_docx(
            filename=body_request.filename,
            original_text=body_request.original_text,
            summary=body_request.summary,
            keywords=body_request.keywords,
            legal_analysis=body_request.legal_analysis,
            case_type=body_request.case_type,
            brief_type=body_request.brief_type or "memo",
            template=body_request.template or "general",
        )
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=legal_brief_{body_request.brief_type or 'memo'}.docx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Brief generation failed: {str(e)}")


from collections import Counter
import json

@router.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """
    Retrieve aggregated analytics: most common entities, case types, summary length trends.
    """
    cases = db.query(CaseDocument).all()
    
    total_cases = len(cases)
    
    entity_counter = Counter()
    case_types = Counter()
    trends = []
    
    # Simple predefined types check based on text context
    type_keywords = {
        "Criminal": ["criminal", "murder", "theft", "assault", "jail", "prison"],
        "Civil": ["civil", "property", "tenant", "landlord", "dispute", "eviction"],
        "Family": ["divorce", "maintenance", "custody", "marriage", "family"],
        "Corporate": ["company", "corporate", "shareholder", "business", "contract", "tax"]
    }
    
    for c in cases:
        # Most common entities
        kw_list = c.keywords if c.keywords else []
        if isinstance(kw_list, str):
            try: kw_list = json.loads(kw_list)
            except: kw_list = []
                
        text_lower = ""
        if c.original_text:
            text_lower = c.original_text.lower()
            
        for kw in kw_list:
            if isinstance(kw, dict):
                ktype = kw.get('type', '')
                if ktype in ["PERSON", "ORG", "GPE", "LAW", "LOC", "FAC"]:
                    # Clean up keyword display
                    k_name = str(kw.get("keyword")).title()
                    entity_counter[k_name] += 1
        
        # Case types logic
        predicted_type = "Misc/Other"
        for ctype, kws in type_keywords.items():
            if any(k in text_lower for k in kws):
                predicted_type = ctype
                break
        case_types[predicted_type] += 1
                
        # Trends
        stats = c.stats if c.stats else {}
        if isinstance(stats, str):
             try: stats = json.loads(stats)
             except: stats = {}
             
        orig_wc = stats.get("original_word_count", 0)
        sum_wc = stats.get("summary_word_count", 0)
        comp_ratio = stats.get("compression_ratio", 0)
        
        if orig_wc > 0:
            trends.append({
                "id": c.id,
                "date": c.created_at.strftime("%Y-%m-%d") if c.created_at else "",
                "original_words": orig_wc,
                "summary_words": sum_wc,
                "compression_ratio": comp_ratio
            })
            
    # Sort trends by ID (proxy for chronological order)
    trends.sort(key=lambda x: x["id"])
    
    # Top 10 entities
    top_entities = [{"name": kv[0], "count": kv[1]} for kv in entity_counter.most_common(10)]
    
    # Format case types
    total_types = sum(case_types.values()) or 1
    case_types_formatted = [{"type": k, "count": v, "percentage": round(v / total_types * 100)} for k, v in case_types.most_common()]

    # Return last 15 trends points to keep charts readable
    return {
        "total_cases": total_cases,
        "top_entities": top_entities,
        "case_types": case_types_formatted,
        "trends": trends[-15:]
    }

@router.get("/chatbot/status")
async def chatbot_status():
    """
    Get the status of the chatbot AI services.
    Indicates if the bot is 'Online' (using an external provider) or 'Offline' (local mode).
    """
    return get_llm_status()
