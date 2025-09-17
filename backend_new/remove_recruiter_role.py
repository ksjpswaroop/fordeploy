"""Remove recruiter role from a user (by email) without deleting user or other roles.

Usage:
  python -m scripts.remove_recruiter_role --email Sriman@svksystems.com
"""
import argparse
from app.core.database import SessionLocal
from app.models.user import User, Role, user_roles
from sqlalchemy import select, update

def remove_recruiter(email: str) -> bool:
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email==email).first()
        if not user:
            print(f"User not found: {email}")
            return False
        recruiter_role = session.query(Role).filter(Role.name=='recruiter').first()
        if not recruiter_role:
            print("Recruiter role not present in database")
            return False
        # Deactivate association instead of delete (safer)
        assoc = session.execute(
            select(user_roles).where(
                user_roles.c.user_id==user.id,
                user_roles.c.role_id==recruiter_role.id,
                user_roles.c.is_active==True
            )
        ).first()
        if not assoc:
            print(f"User {email} does not have active recruiter role")
            return True
        session.execute(
            update(user_roles).where(
                user_roles.c.user_id==user.id,
                user_roles.c.role_id==recruiter_role.id
            ).values(is_active=False)
        )
        session.commit()
        print(f"Recruiter role deactivated for {email}")
        return True
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        return False
    finally:
        session.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--email', required=True)
    args = ap.parse_args()
    remove_recruiter(args.email.strip())

if __name__ == '__main__':
    main()
