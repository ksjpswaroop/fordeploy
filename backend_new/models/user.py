from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Table, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from datetime import datetime
import uuid
from .base import BaseModel, AuditMixin, MetadataMixin
from ..schemas.base import UserRole

# Association table for user roles (many-to-many)
user_roles = Table(
    'user_roles',
    BaseModel.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), default=datetime.utcnow),
    Column('assigned_by', Integer, ForeignKey('users.id')),
    Column('is_active', Boolean, default=True)
)

# Association table for user permissions (many-to-many)
user_permissions = Table(
    'user_permissions',
    BaseModel.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True),
    Column('granted_at', DateTime(timezone=True), default=datetime.utcnow),
    Column('granted_by', Integer, ForeignKey('users.id')),
    Column('is_active', Boolean, default=True)
)

# Association table for role permissions (many-to-many)
role_permissions = Table(
    'role_permissions',
    BaseModel.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), default=datetime.utcnow),
    Column('assigned_by', Integer, ForeignKey('users.id')),
    Column('is_active', Boolean, default=True)
)

class User(BaseModel, AuditMixin, MetadataMixin):
    """User model"""
    __tablename__ = 'users'
    
    # Basic information
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    # Clerk integration fields
    clerk_user_id = Column(String(255), unique=True, index=True, nullable=True)
    clerk_tenant_id = Column(String(255), index=True, nullable=True)
    external_auth_provider = Column(String(50), default='clerk', nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Profile information
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    location = Column(String(200), nullable=True)
    timezone = Column(String(50), default='UTC', nullable=False)
    language = Column(String(10), default='en', nullable=False)
    
    # Professional information
    job_title = Column(String(200), nullable=True)
    department = Column(String(100), nullable=True)
    company = Column(String(200), nullable=True)
    employee_id = Column(String(50), nullable=True)
    
    # Authentication tracking
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Password management
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Email verification
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Settings
    settings = Column(JSON, nullable=True, default={})
    preferences = Column(JSON, nullable=True, default={})
    
    # Relationships
    roles = relationship(
        'Role',
        secondary=user_roles,
        primaryjoin=lambda: User.id == user_roles.c.user_id,
        secondaryjoin=lambda: Role.id == user_roles.c.role_id,
        back_populates='users',
    )
    permissions = relationship(
        'Permission',
        secondary=user_permissions,
        primaryjoin=lambda: User.id == user_permissions.c.user_id,
        secondaryjoin=lambda: Permission.id == user_permissions.c.permission_id,
        back_populates='users',
    )
    
    # User-specific relationships
    created_jobs = relationship(
        'Job',
        primaryjoin="User.id==Job.created_by",
        foreign_keys='Job.created_by',
        back_populates='creator'
    )
    applications = relationship(
        'Application',
        foreign_keys='Application.candidate_id',
        back_populates='candidate'
    )
    interviews_as_interviewer = relationship('Interview', foreign_keys='Interview.interviewer_id', back_populates='interviewer')
    interviews_as_candidate = relationship('Interview', foreign_keys='Interview.candidate_id', back_populates='candidate')
    
    # Bench management relationships
    candidate_bench_profile = relationship('CandidateBench', foreign_keys='CandidateBench.user_id', back_populates='user', uselist=False)
    managed_candidates = relationship('CandidateBench', foreign_keys='CandidateBench.profile_manager_id', back_populates='profile_manager')
    
    # Client management relationships
    managed_clients = relationship('Client', foreign_keys='Client.account_manager_id', back_populates='account_manager')
    sales_clients = relationship('Client', foreign_keys='Client.sales_rep_id', back_populates='sales_rep')
    
    # Communication
    sent_messages = relationship('Message', foreign_keys='Message.sender_id', back_populates='sender')
    received_messages = relationship('Message', foreign_keys='Message.recipient_id', back_populates='recipient')
    # Disambiguate to notifications.user_id only (not created_by/updated_by from AuditMixin)
    notifications = relationship('Notification', back_populates='user', foreign_keys='Notification.user_id')
    communication_preferences = relationship('CommunicationPreference', back_populates='user', uselist=False, foreign_keys='CommunicationPreference.user_id')
    
    # Files and documents
    uploaded_files = relationship(
        'FileUpload',
        back_populates='uploader',
        foreign_keys='FileUpload.uploaded_by'
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', name='{self.first_name} {self.last_name}')>"
    
    @property
    def full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_locked(self):
        """Check if user account is locked"""
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles if role.is_active)
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if user has a specific permission"""
        # Check direct permissions
        if any(perm.name == permission_name for perm in self.permissions if perm.is_active):
            return True
        
        # Check role-based permissions
        for role in self.roles:
            if role.is_active and any(perm.name == permission_name for perm in role.permissions if perm.is_active):
                return True
        
        return False
    
    def get_primary_role(self):
        """Get user's primary role"""
        active_roles = [role for role in self.roles if role.is_active]
        if active_roles:
            # Return the role with highest priority or first one
            return sorted(active_roles, key=lambda r: r.priority or 999)[0]
        return None

class Role(BaseModel, AuditMixin):
    """Role model"""
    __tablename__ = 'roles'
    
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)  # System roles cannot be deleted
    priority = Column(Integer, default=0, nullable=False)  # Higher number = higher priority
    
    # Role settings
    settings = Column(JSON, nullable=True, default={})
    
    # Relationships
    users = relationship(
        'User',
        secondary=user_roles,
        primaryjoin=lambda: Role.id == user_roles.c.role_id,
        secondaryjoin=lambda: User.id == user_roles.c.user_id,
        back_populates='roles',
    )
    permissions = relationship(
        'Permission',
        secondary=role_permissions,
        primaryjoin=lambda: Role.id == role_permissions.c.role_id,
        secondaryjoin=lambda: Permission.id == role_permissions.c.permission_id,
        back_populates='roles',
    )
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if role has a specific permission"""
        return any(perm.name == permission_name for perm in self.permissions if perm.is_active)

class Permission(BaseModel, AuditMixin):
    """Permission model"""
    __tablename__ = 'permissions'
    
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    resource = Column(String(100), nullable=False)  # e.g., 'job', 'application', 'user'
    action = Column(String(50), nullable=False)  # e.g., 'create', 'read', 'update', 'delete'
    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    users = relationship(
        'User',
        secondary=user_permissions,
        primaryjoin=lambda: Permission.id == user_permissions.c.permission_id,
        secondaryjoin=lambda: User.id == user_permissions.c.user_id,
        back_populates='permissions',
    )
    roles = relationship(
        'Role',
        secondary=role_permissions,
        primaryjoin=lambda: Permission.id == role_permissions.c.permission_id,
        secondaryjoin=lambda: Role.id == role_permissions.c.role_id,
        back_populates='permissions',
    )
    
    def __repr__(self):
        return f"<Permission(id={self.id}, name='{self.name}')>"

class UserSession(BaseModel):
    """User session model for tracking active sessions"""
    __tablename__ = 'user_sessions'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True, index=True)
    device_info = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    location = Column(String(200), nullable=True)
    
    # Session management
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship('User')
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id})>"
    
    @property
    def is_expired(self):
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at

class UserProfile(BaseModel, MetadataMixin):
    """Extended user profile model"""
    __tablename__ = 'user_profiles'
    
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False, index=True)
    
    # Personal information
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String(20), nullable=True)
    nationality = Column(String(100), nullable=True)
    marital_status = Column(String(20), nullable=True)
    
    # Contact information
    personal_email = Column(String(255), nullable=True)
    personal_phone = Column(String(20), nullable=True)
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    
    # Address information
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Professional information
    linkedin_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    resume_url = Column(String(500), nullable=True)
    
    # Skills and experience
    skills = Column(JSON, nullable=True, default=[])  # List of skills
    experience_years = Column(Integer, nullable=True)
    current_salary = Column(Integer, nullable=True)
    expected_salary = Column(Integer, nullable=True)
    
    # Preferences
    job_preferences = Column(JSON, nullable=True, default={})
    communication_preferences = Column(JSON, nullable=True, default={})
    
    # Privacy settings
    profile_visibility = Column(String(20), default='private', nullable=False)  # public, private, contacts
    allow_contact = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship('User', backref='profile')
    
    def __repr__(self):
        return f"<UserProfile(id={self.id}, user_id={self.user_id})>"


# --- Auth support tables: Invites and Password Resets ---
class Invite(BaseModel):
    """Admin-issued invite for onboarding without public signup.

    Email + role name + unique code (jti) with expiration and one-time use semantics.
    """
    __tablename__ = 'invites'

    email = Column(String(255), index=True, nullable=False)
    role_name = Column(String(50), nullable=False)
    code_jti = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    __table_args__ = (
        UniqueConstraint('email', 'used_at', name='uniq_open_invite_per_email'),
    )


class PasswordReset(BaseModel):
    """Admin-initiated password reset tokens (short-lived)."""
    __tablename__ = 'password_resets'

    email = Column(String(255), index=True, nullable=False)
    jti = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    requested_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    reason = Column(Text, nullable=True)