from __future__ import annotations
from datetime import datetime
import hashlib
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import BaseModel, AuditMixin, MetadataMixin


class ScrapedJob(BaseModel, AuditMixin, MetadataMixin):
    __tablename__ = "scraped_jobs"

    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)
    job_id_ext = Column(String(200), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True, index=True)
    location = Column(String(255), nullable=True, index=True)
    url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    hash = Column(String(64), nullable=False, index=True, unique=False)
    # Enrichment
    recruiter_name = Column(String(255), nullable=True, index=True)
    recruiter_email = Column(String(255), nullable=True, index=True)
    enriched_at = Column(DateTime, nullable=True)
    # Generation
    cover_letter = Column(Text, nullable=True)
    resume_custom = Column(Text, nullable=True)
    generated_at = Column(DateTime, nullable=True)

    run = relationship("PipelineRun")

    @staticmethod
    def compute_hash(source: str, title: str, company: str | None, location: str | None):
        base = f"{source}|{title}|{company or ''}|{location or ''}".lower()
        return hashlib.sha256(base.encode()).hexdigest()

Index("ix_scraped_jobs_run_source", ScrapedJob.run_id, ScrapedJob.source)
Index("ix_scraped_jobs_company_title", ScrapedJob.company, ScrapedJob.title)

__all__ = ["ScrapedJob"]
