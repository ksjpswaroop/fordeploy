from pydantic import BaseModel, field_validator
from typing import List


class CandidateSimpleCreate(BaseModel):
    # Only the candidate's name is required in the body; recruiter comes from the path
    name: str

    @field_validator("name")
    @classmethod
    def not_empty(cls, v: str):
        if not v or not v.strip():
            raise ValueError("Must not be empty")
        return v.strip()


class CandidateSimpleResponse(BaseModel):
    id: int
    recruiter_identifier: str
    name: str

    class Config:
        from_attributes = True


class CandidateSimpleList(BaseModel):
    items: List[CandidateSimpleResponse]
    total: int
