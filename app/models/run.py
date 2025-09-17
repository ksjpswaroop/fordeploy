from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum as SQLEnum
from datetime import datetime
from .base import BaseModel, AuditMixin, MetadataMixin
from enum import Enum

class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"

class Stage(str, Enum):
    DISCOVER = "discover"
    PARSE = "parse"
    ENRICH = "enrich"
    GENERATE = "generate"
    EMAIL = "email"
    DONE = "done"
    ERROR = "error"


class PipelineRun(BaseModel, AuditMixin, MetadataMixin):
    __tablename__ = "pipeline_runs"

    query = Column(String(500), nullable=False)
    locations = Column(JSON, nullable=True)
    sources = Column(JSON, nullable=True)
    status = Column(SQLEnum(RunStatus), default=RunStatus.QUEUED, index=True, nullable=False)
    stage = Column(String(50), default=Stage.DISCOVER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    counts = Column(JSON, default=dict)  # {jobs: int, enriched: int, emails: int}
    error = Column(String(1000), nullable=True)
    task_id = Column(String(100), nullable=True, unique=True, index=True)

    def mark_running(self):
        self.status = RunStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_done(self):
        self.status = RunStatus.DONE
        self.stage = Stage.DONE
        self.finished_at = datetime.utcnow()

    def mark_error(self, err: str):
        self.status = RunStatus.ERROR
        self.stage = Stage.ERROR
        self.error = err[:1000]
        self.finished_at = datetime.utcnow()

    def set_stage(self, stage: Stage):
        self.stage = stage
