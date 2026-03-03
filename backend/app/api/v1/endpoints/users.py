"""
User Management Endpoints
Authentication, authorization, and user preferences
"""
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.users import UserCreate, UserLogin, UserResponse, Token
from app.services.validation.user_service import UserService

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    """Register a new user"""
    try:
        user_service = UserService()
        new_user = await user_service.create_user(user)
        return new_user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login and get access token"""
    try:
        user_service = UserService()
        token = await user_service.authenticate(credentials)
        return token
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/me", response_model=UserResponse)
async def get_current_user():
    """Get current user profile"""
    # TODO: Implement JWT token validation
    pass


@router.put("/preferences")
async def update_preferences(preferences: dict):
    """Update user preferences"""
    try:
        user_service = UserService()
        result = await user_service.update_preferences(preferences)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
