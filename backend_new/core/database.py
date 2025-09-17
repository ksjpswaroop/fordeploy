from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import StaticPool
from typing import Generator
import os
from .config import settings
from app.models.base import Base as ModelsBase

# Create synchronous engine
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite specific configuration
    sync_engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG
    )
else:
    # PostgreSQL/MySQL configuration
    sync_engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=settings.DEBUG
    )

# Create async engine
if settings.DATABASE_URL.startswith("sqlite"):
    async_engine = create_async_engine(
        settings.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///"),
        echo=settings.DEBUG,
        future=True
    )
else:
    pg_url = settings.DATABASE_URL
    if pg_url.startswith("postgresql+psycopg2://"):
        pg_url = pg_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    elif pg_url.startswith("postgresql://"):
        pg_url = pg_url.replace("postgresql://", "postgresql+asyncpg://")
    async_engine = create_async_engine(
        pg_url,
        echo=settings.DEBUG,
        future=True
    )

# Create session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Use the same Base as models to ensure metadata includes all tables
Base = ModelsBase

# Metadata for migrations
metadata = MetaData()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get synchronous database session.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    """
    Dependency to get asynchronous database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def create_tables():
    """
    Create all tables in the database.
    This should be used for development/testing only.
    In production, use Alembic migrations.
    """
    # Import all models to ensure they are registered with the models Base
    import app.models  # noqa: F401 - register models
    Base.metadata.create_all(bind=sync_engine)

def drop_tables():
    """
    Drop all tables in the database.
    Use with caution - this will delete all data!
    """
    Base.metadata.drop_all(bind=sync_engine)

def init_db():
    """
    Initialize database with default data.
    Creates tables and adds initial data like roles and permissions.
    """
    from app.models import Role, Permission, User
    from app.core.security import get_password_hash
    
    # Create tables
    create_tables()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create default permissions
        permissions = [
            Permission(name="user:read", description="Read user information"),
            Permission(name="user:write", description="Create and update users"),
            Permission(name="user:delete", description="Delete users"),
            Permission(name="job:read", description="Read job information"),
            Permission(name="job:write", description="Create and update jobs"),
            Permission(name="job:delete", description="Delete jobs"),
            Permission(name="application:read", description="Read applications"),
            Permission(name="application:write", description="Create and update applications"),
            Permission(name="application:delete", description="Delete applications"),
            Permission(name="interview:read", description="Read interviews"),
            Permission(name="interview:write", description="Create and update interviews"),
            Permission(name="interview:delete", description="Delete interviews"),
            Permission(name="analytics:read", description="Read analytics data"),
            Permission(name="settings:read", description="Read system settings"),
            Permission(name="settings:write", description="Update system settings"),
            Permission(name="admin:all", description="Full administrative access"),
        ]
        
        for permission in permissions:
            existing = db.query(Permission).filter(Permission.name == permission.name).first()
            if not existing:
                db.add(permission)
        
        db.commit()
        
        # Create default roles
        roles_data = [
            {
                "name": "admin",
                "description": "System Administrator",
                "permissions": ["admin:all"]
            },
            {
                "name": "manager",
                "description": "Hiring Manager",
                "permissions": [
                    "user:read", "job:read", "job:write", "application:read", 
                    "application:write", "interview:read", "interview:write", 
                    "analytics:read"
                ]
            },
            {
                "name": "recruiter",
                "description": "Recruiter",
                "permissions": [
                    "job:read", "application:read", "application:write", 
                    "interview:read", "interview:write", "analytics:read"
                ]
            },
            {
                "name": "candidate",
                "description": "Job Candidate",
                "permissions": ["application:read", "interview:read"]
            }
        ]
        
        for role_data in roles_data:
            existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not existing_role:
                role = Role(
                    name=role_data["name"],
                    description=role_data["description"]
                )
                
                # Add permissions to role
                for perm_name in role_data["permissions"]:
                    permission = db.query(Permission).filter(Permission.name == perm_name).first()
                    if permission:
                        role.permissions.append(permission)
                
                db.add(role)
        
        db.commit()
        
        # Create default admin user if it doesn't exist
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_user = db.query(User).filter(User.email == admin_email).first()
        
        if not admin_user:
            admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
            admin_role = db.query(Role).filter(Role.name == "admin").first()
            
            admin_user = User(
                email=admin_email,
                username="admin",
                first_name="System",
                last_name="Administrator",
                hashed_password=get_password_hash(admin_password),
                is_active=True,
                is_verified=True
            )
            
            if admin_role:
                admin_user.roles.append(admin_role)
            
            db.add(admin_user)
            db.commit()
            
            print(f"Created admin user: {admin_email} / {admin_password}")
        
        print("Database initialized successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

async def init_async_db():
    """Initialize database tables asynchronously"""
    async with async_engine.begin() as conn:
        # Import all models to ensure they are registered
        import app.models  # This will import all models through __init__.py
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """Close database connections"""
    await async_engine.dispose()
    sync_engine.dispose()

class DatabaseManager:
    """
    Database manager for handling connections and transactions.
    """
    
    def __init__(self):
        self.sync_engine = sync_engine
        self.async_engine = async_engine
        self.SessionLocal = SessionLocal
        self.AsyncSessionLocal = AsyncSessionLocal
    
    def get_session(self) -> Session:
        """Get a new synchronous database session"""
        return self.SessionLocal()
    
    async def get_async_session(self) -> AsyncSession:
        """Get a new asynchronous database session"""
        return self.AsyncSessionLocal()
    
    def health_check(self) -> bool:
        """
        Check if database connection is healthy.
        Returns True if connection is working, False otherwise.
        """
        try:
            db = self.get_session()
            # Simple query to test connection
            db.execute("SELECT 1")
            db.close()
            return True
        except Exception:
            return False
    
    def get_connection_info(self) -> dict:
        """
        Get database connection information.
        """
        return {
            "url": str(self.sync_engine.url).replace(str(self.sync_engine.url.password) or "", "***"),
            "driver": self.sync_engine.url.drivername,
            "database": self.sync_engine.url.database,
            "host": self.sync_engine.url.host,
            "port": self.sync_engine.url.port,
            "pool_size": getattr(self.sync_engine.pool, 'size', None),
            "max_overflow": getattr(self.sync_engine.pool, 'max_overflow', None),
        }

# Global database manager instance
db_manager = DatabaseManager()