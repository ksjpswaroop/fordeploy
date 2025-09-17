# DigitalOcean Deployment Guide

This guide provides step-by-step instructions for deploying the AI-Driven Recruitment Platform on DigitalOcean using Docker.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [DigitalOcean Setup](#digitalocean-setup)
3. [Server Configuration](#server-configuration)
4. [Application Deployment](#application-deployment)
5. [SSL Configuration](#ssl-configuration)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Troubleshooting](#troubleshooting)
8. [Security Best Practices](#security-best-practices)

## Prerequisites

Before starting the deployment, ensure you have:

- A DigitalOcean account
- A domain name (optional but recommended)
- Basic knowledge of Linux command line
- Git installed locally
- Docker and Docker Compose knowledge

## DigitalOcean Setup

### 1. Create a Droplet

1. Log in to your DigitalOcean account
2. Click "Create" → "Droplets"
3. Choose the following configuration:
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: 
     - Basic: $12/month (2 GB RAM, 1 vCPU, 50 GB SSD) - Minimum
     - Professional: $24/month (4 GB RAM, 2 vCPUs, 80 GB SSD) - Recommended
   - **Datacenter**: Choose closest to your users
   - **Authentication**: SSH Key (recommended) or Password
   - **Hostname**: `ai-recruitment-platform`

4. Click "Create Droplet"

### 2. Configure DNS (Optional)

If you have a domain:

1. Go to DigitalOcean → Networking → Domains
2. Add your domain
3. Create A records:
   - `@` pointing to your droplet's IP
   - `www` pointing to your droplet's IP

## Server Configuration

### 1. Initial Server Setup

Connect to your droplet:

```bash
ssh root@your_droplet_ip
```

Run the automated setup script:

```bash
curl -sSL https://raw.githubusercontent.com/yourusername/yourrepo/main/scripts/setup-server.sh | bash
```

Or manually download and run:

```bash
wget https://raw.githubusercontent.com/yourusername/yourrepo/main/scripts/setup-server.sh
chmod +x setup-server.sh
./setup-server.sh
```

### 2. What the Setup Script Does

The setup script automatically:

- Updates system packages
- Installs Docker and Docker Compose
- Installs DigitalOcean CLI (doctl)
- Configures firewall (UFW)
- Sets up fail2ban for security
- Creates application user and directories
- Configures log rotation
- Sets up basic monitoring
- Prepares SSL certificate setup

### 3. Manual Setup (Alternative)

If you prefer manual setup, follow these steps:

#### Update System
```bash
apt update && apt upgrade -y
```

#### Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
systemctl start docker
systemctl enable docker
```

#### Install Docker Compose
```bash
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

#### Create Application User
```bash
useradd -m -s /bin/bash appuser
usermod -aG docker appuser
mkdir -p /opt/ai-recruitment-platform
chown -R appuser:appuser /opt/ai-recruitment-platform
```

## Application Deployment

### 1. Clone Repository

Switch to application user and clone the repository:

```bash
su - appuser
cd /opt/ai-recruitment-platform
git clone https://github.com/yourusername/ai-recruitment-platform.git .
```

### 2. Configure Environment

Copy and configure the production environment file:

```bash
cp .env.production .env
nano .env
```

Update the following variables:

```env
# Database Configuration
POSTGRES_DB=ai_recruitment_prod
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://your_db_user:your_secure_password@db:5432/ai_recruitment_prod

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Application Configuration
NODE_ENV=production
API_PORT=8080
FRONTEND_PORT=3000

# Domain Configuration (update with your domain)
DOMAIN=yourdomain.com
NEXT_PUBLIC_API_BASE_URL=https://yourdomain.com/api

# Security
JWT_SECRET=your_jwt_secret_key_here
DEV_BEARER_TOKEN=your_dev_bearer_token_here

# External APIs
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password

# File Upload
MAX_FILE_SIZE=10485760
UPLOAD_DIR=/app/uploads

# CORS
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 3. Deploy Application

Run the deployment script:

```bash
./scripts/deploy.sh
```

The deployment script will:

1. Validate environment configuration
2. Build Docker images
3. Start services with health checks
4. Verify deployment
5. Display service status

### 4. Verify Deployment

Check if all services are running:

```bash
docker-compose -f docker-compose.prod.yml ps
```

Expected output:
```
NAME                    COMMAND                  SERVICE             STATUS              PORTS
ai-recruitment-api      "uvicorn main:app --…"   api                 running (healthy)   0.0.0.0:8080->8080/tcp
ai-recruitment-db       "docker-entrypoint.s…"   db                  running (healthy)   5432/tcp
ai-recruitment-nginx    "/docker-entrypoint.…"   nginx               running             0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
ai-recruitment-redis    "docker-entrypoint.s…"   redis               running (healthy)   6379/tcp
ai-recruitment-web      "docker-entrypoint.s…"   web                 running (healthy)   3000/tcp
```

## SSL Configuration

### 1. Using Let's Encrypt (Recommended)

After your domain is pointing to the server:

```bash
./setup-ssl.sh
```

Or manually:

```bash
# Stop nginx
systemctl stop nginx

# Get certificate
certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com --email your-email@domain.com --agree-tos --non-interactive

# Update nginx configuration for SSL
# The nginx.conf already includes SSL configuration template

# Restart services
docker-compose -f docker-compose.prod.yml restart nginx
```

### 2. SSL Certificate Auto-Renewal

The setup script automatically configures certificate renewal:

```bash
# Check renewal status
certbot renew --dry-run

# Manual renewal if needed
certbot renew
docker-compose -f docker-compose.prod.yml restart nginx
```

## Monitoring and Maintenance

### 1. View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs

# Specific service
docker-compose -f docker-compose.prod.yml logs api
docker-compose -f docker-compose.prod.yml logs web
docker-compose -f docker-compose.prod.yml logs nginx

# Follow logs in real-time
docker-compose -f docker-compose.prod.yml logs -f
```

### 2. Health Checks

```bash
# Check service health
docker-compose -f docker-compose.prod.yml ps

# Manual health check
curl -f http://localhost:8080/health
curl -f http://localhost:3000
```

### 3. Database Backup

```bash
# Create backup
docker-compose -f docker-compose.prod.yml exec db pg_dump -U your_db_user ai_recruitment_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker-compose -f docker-compose.prod.yml exec -T db psql -U your_db_user ai_recruitment_prod < backup_file.sql
```

### 4. Update Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
./scripts/deploy.sh

# Or manually
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Common Issues

#### 1. Services Not Starting

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs

# Check system resources
htop
df -h

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

#### 2. Database Connection Issues

```bash
# Check database status
docker-compose -f docker-compose.prod.yml exec db pg_isready -U your_db_user

# Connect to database
docker-compose -f docker-compose.prod.yml exec db psql -U your_db_user ai_recruitment_prod

# Check database logs
docker-compose -f docker-compose.prod.yml logs db
```

#### 3. SSL Certificate Issues

```bash
# Check certificate status
certbot certificates

# Renew certificate
certbot renew --force-renewal

# Check nginx configuration
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
```

#### 4. High Memory Usage

```bash
# Check memory usage
free -h
docker stats

# Restart services to free memory
docker-compose -f docker-compose.prod.yml restart
```

### Performance Optimization

#### 1. Database Optimization

```sql
-- Connect to database and run these queries
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM your_table;

-- Update statistics
ANALYZE;

-- Vacuum database
VACUUM ANALYZE;
```

#### 2. Redis Optimization

```bash
# Check Redis memory usage
docker-compose -f docker-compose.prod.yml exec redis redis-cli info memory

# Clear cache if needed
docker-compose -f docker-compose.prod.yml exec redis redis-cli flushall
```

## Security Best Practices

### 1. Server Security

- Change default SSH port
- Disable password authentication (use SSH keys only)
- Keep system updated
- Use fail2ban (already configured)
- Regular security audits

### 2. Application Security

- Use strong passwords and JWT secrets
- Enable HTTPS only
- Regular dependency updates
- Monitor logs for suspicious activity
- Implement rate limiting

### 3. Database Security

- Use strong database passwords
- Limit database access
- Regular backups
- Monitor database logs

### 4. Firewall Configuration

```bash
# Check firewall status
ufw status

# Allow specific IPs only (optional)
ufw allow from your_office_ip to any port 22

# Block specific IPs
ufw deny from suspicious_ip
```

## CI/CD with GitHub Actions

The repository includes GitHub Actions workflow for automated deployment:

### 1. Setup GitHub Secrets

Add these secrets to your GitHub repository:

- `DIGITALOCEAN_ACCESS_TOKEN`: Your DigitalOcean API token
- `DROPLET_IP`: Your droplet's IP address
- `DROPLET_USER`: SSH user (usually `appuser`)
- `SSH_PRIVATE_KEY`: Your SSH private key
- `ENV_FILE`: Contents of your `.env` file

### 2. Automatic Deployment

The workflow automatically:

- Runs tests on push/PR
- Builds Docker images
- Deploys to DigitalOcean
- Verifies deployment
- Sends notifications

## Cost Optimization

### 1. Droplet Sizing

- Start with Basic plan ($12/month)
- Monitor resource usage
- Upgrade when needed
- Use monitoring to optimize

### 2. Storage Optimization

- Regular cleanup of logs
- Optimize Docker images
- Use volume mounts efficiently
- Regular database maintenance

### 3. Bandwidth Optimization

- Enable gzip compression (already configured)
- Optimize images and assets
- Use CDN for static files (optional)

## Support and Resources

- [DigitalOcean Documentation](https://docs.digitalocean.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Nginx Documentation](https://nginx.org/en/docs/)

## Conclusion

This deployment guide provides a comprehensive setup for running the AI-Driven Recruitment Platform on DigitalOcean. The configuration includes:

- Automated server setup
- Production-ready Docker configuration
- SSL certificate management
- Monitoring and logging
- Security best practices
- CI/CD integration

For additional support or questions, please refer to the project documentation or create an issue in the repository.