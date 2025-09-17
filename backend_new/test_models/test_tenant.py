from sqlalchemy.orm import Session
from app.models import Tenant


def test_create_tenant_persists(db_session: Session):
    tenant = Tenant(name="Acme Consulting", domain="acme.example")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    assert tenant.id is not None
    assert tenant.name == "Acme Consulting"
