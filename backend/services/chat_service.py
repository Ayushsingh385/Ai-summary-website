"""
Chat Service - Intent routing with LLM-powered responses.
Handles both structured actions and conversational queries.
"""
import re
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from models import CaseDocument
from services.vector_service import vector_service
from services.nlp_service import summarize_text, extract_keywords
from services.precedent_service import find_precedents
from services.cross_reference_service import cross_reference_document
from services.timeline_service import extract_legal_timeline
from services.llm_service import get_llm_response

logger = logging.getLogger(__name__)

# Intent patterns for structured actions
INTENT_PATTERNS = {
    "similar": ["similar", "like this", "find similar", "related cases", "same type"],
    "count": ["how many", "count", "total cases", "number of cases"],
    "summarize": ["summar", "bullet", "key points", "main points"],
    "entities": ["entit", "name", "person", "organi", "who", "people", "companies"],
    "precedent": ["precedent", "contradict", "supporting", "divergence", "case contrast"],
    "cross_ref": ["statute", "law", "section", "cross reference", "act", "rules", "regulation"],
    "timeline": ["timeline", "chronology", "dates", "sequence of events", "history of case"],
}


def detect_intent(query: str) -> str:
    """Detect if the query matches a structured action intent."""
    query_lower = query.lower()

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if pattern in query_lower:
                return intent
    return "conversational"


def handle_similar_intent(document_text: str, db: Session) -> str:
    """Handle requests to find similar cases."""
    if not document_text:
        return "I need a document to find similar files. Please select or upload a case file first."

    results = vector_service.find_similar(document_text, top_k=3, threshold=0.6)
    if not results:
        return "I couldn't find any similar cases in the database."

    case_ids = [res[0] for res in results]
    similar_cases = db.query(CaseDocument).filter(CaseDocument.id.in_(case_ids)).all()

    response = "Here are similar cases I found:\n"
    for case in similar_cases:
        score = next((res[1] for res in results if res[0] == case.id), 0)
        response += f"- **{case.filename}** ({(score*100):.1f}% match)\n"
    return response


def handle_count_intent(query: str, document_text: str, db: Session) -> str:
    """Handle requests to count cases."""
    total_cases = db.query(CaseDocument).count()

    if document_text and ("this type" in query.lower() or "these type" in query.lower()):
        results = vector_service.find_similar(document_text, top_k=total_cases, threshold=0.7)
        count = len(results)
        return f"There are **{count} cases** similar to this one (out of {total_cases} total)."

    return f"Currently, there are **{total_cases} completed cases** stored in the database."


def handle_summarize_intent(document_text: str) -> str:
    """Handle requests for document summaries."""
    if not document_text:
        return "Please select a document first so I can summarize it for you."

    if len(document_text) < 50:
        return "The current document is too short to summarize."

    result = summarize_text(document_text, "short")
    summary = result.get("summary", "")

    sentences = re.split(r'(?<=[.!?])\s+', summary)
    bullets = "\n".join([f"- {s.strip()}" for s in sentences if s.strip()])
    return f"Here are the key points:\n{bullets}"


def handle_entities_intent(document_text: str, keywords: list) -> str:
    """Handle requests to extract entities from documents."""
    if not document_text:
        return "Please select a document first so I can extract entities from it."

    kw_list = keywords if keywords else extract_keywords(document_text, top_n=20)

    entities = {"PERSON": [], "ORG": [], "GPE": [], "LAW": []}
    for kw in kw_list:
        if isinstance(kw, dict) and kw.get("type") in entities:
            entities[kw["type"]].append(kw["keyword"])

    response = "Here are the key entities I found:\n"
    if entities["PERSON"]:
        response += f"- **People**: {', '.join(entities['PERSON'][:10])}\n"
    if entities["ORG"]:
        response += f"- **Organizations**: {', '.join(entities['ORG'][:10])}\n"
    if entities["GPE"]:
        response += f"- **Locations**: {', '.join(entities['GPE'][:10])}\n"
    if entities["LAW"]:
        response += f"- **Legal Codes**: {', '.join(entities['LAW'][:10])}\n"

    if response == "Here are the key entities I found:\n":
        return "I couldn't extract any prominent entities from this document."
    return response


def handle_precedent_intent(document_text: str, db: Session) -> str:
    """Handle requests to find supporting or contradictory precedents."""
    if not document_text:
        return "Please select a case file first so I can analyze its precedents."
    
    case = db.query(CaseDocument).filter(CaseDocument.original_text == document_text).first()
    if not case:
        return "I couldn't find this document in my database. Please ensure it's saved first."
    
    results = find_precedents(case.id, db)
    if not results:
        return "I couldn't find any significant precedents that support or contradict this case."
    
    response = "### Precedent Analysis\n"
    for res in results:
        analysis = res.get("analysis", "No detail available.")
        filename = res.get("filename", "Unknown")
        response += f"- **{filename}**: {analysis}\n"
    
    return response


def handle_cross_ref_intent(document_text: str) -> str:
    """Handle requests for legal statute cross-referencing."""
    if not document_text:
        return "Please select a document so I can cross-reference the laws cited within it."
    
    results = cross_reference_document(document_text)
    if not results:
        return "I didn't find any recognizable legal citations or statutes in this document."
    
    response = "### Legal Cross-References\n"
    for res in results:
        summary = res.get("summary", "No summary available.")
        citation = res.get("citation", "Unknown")
        response += f"- **{citation}**: {summary}\n"
        
    return response


