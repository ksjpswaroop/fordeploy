from fastapi import APIRouter
from .routers import admin, auth, manager, recruiter, candidate, common, job_pipeline

api_router = APIRouter()

# Include all routers
api_router.include_router(admin.router)
api_router.include_router(auth.router)
api_router.include_router(manager.router)
api_router.include_router(recruiter.router)
api_router.include_router(candidate.router)
api_router.include_router(common.router)
api_router.include_router(job_pipeline.router)

# Health check endpoint
@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "API is running"}

@api_router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Recruitment API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }