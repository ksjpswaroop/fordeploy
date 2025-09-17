from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, TypeVar, Generic
from datetime import datetime
from enum import Enum

class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Page size")

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper"""
    items: List[T]
    total: int
    page: int
    size: int
    pages: int

class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str
    data: Optional[dict] = None

class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[dict] = None

# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    PROFILE_MANAGER = "profile_manager"
    JOB_SEEKER = "job_seeker"
    MANAGER = "manager"
    RECRUITER = "recruiter"
    CANDIDATE = "candidate"

class ApplicationStatus(str, Enum):
    SUBMITTED = "submitted"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEWED = "interviewed"
    OFFER_EXTENDED = "offer_extended"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

class InterviewStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"

class InterviewType(str, Enum):
    PHONE = "phone"
    VIDEO = "video"
    IN_PERSON = "in_person"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"

class JobStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class NotificationType(str, Enum):
    APPLICATION = "application"
    INTERVIEW = "interview"
    MESSAGE = "message"
    SYSTEM = "system"
    REMINDER = "reminder"

class DocumentType(str, Enum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    PORTFOLIO = "portfolio"
    CERTIFICATE = "certificate"
    OTHER = "other"

class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class ExperienceLevel(str, Enum):
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"

# Bench Management Enums
class BenchStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SOLD = "sold"
    ARCHIVED = "archived"

class AvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    ENGAGED = "engaged"
    UNAVAILABLE = "unavailable"

class SalesStatus(str, Enum):
    PROSPECT = "prospect"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"

class ClientType(str, Enum):
    DIRECT = "direct"
    VENDOR = "vendor"
    PRIME = "prime"
    SUBCONTRACTOR = "subcontractor"

class ClientStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROSPECT = "prospect"
    BLACKLISTED = "blacklisted"
    PREFERRED = "preferred"

class PaymentTerms(str, Enum):
    NET_15 = "net_15"
    NET_30 = "net_30"
    NET_45 = "net_45"
    NET_60 = "net_60"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"

class WorkAuthorization(str, Enum):
    CITIZEN = "citizen"
    GREEN_CARD = "green_card"
    H1B = "h1b"
    L1 = "l1"
    OPT = "opt"
    CPT = "cpt"
    TN = "tn"
    OTHER = "other"

class RemoteWorkPreference(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    FLEXIBLE = "flexible"