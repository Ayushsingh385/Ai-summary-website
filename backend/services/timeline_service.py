"""
Timeline Service — Extracts chronological events from legal documents.
Transforms unstructured case text into a structured, sorted timeline
suitable for frontend visualization.
"""
import logging
import re
from datetime import datetime
from typing import List, Dict, Any
from services.llm_service import get_llm_response

logger = logging.getLogger(__name__)

def extract_legal_timeline(text: str) -> List[Dict[str, Any]]:
    """
    Extracts a chronological sequence of events from a document.
    """
    system_prompt = (
        "You are a legal chronologist. Your goal is to extract every significant event, "
        "filing, order, and communication from the provided text. "
        "For each event, identify: \n"
        "1. The Date (Standardize to YYYY-MM-DD if possible, otherwise keep original).\n"
        "2. The Event (A concise description of what happened).\n"
        "3. The Actor (Who initiated or was the subject of the event).\n"
        "4. The Significance (Why this event matters to the case outcome).\n\n"
        "Format the output as a valid JSON list of objects: "
        "[{\"date\": \"...\", \"event\": \"...\", \"actor\": \"...\", \"significance\": \"...\"}]"
    )

    user_msg = f"Extract the timeline of events from this legal document:\n\n{text}"

    try:
        # Use LLM for high-precision timeline extraction (handles complex date phrasing better than regex)
        result = get_llm_response(user_message=user_msg, system_prompt=system_prompt)
        response_text = result.get("response", "[]")
        
        # Clean the response in case LLM wrapped JSON in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        import json
        timeline = json.loads(response_text)
        
        # Sort timeline by date (attempting a best-effort sort)
        timeline.sort(key=lambda x: x.get("date", "9999-12-31"))
        
        return timeline

    except Exception as e:
        logger.error(f"Timeline extraction failed: {e}")
        # Fallback to a basic regex-based date extractor if LLM fails
        return _regex_timeline_fallback(text)

def _regex_timeline_fallback(text: str) -> List[Dict[str, Any]]:
    """
    Basic regex fallback that finds date-like patterns and the sentence following them.
    """
    timeline = []
    # Simplified date pattern (DD/MM/YYYY, DD-MM-YYYY, Month DD, YYYY)
    date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})'
    
    matches = re.finditer(date_pattern, text)
    for match in matches:
        date_str = match.group()
        # Grab the rest of the sentence
        start = match.start()
        end = text.find('.', start)
        if end == -1: end = start + 200
        
        event_text = text[start:end].strip()
        timeline.append({
            "date": date_str,
            "event": event_text,
            "actor": "Unknown",
            "significance": "Extracted via fallback regex"
        })
        
    return timeline
