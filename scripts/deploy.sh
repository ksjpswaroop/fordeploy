#!/bin/bash

# =============================================================================
# AI RECRUITMENT PLATFORM - DIGITALOCEAN DEPLOYMENT SCRIPT
# =============================================================================
# This script deploys the application to DigitalOcean using Docker Compose
# Usage: ./scripts/deploy.sh [environment]
# Example: ./scripts/deploy.sh production

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
PROJECT_NAME="ai-recruitment-platform"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking deployment requirements..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if environment file exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file $ENV_FILE not found."
        log_info "Please copy .env.production to .env and configure your settings."
        exit 1
    fi
    
    # Check if compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Docker Compose file $COMPOSE_FILE not found."
        exit 1
    fi
    
    log_success "All requirements met."
}

validate_environment() {
    log_info "Validating environment configuration..."
    
    # Check critical environment variables
    source "$ENV_FILE"
    
    REQUIRED_VARS=(
        "SECRET_KEY"
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
        "JWT_SECRET_KEY"
        "CLERK_SECRET_KEY"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "Required environment variable $var is not set."
            exit 1
        fi
    done
    
    # Check if using default/insecure values
    if [ "$SECRET_KEY" = "your-super-secret-key-change-this-in-production" ]; then
        log_error "SECRET_KEY is still using the default value. Please change it."
        exit 1
    fi
    
    log_success "Environment validation passed."
}

backup_data() {
    log_info "Creating backup of existing data..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup database if container exists
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "ai_recruitment_db"; then
        log_info "Backing up database..."
        docker-compose -f "$COMPOSE_FILE" exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_DIR/database.sql"
        log_success "Database backup created: $BACKUP_DIR/database.sql"
    fi
    
    # Backup uploaded files
    if [ -d "uploads" ]; then
        log_info "Backing up uploaded files..."
        cp -r uploads "$BACKUP_DIR/"
        log_success "Files backup created: $BACKUP_DIR/uploads"
    fi
    
    log_success "Backup completed: $BACKUP_DIR"
}

deploy_application() {
    log_info "Starting deployment process..."
    
    # Pull latest images
    log_info "Pulling latest Docker images..."
    docker-compose -f "$COMPOSE_FILE" pull
    
    # Build application images
    log_info "Building application images..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    # Stop existing containers
    log_info "Stopping existing containers..."
    docker-compose -f "$COMPOSE_FILE" down
    
    # Start services
    log_info "Starting services..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 30
    
    # Check service health
    check_service_health
    
    log_success "Deployment completed successfully!"
}

check_service_health() {
    log_info "Checking service health..."
    
    # Check database
    if docker-compose -f "$COMPOSE_FILE" exec -T db pg_isready -U "$POSTGRES_USER" > /dev/null 2>&1; then
        log_success "Database is healthy"
    else
        log_error "Database health check failed"
        return 1
    fi
    
    # Check Redis
    if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis is healthy"
    else
        log_error "Redis health check failed"
        return 1
    fi
    
    # Check backend API
    sleep 10  # Give backend more time to start
    if curl -f http://localhost:8080/health > /dev/null 2>&1; then
        log_success "Backend API is healthy"
    else
        log_error "Backend API health check failed"
        return 1
    fi
    
    # Check frontend
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        log_success "Frontend is healthy"
    else
        log_warning "Frontend health check failed (this might be normal if behind nginx)"
    fi
    
    # Check nginx
    if curl -f http://localhost/health > /dev/null 2>&1; then
        log_success "Nginx is healthy"
    else
        log_error "Nginx health check failed"
        return 1
    fi
}

show_deployment_info() {
    log_info "Deployment Information:"
    echo "=========================="
    echo "Environment: $ENVIRONMENT"
    echo "Project: $PROJECT_NAME"
    echo "Compose File: $COMPOSE_FILE"
    echo "Environment File: $ENV_FILE"
    echo ""
    echo "Services:"
    docker-compose -f "$COMPOSE_FILE" ps
    echo ""
    echo "Access URLs:"
    echo "- Application: http://your-droplet-ip"
    echo "- API Health: http://your-droplet-ip/health-check"
    echo "- API Docs: http://your-droplet-ip/api/docs"
    echo ""
    echo "Logs:"
    echo "- View all logs: docker-compose -f $COMPOSE_FILE logs -f"
    echo "- View backend logs: docker-compose -f $COMPOSE_FILE logs -f api"
    echo "- View frontend logs: docker-compose -f $COMPOSE_FILE logs -f web"
    echo "=========================="
}

cleanup_old_images() {
    log_info "Cleaning up old Docker images..."
    docker image prune -f
    docker system prune -f
    log_success "Cleanup completed."
}

# Main execution
main() {
    log_info "Starting deployment for environment: $ENVIRONMENT"
    
    check_requirements
    validate_environment
    
    # Ask for confirmation in production
    if [ "$ENVIRONMENT" = "production" ]; then
        echo -n "Are you sure you want to deploy to production? (y/N): "
        read -r confirmation
        if [ "$confirmation" != "y" ] && [ "$confirmation" != "Y" ]; then
            log_info "Deployment cancelled."
            exit 0
        fi
    fi
    
    backup_data
    deploy_application
    cleanup_old_images
    show_deployment_info
    
    log_success "Deployment completed successfully!"
    log_info "Your application should now be accessible at http://your-droplet-ip"
}

# Handle script interruption
trap 'log_error "Deployment interrupted!"; exit 1' INT TERM

# Run main function
main "$@"