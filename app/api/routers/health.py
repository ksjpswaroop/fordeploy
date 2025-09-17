from fastapi import APIRouter

from app.schemas.pipeline import HealthResponse
from app.services.pipeline import PipelineService

router = APIRouter()

@router.get("/healthz", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify API and service health
    """
    return PipelineService.check_health()
