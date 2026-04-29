"""
Chat Service - Intent routing with LLM-powered responses.
Handles both structured actions and conversational queries.
"""
import re
from typing import Dict, Any
from sqlalchemy.orm import Session
from models import CaseDocument
from services.vector_service import vector_service
from services.nlp_service import summarize_text, extract_keywords
from services.llm_service import get_llm_response

# Intent patterns for structured actions
INTENT_PATTERNS = {
    "similar": ["similar", "like this", "find similar", "related cases", "same type"],
    "count": ["how many", "count", "total cases", "number of cases"],
    "summarize": ["summar", "bullet", "key points", "main points"],
    "entities": ["entit", "name", "person", "organi", "who", "people", "companies"],
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


def process_chat_query(
    query: str,
    document_text: str = None,
    keywords: list = None,
    db: Session = None
) -> Dict[str, Any]:
    """
    Process a chat query using intent routing and LLM.
    Returns a dict with 'response' and 'provider' (meta-info).
    """
    if not query or not query.strip():
        return {"response": "Please ask me something about your documents.", "provider": "local"}

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
        # This now returns {"response": "...", "provider": "..."}
        result = get_llm_response(
            user_message=query,
            system_prompt=system_prompt,
            document_context=context
        )
        return result
    except Exception as e:
        # Fallback response if LLM fails
        msg = "I've currently reached my daily processing limit for advanced cloud analysis. No worries! I'm switching to **Local Processing Mode** to continue helping you. The advanced analysis limit resets daily at **midnight Pacific Time (approx. 12:30 PM IST)**. My answers might be a bit simpler for now, but I can still assist with your legal documents!"
        return {"response": msg, "provider": "offline"}