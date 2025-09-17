from sqlalchemy import Column, String, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from .base import BaseModel


class CandidateSimple(BaseModel):
    """Lightweight candidate name list tied to a recruiter.

    Separate from full User accounts; quick freeform list.
    """
    __tablename__ = "recruiter_candidate_names"
    __table_args__ = (
        UniqueConstraint("recruiter_identifier", "name", name="uq_recruiter_candidate_name"),
    )

    recruiter_identifier = Column(String(255), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):  # pragma: no cover
        return f"<CandidateSimple(id={self.id}, recruiter='{self.recruiter_identifier}', name='{self.name}')>"
