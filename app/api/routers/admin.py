from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import get_db
from app.core.config import settings
from jose import jwt
from app.api.dependencies import get_current_user, require_admin, require_password_fresh
from app.models.user import User, Role, Permission
from app.models.communication import EmailTemplate
from app.schemas.user import (
    RoleCreate, RoleUpdate, RoleResponse,
    PermissionCreate, PermissionUpdate, PermissionResponse,
    UserResponse, UserUpdate
)
from app.schemas.communication import (
    EmailTemplateCreate, EmailTemplateUpdate, EmailTemplateResponse
)
from app.schemas.base import PaginatedResponse

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_password_fresh)])

# Role Management
@router.get("/roles", response_model=PaginatedResponse[RoleResponse])
async def get_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get all roles with pagination and filtering."""
    query = db.query(Role)
    
    if search:
        query = query.filter(
            or_(
                Role.name.ilike(f"%{search}%"),
                Role.description.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.filter(Role.is_active == is_active)
    
    total = query.count()
    roles = query.offset(skip).limit(limit).all()
    
    return PaginatedResponse(
        items=roles,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )

@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new role."""
    # Check if role name already exists
    existing_role = db.query(Role).filter(Role.name == role_data.name).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists"
        )
    
    role = Role(**role_data.dict(), created_by=current_user.id)
    db.add(role)
    db.commit()
    db.refresh(role)
    
    return role

@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get a specific role by ID."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return role

@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a role."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Check if new name conflicts with existing role
    if role_data.name and role_data.name != role.name:
        existing_role = db.query(Role).filter(
            and_(Role.name == role_data.name, Role.id != role_id)
        ).first()
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role with this name already exists"
            )
    
    update_data = role_data.dict(exclude_unset=True)
    update_data['updated_by'] = current_user.id
    
    for field, value in update_data.items():
        setattr(role, field, value)
    
    db.commit()
    db.refresh(role)
    
    return role

@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a role (soft delete)."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Check if role is assigned to any users
    users_with_role = db.query(User).filter(User.roles.contains(role)).first()
    if users_with_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete role that is assigned to users"
        )
    
    role.soft_delete()
    db.commit()

# Permission Management
@router.get("/permissions", response_model=PaginatedResponse[PermissionResponse])
async def get_permissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    resource: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get all permissions with pagination and filtering."""
    query = db.query(Permission)
    
    if search:
        query = query.filter(
            or_(
                Permission.name.ilike(f"%{search}%"),
                Permission.description.ilike(f"%{search}%")
            )
        )
    
    if resource:
        query = query.filter(Permission.resource == resource)
    
    total = query.count()
    permissions = query.offset(skip).limit(limit).all()
    
    return PaginatedResponse(
        items=permissions,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )

@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    permission_data: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new permission."""
    # Check if permission already exists
    existing_permission = db.query(Permission).filter(
        and_(
            Permission.name == permission_data.name,
            Permission.resource == permission_data.resource
        )
    ).first()
    if existing_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission with this name and resource already exists"
        )
    
    permission = Permission(**permission_data.dict(), created_by=current_user.id)
    db.add(permission)
    db.commit()
    db.refresh(permission)
    
    return permission

