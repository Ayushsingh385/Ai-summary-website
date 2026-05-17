"""
Cross Reference Service — Enriches legal citations with meanings, 
links, and summaries of statutes and laws.
"""
import logging
import re
from typing import List, Dict, Any, Optional
from services.llm_service import get_llm_response
from services.nlp_service import CITATION_PATTERNS

logger = logging.getLogger(__name__)

# A small local cache for extremely common statutes to avoid LLM calls
LOCAL_STATUTE_KNOWLEDGE = {
    "CrPC": "Code of Criminal Procedure - Main procedural law for criminal courts in India.",
    "IPC": "Indian Penal Code - Defines crimes and prescribes punishments.",
    "CPC": "Code of Civil Procedure - Procedural law for civil courts in India.",
    "MLR Code": "Maharashtra Land Revenue Code - Governing law for land administration in Maharashtra.",
    "Constitution of India": "The supreme law of India."
}

def extract_all_citations(text: str) -> List[Dict[str, Any]]:
    """
    Scans text using CITATION_PATTERNS and returns a list of all found citations
    with their categories.
    """
    citations = []
    
    for category, pattern in CITATION_PATTERNS.items():
        matches = re.finditer(pattern, text)
        for match in matches:
            citations.append({
                "text": match.group(),
                "category": category,
                "start": match.start(),
                "end": match.end()
            })
            
    # Sort by position in text
    citations.sort(key=lambda x: x["start"])
    return citations

def enrich_citation(citation_text: str, category: str) -> Dict[str, Any]:
    """
    Provides a legal summary and context for a specific citation.
    Uses a local cache first, then the LLM.
    """
    # 1. Try local cache (simple keyword match)
    for key, description in LOCAL_STATUTE_KNOWLEDGE.items():
        if key.lower() in citation_text.lower():
            return {
                "citation": citation_text,
                "category": category,
                "summary": description,
                "source": "local_cache",
                "is_verified": True
            }

    # 2. Use LLM for deep enrichment
    system_prompt = (
        "You are a legal researcher. Your task is to explain a specific legal citation. "
        "Provide a concise summary (1-2 sentences) of what this specific section or law "
        "generally covers. If it's a specific section, explain the purpose of that section."
    )
    
    user_msg = f"Explain the following legal citation: {citation_text}. Category: {category}."
    
    try:
        result = get_llm_response(user_message=user_msg, system_prompt=system_prompt)
        summary = result.get("response", "No summary available.")
        
        return {
            "citation": citation_text,
            "category": category,
            "summary": summary,
            "source": "llm_analysis",
            "is_verified": False # LLM can hallucinate, mark as not verified
        }
    except Exception as e:
        logger.error(f"Enrichment failed for {citation_text}: {e}")
        return {
            "citation": citation_text,
            "category": category,
            "summary": "Unable to retrieve summary at this time.",
            "source": "error",
            "is_verified": False
        }

def cross_reference_document(text: str) -> List[Dict[str, Any]]:
    """
    The main entry point: extracts all citations and enriches each one.
    """
    citations = extract_all_citations(text)
    enriched_results = []
    
    # To avoid redundant LLM calls for the same citation in one doc
    seen_citations = set()
    
    for cit in citations:
        cit_text = cit["text"]
        if cit_text in seen_citations:
            # Reuse previous enrichment for the same text
            # This is a simple optimization.
            continue
            
        enriched = enrich_citation(cit_text, cit["category"])
        enriched_results.append(enriched)
        seen_citations.add(cit_text)
        
    return enriched_results
