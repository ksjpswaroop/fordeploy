from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy import JSON, String
from datetime import datetime
from .base import BaseModel, AuditMixin, MetadataMixin
from ..schemas.base import ApplicationStatus

class Application(BaseModel, AuditMixin, MetadataMixin):
    """Application model"""
    __tablename__ = 'applications'
    
    # Foreign keys
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    recruiter_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    
    # Application status and tracking
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.SUBMITTED, nullable=False, index=True)
    previous_status = Column(SQLEnum(ApplicationStatus), nullable=True)
    status_changed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    status_changed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Application source
    source = Column(String(100), nullable=True)  # website, linkedin, referral, etc.
    referrer_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # If referred by someone
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    
    # Candidate information at time of application
    candidate_name = Column(String(200), nullable=False)
    candidate_email = Column(String(255), nullable=False)
    candidate_phone = Column(String(20), nullable=True)
    candidate_location = Column(String(200), nullable=True)
    
    # Resume and documents
    resume_file_id = Column(Integer, ForeignKey('file_uploads.id'), nullable=True)
    cover_letter = Column(Text, nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    
    # Screening questions responses
    screening_responses = Column(JSON, nullable=True, default={})  # Question ID -> Response
    
    # Salary expectations
    expected_salary_min = Column(Numeric(12, 2), nullable=True)
    expected_salary_max = Column(Numeric(12, 2), nullable=True)
    salary_currency = Column(String(3), default='USD', nullable=False)
    salary_negotiable = Column(Boolean, default=True, nullable=False)
    
    # Availability
    available_start_date = Column(DateTime, nullable=True)
    notice_period_days = Column(Integer, nullable=True)
    
    # Preferences
    work_authorization = Column(String(100), nullable=True)  # citizen, visa, etc.
    willing_to_relocate = Column(Boolean, default=False, nullable=False)
    remote_work_preference = Column(String(50), nullable=True)  # remote, hybrid, onsite
    
    # Assessment and scoring
    overall_score = Column(Numeric(5, 2), nullable=True)  # 0-100 score
    technical_score = Column(Numeric(5, 2), nullable=True)
    cultural_fit_score = Column(Numeric(5, 2), nullable=True)
    experience_match_score = Column(Numeric(5, 2), nullable=True)
    
    # AI/ML scores
    ai_resume_score = Column(Numeric(5, 2), nullable=True)
    ai_match_score = Column(Numeric(5, 2), nullable=True)
    ai_keywords_matched = Column(JSON, nullable=True)  # Store as JSON array
    
    # Flags and markers
    is_starred = Column(Boolean, default=False, nullable=False)
    is_flagged = Column(Boolean, default=False, nullable=False)
    flag_reason = Column(String(200), nullable=True)
    
    # Communication tracking
    last_contact_date = Column(DateTime(timezone=True), nullable=True)
    contact_count = Column(Integer, default=0, nullable=False)
    
    # Rejection information
    rejection_reason = Column(String(200), nullable=True)
    rejection_feedback = Column(Text, nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Offer information
    offer_extended_at = Column(DateTime(timezone=True), nullable=True)
    offer_expires_at = Column(DateTime(timezone=True), nullable=True)
    offer_accepted_at = Column(DateTime(timezone=True), nullable=True)
    offer_declined_at = Column(DateTime(timezone=True), nullable=True)
    offer_details = Column(JSON, nullable=True, default={})
    
    # Onboarding
    onboarding_started_at = Column(DateTime(timezone=True), nullable=True)
    onboarding_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Analytics and tracking
    time_in_pipeline_hours = Column(Integer, nullable=True)
    application_completion_time_seconds = Column(Integer, nullable=True)
    
    # External integrations
    external_application_id = Column(String(100), nullable=True)
    ats_sync_status = Column(String(50), nullable=True)
    last_ats_sync = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    job = relationship('Job', back_populates='applications')
    candidate = relationship('User', foreign_keys=[candidate_id], back_populates='applications')
    recruiter = relationship('User', foreign_keys=[recruiter_id])
    referrer = relationship('User', foreign_keys=[referrer_id])
    resume_file = relationship('FileUpload', foreign_keys=[resume_file_id])
    
    # Related entities
    interviews = relationship('Interview', back_populates='application', cascade='all, delete-orphan')
    assessments = relationship('Assessment', back_populates='application', cascade='all, delete-orphan')
    notes = relationship('ApplicationNote', back_populates='application', cascade='all, delete-orphan')
    status_history = relationship('ApplicationStatusHistory', back_populates='application', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Application(id={self.id}, job_id={self.job_id}, candidate='{self.candidate_name}', status='{self.status}')>"
    
    @property
    def days_in_pipeline(self):
        """Calculate days since application was submitted"""
        return (datetime.utcnow() - self.created_at).days
    
    @property
    def is_active(self):
        """Check if application is in an active status"""
        # NOTE: The enum currently only defines: SUBMITTED, APPLIED, SCREENING,
        # INTERVIEW_SCHEDULED, INTERVIEWED, OFFER_EXTENDED, HIRED, REJECTED, WITHDRAWN.
        # The previous implementation referenced members that do not exist
        # (UNDER_REVIEW, PHONE_SCREEN, TECHNICAL_INTERVIEW, FINAL_INTERVIEW, REFERENCE_CHECK, BACKGROUND_CHECK)
        # causing AttributeError at runtime during serialization. We treat any
        # non-terminal status as active. Terminal (closed) statuses are: HIRED, REJECTED, WITHDRAWN.
        closed = {
            ApplicationStatus.HIRED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
        return self.status not in closed
    
    @property
    def is_closed(self):
        """Check if application is in a closed status"""
        # OFFER_DECLINED isn't part of the enum; mirror logic above.
        return self.status in {
            ApplicationStatus.HIRED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    
    def update_status(self, new_status: ApplicationStatus, changed_by: int = None, reason: str = None):
        """Update application status with history tracking"""
        if self.status != new_status:
            # Create status history entry
            status_history = ApplicationStatusHistory(
                application_id=self.id,
                from_status=self.status,
                to_status=new_status,
                changed_by=changed_by,
                reason=reason
            )
            
            # Update current status
            self.previous_status = self.status
            self.status = new_status
            self.status_changed_at = datetime.utcnow()
            self.status_changed_by = changed_by
            
            return status_history
        return None
    
    def calculate_match_score(self):
        """Calculate overall match score based on various factors"""
        scores = []
        
        if self.technical_score is not None:
            scores.append(float(self.technical_score))
        if self.cultural_fit_score is not None:
            scores.append(float(self.cultural_fit_score))
        if self.experience_match_score is not None:
            scores.append(float(self.experience_match_score))
        if self.ai_match_score is not None:
            scores.append(float(self.ai_match_score))
        
        if scores:
            self.overall_score = sum(scores) / len(scores)
        
        return self.overall_score

class ApplicationStatusHistory(BaseModel):
    """Application status change history"""
    __tablename__ = 'application_status_history'
    
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, index=True)
    from_status = Column(SQLEnum(ApplicationStatus), nullable=True)
    to_status = Column(SQLEnum(ApplicationStatus), nullable=False)
    changed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    reason = Column(String(500), nullable=True)
    
    # Relationships
    application = relationship('Application', back_populates='status_history')
    changed_by_user = relationship(
        'User',
        foreign_keys='ApplicationStatusHistory.changed_by',
        primaryjoin='User.id==ApplicationStatusHistory.changed_by'
    )
    
    def __repr__(self):
        return f"<ApplicationStatusHistory(id={self.id}, application_id={self.application_id}, {self.from_status} -> {self.to_status})>"

class ApplicationNote(BaseModel, AuditMixin):
    """Notes on applications"""
    __tablename__ = 'application_notes'
    
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, index=True)
    note_type = Column(String(50), default='general', nullable=False)  # general, interview, assessment, etc.
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    
    # Visibility and sharing
    is_private = Column(Boolean, default=False, nullable=False)
    visible_to_candidate = Column(Boolean, default=False, nullable=False)
    
    # Importance and categorization
    priority = Column(String(20), default='normal', nullable=False)  # low, normal, high
    tags = Column(JSON, nullable=True)  # Store as JSON array
    
    # Relationships
    application = relationship('Application', back_populates='notes')
    # Disambiguate author to use created_by from AuditMixin as the FK to users
    author = relationship('User', foreign_keys='ApplicationNote.created_by', primaryjoin='User.id==ApplicationNote.created_by')
    
    def __repr__(self):
        return f"<ApplicationNote(id={self.id}, application_id={self.application_id}, type='{self.note_type}')>"

class Assessment(BaseModel, AuditMixin, MetadataMixin):
    """Assessment/test results for applications"""
    __tablename__ = 'assessments'
    
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, index=True)
    
    # Assessment details
    assessment_type = Column(String(100), nullable=False)  # technical, personality, cognitive, etc.
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Assessment configuration
    max_score = Column(Numeric(10, 2), default=100, nullable=False)
    passing_score = Column(Numeric(10, 2), nullable=True)
    time_limit_minutes = Column(Integer, nullable=True)
    
    # Results
    score = Column(Numeric(10, 2), nullable=True)
    percentage = Column(Numeric(5, 2), nullable=True)
    grade = Column(String(10), nullable=True)  # A, B, C, D, F or Pass/Fail
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    time_taken_minutes = Column(Integer, nullable=True)
    
    # Status
    status = Column(String(50), default='pending', nullable=False)  # pending, in_progress, completed, expired
    
    # Assessment data
    questions = Column(JSON, nullable=True, default=[])  # Assessment questions
    responses = Column(JSON, nullable=True, default=[])  # Candidate responses
    detailed_results = Column(JSON, nullable=True, default={})  # Detailed scoring breakdown
    
    # External assessment integration
    external_assessment_id = Column(String(100), nullable=True)
    external_url = Column(String(500), nullable=True)
    
    # Relationships
    application = relationship('Application', back_populates='assessments')
    
    def __repr__(self):
        return f"<Assessment(id={self.id}, application_id={self.application_id}, type='{self.assessment_type}', score={self.score})>"
    
    @property
    def is_passed(self):
        """Check if assessment was passed"""
        if self.passing_score and self.score:
            return self.score >= self.passing_score
        return None
    
    @property
    def duration_display(self):
        """Get formatted duration"""
        if self.time_taken_minutes:
            hours = self.time_taken_minutes // 60
            minutes = self.time_taken_minutes % 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        return "Not completed"

class ApplicationFeedback(BaseModel, AuditMixin):
    """Feedback on applications from various stakeholders"""
    __tablename__ = 'application_feedback'
    
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, index=True)
    feedback_type = Column(String(50), nullable=False)  # recruiter, hiring_manager, interviewer, etc.
    
    # Feedback content
    rating = Column(Integer, nullable=True)  # 1-5 or 1-10 scale
    comments = Column(Text, nullable=True)
    recommendation = Column(String(50), nullable=True)  # hire, reject, maybe, interview
    
    # Structured feedback
    criteria_scores = Column(JSON, nullable=True, default={})  # {"technical": 8, "communication": 7}
    strengths = Column(JSON, nullable=True)  # Store as JSON array
    weaknesses = Column(JSON, nullable=True)  # Store as JSON array
    
    # Visibility
    is_confidential = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    application = relationship('Application')
    reviewer = relationship('User', foreign_keys='ApplicationFeedback.created_by', primaryjoin='User.id==ApplicationFeedback.created_by')
    
    def __repr__(self):
        return f"<ApplicationFeedback(id={self.id}, application_id={self.application_id}, type='{self.feedback_type}', rating={self.rating})>"