@router.put("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: int,
    permission_data: PermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a permission."""
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    update_data = permission_data.dict(exclude_unset=True)
    update_data['updated_by'] = current_user.id
    
    for field, value in update_data.items():
        setattr(permission, field, value)
    
    db.commit()
    db.refresh(permission)
    
    return permission

@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a permission (soft delete)."""
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    permission.soft_delete()
    db.commit()

# User Management
@router.get("/users", response_model=PaginatedResponse[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    role_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get all users with pagination and filtering."""
    query = db.query(User)
    
    if search:
        query = query.filter(
            or_(
                User.email.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if role_id:
        role = db.query(Role).filter(Role.id == role_id).first()
        if role:
            query = query.filter(User.roles.contains(role))
    
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    
    return PaginatedResponse(
        items=users,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    update_data = user_data.dict(exclude_unset=True)
    update_data['updated_by'] = current_user.id
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user

# --- Password admin ops (set temporary password) ---
from pydantic import BaseModel, EmailStr
from app.api.routers.auth import get_password_hash  # reuse same hashing

class SetTempPasswordIn(BaseModel):
    email: EmailStr
    temp_password: str

@router.post("/users/set-temp-password", status_code=status.HTTP_200_OK)
async def admin_set_temp_password(
    body: SetTempPasswordIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin sets a temporary password; user must change on next login.

    We use preferences["must_change_password"] flag to enforce freshness.
    """
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Set temp password
    user.hashed_password = get_password_hash(body.temp_password)
    prefs = dict(user.preferences or {})
    prefs["must_change_password"] = True
    user.preferences = prefs
    db.commit()
    return {"ok": True}


# --- Admin password reset request (issues reset token; return for dev/testing) ---
class ResetRequestIn(BaseModel):
    email: EmailStr
    reason: Optional[str] = None

class ResetRequestOut(BaseModel):
    reset_token: str

@router.post("/users/password-reset/request", response_model=ResetRequestOut)
async def admin_password_reset_request(
    body: ResetRequestIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    from uuid import uuid4
    from app.models.user import PasswordReset
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    jti = uuid4().hex
    pr = PasswordReset(
        email=body.email,
        jti=jti,
        expires_at=datetime.utcnow() + timedelta(minutes=60),
        requested_by_user_id=current_user.id,
        reason=body.reason,
    )
    db.add(pr)
    db.commit()
    # Build JWT reset token (type=reset)
    from jose import jwt
    token = jwt.encode({"sub": body.email, "type": "reset", "jti": jti, "exp": datetime.utcnow() + timedelta(minutes=60)}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return ResetRequestOut(reset_token=token)

@router.post("/users/{user_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Deactivate a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user.is_active = False
    user.updated_by = current_user.id
    db.commit()

@router.post("/users/{user_id}/activate", status_code=status.HTTP_204_NO_CONTENT)
async def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Activate a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    user.updated_by = current_user.id
    db.commit()

# Email Template Management
@router.get("/email-templates", response_model=PaginatedResponse[EmailTemplateResponse])
async def get_email_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    template_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get all email templates with pagination and filtering."""
    query = db.query(EmailTemplate)
    
    if search:
        query = query.filter(
            or_(
                EmailTemplate.name.ilike(f"%{search}%"),
                EmailTemplate.subject.ilike(f"%{search}%")
            )
        )
    
    if template_type:
        query = query.filter(EmailTemplate.template_type == template_type)
    
    if is_active is not None:
        query = query.filter(EmailTemplate.is_active == is_active)
    
    total = query.count()
    templates = query.offset(skip).limit(limit).all()
    
    return PaginatedResponse(
        items=templates,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )

@router.post("/email-templates", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_email_template(
    template_data: EmailTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new email template."""
    # Check if template name already exists
    existing_template = db.query(EmailTemplate).filter(
        EmailTemplate.name == template_data.name
    ).first()
    if existing_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email template with this name already exists"
        )
    
    template = EmailTemplate(**template_data.dict(), created_by=current_user.id)
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return template

@router.get("/email-templates/{template_id}", response_model=EmailTemplateResponse)
async def get_email_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get a specific email template by ID."""
    template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found"
        )
    return template

@router.put("/email-templates/{template_id}", response_model=EmailTemplateResponse)
async def update_email_template(
    template_id: int,
    template_data: EmailTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update an email template."""
    template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found"
        )
    
    # Check if new name conflicts with existing template
    if template_data.name and template_data.name != template.name:
        existing_template = db.query(EmailTemplate).filter(
            and_(EmailTemplate.name == template_data.name, EmailTemplate.id != template_id)
        ).first()
        if existing_template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email template with this name already exists"
            )
    
    update_data = template_data.dict(exclude_unset=True)
    update_data['updated_by'] = current_user.id
    
    for field, value in update_data.items():
        setattr(template, field, value)
    
    db.commit()
    db.refresh(template)
    
    return template

@router.delete("/email-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete an email template (soft delete)."""
    template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found"
        )
    
    template.soft_delete()
    db.commit()

@router.post("/email-templates/{template_id}/duplicate", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_email_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Duplicate an email template."""
    template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found"
        )
    
    # Create a copy with modified name
    new_template = EmailTemplate(
        name=f"{template.name} (Copy)",
        subject=template.subject,
        body_text=template.body_text,
        body_html=template.body_html,
        template_type=template.template_type,
        variables=template.variables,
        description=template.description,
        is_active=False,  # Start as inactive
        created_by=current_user.id
    )
    
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    
    return new_template

# ---------------------------------------------------------------------------
# Recruiter Directory & Candidate Reassignment (New)
# ---------------------------------------------------------------------------
from app.models.recruiter_directory import RecruiterDirectory
from app.models.candidate_simple import CandidateSimple
from app.models.recruiter_candidate import (
    RecruiterCandidateProfile, RecruiterCandidateActivity, RecruiterCandidateNote,
    RecruiterCandidateDocument, RecruiterCandidateCommunication, RecruiterCandidateInterview
)
from app.schemas.recruiter_directory import (
    RecruiterDirectoryCreate, RecruiterDirectoryUpdate, RecruiterDirectoryResponse, RecruiterDirectoryList
)
from pydantic import BaseModel

@router.post("/recruiters", response_model=RecruiterDirectoryResponse)
def create_recruiter_directory(payload: RecruiterDirectoryCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    existing = db.query(RecruiterDirectory).filter(RecruiterDirectory.recruiter_identifier == payload.recruiter_identifier).first()
    if existing:
        raise HTTPException(status_code=400, detail="Recruiter identifier already exists")
    obj = RecruiterDirectory(recruiter_identifier=payload.recruiter_identifier.strip(), display_name=payload.display_name.strip())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return RecruiterDirectoryResponse.model_validate(obj)

@router.get("/recruiters", response_model=RecruiterDirectoryList)
def list_recruiter_directory(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    q = db.query(RecruiterDirectory).order_by(RecruiterDirectory.display_name.asc())
    rows = q.all()
    return RecruiterDirectoryList(items=[RecruiterDirectoryResponse.model_validate(r) for r in rows], total=len(rows))

@router.put("/recruiters/{recruiter_identifier}", response_model=RecruiterDirectoryResponse)
def update_recruiter_directory(recruiter_identifier: str, payload: RecruiterDirectoryUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    obj = db.query(RecruiterDirectory).filter(RecruiterDirectory.recruiter_identifier == recruiter_identifier).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Recruiter directory entry not found")
    obj.display_name = payload.display_name.strip()
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return RecruiterDirectoryResponse.model_validate(obj)

class CandidateReassignmentRequest(BaseModel):
    candidate_ids: list[int]
    new_recruiter_identifier: str

@router.post("/recruiters/reassign")
def reassign_candidates(payload: CandidateReassignmentRequest, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    target = payload.new_recruiter_identifier.strip()
    if not target:
        raise HTTPException(status_code=400, detail="New recruiter identifier required")
    cands = db.query(CandidateSimple).filter(CandidateSimple.id.in_(payload.candidate_ids)).all()
    if len(cands) != len(payload.candidate_ids):
        missing = set(payload.candidate_ids) - {c.id for c in cands}
        raise HTTPException(status_code=404, detail=f"Missing candidates: {sorted(missing)}")
    for cand in cands:
        if cand.recruiter_identifier == target:
            continue
        cand.recruiter_identifier = target
        db.query(RecruiterCandidateProfile).filter(RecruiterCandidateProfile.candidate_id == cand.id).update({RecruiterCandidateProfile.recruiter_identifier: target})
        db.query(RecruiterCandidateActivity).filter(RecruiterCandidateActivity.candidate_id == cand.id).update({RecruiterCandidateActivity.recruiter_identifier: target})
        db.query(RecruiterCandidateNote).filter(RecruiterCandidateNote.candidate_id == cand.id).update({RecruiterCandidateNote.recruiter_identifier: target})
        db.query(RecruiterCandidateDocument).filter(RecruiterCandidateDocument.candidate_id == cand.id).update({RecruiterCandidateDocument.recruiter_identifier: target})
        db.query(RecruiterCandidateCommunication).filter(RecruiterCandidateCommunication.candidate_id == cand.id).update({RecruiterCandidateCommunication.recruiter_identifier: target})
        db.query(RecruiterCandidateInterview).filter(RecruiterCandidateInterview.candidate_id == cand.id).update({RecruiterCandidateInterview.recruiter_identifier: target})
    db.commit()
    return {"updated": len(cands), "new_recruiter_identifier": target}