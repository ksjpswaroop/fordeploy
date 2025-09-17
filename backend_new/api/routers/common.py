from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import os
import uuid
import io

from app.core.database import get_db
from app.core.config import settings
from app.api.dependencies import get_current_user
from app.models.user import User, Role
from app.models.job import Job
from app.models.application import Application
from app.models.upload import Document
from app.models.communication import Notification
from app.schemas.upload import FileUploadResponse
from app.schemas.notification import NotificationResponse, NotificationListResponse
from app.schemas.search import SearchRequest, GlobalSearchResponse
from app.schemas.common import HealthResponse, SystemStatsResponse

router = APIRouter(prefix="/common", tags=["common"])

# Health Check
@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint
    """
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "unhealthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        database=db_status,
        redis="healthy",  # Would check Redis connection
        services={
            "api": "healthy",
            "database": db_status,
            "redis": "healthy",
            "email": "healthy"
        }
    )

@router.get("/health/detailed", response_model=SystemStatsResponse)
async def detailed_health_check(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Detailed system health and statistics (admin only)
    """
    user_roles = [role.name for role in current_user.roles]
    if "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Get system statistics
    total_users = db.query(User).count()
    total_jobs = db.query(Job).count()
    total_applications = db.query(Application).count()
    active_jobs = db.query(Job).filter(Job.status == "active").count()
    
    return SystemStatsResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        uptime_seconds=0,  # Would calculate actual uptime
        total_users=total_users,
        total_jobs=total_jobs,
        total_applications=total_applications,
        active_jobs=active_jobs,
        memory_usage_mb=0.0,  # Would get actual memory usage
        cpu_usage_percent=0.0,  # Would get actual CPU usage
        disk_usage_percent=0.0,  # Would get actual disk usage
        database_connections=0,  # Would get actual DB connections
        redis_connections=0  # Would get actual Redis connections
    )

# File Upload
@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    document_type: str = Query(..., description="Type of document (resume, cover_letter, portfolio, etc.)"),
    description: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a file (documents, images, etc.)
    """
    # Optional dependencies loaded lazily
    try:
        import magic  # type: ignore
    except Exception:  # pragma: no cover - optional dep
        magic = None  # type: ignore
    try:
        from PIL import Image  # type: ignore
    except Exception:  # pragma: no cover - optional dep
        Image = None  # type: ignore

    # Validate file size
    if file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes"
        )
    
    # Validate file type
    if file.content_type not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not allowed"
        )
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, unique_filename)
    
    try:
        content = await file.read()
        
        # Validate file content using python-magic when available
        if magic:
            mime_type = magic.from_buffer(content, mime=True)
        else:
            mime_type = file.content_type or "application/octet-stream"
        if mime_type not in settings.ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match declared type"
            )
        
        # For images, validate and potentially resize
        if mime_type.startswith('image/') and Image is not None:
            try:
                image = Image.open(io.BytesIO(content))
                # Resize if too large
                if image.width > 2048 or image.height > 2048:
                    image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                    # Save resized image
                    image.save(file_path, optimize=True, quality=85)
                else:
                    with open(file_path, "wb") as f:
                        f.write(content)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid image file"
                )
        else:
            with open(file_path, "wb") as f:
                f.write(content)
        
        # Create document record
        document = Document(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=len(content),
            mime_type=mime_type,
            document_type=document_type,
            description=description,
            uploaded_by=current_user.id
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return FileUploadResponse(
            id=document.id,
            filename=document.filename,
            original_filename=document.original_filename,
            file_size=document.file_size,
            mime_type=document.mime_type,
            document_type=document.document_type,
            upload_url=f"/api/common/files/{document.id}",
            uploaded_at=document.created_at
        )
        
    except Exception:
        # Clean up file if database operation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed"
        )

@router.get("/files/{file_id}")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download a file by ID
    """
    document = db.query(Document).filter(Document.id == file_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permissions (users can only access their own files, or admin/manager can access all)
    user_roles = [role.name for role in current_user.roles]
    if (document.uploaded_by != current_user.id and 
        not any(role in ["admin", "manager"] for role in user_roles)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    if not os.path.exists(document.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )
    
    from fastapi.responses import FileResponse
    return FileResponse(
        path=document.file_path,
        filename=document.original_filename,
        media_type=document.mime_type
    )

# Notifications
@router.get("/notifications", response_model=NotificationListResponse)
async def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user notifications
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    
    total = query.count()
    notifications = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    
    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(notif) for notif in notifications],
        total=total,
        unread_count=db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False)
        ).count(),
        skip=skip,
        limit=limit
    )

