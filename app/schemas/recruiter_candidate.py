from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class RecruiterCandidateProfileCreate(BaseModel):
    recruiter_identifier: str
    candidate_id: int
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class RecruiterCandidateProfileUpdate(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class RecruiterCandidateProfileResponse(BaseModel):
    id: int
    candidate_id: int
    recruiter_identifier: str
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    last_activity_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecruiterCandidateActivityCreate(BaseModel):
    recruiter_identifier: str
    candidate_id: int
    type: str = Field(..., pattern=r"^[a-z0-9_\-]+$")
    title: Optional[str] = None
    job_id: Optional[int] = None
    run_id: Optional[int] = None
    details: Optional[Any] = None


class RecruiterCandidateActivityResponse(BaseModel):
    id: int
    candidate_id: int
    recruiter_identifier: str
    type: str
    title: Optional[str] = None
    job_id: Optional[int] = None
    run_id: Optional[int] = None
    details: Optional[Any] = None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecruiterCandidateActivityList(BaseModel):
    items: List[RecruiterCandidateActivityResponse]
    total: int


# Notes
class RecruiterCandidateNoteCreate(BaseModel):
    recruiter_identifier: str
    candidate_id: int
    title: Optional[str] = None
    content: str
    note_type: str = Field("general", pattern=r"^[a-z0-9_\-]+$")
    is_private: bool = False
    tags: Optional[List[str]] = None


class RecruiterCandidateNoteResponse(BaseModel):
    id: int
    candidate_id: int
    recruiter_identifier: str
    title: Optional[str] = None
    content: str
    note_type: str
    is_private: bool
    tags: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Documents
class RecruiterCandidateDocumentCreate(BaseModel):
    recruiter_identifier: str
    candidate_id: int
    filename: str
    document_type: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None


class RecruiterCandidateDocumentResponse(BaseModel):
    id: int
    candidate_id: int
    recruiter_identifier: str
    filename: str
    document_type: Optional[str] = None
    storage_path: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    download_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Communications
class RecruiterCandidateCommunicationCreate(BaseModel):
    recruiter_identifier: str
    candidate_id: int
    communication_type: str = Field("email", pattern=r"^[a-z_]+$")
    subject: Optional[str] = None
    content: str


class RecruiterCandidateCommunicationResponse(BaseModel):
    id: int
    candidate_id: int
    recruiter_identifier: str
    communication_type: str
    subject: Optional[str] = None
    content: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Interviews
class RecruiterCandidateInterviewCreate(BaseModel):
    recruiter_identifier: str
    candidate_id: int
    title: str
    interview_type: str = Field("phone_screening", pattern=r"^[a-z_]+$")
    job_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None


class RecruiterCandidateInterviewResponse(BaseModel):
    id: int
    candidate_id: int
    recruiter_identifier: str
    title: str
    interview_type: str
    job_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
