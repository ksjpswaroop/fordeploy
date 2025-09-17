"""User service for managing user operations with Clerk integration."""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status

from app.models.user import User, Role, Permission
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.auth.clerk_client import clerk_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class UserService:
    """Service class for user operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_user_from_clerk(self, clerk_user_data: Dict[str, Any]) -> User:
        """Create a new user from Clerk user data."""
        try:
            # Extract user information from Clerk data
            email = clerk_user_data.get('email_addresses', [{}])[0].get('email_address')
            first_name = clerk_user_data.get('first_name', '')
            last_name = clerk_user_data.get('last_name', '')
            clerk_user_id = clerk_user_data.get('id')
            
            if not email or not clerk_user_id:
                raise ValueError("Email and Clerk user ID are required")
            
            # Check if user already exists
            existing_user = self.get_user_by_clerk_id(clerk_user_id)
            if existing_user:
                return existing_user
            
            # Create new user
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                clerk_user_id=clerk_user_id,
                clerk_tenant_id=clerk_user_data.get('tenant_id'),
                external_auth_provider='clerk',
                is_active=True,
                is_verified=True,  # Clerk handles verification
                hashed_password='',  # Not needed for Clerk users
                username=email.split('@')[0]  # Generate username from email
            )
            
            # Assign default role based on tenant or other criteria
            default_role = self.get_default_role_for_user(clerk_user_data)
            if default_role:
                user.roles.append(default_role)
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"Created new user from Clerk: {user.email} (ID: {user.id})")
            return user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user from Clerk data: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
    
    def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[User]:
        """Get user by Clerk user ID."""
        return self.db.query(User).filter(
            User.clerk_user_id == clerk_user_id,
            User.is_deleted == False
        ).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        return self.db.query(User).filter(
            User.email == email,
            User.is_deleted == False
        ).first()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(
            User.id == user_id,
            User.is_deleted == False
        ).first()
    
    def update_user_from_clerk(self, user: User, clerk_user_data: Dict[str, Any]) -> User:
        """Update existing user with latest Clerk data."""
        try:
            # Update user information from Clerk
            email = clerk_user_data.get('email_addresses', [{}])[0].get('email_address')
            if email:
                user.email = email
            
            if clerk_user_data.get('first_name'):
                user.first_name = clerk_user_data['first_name']
            
            if clerk_user_data.get('last_name'):
                user.last_name = clerk_user_data['last_name']
            
            # Update tenant ID if changed
            if clerk_user_data.get('tenant_id'):
                user.clerk_tenant_id = clerk_user_data['tenant_id']
            
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"Updated user from Clerk: {user.email} (ID: {user.id})")
            return user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user from Clerk data: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )
    
    def get_users_by_tenant(self, tenant_id: str) -> List[User]:
        """Get all users in a specific tenant."""
        return self.db.query(User).filter(
            User.clerk_tenant_id == tenant_id,
            User.is_deleted == False
        ).all()
    
    def assign_role_to_user(self, user_id: int, role_name: str, assigned_by: int) -> bool:
        """Assign a role to a user."""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            role = self.db.query(Role).filter(
                Role.name == role_name,
                Role.is_active == True
            ).first()
            
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Role not found"
                )
            
            # Check if user already has this role
            if role not in user.roles:
                user.roles.append(role)
                self.db.commit()
                logger.info(f"Assigned role '{role_name}' to user {user.email}")
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error assigning role to user: {str(e)}")
            return False
    
    def remove_role_from_user(self, user_id: int, role_name: str) -> bool:
        """Remove a role from a user."""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            role = self.db.query(Role).filter(
                Role.name == role_name
            ).first()
            
            if role and role in user.roles:
                user.roles.remove(role)
                self.db.commit()
                logger.info(f"Removed role '{role_name}' from user {user.email}")
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing role from user: {str(e)}")
            return False
    
    def get_default_role_for_user(self, clerk_user_data: Dict[str, Any]) -> Optional[Role]:
        """Determine default role for a new user based on Clerk data."""
        # Default role assignment logic
        # This can be customized based on tenant, email domain, or other criteria
        
        # Check if user has specific role metadata from Clerk
        public_metadata = clerk_user_data.get('public_metadata', {})
        private_metadata = clerk_user_data.get('private_metadata', {})
        
        # Look for role in metadata
        role_name = (
            public_metadata.get('role') or 
            private_metadata.get('role') or 
            'candidate'  # Default role
        )
        
        return self.db.query(Role).filter(
            Role.name == role_name,
            Role.is_active == True
        ).first()
    
    def sync_user_with_clerk(self, user: User) -> User:
        """Sync user data with Clerk."""
        try:
            if not user.clerk_user_id:
                logger.warning(f"User {user.email} has no Clerk ID, skipping sync")
                return user
            
            # Fetch latest user data from Clerk
            clerk_user_data = clerk_client.get_user(user.clerk_user_id)
            if clerk_user_data:
                return self.update_user_from_clerk(user, clerk_user_data)
            
            return user
            
        except Exception as e:
            logger.error(f"Error syncing user with Clerk: {str(e)}")
            return user


def get_user_service(db: Session) -> UserService:
    """Get user service instance."""
    return UserService(db)