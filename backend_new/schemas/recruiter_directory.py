from pydantic import BaseModel, field_validator
from typing import Optional

class RecruiterDirectoryCreate(BaseModel):
    recruiter_identifier: str
    display_name: str

    @field_validator("recruiter_identifier", "display_name")
    @classmethod
    def not_blank(cls, v: str):
        if not v or not v.strip():
            raise ValueError("Must not be blank")
        return v.strip()

class RecruiterDirectoryUpdate(BaseModel):
    display_name: str

    @field_validator("display_name")
    @classmethod
    def not_blank(cls, v: str):
        if not v or not v.strip():
            raise ValueError("Must not be blank")
        return v.strip()

class RecruiterDirectoryResponse(BaseModel):
    id: int
    recruiter_identifier: str
    display_name: str

    class Config:
        from_attributes = True

class RecruiterDirectoryList(BaseModel):
    items: list[RecruiterDirectoryResponse]
    total: int
