# Backend Deployment Guide - Digital Ocean

## Prerequisites
- Digital Ocean account
- Docker installed locally
- Digital Ocean CLI (doctl) installed and configured

## Deployment Options

### Option 1: Digital Ocean App Platform (Recommended)

1. **Create App Spec File** (`app-backend.yaml`):
```yaml
name: recruitment-backend
services:
- name: api
  source_dir: /
  github:
    repo: your-username/your-repo
    branch: main
  run_command: uvicorn app:app --host 0.0.0.0 --port $PORT
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 8000
  routes:
  - path: /
  health_check:
    http_path: /health
  envs:
  - key: DATABASE_URL
    value: sqlite:///./recruitment_mvp.db
  - key: DEBUG
    value: "False"
  - key: HOST
    value: "0.0.0.0"
  - key: PORT
    value: "8000"
  # Add other environment variables from env-1 file
```

2. **Deploy using doctl**:
```bash
doctl apps create --spec app-backend.yaml
```

### Option 2: Digital Ocean Droplet with Docker

1. **Create a Droplet**:
```bash
doctl compute droplet create recruitment-backend \
  --image docker-20-04 \
  --size s-1vcpu-1gb \
  --region nyc1 \
  --ssh-keys your-ssh-key-id
```

2. **SSH into the droplet and deploy**:
```bash
# Clone your repository
git clone https://github.com/your-username/your-repo.git
cd your-repo

# Build and run the backend
docker build -f Dockerfile.backend -t recruitment-backend .
docker run -d -p 8000:8000 --name backend recruitment-backend
```

### Option 3: Digital Ocean Container Registry + App Platform

1. **Build and push to registry**:
```bash
# Build the image
docker build -f Dockerfile.backend -t recruitment-backend .

# Tag for Digital Ocean registry
docker tag recruitment-backend registry.digitalocean.com/your-registry/recruitment-backend:latest

# Push to registry
docker push registry.digitalocean.com/your-registry/recruitment-backend:latest
```

2. **Create App Spec for container**:
```yaml
name: recruitment-backend
services:
- name: api
  image:
    registry_type: DOCR
    repository: recruitment-backend
    tag: latest
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 8000
  routes:
  - path: /
  health_check:
    http_path: /health
```

## Environment Variables Setup

Create these environment variables in Digital Ocean App Platform:

### Required Variables:
- `DATABASE_URL`: Your database connection string
- `DEBUG`: Set to "False" for production
- `HOST`: "0.0.0.0"
- `PORT`: "8000"

### Optional Variables (from env-1):
- `SENDGRID_API_KEY`: Your SendGrid API key
- `SENDGRID_FROM_EMAIL`: Verified sender email
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `APIFY_API_TOKEN`: Apify API token
- `CLERK_SECRET_KEY`: Clerk authentication key

## Database Setup

### For Production:
1. **Create a managed PostgreSQL database**:
```bash
doctl databases create recruitment-db \
  --engine pg \
  --version 15 \
  --size db-s-1vcpu-1gb \
  --region nyc1
```

2. **Update DATABASE_URL** to use PostgreSQL:
```
postgresql://username:password@host:port/database?sslmode=require
```

### For Development:
- SQLite database will be created automatically
- Data will persist in the container volume

## SSL/HTTPS Setup

Digital Ocean App Platform automatically provides SSL certificates for custom domains.

1. **Add custom domain** in the App Platform dashboard
2. **Update DNS** to point to the provided endpoint
3. **SSL certificate** will be automatically provisioned

## Monitoring and Logs

1. **View logs**:
```bash
doctl apps logs your-app-id --type run
```

2. **Monitor health**:
- Health check endpoint: `https://your-app.ondigitalocean.app/health`
- App Platform dashboard provides metrics

## Scaling

To scale the backend:
```bash
doctl apps update your-app-id --spec updated-app-spec.yaml
```

Update the `instance_count` in your app spec file.

## Troubleshooting

### Common Issues:

1. **Module not found error**:
   - Ensure `app.py` is in the root directory
   - Check that all dependencies are in `requirements.txt`

2. **Database connection issues**:
   - Verify DATABASE_URL format
   - Check database credentials and network access

3. **Environment variables not loading**:
   - Ensure all required variables are set in App Platform
   - Check variable names match exactly

### Debug Commands:
```bash
# Check app status
doctl apps get your-app-id

# View recent deployments
doctl apps list-deployments your-app-id

# Restart the app
doctl apps create-deployment your-app-id
```