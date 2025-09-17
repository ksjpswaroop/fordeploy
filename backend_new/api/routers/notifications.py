from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.permissions import get_current_user, UserContext, require_permission, Permission
from app.schemas.notification_api import NotificationOut
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.api.utils.pagination import build_pagination_meta
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/notifications", tags=["notifications"],
                   responses={404: {"description": "Not found"}})


def get_service() -> NotificationService:
    return NotificationService()


@router.get("/", response_model=PaginatedResponse[NotificationOut], summary="List notifications", description="Paginated list of notifications for the current user. Excludes dismissed by default.")
@require_permission(Permission.NOTIFICATION_READ)
async def list_notifications(
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
    read: Optional[bool] = Query(None),
    dismissed: Optional[bool] = Query(None),
    skip: int = 0,
    limit: int = 50,
    order: str = Query("desc", pattern="^(asc|desc)$"),
):
    items, total = service.list_for_user(
        db,
        user_id=int(current_user.user_id),
        read=read,
        dismissed=dismissed,
        skip=skip,
        limit=limit,
        order_desc=(order == "desc"),
    )
    meta = build_pagination_meta(total=total, skip=skip, limit=limit)
    return PaginatedResponse[NotificationOut](data=items, meta=meta)


@router.patch("/{notification_id}/read", response_model=NotificationOut, summary="Mark notification as read")
@require_permission(Permission.NOTIFICATION_UPDATE)
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
):
    try:
        return service.mark_read(db, user_id=int(current_user.user_id), notification_id=notification_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")


@router.patch("/{notification_id}/dismiss", response_model=NotificationOut, summary="Dismiss notification")
@require_permission(Permission.NOTIFICATION_UPDATE)
async def dismiss_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
):
    try:
        return service.dismiss(db, user_id=int(current_user.user_id), notification_id=notification_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")


@router.get("/unread-count", response_model=dict, summary="Get unread notification count")
@require_permission(Permission.NOTIFICATION_READ)
async def unread_count(
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
):
    count = service.unread_count(db, user_id=int(current_user.user_id))
    return {"unread": count}


@router.put("/mark-all-read", response_model=SuccessResponse, summary="Mark all notifications as read")
@require_permission(Permission.NOTIFICATION_UPDATE)
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
):
    updated = service.mark_all_read(db, user_id=int(current_user.user_id))
    return SuccessResponse(success=True, message=f"Marked {updated} notifications as read")


@router.delete("/{notification_id}", response_model=SuccessResponse, summary="Delete a notification")
@require_permission(Permission.NOTIFICATION_UPDATE)
async def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    service: NotificationService = Depends(get_service),
):
    try:
        service.delete(db, user_id=int(current_user.user_id), notification_id=notification_id)
        return SuccessResponse(success=True, message="Notification deleted")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
