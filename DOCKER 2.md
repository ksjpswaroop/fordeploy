# Docker Configuration Guide

This document explains the Docker setup for the AI-Driven Recruitment Platform, including development and production configurations.

## Table of Contents

1. [Overview](#overview)
2. [Development Setup](#development-setup)
3. [Production Setup](#production-setup)
4. [Docker Images](#docker-images)
5. [Environment Variables](#environment-variables)
6. [Networking](#networking)
7. [Volumes and Data Persistence](#volumes-and-data-persistence)
8. [Health Checks](#health-checks)
9. [Scaling](#scaling)
10. [Best Practices](#best-practices)

## Overview

The application uses a multi-container Docker setup with the following services:

- **PostgreSQL Database** (`db`): Primary data storage
- **Redis** (`redis`): Caching and session storage
- **FastAPI Backend** (`api`): Python API server
- **Next.js Frontend** (`web`): React-based web application
- **Nginx** (`nginx`): Reverse proxy and load balancer

## Development Setup

### Quick Start

```bash
# Clone repository
git clone <repository-url>
cd ai-recruitment-platform

# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f
```

### Development Configuration

The `docker-compose.yml` file provides a simplified setup for development:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DEV_BEARER_TOKEN=${DEV_BEARER_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    restart: unless-stopped
```

### Development Commands

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d api

# View service logs
docker-compose logs api
docker-compose logs -f web

# Execute commands in containers
docker-compose exec api bash
docker-compose exec db psql -U postgres

# Stop all services
docker-compose down

# Remove volumes (careful - deletes data)
docker-compose down -v
```

## Production Setup

### Production Configuration

The `docker-compose.prod.yml` file provides a production-ready setup:

```yaml
version: '3.9'

services:
  db:
    image: postgres:15-alpine
    container_name: ai-recruitment-db
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - dbdata:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - ai-recruitment-network

  redis:
    image: redis:7-alpine
    container_name: ai-recruitment-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - ai-recruitment-network

  api:
    build: .
    container_name: ai-recruitment-api
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET=${JWT_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8080:8080"
    volumes:
      - ./uploads:/app/uploads
      - ./generated_docs:/app/generated_docs
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - ai-recruitment-network

  web:
    build: ./frontend
    container_name: ai-recruitment-web
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
    depends_on:
      api:
        condition: service_healthy
    ports:
      - "3000:3000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - ai-recruitment-network

  nginx:
    image: nginx:alpine
    container_name: ai-recruitment-nginx
    depends_on:
      - api
      - web
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
      - /etc/letsencrypt:/etc/letsencrypt
    restart: unless-stopped
    networks:
      - ai-recruitment-network

volumes:
  dbdata:
  redis_data:

networks:
  ai-recruitment-network:
    driver: bridge
```

### Production Commands

```bash
# Start production environment
docker-compose -f docker-compose.prod.yml up -d

# Build without cache
docker-compose -f docker-compose.prod.yml build --no-cache

# View production logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# Stop production environment
docker-compose -f docker-compose.prod.yml down
```

## Docker Images

### Backend API (FastAPI)

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (required for some Python packages)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Set work directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/uploads /app/generated_docs /app/logs

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Frontend (Next.js)

**frontend/Dockerfile:**
```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM node:20-alpine AS runner

WORKDIR /app

# Set environment
ENV NODE_ENV=production

# Copy built application
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Start application
CMD ["npm", "start"]
```

## Environment Variables

### Required Variables

```env
# Database
POSTGRES_DB=ai_recruitment
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password
DATABASE_URL=postgresql://postgres:secure_password@db:5432/ai_recruitment

# Redis
REDIS_URL=redis://redis:6379/0

# Application
NODE_ENV=production
API_PORT=8080
FRONTEND_PORT=3000

# Security
JWT_SECRET=your_jwt_secret_here
DEV_BEARER_TOKEN=your_bearer_token_here

# External APIs
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key

# Domain (for production)
DOMAIN=yourdomain.com
NEXT_PUBLIC_API_BASE_URL=https://yourdomain.com/api

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password

# File Upload
MAX_FILE_SIZE=10485760
UPLOAD_DIR=/app/uploads

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Environment Files

- `.env` - Development environment
- `.env.production` - Production template
- `.env.local` - Local overrides (not committed)

## Networking

### Network Configuration

The production setup uses a custom bridge network:

```yaml
networks:
  ai-recruitment-network:
    driver: bridge
```

### Service Communication

- **Internal communication**: Services communicate using service names
- **External access**: Only nginx exposes ports 80/443 to the host
- **Database access**: Only accessible from within the network

### Port Mapping

| Service | Internal Port | External Port | Purpose |
|---------|---------------|---------------|---------|
| nginx   | 80, 443       | 80, 443       | HTTP/HTTPS |
| api     | 8080          | 8080*         | API (dev only) |
| web     | 3000          | 3000*         | Frontend (dev only) |
| db      | 5432          | -             | Database |
| redis   | 6379          | -             | Cache |

*External ports only exposed in development

## Volumes and Data Persistence

### Named Volumes

```yaml
volumes:
  dbdata:           # PostgreSQL data
  redis_data:       # Redis persistence
```

### Bind Mounts

```yaml
volumes:
  - ./uploads:/app/uploads                    # File uploads
  - ./generated_docs:/app/generated_docs      # Generated documents
  - ./logs:/app/logs                          # Application logs
  - ./nginx/nginx.conf:/etc/nginx/nginx.conf  # Nginx configuration
  - /etc/letsencrypt:/etc/letsencrypt         # SSL certificates
```

### Backup Strategy

```bash
# Database backup
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres ai_recruitment > backup.sql

# Volume backup
docker run --rm -v ai-recruitment_dbdata:/data -v $(pwd):/backup alpine tar czf /backup/dbdata.tar.gz -C /data .

# Restore volume
docker run --rm -v ai-recruitment_dbdata:/data -v $(pwd):/backup alpine tar xzf /backup/dbdata.tar.gz -C /data
```

## Health Checks

### Configuration

All services include health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Health Check Endpoints

- **API**: `GET /health`
- **Frontend**: `GET /` (homepage)
- **Database**: `pg_isready` command
- **Redis**: `redis-cli ping`

### Monitoring Health

```bash
# Check health status
docker-compose -f docker-compose.prod.yml ps

# View health check logs
docker inspect --format='{{json .State.Health}}' ai-recruitment-api
```

## Scaling

### Horizontal Scaling

```bash
# Scale API service
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# Scale with load balancer
docker-compose -f docker-compose.prod.yml up -d --scale api=3 --scale web=2
```

### Load Balancing

Nginx configuration supports multiple backend instances:

```nginx
upstream backend {
    server api:8080;
    # Additional instances will be auto-discovered
}

upstream frontend {
    server web:3000;
    # Additional instances will be auto-discovered
}
```

### Resource Limits

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## Best Practices

### 1. Image Optimization

- Use multi-stage builds
- Use Alpine Linux base images
- Minimize layers
- Use .dockerignore files
- Don't run as root user

### 2. Security

- Use non-root users in containers
- Scan images for vulnerabilities
- Use secrets management
- Limit container capabilities
- Use read-only filesystems where possible

### 3. Performance

- Use health checks
- Implement graceful shutdowns
- Use connection pooling
- Optimize resource limits
- Use caching strategies

### 4. Monitoring

- Centralized logging
- Metrics collection
- Health monitoring
- Resource monitoring
- Alert configuration

### 5. Development Workflow

```bash
# Development cycle
docker-compose up -d          # Start services
docker-compose logs -f api    # Monitor logs
docker-compose exec api bash  # Debug container
docker-compose restart api    # Restart service
docker-compose down           # Stop services
```

### 6. Production Deployment

```bash
# Production deployment
git pull origin main
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml logs -f
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Check if ports are already in use
2. **Permission issues**: Ensure proper file permissions
3. **Memory issues**: Monitor container resource usage
4. **Network issues**: Check service connectivity
5. **Volume issues**: Verify mount paths and permissions

### Debug Commands

```bash
# Container inspection
docker inspect <container_name>

# Resource usage
docker stats

# Network inspection
docker network ls
docker network inspect ai-recruitment_ai-recruitment-network

# Volume inspection
docker volume ls
docker volume inspect ai-recruitment_dbdata

# Execute commands in containers
docker-compose exec api python manage.py shell
docker-compose exec db psql -U postgres
```

This Docker configuration provides a robust, scalable, and maintainable setup for both development and production environments.