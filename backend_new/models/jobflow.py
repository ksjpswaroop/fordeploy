from __future__ import annotations

"""Job flow specific models: Company, Recruiter, Email, Asset.

These are purpose-built for the automated sourcing pipeline and kept
separate from the broader ATS-style models already present to avoid
namespace collisions and unintended coupling.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Boolean,
    Numeric,
    Index,
)
from sqlalchemy.orm import relationship

from .base import BaseModel, AuditMixin, MetadataMixin


class Company(BaseModel, AuditMixin, MetadataMixin):
    __tablename__ = "companies"

    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=True, unique=True, index=True)
    linkedin_url = Column(String(500), nullable=True)
    last_enriched_at = Column(DateTime, nullable=True)

    # Relationships
    recruiters = relationship("Recruiter", back_populates="company", cascade="all, delete-orphan")
    jobs = relationship("Job", primaryjoin="Company.name==foreign(Job.summary)", viewonly=True)

    def mark_enriched(self):
        self.last_enriched_at = datetime.utcnow()


class Recruiter(BaseModel, AuditMixin, MetadataMixin):
    __tablename__ = "recruiters"

    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    email = Column(String(320), nullable=True, index=True)
    source = Column(String(50), nullable=True)
    confidence = Column(Numeric(5, 2), nullable=True)

    company = relationship("Company", back_populates="recruiters")


class EmailStatus(str, Enum):
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    SPAM = "spam"
    FAILED = "failed"
    REPLIED = "replied"


class Email(BaseModel, AuditMixin, MetadataMixin):
    __tablename__ = "emails"

    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)
    to_email = Column(String(320), nullable=False, index=True)
    to_name = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text, nullable=True)
    status = Column(String(50), default=EmailStatus.QUEUED, nullable=False, index=True)
    sg_message_id = Column(String(255), nullable=True, unique=True)
    opens = Column(Integer, default=0, nullable=False)
    clicks = Column(Integer, default=0, nullable=False)
    replied = Column(Boolean, default=False, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    last_event_at = Column(DateTime, nullable=True)

    run = relationship("PipelineRun")
    job = relationship("Job")

    def mark_event(self, event: str):
        now = datetime.utcnow()
        if event == "delivered":
            self.status = EmailStatus.DELIVERED
        elif event == "open":
            self.status = EmailStatus.OPENED
            self.opens += 1
        elif event == "click":
            self.status = EmailStatus.CLICKED
            self.clicks += 1
        elif event == "bounce":
            self.status = EmailStatus.BOUNCED
        elif event == "spamreport":
            self.status = EmailStatus.SPAM
        self.last_event_at = now


class AssetKind(str, Enum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"


class Asset(BaseModel, AuditMixin, MetadataMixin):
    __tablename__ = "assets"

    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)
    path = Column(String(500), nullable=False)
    kind = Column(String(50), nullable=False, index=True)
    llm_model = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)

    run = relationship("PipelineRun")
    job = relationship("Job")


# Helpful composite indexes
Index("ix_emails_run_job", Email.run_id, Email.job_id)
Index("ix_assets_run_job", Asset.run_id, Asset.job_id)

__all__ = [
    "Company",
    "Recruiter",
    "Email",
    "EmailStatus",
    "Asset",
    "AssetKind",
]
