"""Schema for creating a minimal real Application record (recruiter-driven quick add).

This is intentionally lightweight to enable fast manual data entry from the UI
without requiring the full candidate account + resume flow yet. It stores the
candidate display fields directly on the Application row (already supported by
the model) so that the recruiter applications list immediately reflects newly
added data.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ApplicationCreateInput(BaseModel):
    job_id: int = Field(..., description="Existing Job numeric ID")
    candidate_name: str = Field(..., min_length=1, max_length=200)
    candidate_email: str = Field(..., min_length=3, max_length=255)
    candidate_id: int = Field(1, description="Temporary candidate user id reference (dev seed)")
    source: Optional[str] = Field(None, max_length=100, description="Source tag e.g. referral, manual, linkedin")
