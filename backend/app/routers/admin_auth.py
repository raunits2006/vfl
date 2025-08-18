"""
Admin authentication router for secure admin login and management.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional

from app.database import get_session
from app.models.admin_model import Admin
from app.utils.admin_auth import (
    authenticate_admin,
    create_admin_access_token,
    get_admin_password_hash,
    get_current_active_admin,
    ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/admin/auth", tags=["admin-authentication"])

# Pydantic models
class AdminRegister(BaseModel):
    username: str
    password: str
    is_super_admin: bool = False
    can_manage_players: bool = True
    can_manage_users: bool = False
    can_manage_leagues: bool = False
    can_manage_matches: bool = False
    can_view_analytics: bool = True

class AdminResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    is_super_admin: bool
    can_manage_players: bool
    can_manage_users: bool
    can_manage_leagues: bool
    can_manage_matches: bool
    can_view_analytics: bool
    created_at: str
    last_login: Optional[str]

class AdminToken(BaseModel):
    access_token: str
    token_type: str

@router.post("/register", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
def register_admin(
    admin_data: AdminRegister,
    session: Session = Depends(get_session),
    current_admin: Admin = Depends(get_current_active_admin)  # Only existing admins can create new ones
):
    """Register a new admin account. Requires existing admin authentication."""
    
    # Only super admins can create other admins
    if not current_admin.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can create new admin accounts"
        )
    
    # Check if admin already exists
    existing_admin = session.exec(select(Admin).where(Admin.username == admin_data.username)).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin with this username already exists"
        )
    
    # Create new admin
    hashed_password = get_admin_password_hash(admin_data.password)
    new_admin = Admin(
        username=admin_data.username,
        hashed_password=hashed_password,
        is_super_admin=admin_data.is_super_admin,
        can_manage_players=admin_data.can_manage_players,
        can_manage_users=admin_data.can_manage_users,
        can_manage_leagues=admin_data.can_manage_leagues,
        can_manage_matches=admin_data.can_manage_matches,
        can_view_analytics=admin_data.can_view_analytics
    )
    
    session.add(new_admin)
    session.commit()
    session.refresh(new_admin)
    
    return AdminResponse(
        id=new_admin.id,
        username=new_admin.username,
        is_active=new_admin.is_active,
        is_super_admin=new_admin.is_super_admin,
        can_manage_players=new_admin.can_manage_players,
        can_manage_users=new_admin.can_manage_users,
        can_manage_leagues=new_admin.can_manage_leagues,
        can_manage_matches=new_admin.can_manage_matches,
        can_view_analytics=new_admin.can_view_analytics,
        created_at=new_admin.created_at.isoformat(),
        last_login=new_admin.last_login.isoformat() if new_admin.last_login else None
    )

@router.post("/login", response_model=AdminToken)
def login_admin(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """Login admin and return access token."""
    admin = authenticate_admin(session, form_data.username, form_data.password)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_admin_access_token(
        data={"sub": admin.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=AdminResponse)
def read_current_admin(current_admin: Admin = Depends(get_current_active_admin)):
    """Get current admin information."""
    return AdminResponse(
        id=current_admin.id,
        username=current_admin.username,
        is_active=current_admin.is_active,
        is_super_admin=current_admin.is_super_admin,
        can_manage_players=current_admin.can_manage_players,
        can_manage_users=current_admin.can_manage_users,
        can_manage_leagues=current_admin.can_manage_leagues,
        can_manage_matches=current_admin.can_manage_matches,
        can_view_analytics=current_admin.can_view_analytics,
        created_at=current_admin.created_at.isoformat(),
        last_login=current_admin.last_login.isoformat() if current_admin.last_login else None
    )

# Initial admin creation endpoint (only works if no admins exist)
@router.post("/init", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
def create_initial_admin(
    admin_data: AdminRegister,
    session: Session = Depends(get_session)
):
    """Create the first admin account. Only works if no admins exist in the system."""
    
    # Check if any admins already exist
    existing_admin_count = session.exec(select(Admin)).all()
    if existing_admin_count:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin accounts already exist. Use /register endpoint."
        )
    
    # Create first admin (automatically super admin)
    hashed_password = get_admin_password_hash(admin_data.password)
    new_admin = Admin(
        username=admin_data.username,
        hashed_password=hashed_password,
        is_super_admin=True,  # First admin is always super admin
        can_manage_players=True,
        can_manage_users=True,
        can_manage_leagues=True,
        can_manage_matches=True,
        can_view_analytics=True
    )
    
    session.add(new_admin)
    session.commit()
    session.refresh(new_admin)
    
    return AdminResponse(
        id=new_admin.id,
        username=new_admin.username,
        is_active=new_admin.is_active,
        is_super_admin=new_admin.is_super_admin,
        can_manage_players=new_admin.can_manage_players,
        can_manage_users=new_admin.can_manage_users,
        can_manage_leagues=new_admin.can_manage_leagues,
        can_manage_matches=new_admin.can_manage_matches,
        can_view_analytics=new_admin.can_view_analytics,
        created_at=new_admin.created_at.isoformat(),
        last_login=new_admin.last_login.isoformat() if new_admin.last_login else None
    )
