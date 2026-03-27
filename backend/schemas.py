from pydantic import BaseModel, EmailStr
from typing import Optional

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
