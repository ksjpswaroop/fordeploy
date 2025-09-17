from pydantic_settings import BaseSettings
from typing import Optional, List
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Recruitment API"
    APP_VERSION: str = "1.0.0"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database settings
    # Default to SQLite for local dev; override with Postgres (e.g., Supabase) in env
    DATABASE_URL: str = "sqlite:///./recruitment_mvp.db"
    SQLITE_DATABASE_URL: str = "sqlite:///./recruitment_mvp.db"
    # Optional Supabase Postgres connection URL, e.g.:
    # postgresql+psycopg2://<user>:<pass>@<host>:5432/postgres?sslmode=require
    SUPABASE_POSTGRES_URL: Optional[str] = None
    # Supabase Storage (optional)
    SUPABASE_URL: Optional[str] = None  # e.g., https://your-project.supabase.co
    SUPABASE_ANON_KEY: Optional[str] = None  # optional, frontend
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None  # backend-only for storage/server ops
    SUPABASE_STORAGE_BUCKET_UPLOADS: str = "uploads"
    SUPABASE_STORAGE_BUCKET_DOCS: str = "docs"
    
    # Security settings
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Clerk Authentication Configuration (optional in non-production)
    CLERK_SECRET_KEY: Optional[str] = None
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    CLERK_JWT_SECRET: Optional[str] = None
    # Optional base64-encoded variant (for Docker single-line env). If provided, it overrides CLERK_JWT_SECRET.
    CLERK_JWT_SECRET_BASE64: Optional[str] = None
    # Development auth bypass (Bearer token). If set, requests with this token are authenticated without Clerk.
    DEV_BEARER_TOKEN: Optional[str] = None
    # Use numeric-friendly defaults to interoperate with endpoints that cast to int
    DEV_USER_ID: str = "1"
    DEV_USER_EMAIL: str = "dev@example.com"
    DEV_USER_ROLE: str = "manager"  # one of: admin, manager, recruiter, candidate
    DEV_TENANT_ID: str = "1"
    
    # CORS settings (string, comma-separated). Use cors_origins_list property in code.
    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: str = "*"
    
    # File upload settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "uploads"
    ALLOWED_FILE_TYPES: List[str] = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
        "image/gif"
    ]
    
    # Email settings
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    EMAIL_FROM: str = "noreply@recruitment.com"
    EMAIL_FROM_NAME: str = "Recruitment System"
    
    # Redis settings (for caching and sessions)
    REDIS_URL: str = "redis://localhost:6379"
    
    # Pagination settings
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Session settings
    SESSION_TIMEOUT_MINUTES: int = 60
    MAX_SESSIONS_PER_USER: int = 5
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # External API settings
    OPENAI_API_KEY: Optional[str] = None
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    APIFY_TOKEN: Optional[str] = Field(default=None, validation_alias="APIFY_TOKEN")
    APIFY_API_TOKEN: Optional[str] = Field(default=None, validation_alias="APIFY_API_TOKEN")
    APOLLO_API_KEY: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None
    DEMO_SEED_JOBS: bool = False  # when true, seed synthetic jobs if scraping returns zero
    # SendGrid related (optional but required for email stage)
    SENDGRID_FROM_EMAIL: Optional[str] = None
    SENDGRID_FROM_NAME: Optional[str] = None
    SENDGRID_SANDBOX: Optional[bool] = None  # if true force sandbox mode (no real delivery)
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Application settings
    RESUME_MATCH_THRESHOLD: float = 30.0
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"

    def model_post_init(self, __context):
        # Decode base64 Clerk key if provided
        if self.CLERK_JWT_SECRET_BASE64 and not self.CLERK_JWT_SECRET:
            import base64
            try:
                decoded = base64.b64decode(self.CLERK_JWT_SECRET_BASE64).decode("utf-8")
                object.__setattr__(self, "CLERK_JWT_SECRET", decoded)
            except Exception:
                # Leave as-is if decoding fails
                pass
        # Prefer Supabase Postgres URL if provided
        try:
            supa = (self.SUPABASE_POSTGRES_URL or "").strip()
            if supa:
                # Normalize schemes
                if supa.startswith("postgres://"):
                    supa = supa.replace("postgres://", "postgresql+psycopg2://", 1)
                if supa.startswith("postgresql://"):
                    supa = supa.replace("postgresql://", "postgresql+psycopg2://", 1)
                object.__setattr__(self, "DATABASE_URL", supa)
        except Exception:
            # Non-fatal; keep existing DATABASE_URL
            pass

    @property
    def cors_origins_list(self) -> List[str]:
        val = (self.CORS_ORIGINS or "").strip()
        if not val or val == "*":
            return ["*"]
        return [p.strip() for p in val.split(',') if p.strip()]

    @property
    def apify_token(self) -> Optional[str]:
        """Return the configured Apify token from either env name."""
        tok = self.APIFY_TOKEN or self.APIFY_API_TOKEN
        if tok:
            return tok.strip()
        return tok

    @property
    def clerk_enabled(self) -> bool:
        """Clerk is enabled only if required keys are present."""
        return bool(self.CLERK_SECRET_KEY and self.CLERK_PUBLISHABLE_KEY)

    @property
    def dev_auth_enabled(self) -> bool:
        """Development auth is enabled when a DEV_BEARER_TOKEN is configured."""
        return bool(self.DEV_BEARER_TOKEN)

    @property
    def supabase_storage_enabled(self) -> bool:
        """True when storage configuration is present for backend uploads."""
        return bool(self.SUPABASE_URL and (self.SUPABASE_SERVICE_ROLE_KEY or self.SUPABASE_ANON_KEY))

settings = Settings()