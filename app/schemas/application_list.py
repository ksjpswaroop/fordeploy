"""Lightweight application list item schema for listing endpoints (recruiter & candidate views)."""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ApplicationListItem(BaseModel):
    """Flattened application record for list views.

    This avoids the heavier candidate.JobApplicationResponse requirements
    (job_title/company_name fields that aren't always stored) and keeps
    only fields we can reliably source from the ORM Application + Job relation.
    """

    id: int
    job_id: int
    job_title: Optional[str] = None
    candidate_id: int
    candidate_name: str
    candidate_email: str
    status: str
    source: Optional[str] = None
    applied_at: datetime
    last_updated: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
