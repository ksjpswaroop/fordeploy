"""API v1 module initialization."""

from fastapi import APIRouter
from .admin import router as admin_router
from .manager import router as manager_router
from .recruiter import router as recruiter_router
from .candidate import router as candidate_router
from .common import router as common_router
from app.api.routers.bench import router as bench_router
from app.api.routers.notifications import router as notifications_router
from app.api.routers.run import router as run_router

# Create main v1 router
api_router = APIRouter(prefix="/v1")

# Include all sub-routers
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(manager_router, prefix="/manager", tags=["manager"])
api_router.include_router(recruiter_router, prefix="/recruiter", tags=["recruiter"])  # apply prefix here (router has none)
api_router.include_router(candidate_router, prefix="/candidate", tags=["candidate"])  # apply prefix here (router has none)
# common_router already has prefix "/common"
api_router.include_router(common_router, tags=["common"])
api_router.include_router(bench_router, prefix="/bench", tags=["bench"])
api_router.include_router(notifications_router, tags=["notifications"])
api_router.include_router(run_router, prefix="/pipeline", tags=["pipeline"])

__all__ = ["api_router"]