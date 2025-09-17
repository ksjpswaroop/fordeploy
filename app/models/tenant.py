from sqlalchemy import Column, Integer, String, Text, JSON
from .base import BaseModel, AuditMixin, MetadataMixin


class Tenant(BaseModel, AuditMixin, MetadataMixin):
    """Tenant model representing a consulting company/account."""
    __tablename__ = "tenants"

    name = Column(String(200), nullable=False, unique=True, index=True)
    domain = Column(String(255), nullable=True, unique=True, index=True)
    settings = Column(JSON, nullable=True, default={})
    description = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name='{self.name}')>"


class TenantAwareMixin:
    """Mixin to add tenant_id foreign key to tenant-scoped models."""
    tenant_id = Column(Integer, nullable=False, index=True)
