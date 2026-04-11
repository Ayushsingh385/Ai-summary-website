from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any, Dict

class UserCreate(BaseModel):
    user_id: str
    employee_id: str
    email_id: str
    password: str

class UserLogin(BaseModel):
    user_id: str
    password: str

class UserResponse(BaseModel):
    id: int
    user_id: str
    employee_id: str
    email_id: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class CaseComparisonCreate(BaseModel):
    filename1: str
    filename2: str
    text1: str
    text2: str
    comparison_summary: str
    shared_entities: List[Any]
    similarities: Optional[List[Any]] = []
    differences: Optional[List[Any]] = []
    shared_blocks: Optional[List[Any]] = []

class CaseComparisonResponse(BaseModel):
    id: int
    filename1: str
    filename2: str
    text1: str
    text2: str
    comparison_summary: str
    shared_entities: List[Any]
    similarities: Optional[List[Any]] = []
    differences: Optional[List[Any]] = []
    shared_blocks: Optional[List[Any]] = []

    class Config:
        from_attributes = True
