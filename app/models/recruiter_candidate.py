from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class RecruiterCandidateProfile(BaseModel):
    """Extended profile for a recruiter-managed lightweight candidate (CandidateSimple).

    Stores contact and misc metadata. Separate from real User accounts.
    """
    __tablename__ = "recruiter_candidate_profiles"

    candidate_id = Column(Integer, ForeignKey('recruiter_candidate_names.id', ondelete='CASCADE'), nullable=False, index=True, unique=True)
    recruiter_identifier = Column(String(255), index=True, nullable=False)

    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    title = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    last_activity_at = Column(DateTime(timezone=True), nullable=True)

    candidate = relationship('CandidateSimple')

    def __repr__(self):  # pragma: no cover
        return f"<RecruiterCandidateProfile(id={self.id}, candidate_id={self.candidate_id}, email='{self.email}')>"


class RecruiterCandidateActivity(BaseModel):
    """Timeline activity for a recruiter-managed candidate.

    Captures actions taken in dashboard: runs, generations, emails, notes, uploads, etc.
    """
    __tablename__ = "recruiter_candidate_activities"

    candidate_id = Column(Integer, ForeignKey('recruiter_candidate_names.id', ondelete='CASCADE'), nullable=False, index=True)
    recruiter_identifier = Column(String(255), index=True, nullable=False)

    type = Column(String(100), nullable=False)  # run_started, run_completed, doc_generated, email_sent, note, upload, custom
    title = Column(String(255), nullable=True)
    job_id = Column(Integer, nullable=True, index=True)
    run_id = Column(Integer, nullable=True, index=True)
    details = Column(Text, nullable=True)  # JSON string

    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    candidate = relationship('CandidateSimple')

    __table_args__ = (
        Index('ix_recruiter_candidate_activity_key', 'recruiter_identifier', 'candidate_id', 'occurred_at'),
    )

    def __repr__(self):  # pragma: no cover
        return f"<RecruiterCandidateActivity(id={self.id}, candidate_id={self.candidate_id}, type='{self.type}')>"


class RecruiterCandidateNote(BaseModel):
    """Freeform notes per recruiter-managed candidate."""
    __tablename__ = "recruiter_candidate_notes"

    candidate_id = Column(Integer, ForeignKey('recruiter_candidate_names.id', ondelete='CASCADE'), nullable=False, index=True)
    recruiter_identifier = Column(String(255), index=True, nullable=False)

    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    note_type = Column(String(50), nullable=False, default='general')
    is_private = Column(Integer, nullable=False, default=0)  # 0/1 for simplicity
    tags = Column(String(500), nullable=True)  # comma-separated simple tags

    candidate = relationship('CandidateSimple')

    __table_args__ = (
        Index('ix_recruiter_candidate_notes_key', 'recruiter_identifier', 'candidate_id', 'created_at'),
    )

    def __repr__(self):  # pragma: no cover
        return f"<RecruiterCandidateNote(id={self.id}, candidate_id={self.candidate_id}, type='{self.note_type}')>"


class RecruiterCandidateDocument(BaseModel):
    """Simple document metadata for recruiter-managed candidate uploads."""
    __tablename__ = "recruiter_candidate_documents"

    candidate_id = Column(Integer, ForeignKey('recruiter_candidate_names.id', ondelete='CASCADE'), nullable=False, index=True)
    recruiter_identifier = Column(String(255), index=True, nullable=False)

    filename = Column(String(500), nullable=False)
    document_type = Column(String(100), nullable=True)
    storage_path = Column(String(1000), nullable=False)
    mime_type = Column(String(150), nullable=True)
    file_size = Column(Integer, nullable=True)

    candidate = relationship('CandidateSimple')

    __table_args__ = (
        Index('ix_recruiter_candidate_documents_key', 'recruiter_identifier', 'candidate_id', 'created_at'),
    )

    def __repr__(self):  # pragma: no cover
        return f"<RecruiterCandidateDocument(id={self.id}, candidate_id={self.candidate_id}, filename='{self.filename}')>"


class RecruiterCandidateCommunication(BaseModel):
    """Minimal communication log with candidate."""
    __tablename__ = "recruiter_candidate_communications"

    candidate_id = Column(Integer, ForeignKey('recruiter_candidate_names.id', ondelete='CASCADE'), nullable=False, index=True)
    recruiter_identifier = Column(String(255), index=True, nullable=False)

    communication_type = Column(String(50), nullable=False, default='email')  # email, phone, sms, chat
    subject = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default='sent')

    candidate = relationship('CandidateSimple')

    __table_args__ = (
        Index('ix_recruiter_candidate_comms_key', 'recruiter_identifier', 'candidate_id', 'created_at'),
    )

    def __repr__(self):  # pragma: no cover
        return f"<RecruiterCandidateCommunication(id={self.id}, type='{self.communication_type}', status='{self.status}')>"


class RecruiterCandidateInterview(BaseModel):
    """Minimal interview records independent of full Interview model."""
    __tablename__ = "recruiter_candidate_interviews"

    candidate_id = Column(Integer, ForeignKey('recruiter_candidate_names.id', ondelete='CASCADE'), nullable=False, index=True)
    recruiter_identifier = Column(String(255), index=True, nullable=False)

    title = Column(String(255), nullable=False)
    interview_type = Column(String(50), nullable=False, default='phone_screening')
    job_id = Column(Integer, nullable=True, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    location = Column(String(500), nullable=True)
    status = Column(String(50), nullable=False, default='scheduled')

    candidate = relationship('CandidateSimple')

    __table_args__ = (
        Index('ix_recruiter_candidate_interviews_key', 'recruiter_identifier', 'candidate_id', 'scheduled_at'),
    )

    def __repr__(self):  # pragma: no cover
        return f"<RecruiterCandidateInterview(id={self.id}, title='{self.title}', status='{self.status}')>"
