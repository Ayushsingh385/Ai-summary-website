"""
Precedent Service — Analyzes relationships between legal cases.
Identifies supporting and contradictory precedents by comparing facts and outcomes.
"""
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from models import CaseDocument
from services.vector_service import vector_service
from services.llm_service import get_llm_response

logger = logging.getLogger(__name__)

def analyze_case_relationship(target_case: CaseDocument, candidate_case: CaseDocument) -> Dict[str, Any]:
    """
    Determines if a candidate case supports or contradicts the target case.
    """
    system_prompt = (
        "You are a senior legal researcher. Compare two legal cases. "
        "Analyze the 'Facts' (what happened) and the 'Outcome' (what was decided). "
        "Determine if the candidate case is a 'Supporting Precedent' (similar facts, similar outcome) "
        "or a 'Contradictory Precedent' (similar facts, different outcome). "
        "Be precise and cite the specific reason for the divergence."
    )

    # We construct a structured comparison prompt
    user_msg = (
        f"TARGET CASE:\nFilename: {target_case.filename}\nSummary: {target_case.summary_text}\n\n"
        f"CANDIDATE CASE:\nFilename: {candidate_case.filename}\nSummary: {candidate_case.summary_text}\n\n"
        "Task: Compare these cases. Return a JSON-like response with: "
        "1. relationship (Supporting/Contradictory/Irrelevant) "
        "2. reasoning (Short explanation of why) "
        "3. divergence_point (What specific fact or law led to a different outcome, if any)."
    )

    try:
        result = get_llm_response(user_message=user_msg, system_prompt=system_prompt)
        return {
            "case_id": candidate_case.id,
            "filename": candidate_case.filename,
            "analysis": result.get("response", "No analysis generated."),
            "provider": result.get("provider", "unknown")
        }
    except Exception as e:
        logger.error(f"Precedent analysis failed: {e}")
        return {"case_id": candidate_case.id, "filename": candidate_case.filename, "error": str(e)}

def find_precedents(case_id: int, db: Session, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Finds the most relevant precedents and classifies them as supporting or contradictory.
    """
    # 1. Fetch target case
    target = db.query(CaseDocument).filter(CaseDocument.id == case_id).first()
    if not target:
        return []

    # 2. Use vector service to find semantically similar cases (Fact-pattern match)
    similar_results = vector_service.find_similar(target.original_text, top_k=top_k, threshold=0.6)
    if not similar_results:
        return []

    similar_ids = [res[0] for res in similar_results]
    candidates = db.query(CaseDocument).filter(CaseDocument.id.in_(similar_ids)).all()

    # 3. Analyze each candidate's outcome relative to target
    precedents = []
    for candidate in candidates:
        if candidate.id == target.id:
            continue
        
        analysis = analyze_case_relationship(target, candidate)
        precedents.append(analysis)

    return precedents
