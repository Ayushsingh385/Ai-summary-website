import re
from sqlalchemy.orm import Session
from models import CaseDocument
from services.vector_service import vector_service
from services.nlp_service import summarize_text, extract_keywords

def process_chat_query(query: str, document_text: str = None, keywords: list = None, db: Session = None) -> str:
    """
    Intent-based routing for offline NLP chatbot.
    """
    query_lower = query.lower()

    # Intent 1: Similarity Search
    if "similar" in query_lower or "like this" in query_lower:
        search_text = document_text if document_text else query
        if not search_text:
            return "I need a document to find similar files. Please select or upload a case file first!"
            
        results = vector_service.find_similar(search_text, top_k=3, threshold=0.6)
        if not results:
            return "I couldn't find any heavily similar cases in the database."
            
        case_ids = [res[0] for res in results]
        similar_cases = db.query(CaseDocument).filter(CaseDocument.id.in_(case_ids)).all()
        
        response = "Here are some similar cases I found in the database:\n"
        for idx, case in enumerate(similar_cases):
            # Try to grab the score, defaulting to 0 if not matched properly
            score = next((res[1] for res in results if res[0] == case.id), 0)
            response += f"- **{case.filename}** ({(score*100):.1f}% match)\n"
        return response

    # Intent 2: Database Intelligence (Counting)
    if "how many" in query_lower or "count" in query_lower:
        total_cases = db.query(CaseDocument).count()
        if document_text and ("this type" in query_lower or "these type" in query_lower):
            # If asking for "this type", we count similar files specifically
            results = vector_service.find_similar(document_text, top_k=total_cases, threshold=0.7)
            count = len(results)
            return f"There are **{count} cases** highly similar to this one in the database (out of {total_cases} total)."
        
        return f"Currently, there are **{total_cases} completed cases** stored securely in your database."

    # Intent 3: Document Bullet Points
    if document_text and ("bullet" in query_lower or "point" in query_lower or "summar" in query_lower):
        if len(document_text) < 50:
            return "The current document is too short to summarize into bullet points."
            
        result = summarize_text(document_text, "short")
        summary = result.get("summary", "")
        
        # Format as simple bullet points by breaking on sentences
        sentences = re.split(r'(?<=[.!?])\s+', summary)
        bullets = "\n".join([f"- {s.strip()}" for s in sentences if s.strip()])
        return f"Here are the key bullet points for this file:\n{bullets}"

    # Intent 4: Entities and Information Extraction
    if document_text and ("entit" in query_lower or "name" in query_lower or "person" in query_lower or "organi" in query_lower):
        kw_list = keywords if keywords else extract_keywords(document_text, top_n=20)
        
        entities = {"PERSON": [], "ORG": [], "GPE": [], "LAW": []}
        for kw in kw_list:
            if isinstance(kw, dict) and kw.get("type") in entities:
                entities[kw["type"]].append(kw["keyword"])
        
        response = "Here are the key entities I found in this document:\n"
        if entities["PERSON"]: response += f"- **People**: {', '.join(entities['PERSON'])[:100]}...\n"
        if entities["ORG"]: response += f"- **Organizations**: {', '.join(entities['ORG'])[:100]}...\n"
        if entities["GPE"]: response += f"- **Locations**: {', '.join(entities['GPE'])[:100]}...\n"
        if entities["LAW"]: response += f"- **Legal Codes**: {', '.join(entities['LAW'])[:100]}...\n"
        
        if response == "Here are the key entities I found in this document:\n":
            return "I couldn't extract any prominent people or organizations from this text."
        return response

    # Default Fallback
    return ("I'm your intelligent summarizing assistant! I can help you with:\n"
            "- Finding similar past cases to the one you're currently viewing.\n"
            "- Counting how many total files or similar files are in the database.\n"
            "- Extracting people, organizations, and legal entities from the text.\n"
            "- Formatting the document into readable bullet points.")
