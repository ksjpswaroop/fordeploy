"""
Vercel serverless handler for FastAPI application
"""
import os
import sys

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.main import app

# Vercel expects a handler function
def handler(request, response):
    return app(request, response)

# For Vercel's Python runtime
app = app