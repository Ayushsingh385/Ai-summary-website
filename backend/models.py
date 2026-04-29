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
    tags = Column(JSON, default=list)
    status = Column(String, default="new", index=True)
    brief_type = Column(String, nullable=True)
    case_type = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    employee_id = Column(String)
    email_id = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class CaseComparison(Base):
    __tablename__ = "case_comparisons"

    id = Column(Integer, primary_key=True, index=True)
    filename1 = Column(String)
    filename2 = Column(String)
    text1 = Column(Text)
    text2 = Column(Text)
    comparison_summary = Column(Text)
    shared_entities = Column(JSON)
    similarities = Column(JSON, nullable=True)
    differences = Column(JSON, nullable=True)
    shared_blocks = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
