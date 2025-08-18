#!/usr/bin/env python3
"""
Script to create the first admin account for the Valorant Fantasy League admin panel.
Run this after setting up the database to create your initial admin user.
"""

import os
import sys
from getpass import getpass

# Add the parent directory to the Python path so we can import our app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlmodel import Session, select, create_engine
from app.models.admin_model import Admin
from app.utils.admin_auth import get_admin_password_hash
from app.core.config import settings

def create_admin():
    """Create the first admin account."""
    
    # Create database engine
    engine = create_engine(str(settings.DATABASE_URL))
    
    with Session(engine) as session:
        # Check if any admins already exist
        existing_admins = session.exec(select(Admin)).all()
        if existing_admins:
            print("❌ Admin accounts already exist in the system.")
            print("Use the /admin/auth/register endpoint to create additional admins.")
            return
        
        print("🔧 Creating first admin account...")
        print("This admin will have super admin privileges and can create other admin accounts.")
        print()
        
        # Get admin details
        username = input("Enter admin username: ").strip()
        if not username:
            print("❌ Username cannot be empty.")
            return
            
        # Check if username already exists (as a regular user)
        from app.models.user_model import User
        existing_user = session.exec(select(User).where(User.username == username)).first()
        if existing_user:
            print(f"❌ Username '{username}' is already taken by a regular user.")
            return
        
        password = getpass("Enter admin password: ").strip()
        if not password:
            print("❌ Password cannot be empty.")
            return
        
        confirm_password = getpass("Confirm admin password: ").strip()
        if password != confirm_password:
            print("❌ Passwords do not match.")
            return
        
        if len(password) < 8:
            print("❌ Password must be at least 8 characters long.")
            return
        
        # Create the admin
        try:
            hashed_password = get_admin_password_hash(password)
            admin = Admin(
                username=username,
                hashed_password=hashed_password,
                is_super_admin=True,  # First admin is always super admin
                can_manage_players=True,
                can_manage_users=True,
                can_manage_leagues=True,
                can_manage_matches=True,
                can_view_analytics=True
            )
            
            session.add(admin)
            session.commit()
            session.refresh(admin)
            
            print()
            print("✅ Admin account created successfully!")
            print(f"Username: {admin.username}")
            print(f"Admin ID: {admin.id}")
            print("Permissions: Super Admin (all permissions)")
            print()
            print("You can now log in to the admin panel at: /admin/login")
            print("Additional admin accounts can be created from the admin panel.")
            
        except Exception as e:
            print(f"❌ Error creating admin account: {e}")
            session.rollback()

if __name__ == "__main__":
    create_admin()
