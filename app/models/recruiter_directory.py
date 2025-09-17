from sqlalchemy import Column, String, UniqueConstraint
from .base import BaseModel

class RecruiterDirectory(BaseModel):
    """Directory mapping recruiter identifier (email) -> display name.
    Admin managed. Identifier aligns with recruiter_identifier used in candidate tables.
    """
    __tablename__ = "recruiter_directory"
    __table_args__ = (
        UniqueConstraint("recruiter_identifier", name="uq_recruiter_dir_identifier"),
    )

    recruiter_identifier = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RecruiterDirectory(id={self.id}, recruiter_identifier={self.recruiter_identifier}, display_name={self.display_name})>"
