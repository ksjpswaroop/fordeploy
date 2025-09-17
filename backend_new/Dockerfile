# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Set work directory
WORKDIR /app


# Install system dependencies, Rust, and procps (for ps command)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        procps \
        build-essential \
        libpq-dev \
        gcc \
        rustc \
        cargo \
        postgresql-client \
        && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app/data /app/logs

# Copy requirements file
COPY requirements.txt .


# Set Rust environment variable for impit build
ENV RUSTFLAGS="--cfg reqwest_unstable"

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Ensure scripts are executable
RUN chmod +x scripts/prestart.sh || true

# Expose the API port
EXPOSE 8080

# Default CMD: Uvicorn for development. In production, override with compose to run prestart + gunicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]