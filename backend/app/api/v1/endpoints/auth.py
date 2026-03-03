"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.refresh_token import RefreshToken, RevokedToken
from app.schemas.auth import (
    UserCreate, UserResponse, UserUpdate, UserLogin, 
    Token, PasswordChange, RefreshTokenRequest
)
from app.core.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, require_admin, get_current_active_user
)
from app.core.security import create_refresh_token, decode_token
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# OAuth2 scheme for logout endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
ALGORITHM = "HS256"


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint - returns access and refresh tokens"""
    # Allow login by username OR email (case-insensitive)
    identifier = form_data.username
    user = db.query(User).filter(
        (User.username.ilike(identifier)) | (User.email.ilike(identifier))
    ).first()
    
    # Verify password with protected logging to surface server-side errors
    try:
        logger.info(f"Attempting password verification for user: {identifier}")
        logger.info(f"User found: {user is not None}")
        if user:
            logger.info(f"User hash starts with: {user.hashed_password[:20]}")
        pwd_ok = user and verify_password(form_data.password, user.hashed_password)
        logger.info(f"Password verification result: {pwd_ok}")
    except Exception as e:
        # Log full exception for debugging and return 500 so we can see server logs
        logger.exception("Error during password verification")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during password verification"
        )

    if not pwd_ok:
        logger.info(f"Failed login attempt for identifier='{identifier}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token (short-lived, 15 minutes)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
        }
    )
    
    # Create refresh token (long-lived, 7 days) and store in database
    refresh_token_str, refresh_expires_at = create_refresh_token(user.id)
    
    # Store refresh token in database
    refresh_token_record = RefreshToken(
        token=refresh_token_str,
        user_id=user.id,
        expires_at=refresh_expires_at,
        revoked=False
    )
    db.add(refresh_token_record)
    db.commit()
    
    logger.info(f"User '{user.username}' logged in successfully")
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token_str,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        # Decode refresh token
        payload = decode_token(refresh_request.refresh_token)
        
        # Verify token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = int(payload.get("sub"))
        jti = payload.get("jti")
        
        # Check if refresh token exists in database and is not revoked
        refresh_token_record = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_request.refresh_token,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False
        ).first()
        
        if not refresh_token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked refresh token"
            )
        
        # Check if token is expired
        if refresh_token_record.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Revoke old refresh token (token rotation)
        refresh_token_record.revoked = True
        
        # Create new access token
        new_access_token = create_access_token(
            data={
                "sub": user.username,
                "user_id": user.id,
                "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
            }
        )
        
        # Create new refresh token
        new_refresh_token_str, new_refresh_expires_at = create_refresh_token(user.id)
        
        # Mark old token as replaced
        refresh_token_record.replaced_by_token = new_refresh_token_str
        
        # Store new refresh token
        new_refresh_token_record = RefreshToken(
            token=new_refresh_token_str,
            user_id=user.id,
            expires_at=new_refresh_expires_at,
            revoked=False
        )
        db.add(new_refresh_token_record)
        db.commit()
        
        logger.info(f"Tokens refreshed for user '{user.username}'")
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token_str,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token"
        )


@router.post("/logout")
async def logout(
    refresh_token: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Logout endpoint - revokes refresh token and adds access token to blacklist"""
    from app.core.auth import get_token_jti
    from jose import jwt
    
    try:
        # Revoke refresh token if provided
        if refresh_token:
            refresh_token_record = db.query(RefreshToken).filter(
                RefreshToken.token == refresh_token,
                RefreshToken.user_id == current_user.id
            ).first()
            
            if refresh_token_record and not refresh_token_record.revoked:
                refresh_token_record.revoked = True
                logger.info(f"Revoked refresh token for user '{current_user.username}'")
        
        # Add access token to blacklist (revoked_tokens table)
        jti = get_token_jti(token)
        if jti:
            # Decode to get expiration time
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            expires_at = datetime.fromtimestamp(payload.get('exp'))
            
            revoked_token = RevokedToken(
                jti=jti,
                token_type='access',
                user_id=current_user.id,
                revoked_at=datetime.utcnow(),
                expires_at=expires_at
            )
            db.add(revoked_token)
            logger.info(f"Added access token to blacklist for user '{current_user.username}'")
        
        db.commit()
        logger.info(f"User '{current_user.username}' logged out")
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.exception(f"Error during logout: {e}")
        db.rollback()
        return {"message": "Logout completed (with errors)"}



@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password"""
    # Verify old password
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    logger.info(f"User '{current_user.username}' changed password")
    return {"message": "Password changed successfully"}


# Admin endpoints for user management
@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create new user (admin only)"""
    # Check if username exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"Admin '{current_user.username}' created user '{user.username}' with role '{user.role}'")
    return user


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    if user_data.email is not None:
        # Check email uniqueness
        existing = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        user.email = user_data.email
    
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    
    if user_data.role is not None:
        user.role = user_data.role
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    if user_data.password is not None:
        user.hashed_password = get_password_hash(user_data.password)
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Admin '{current_user.username}' updated user '{user.username}'")
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    username = user.username
    db.delete(user)
    db.commit()
    
    logger.info(f"Admin '{current_user.username}' deleted user '{username}'")
    return {"message": f"User '{username}' deleted successfully"}
