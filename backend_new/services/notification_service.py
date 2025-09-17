from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.communication import Notification


class NotificationService:
    def list_for_user(
        self,
        db: Session,
        user_id: int,
        read: Optional[bool] = None,
        dismissed: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
        order_desc: bool = True,
    ) -> Tuple[List[Notification], int]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if read is not None:
            stmt = stmt.where(Notification.is_read == read)
        # By default exclude dismissed unless explicitly requested
        if dismissed is None:
            stmt = stmt.where(Notification.is_dismissed == False)
        else:
            stmt = stmt.where(Notification.is_dismissed == dismissed)
        if order_desc:
            stmt = stmt.order_by(Notification.created_at.desc())
        else:
            stmt = stmt.order_by(Notification.created_at.asc())
        items = db.execute(stmt.offset(skip).limit(limit)).scalars().all()
        # Count total with same conditions (approx for SQLite is fine)
        count_stmt = select(func.count(Notification.id)).where(Notification.user_id == user_id)
        if read is not None:
            count_stmt = count_stmt.where(Notification.is_read == read)
        if dismissed is None:
            count_stmt = count_stmt.where(Notification.is_dismissed == False)
        else:
            count_stmt = count_stmt.where(Notification.is_dismissed == dismissed)
        total = db.scalar(count_stmt) or 0
        return items, total

    def mark_read(self, db: Session, user_id: int, notification_id: int) -> Notification:
        notif = db.get(Notification, notification_id)
        if not notif or notif.user_id != user_id:
            raise ValueError("Notification not found")
        if not notif.is_read:
            notif.mark_as_read()
            db.add(notif)
            db.commit()
            db.refresh(notif)
        return notif

    def dismiss(self, db: Session, user_id: int, notification_id: int) -> Notification:
        notif = db.get(Notification, notification_id)
        if not notif or notif.user_id != user_id:
            raise ValueError("Notification not found")
        if not notif.is_dismissed:
            notif.dismiss()
            db.add(notif)
            db.commit()
            db.refresh(notif)
        return notif

    def unread_count(self, db: Session, user_id: int) -> int:
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
            Notification.is_dismissed == False,  # noqa: E712
        )
        return int(db.scalar(stmt) or 0)

    def mark_all_read(self, db: Session, user_id: int) -> int:
        # Update all non-read, non-dismissed
        q = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
            Notification.is_dismissed == False,  # noqa: E712
        )
        updated = q.update({Notification.is_read: True})
        db.commit()
        return int(updated or 0)

    def delete(self, db: Session, user_id: int, notification_id: int) -> None:
        notif = db.get(Notification, notification_id)
        if not notif or notif.user_id != user_id:
            raise ValueError("Notification not found")
        db.delete(notif)
        db.commit()
