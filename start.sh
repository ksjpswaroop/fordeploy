#!/bin/bash
set -e

# Better error handling
handle_error() {
  echo "ERROR: An error occurred at line $1, exit code $2"
  exit $2
}
trap 'handle_error $LINENO $?' ERR

echo "=== Starting application ==="
echo "Checking environment..."

# Load environment variables with error handling
if [ -f ".env" ]; then
  echo "Loading environment variables from .env file"
  set -a
  source .env
  set +a
else
  echo "WARNING: No .env file found, using default environment variables"
fi

# Check if requirements are installed
echo "Verifying Python packages..."
if ! python -c "import fastapi" &>/dev/null; then
  echo "ERROR: Required packages not installed. Try running: pip install -r requirements.txt"
  exit 1
fi

# Create necessary directories
mkdir -p data logs

# Check for simple_main.py
if [ ! -f "simple_main.py" ]; then
  echo "ERROR: simple_main.py not found! This file is required to run the application."
  echo "Please create this file with your FastAPI application."
  exit 1
fi

# Print debug info
echo "=============================="
echo "ENVIRONMENT INFO:"
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "Contents: $(ls -la)"
echo "Environment variables:"
echo "- PORT=${PORT:-8000}"
echo "- HOST=${HOST:-0.0.0.0}"
echo "- DEBUG=${DEBUG:-False}"
echo "=============================="

# Start the API server in the background with output redirection
echo "Starting API server..."
python simple_main.py > logs/api.log 2>&1 &
API_PID=$!
echo "API server started with PID: $API_PID"

# Check if API server started successfully
sleep 3
if ! ps -p $API_PID > /dev/null; then
  echo "ERROR: API server failed to start. Check logs/api.log for details:"
  cat logs/api.log
  exit 1
fi

# Start the email tracker server in the background (if it exists)
if [ -f "email_tracker.py" ]; then
  echo "Starting email tracker..."
  python email_tracker.py > logs/email_tracker.log 2>&1 &
  EMAIL_TRACKER_PID=$!
  echo "Email tracker started with PID: $EMAIL_TRACKER_PID"
  
  # Check if email tracker started successfully
  sleep 2
  if ! ps -p $EMAIL_TRACKER_PID > /dev/null; then
    echo "ERROR: Email tracker failed to start. Check logs/email_tracker.log for details:"
    cat logs/email_tracker.log
    exit 1
  fi
else
  echo "No email_tracker.py found, skipping email tracker service"
  EMAIL_TRACKER_PID=""
fi

echo "All services started successfully!"
echo "API server: http://${HOST:-0.0.0.0}:${PORT:-8000}"
if [ ! -z "$EMAIL_TRACKER_PID" ]; then
  echo "Email tracker: http://${HOST:-0.0.0.0}:${EMAIL_TRACKER_PORT:-8001}"
fi

# Function to handle termination
cleanup() {
    echo "Stopping servers..."
    if [ ! -z "$API_PID" ] && ps -p $API_PID > /dev/null; then
      kill $API_PID 2>/dev/null || true
      echo "API server stopped"
    fi
    
    if [ ! -z "$EMAIL_TRACKER_PID" ] && ps -p $EMAIL_TRACKER_PID > /dev/null; then
      kill $EMAIL_TRACKER_PID 2>/dev/null || true
      echo "Email tracker stopped"
    fi
    echo "Cleanup complete"
    exit 0
}

# Register the cleanup function for SIGTERM and SIGINT
trap cleanup SIGTERM SIGINT

echo "Services running. Press Ctrl+C to stop."

# Create a simple watchdog to restart services if they crash
while true; do
  if [ ! -z "$API_PID" ] && ! ps -p $API_PID > /dev/null; then
    echo "WARNING: API server crashed, restarting..."
    python simple_main.py > logs/api.log 2>&1 &
    API_PID=$!
  fi
  
  if [ ! -z "$EMAIL_TRACKER_PID" ] && ! ps -p $EMAIL_TRACKER_PID > /dev/null; then
    echo "WARNING: Email tracker crashed, restarting..."
    python email_tracker.py > logs/email_tracker.log 2>&1 &
    EMAIL_TRACKER_PID=$!
  fi
  
  sleep 5
done
