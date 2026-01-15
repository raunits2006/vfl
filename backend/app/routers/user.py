"""
User router for authenticated user operations.
All endpoints require authentication. Users can only modify their own data.
Admin endpoints for managing all users are in admin.py.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from app.database import get_session
from app.models.user_model import User
from app.utils.auth import get_current_active_user

router = APIRouter(prefix="/users", tags=["users"])

# Pydantic models for request/response
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get the current authenticated user's information."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat()
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific user by ID. Requires authentication."""
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
        is_active=user.is_active,
        created_at=user.created_at.isoformat()
    )


@router.put("/me", response_model=UserResponse)
def update_current_user(
    user_data: UserUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Update the current authenticated user's information."""
    # Update fields if provided
    if user_data.username is not None:
        # Check if new username already exists
        existing_user = session.exec(
            select(User).where(User.username == user_data.username, User.id != current_user.id)
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        current_user.username = user_data.username
    
    if user_data.email is not None:
        # Check if new email already exists
        existing_email = session.exec(
            select(User).where(User.email == user_data.email, User.id != current_user.id)
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        current_user.email = user_data.email
    
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat()
    )


@router.delete("/me")
def delete_current_user(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Delete the current authenticated user's account."""
    session.delete(current_user)
    session.commit()
    
    return {"message": "Account deleted successfully"}