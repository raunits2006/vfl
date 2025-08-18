"""
Authentication router for user login, registration, and token management.
"""
from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from app.database import get_session
from app.models.user_model import User
from app.utils.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/auth", tags=["authentication"])

# Pydantic models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user_data: UserRegister,
    session: Session = Depends(get_session)
):
    """Register a new user."""
    # Check if username OR email already exist (avoid enumeration)
    existing = session.exec(
        select(User).where(
            or_(
                User.username == user_data.username,
                User.email == user_data.email,
            )
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account already exists"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    session.add(user)
    try:
        session.commit()
        session.refresh(user)
    except Exception as e:
        session.rollback()
        # Handle potential race condition with defensive error handling
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account already exists"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at.isoformat()
    )

@router.post("/login", response_model=Token)
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """Login user and return access token."""
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat()
    )

@router.post("/refresh", response_model=Token)
def refresh_token(current_user: User = Depends(get_current_active_user)):
    """Refresh the access token for the current user."""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