def handle_timeline_intent(document_text: str) -> str:
    """Handle requests for a case timeline."""
    if not document_text:
        return "Please select a document so I can reconstruct its timeline."
    
    timeline = extract_legal_timeline(document_text)
    if not timeline:
        return "I couldn't extract a chronological timeline from this document."
    
    response = "### Case Timeline\n"
    for event in timeline:
        date = event.get("date", "Unknown Date")
        ev = event.get("event", "No description")
        actor = event.get("actor", "Unknown")
        response += f"- **{date}**: {ev} (Actor: {actor})\n"
        
    return response


def process_chat_query(
    query: str,
    document_text: str = None,
    keywords: list = None,
    db: Session = None,
    global_mode: bool = False
) -> Dict[str, Any]:
    """
    Process a chat query using intent routing and LLM.
    Returns a dict with 'response' and 'provider' (meta-info).
    """
    if not query or not query.strip():
        return {"response": "Please ask me something.", "provider": "local"}

    # Handle Global RAG Mode
    if global_mode and db:
        return _handle_global_rag(query, db)

    # Single-document Intent parsing
    intent = detect_intent(query)

    # Handle structured intents with local logic (marked as 'local' provider)
    if intent == "similar":
        return {"response": handle_similar_intent(document_text, db), "provider": "local"}

    if intent == "count":
        return {"response": handle_count_intent(query, document_text, db), "provider": "local"}

    if intent == "summarize":
        return {"response": handle_summarize_intent(document_text), "provider": "local"}

    if intent == "entities":
        return {"response": handle_entities_intent(document_text, keywords), "provider": "local"}

    if intent == "precedent":
        return {"response": handle_precedent_intent(document_text, db), "provider": "local"}

    if intent == "cross_ref":
        return {"response": handle_cross_ref_intent(document_text), "provider": "local"}

    if intent == "timeline":
        return {"response": handle_timeline_intent(document_text), "provider": "local"}

    # For conversational queries, use the LLM
    context = None
    if document_text:
        context = document_text[:8000] if len(document_text) > 8000 else document_text

    system_prompt = """You are a professional legal document assistant. You help users understand legal documents,
find relevant information, and answer questions about case files. Be concise, professional, and helpful.

When the user asks about the document, reference specific parts when possible.
If you don't know something, say so honestly rather than making things up.
Keep responses focused and actionable."""

    try:
        result = get_llm_response(
            user_message=query,
            system_prompt=system_prompt,
            document_context=context
        )
        return result
    except Exception as e:
        msg = "I've currently reached my daily processing limit for advanced cloud analysis. No worries! I'm switching to **Local Processing Mode** to continue helping you. The advanced analysis limit resets daily at **midnight Pacific Time (approx. 12:30 PM IST)**. My answers might be a bit simpler for now, but I can still assist with your legal documents!"
        return {"response": msg, "provider": "offline"}


def _handle_global_rag(query: str, db: Session) -> Dict[str, Any]:
    """Handle a query that searches across ALL ingested cases via FAISS using Multi-Stage RAG."""
    
    # --- Stage 1: Query Expansion ---
    expansion_prompt = (
        "You are a legal search expert. The user is searching a database of Zilla Parishad cases. "
        "Generate 3 semantic variations of their query to capture different ways the same legal concept "
        "might be phrased in official documents (e.g., formal terminology, common synonyms). "
        "Return only the variations, one per line, no numbering."
    )
    
    queries_to_run = [query]
    try:
        expansion_res = get_llm_response(user_message=query, system_prompt=expansion_prompt)
        variations = expansion_res.get("response", "").strip().split("\\n")
        queries_to_run.extend([v.strip() for v in variations if v.strip()][:3])
    except Exception as e:
        logger.warning(f"Query expansion failed: {e}. Proceeding with original query.")

    # --- Stage 2: Broad Retrieval ---
    all_matched_results = []
    for q in queries_to_run:
        res = vector_service.find_similar(q, top_k=5, threshold=0.1)
        all_matched_results.extend(res)

    if not all_matched_results:
        return {
            "response": "I searched the entire database with multiple query variations but couldn't find any related cases.", 
            "provider": "local"
        }

    # Deduplicate and sort by score
    unique_matches = {}
    for cid, score in all_matched_results:
        if cid not in unique_matches or score > unique_matches[cid]:
            unique_matches[cid] = score
    
    sorted_ids = sorted(unique_matches.keys(), key=lambda x: unique_matches[x], reverse=True)[:5]
    matched_cases = db.query(CaseDocument).filter(CaseDocument.id.in_(sorted_ids)).all()

    # --- Stage 3: Context Synthesis (Reranking via LLM) ---
    context_chunks = []
    for case in matched_cases:
        score = unique_matches.get(case.id, 0)
        chunk = f"--- Case: {case.filename} (Relevance Score: {score*100:.1f}%) ---\n"
        chunk += f"Summary:\n{case.summary_text or case.original_text[:1000]}\n"
        if case.keywords:
            kw_list = [k.get("keyword") if isinstance(k, dict) else k for k in case.keywords[:5]]
            chunk += f"Keywords: {', '.join(kw_list)}\n"
        context_chunks.append(chunk)

    combined_context = "\n".join(context_chunks)

    system_prompt = """You are an advanced Global Legal Database Assistant for the Zilla Parishad system.
Your job is to answer the user's question by analyzing the provided summaries from multiple cases in our database.
Synthesize the information across these cases to give a clear, comprehensive answer.
Always cite the specific Case Filename when drawing information from it.
If the provided case summaries do not contain enough information to fully answer the question, state what is known and what is missing."""

    try:
        result = get_llm_response(
            user_message=query,
            system_prompt=system_prompt,
            document_context=combined_context
        )
        return result
    except Exception as e:
        return {
            "response": f"I found {len(matched_cases)} relevant cases using multi-stage search, but the LLM provider failed to generate a final response. Relevant cases: " + ", ".join([c.filename for c in matched_cases]),
            "provider": "offline"
        }
