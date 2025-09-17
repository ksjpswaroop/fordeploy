#!/usr/bin/env python
"""Idempotent script to create or promote specified emails to admin with a default password.

Usage:
  python -m scripts.seed_admin_users

Environment:
  PASSWORD (optional) override default password

Notes:
  - If user exists: ensure active, set password to provided one, attach admin role if missing.
  - If user missing: create with first_name derived from email local part.
"""
from app.core.database import SessionLocal
from app.models.user import User, Role
from app.api.routers.auth import get_password_hash
from sqlalchemy.orm import Session
import os

TARGET_EMAILS = [
    'Sriman@svksystems.com',
    'Vamshi@molinatek.com',
    'Sreelekha@scholaritinc.com',
    'Vijay@svksystems.com',
]
DEFAULT_PASSWORD = os.environ.get('PASSWORD', 'scholarIT@123')
ADMIN_ROLE_NAME = 'admin'


def get_or_create_admin_role(db: Session) -> Role:
    role = db.query(Role).filter(Role.name == ADMIN_ROLE_NAME).first()
    if not role:
        role = Role(name=ADMIN_ROLE_NAME, display_name='Administrator', description='System administrator', priority=100)
        db.add(role)
        db.commit(); db.refresh(role)
    return role


def ensure_user_admin(db: Session, email: str, password: str, admin_role: Role):
    user = db.query(User).filter(User.email == email).first()
    created = False
    if not user:
        local = email.split('@')[0]
        user = User(
            email=email,
            first_name=local.capitalize(),
            last_name='',
            hashed_password=get_password_hash(password),
            is_active=True,
            is_verified=True,
            is_superuser=False,
        )
        db.add(user)
        created = True
        db.commit(); db.refresh(user)
    else:
        # update password and activation
        user.hashed_password = get_password_hash(password)
        user.is_active = True
        user.is_verified = True
        db.commit(); db.refresh(user)

    if not any(r.name == admin_role.name for r in user.roles):
        user.roles.append(admin_role)
        db.commit(); db.refresh(user)

    return created, user


def main():
    db = SessionLocal()
    try:
        admin_role = get_or_create_admin_role(db)
        results = []
        for email in TARGET_EMAILS:
            created, user = ensure_user_admin(db, email, DEFAULT_PASSWORD, admin_role)
            results.append((email, 'created' if created else 'updated', [r.name for r in user.roles]))
        print('=== Admin Seeding Summary ===')
        for email, action, roles in results:
            print(f'{email}: {action}; roles={roles}')
        print('Password set to provided default for all listed users.')
    finally:
        db.close()


if __name__ == '__main__':
    main()
