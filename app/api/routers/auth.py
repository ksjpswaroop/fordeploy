from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import jwt
from passlib.context import CryptContext

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User, Role, UserSession, Invite as InviteModel, PasswordReset as PasswordResetModel
from app.schemas.user import (
    UserCreate, UserResponse, UserLogin, Token, 
    PasswordReset, PasswordResetRequest, PasswordChange
)
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def _set_must_change_password(user: User, flag: bool = True):
    """Set a soft flag in preferences JSON to require password change.

    Avoids schema migrations; consumers should use require_password_fresh dep.
    """
    prefs = dict(user.preferences or {})
    prefs["must_change_password"] = bool(flag)
    user.preferences = prefs

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def _now_utc():
    return datetime.now(timezone.utc)

def _encode_with_ttl(data: dict, minutes: int) -> str:
    return create_access_token(data, expires_delta=timedelta(minutes=minutes))

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password (case-insensitive email)."""
    if not email:
        return None
    norm_email = email.strip().lower()
    # Case-insensitive match so existing mixed-case records still work
    user = db.query(User).filter(func.lower(User.email) == norm_email).first()
    if not user or not getattr(user, 'hashed_password', None):
        return None
    try:
        if not verify_password(password, user.hashed_password):
            return None
    except Exception:
        # Hash could be in legacy/invalid format
        return None
    return user

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user
    user_dict = user_data.dict()
    requested_role = user_dict.pop('role', None)
    user_dict.pop('password')
    user_dict['hashed_password'] = hashed_password
    
    user = User(**user_dict)
    
    # Assign requested role or fallback to candidate
    role_name = (requested_role.value if hasattr(requested_role, 'value') else requested_role) or "candidate"
    role_obj = db.query(Role).filter(Role.name == role_name).first()
    if not role_obj:
        role_obj = db.query(Role).filter(Role.name == "candidate").first()
    if role_obj:
        user.roles.append(role_obj)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

# ---- Invite and Activation ----
from pydantic import BaseModel, EmailStr
from uuid import uuid4

class InviteCreateIn(BaseModel):
    email: EmailStr
    role: str  # admin|recruiter|candidate (admin allowed only by super-admin; enforced in admin router)

class InviteOut(BaseModel):
    invite_token: str

@router.post("/invite", response_model=InviteOut)
async def create_invite(
    payload: InviteCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an invite token. Caller must be admin/super_admin in higher-level router guard.
    For now, minimal enforcement assumes admin guard is applied by route inclusion.
    """
    jti = uuid4().hex
    inv = InviteModel(
        email=payload.email,
        role_name=payload.role,
        code_jti=jti,
        expires_at=_now_utc() + timedelta(hours=48),
        created_by_user_id=current_user.id,
    )
    db.add(inv)
    db.commit()
    token = _encode_with_ttl({"sub": payload.email, "role": payload.role, "type": "invite", "jti": jti}, minutes=48*60)
    return InviteOut(invite_token=token)

class ActivateIn(BaseModel):
    invite_token: str
    password: str

