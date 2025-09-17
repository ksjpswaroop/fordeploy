"""Alembic environment configuration for database migrations."""

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models.base import Base

# Import all models to ensure they are registered with SQLAlchemy
from app.models.user import User, Role, Permission, UserSession, UserProfile
from app.models.job import Job, Department, Skill, JobTemplate, JobView
from app.models.bench import CandidateBench, Certification, CandidateSubmission, CandidateSale, CandidateInterview
from app.models.application import Application, ApplicationStatusHistory, ApplicationNote, Assessment, ApplicationFeedback
from app.models.interview import Interview, InterviewFeedback, InterviewNote, InterviewRecording, InterviewSlot, InterviewTemplate
from app.models.communication import Message, Notification, CallLog, EmailTemplate, CommunicationPreference, BulkCommunication
from app.models.analytics import RecruitmentMetric, JobAnalytics, CandidateAnalytics, RecruiterPerformance, PipelineAnalytics, DiversityMetrics, CustomMetric, MetricValue, Report
from app.models.upload import FileUpload, Document, DocumentVersion, DocumentComment, FileShare, FileAccessLog, FileVersion, BulkUpload
from app.models.recruiter_directory import RecruiterDirectory  # ensure recruiter_directory model included for autogenerate

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url():
    """Get database URL from settings."""
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Override the sqlalchemy.url in the alembic.ini with our settings
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()