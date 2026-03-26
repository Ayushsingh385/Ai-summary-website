from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
from database import Base

class CaseDocument(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    original_text = Column(Text)
    summary_text = Column(Text)
    keywords = Column(JSON)
    stats = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
