from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.chat_service import process_chat_query
from database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/chat", tags=["ChatBot"])

class ChatRequest(BaseModel):
    query: str
    document_text: Optional[str] = None
    document_keywords: Optional[list] = None

@router.post("/")
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Process a chat query using the Intent-Based engine.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
        
    result = process_chat_query(
        request.query, 
        request.document_text, 
        request.document_keywords,
        db
    )
    
    # result is now {"response": str, "provider": str}
    return result
