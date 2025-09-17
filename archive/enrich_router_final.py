from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os

# Import functions from the main pipeline script
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from job_application_pipeline import enrich_contacts

router = APIRouter()

class EnrichRequest(BaseModel):
    database: str = "jobs.db"

class EnrichResponse(BaseModel):
    jobs_enriched: int
    message: str

@router.post("/enrich", response_model=EnrichResponse)
def enrich_job_contacts(request: EnrichRequest):
    """Enrich jobs with contact information using Apollo."""
    # Enrich contacts in the database
    try:
        # The original function doesn't return the count, so we'll mock this for now
        enrich_contacts(request.database)
        # In a real implementation, you would modify enrich_contacts to return the count
        return EnrichResponse(
            jobs_enriched=0,  # This should be the actual count
            message="Successfully enriched job contacts"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enriching contacts: {str(e)}")