@router.put("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a notification as read
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    db.refresh(notification)
    
    return NotificationResponse.model_validate(notification)

@router.put("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark all notifications as read
    """
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False)
    ).update({
        "is_read": True,
        "read_at": datetime.utcnow()
    })
    db.commit()
    
    return {"message": "All notifications marked as read"}

# Global Search
@router.post("/search", response_model=GlobalSearchResponse)
async def global_search(
    search_request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Global search across jobs, candidates, applications
    """
    results = GlobalSearchResponse(
        query=search_request.query,
        total_results=0,
        jobs=[],
        candidates=[],
        applications=[]
    )
    
    # Search jobs
    if "jobs" in search_request.search_types:
        job_query = db.query(Job).filter(
            Job.title.ilike(f"%{search_request.query}%") |
            Job.description.ilike(f"%{search_request.query}%") |
            Job.requirements.ilike(f"%{search_request.query}%")
        )
        
        if search_request.filters:
            if search_request.filters.get("status"):
                job_query = job_query.filter(Job.status == search_request.filters["status"])
            if search_request.filters.get("location"):
                job_query = job_query.filter(Job.location.ilike(f"%{search_request.filters['location']}%"))
        
        jobs = job_query.limit(search_request.limit).all()
        results.jobs = [{
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "status": job.status,
            "created_at": job.created_at
        } for job in jobs]
    
    # Search candidates (admin/manager/recruiter only)
    user_roles = [role.name for role in current_user.roles]
    if ("candidates" in search_request.search_types and 
        any(role in ["admin", "manager", "recruiter"] for role in user_roles)):
        
        candidate_query = db.query(User).join(User.roles).filter(
            Role.name == "candidate"
        ).filter(
            User.first_name.ilike(f"%{search_request.query}%") |
            User.last_name.ilike(f"%{search_request.query}%") |
            User.email.ilike(f"%{search_request.query}%")
        )
        
        candidates = candidate_query.limit(search_request.limit).all()
        results.candidates = [{
            "id": candidate.id,
            "name": f"{candidate.first_name} {candidate.last_name}",
            "email": candidate.email,
            "created_at": candidate.created_at
        } for candidate in candidates]
    
    # Search applications (based on user role)
    if "applications" in search_request.search_types:
        app_query = db.query(Application)
        
        # Filter based on user role
        if "candidate" in user_roles:
            app_query = app_query.filter(Application.candidate_id == current_user.id)
        elif "recruiter" in user_roles:
            # Recruiters see applications for their jobs
            app_query = app_query.join(Job).filter(Job.recruiter_id == current_user.id)
        # Admin and managers see all applications
        
        applications = app_query.limit(search_request.limit).all()
        results.applications = [{
            "id": app.id,
            "job_title": app.job.title if app.job else "Unknown",
            "candidate_name": f"{app.candidate.first_name} {app.candidate.last_name}" if app.candidate else "Unknown",
            "status": app.status,
            "applied_at": app.created_at
        } for app in applications]
    
    results.total_results = len(results.jobs) + len(results.candidates) + len(results.applications)
    
    return results

# System Information
@router.get("/system/info")
async def get_system_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get system information
    """
    return {
        "app_name": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "features": {
            "file_upload": True,
            "notifications": True,
            "search": True,
            "analytics": True,
            "email": True
        },
        "limits": {
            "max_file_size": settings.MAX_FILE_SIZE,
            "allowed_file_types": settings.ALLOWED_FILE_TYPES,
            "pagination_limit": 100
        }
    }