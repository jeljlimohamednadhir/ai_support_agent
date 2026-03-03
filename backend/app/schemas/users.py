"""
User Schemas
"""
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    """User creation"""
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login"""
    username: str
    password: str


class UserResponse(BaseModel):
    """User response"""
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool = True
    role: str = "user"


class Token(BaseModel):
    """JWT Token"""
    access_token: str
    token_type: str = "bearer"
