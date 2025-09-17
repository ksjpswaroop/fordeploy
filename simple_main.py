import os
import sys
import uvicorn
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

try:
    # Load environment variables from .env file
    logger.info("Loading environment variables")
    load_dotenv()

    # Print environment variables for debugging (excluding secrets)
    env_vars = {k: v for k, v in os.environ.items() 
               if not any(secret in k.lower() for secret in ['key', 'token', 'pass', 'secret'])}
    logger.info(f"Environment variables loaded: {env_vars}")
except Exception as e:
    logger.error(f"Error loading environment: {e}")
    # Continue anyway with default values

# Create FastAPI app
app = FastAPI(
    title="Recruitment API",
    description="Simplified recruitment system API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and container orchestration"""
    return {
        "status": "healthy", 
        "service": "api",
        "version": os.getenv("APP_VERSION", "1.0.0")
    }

@app.get("/")
async def root():
    """Root endpoint that shows the API is running"""
    return {
        "message": "Recruitment System API is running",
        "documentation": "/docs",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.get("/config")
async def config():
    """Endpoint to check non-sensitive configuration"""
    return {
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": os.getenv("PORT", "8000"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug": os.getenv("DEBUG", "False").lower() == "true",
    }

# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all unhandled errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": f"Internal Server Error: {str(exc)}"}
    )

# Add email tracking endpoints
@app.get("/track/{email_id}")
async def track_open(email_id: str):
    """Track email opens"""
    logger.info(f"Email {email_id} was opened")
    return JSONResponse(content={"status": "tracked"}, status_code=200)

if __name__ == "__main__":
    try:
        port = int(os.getenv("PORT", "8000"))
        host = os.getenv("HOST", "0.0.0.0")
        reload = os.getenv("RELOAD", "False").lower() == "true"
        
        logger.info(f"Starting API server at {host}:{port} (reload={reload})")
        
        uvicorn.run(
            "simple_main:app", 
            host=host, 
            port=port, 
            reload=reload,
            log_level=os.getenv("LOG_LEVEL", "info").lower()
        )
    except Exception as e:
        logger.critical(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)
