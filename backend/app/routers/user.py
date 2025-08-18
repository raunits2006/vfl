from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from app.database import get_session
from app.models.user_model import User
from app.utils.auth import get_current_active_user, get_password_hash

router = APIRouter(prefix="/users", tags=["users"])

# Pydantic models for request/response
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    session: Session = Depends(get_session)
):
    """Create a new user"""
    # Check if username already exists
    existing_user = session.exec(select(User).where(User.username == user_data.username)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists
    existing_email = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at.isoformat()
    )

@router.get("/", response_model=List[UserResponse])
def get_users(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """Get all users"""
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
        for user in users
    ]

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    session: Session = Depends(get_session)
):
    """Get a specific user by ID"""
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at.isoformat()
    )

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: Session = Depends(get_session)
):
    """Update a user"""
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields if provided
    if user_data.username is not None:
        # Check if new username already exists
        existing_user = session.exec(select(User).where(User.username == user_data.username, User.id != user_id)).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        user.username = user_data.username
    
    if user_data.email is not None:
        # Check if new email already exists
        existing_email = session.exec(select(User).where(User.email == user_data.email, User.id != user_id)).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        user.email = user_data.email
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at.isoformat()
    )

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    session: Session = Depends(get_session)
):
    """Delete a user"""
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    session.delete(user)
    session.commit()
    
    return {"message": "User deleted successfully"} 