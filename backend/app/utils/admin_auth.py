"""
Admin authentication utilities for secure admin access.
Separate from regular user authentication for enhanced security.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.database import get_session
from app.models.admin_model import Admin
from app.core.config import settings

# Admin-specific security configuration
# In production, ADMIN_SECRET_KEY MUST be set independently — refuses to start otherwise.
# In development, a predictable derivation is acceptable for convenience.
if settings.ENVIRONMENT == "production":
    if not settings.ADMIN_SECRET_KEY:
        raise SystemExit(
            "FATAL: ADMIN_SECRET_KEY must be set in production. "
            "It must be a separate, independent secret from SECRET_KEY."
        )
    ADMIN_SECRET_KEY = settings.ADMIN_SECRET_KEY
else:
    ADMIN_SECRET_KEY = settings.ADMIN_SECRET_KEY or (settings.SECRET_KEY + "_ADMIN")
ADMIN_ALGORITHM = "HS256"
ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Shorter token expiry for admin

# Password hashing with stronger rounds for admin
admin_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=14)

# OAuth2 scheme for admin
admin_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="admin/auth/login")

def verify_admin_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash for admin."""
    return admin_pwd_context.verify(plain_password, hashed_password)

def get_admin_password_hash(password: str) -> str:
    """Hash a password for admin with stronger encryption."""
    return admin_pwd_context.hash(password)

def create_admin_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create access token for admin."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "admin"})
    encoded_jwt = jwt.encode(to_encode, ADMIN_SECRET_KEY, algorithm=ADMIN_ALGORITHM)
    return encoded_jwt

def verify_admin_token(token: str) -> Optional[str]:
    """Verify admin token and return username."""
    try:
        payload = jwt.decode(token, ADMIN_SECRET_KEY, algorithms=[ADMIN_ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if username is None or token_type != "admin":
            return None
        return username
    except JWTError:
        return None

def authenticate_admin(session: Session, username: str, password: str) -> Optional[Admin]:
    """Authenticate an admin with username and password."""
    admin = session.exec(select(Admin).where(Admin.username == username)).first()
    if not admin:
        return None
    if not admin.is_active:
        return None
    if not verify_admin_password(password, admin.hashed_password):
        return None
    
    # Update last login
    admin.last_login = datetime.utcnow()
    session.add(admin)
    session.commit()
    session.refresh(admin)
    
    return admin

async def get_current_admin(
    token: str = Depends(admin_oauth2_scheme),
    session: Session = Depends(get_session)
) -> Admin:
    """Get the current authenticated admin from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    username = verify_admin_token(token)
    if username is None:
        raise credentials_exception
    
    admin = session.exec(select(Admin).where(Admin.username == username)).first()
    if admin is None or not admin.is_active:
        raise credentials_exception
    
    return admin

async def get_current_active_admin(current_admin: Admin = Depends(get_current_admin)) -> Admin:
    """Ensure admin is active."""
    if not current_admin.is_active:
        raise HTTPException(status_code=400, detail="Inactive admin")
    return current_admin

def require_permission(permission_field: str):
    """Decorator to require specific admin permission."""
    def permission_checker(admin: Admin = Depends(get_current_active_admin)) -> Admin:
        if admin.is_super_admin:
            return admin
        
        if not hasattr(admin, permission_field) or not getattr(admin, permission_field):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Admin lacks required permission: {permission_field}"
            )
        return admin
    return permission_checker

# Permission dependencies
require_player_management = require_permission("can_manage_players")
require_user_management = require_permission("can_manage_users")
require_league_management = require_permission("can_manage_leagues")
require_match_management = require_permission("can_manage_matches")
require_analytics_access = require_permission("can_view_analytics")