@router.post("/activate", response_model=Token)
async def activate(body: ActivateIn, db: Session = Depends(get_db)):
    from jose import JWTError
    try:
        data = jwt.decode(body.invite_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid invite token")
    if data.get("type") != "invite":
        raise HTTPException(status_code=400, detail="Wrong token type")
    email, role, jti = data.get("sub"), data.get("role"), data.get("jti")
    inv = db.query(InviteModel).filter(InviteModel.code_jti == jti).first()
    if not inv or inv.used_at is not None or inv.email.lower() != str(email).lower():
        raise HTTPException(status_code=400, detail="Invite not found or used")
    if inv.expires_at < _now_utc():
        raise HTTPException(status_code=400, detail="Invite expired")

    user = db.query(User).filter(User.email == email).first()
    created = False
    if user is None:
        user = User(email=email, first_name=email.split('@')[0], last_name="", hashed_password=get_password_hash(body.password), is_active=True)
        db.add(user)
        created = True
    else:
        user.hashed_password = get_password_hash(body.password)
        user.is_active = True
    # First commit user upsert
    try:
        db.commit(); db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"activate user commit failed: {e}")

    # Assign role if available
    if role and not any(r.name == role for r in user.roles):
        role_obj = db.query(Role).filter(Role.name == role).first()
        if role_obj:
            user.roles.append(role_obj)
            try:
                db.commit(); db.refresh(user)
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail=f"activate role assign failed: {e}")

    # Mark invite used
    inv.used_at = _now_utc()
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"activate invite commit failed: {e}")

    access_token = create_access_token({"sub": str(user.id)}, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer", "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    
    # Create session record
    session = UserSession(
        user_id=user.id,
        session_token=create_access_token(data={"sub": str(user.id)}),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        ip_address=form_data.client_id if hasattr(form_data, 'client_id') else None,
        user_agent=form_data.client_secret if hasattr(form_data, 'client_secret') else None
    )
    
    db.add(session)
    db.commit()
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # Determine primary role name (fallback to candidate if none)
    primary_role = None
    candidate_email = "kc5817@srmist.edu.in"
    if user.email.lower() == candidate_email:
        primary_role = 'candidate'
    else:
        try:
            if hasattr(user, 'get_primary_role'):
                pr = user.get_primary_role()
                primary_role = pr.name if pr else None
        except Exception:
            primary_role = None
        if not primary_role:
            # Fallback logic: inspect roles relationship directly
            try:
                if user.roles:
                    primary_role = getattr(user.roles[0], 'name', None)
            except Exception:
                primary_role = None
        if not primary_role:
            primary_role = 'candidate'

    access_token = create_access_token(
        data={"sub": str(user.id), "role": primary_role, "email": user.email}, expires_delta=access_token_expires
    )
    
    # Surface must_change_password flag for UI convenience
    must_change = bool((user.preferences or {}).get("must_change_password", False))
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "must_change_password": must_change,
        "role": primary_role,
    }

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout current user."""
    # Invalidate all active sessions for the user
    active_sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).all()
    
    for session in active_sessions:
        session.is_active = False
        session.logged_out_at = datetime.utcnow()
    
    db.commit()

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return current_user

@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refresh access token."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # Determine role & include email for consistency
    role_name = None
    try:
        pr = current_user.get_primary_role() if hasattr(current_user, 'get_primary_role') else None
        role_name = pr.name if pr else None
    except Exception:
        role_name = None
    if not role_name:
        role_name = 'candidate'
    access_token = create_access_token(
        data={"sub": str(current_user.id), "role": role_name, "email": current_user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.password_changed_at = datetime.utcnow()
    _set_must_change_password(current_user, False)
    
    # Invalidate all sessions except current one
    active_sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).all()
    
    for session in active_sessions:
        session.is_active = False
        session.logged_out_at = datetime.utcnow()
    
    db.commit()

@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(
    request_data: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request password reset."""
    user = db.query(User).filter(User.email == request_data.email).first()
    if not user:
        # Don't reveal if email exists or not
        return
    
    # Generate reset token
    reset_token = create_access_token(
        data={"sub": str(user.id), "type": "password_reset"},
        expires_delta=timedelta(hours=1)  # Reset token expires in 1 hour
    )
    
    user.password_reset_token = reset_token
    user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
    
    db.commit()
    
    # TODO: Send email with reset link
    # send_password_reset_email(user.email, reset_token)

@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """Reset password using reset token."""
    try:
        payload = jwt.decode(
            reset_data.token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: int = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    # Check if token matches and hasn't expired
    if (user.password_reset_token != reset_data.token or 
        user.password_reset_expires < datetime.utcnow()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    user.password_changed_at = datetime.utcnow()
    user.password_reset_token = None
    user.password_reset_expires = None
    _set_must_change_password(user, False)
    
    # Invalidate all sessions
    active_sessions = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_active == True
    ).all()
    
    for session in active_sessions:
        session.is_active = False
        session.logged_out_at = datetime.utcnow()
    
    db.commit()


class ResetConfirmIn(BaseModel):
    reset_token: str
    new_password: str

@router.post("/reset/confirm", response_model=Token)
async def reset_confirm(body: ResetConfirmIn, db: Session = Depends(get_db)):
    """Confirm reset via admin-issued short-lived token."""
    try:
        data = jwt.decode(body.reset_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid reset token")
    if data.get("type") != "reset":
        raise HTTPException(status_code=400, detail="Wrong token type")
    email, jti = data.get("sub"), data.get("jti")
    pr = db.query(PasswordResetModel).filter(PasswordResetModel.jti == jti).first()
    if not pr or pr.used_at is not None or pr.email.lower() != str(email).lower():
        raise HTTPException(status_code=400, detail="Reset record invalid/used")
    if pr.expires_at < _now_utc():
        raise HTTPException(status_code=400, detail="Reset token expired")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = get_password_hash(body.new_password)
    user.password_changed_at = datetime.utcnow()
    _set_must_change_password(user, False)
    pr.used_at = _now_utc()
    db.commit()
    access_token = create_access_token({"sub": str(user.id)}, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer", "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}

@router.get("/sessions", response_model=list)
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's active sessions."""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).all()
    
    return [{
        "id": session.id,
        "created_at": session.created_at,
        "expires_at": session.expires_at,
        "ip_address": session.ip_address,
        "user_agent": session.user_agent,
        "last_activity": session.last_activity
    } for session in sessions]

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke a specific session."""
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.is_active = False
    session.logged_out_at = datetime.utcnow()
    db.commit()