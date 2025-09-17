from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

# Search request schema
class SearchRequest(BaseModel):
    """Global search request"""
    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    search_types: List[str] = Field(
        default=["jobs", "candidates", "applications"],
        description="Types of entities to search (jobs, candidates, applications)"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional filters for search"
    )
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results per type")
    
    model_config = ConfigDict(from_attributes=True)

# Search response schemas
class JobSearchResult(BaseModel):
    """Job search result"""
    id: int
    title: str
    company: str
    location: str
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CandidateSearchResult(BaseModel):
    """Candidate search result"""
    id: int
    name: str
    email: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ApplicationSearchResult(BaseModel):
    """Application search result"""
    id: int
    job_title: str
    candidate_name: str
    status: str
    applied_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SearchResponse(BaseModel):
    """Basic search response"""
    query: str
    total_results: int
    results: List[Dict[str, Any]] = []
    
    model_config = ConfigDict(from_attributes=True)

class GlobalSearchResponse(BaseModel):
    """Global search response with categorized results"""
    query: str
    total_results: int
    jobs: List[Dict[str, Any]] = []
    candidates: List[Dict[str, Any]] = []
    applications: List[Dict[str, Any]] = []
    
    model_config = ConfigDict(from_attributes=True)

# Advanced search schemas
class AdvancedSearchFilters(BaseModel):
    """Advanced search filters"""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    status: Optional[List[str]] = None
    location: Optional[str] = None
    department: Optional[str] = None
    experience_level: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class AdvancedSearchRequest(BaseModel):
    """Advanced search request"""
    query: str = Field(..., min_length=1, max_length=200)
    search_type: str = Field(..., description="Type of entity to search")
    filters: Optional[AdvancedSearchFilters] = None
    sort_by: Optional[str] = Field(default="relevance", description="Sort field")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    
    model_config = ConfigDict(from_attributes=True)

class SearchSuggestion(BaseModel):
    """Search suggestion"""
    text: str
    type: str
    count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

class SearchSuggestionsResponse(BaseModel):
    """Search suggestions response"""
    query: str
    suggestions: List[SearchSuggestion] = []
    
    model_config = ConfigDict(from_attributes=True)