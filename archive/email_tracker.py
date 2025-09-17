import os
import sys
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create FastAPI app for email tracking
app = FastAPI(title="Email Tracking Service")

# Configure CORS
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
    return {"status": "healthy"}

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>Email Tracking Service</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                h1 { color: #333; }
            </style>
        </head>
        <body>
            <h1>Email Tracking Service</h1>
            <p>This service tracks email opens and clicks.</p>
        </body>
    </html>
    """

@app.get("/track/{email_id}")
async def track_open(email_id: str):
    print(f"Email {email_id} was opened")
    # In a real implementation, you would log this to a database
    return HTMLResponse(content="", status_code=200)

# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": f"Internal Server Error: {str(exc)}"}
    )

if __name__ == "__main__":
    port = int(os.getenv("EMAIL_TRACKER_PORT", "8001"))
    host = os.getenv("HOST", "0.0.0.0")
    reload = os.getenv("RELOAD", "False").lower() == "true"
    
    print(f"Starting Email Tracker server at {host}:{port}")
    uvicorn.run(
        "email_tracker:app", 
        host=host, 
        port=port, 
        reload=reload,
        log_level="info"
    )
