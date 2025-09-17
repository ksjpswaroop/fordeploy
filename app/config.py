import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    """Application settings."""
    APP_NAME: str = "AI Recruitment Pipeline"
    APIFY_TOKEN: str = os.getenv("APIFY_TOKEN", "")
    APOLLO_API_KEY: str = os.getenv("APOLLO_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./jobs.db")
    
    # Default Apify actor ID
    DEFAULT_ACTOR_ID: str = "BHzefUZlZRKWxkTck"
    
settings = Settings()
