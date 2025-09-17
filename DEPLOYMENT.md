# Deployment Guide - AI-Driven Recruitment Platform

This guide covers deploying both the frontend (Next.js) and backend (FastAPI) services as separate applications on Digital Ocean.

## 🚀 Quick Start

### Prerequisites
- Digital Ocean account
- GitHub repository with your code
- Domain name (optional)
- Digital Ocean CLI (`doctl`) installed

### 1. Prepare Your Repository

Ensure your repository has these files:
- `app.py` - FastAPI backend application
- `requirements.txt` - Python dependencies
- `package.json` - Node.js dependencies
- `Dockerfile.backend` - Backend container configuration
- `Dockerfile.frontend` - Frontend container configuration
- `app-backend.yaml` - Backend deployment spec
- `app-frontend.yaml` - Frontend deployment spec

### 2. Set Up Environment Variables

1. Copy `.env.example` to `.env` and fill in your values
2. Update the App Platform spec files with your actual values
3. Never commit sensitive keys to your repository

### 3. Deploy Backend Service

```bash
# Update app-backend.yaml with your repository details
# Then deploy:
doctl apps create --spec app-backend.yaml
```

### 4. Deploy Frontend Service

```bash
# Update app-frontend.yaml with your repository details and backend URL
# Then deploy:
doctl apps create --spec app-frontend.yaml
```

## 📋 Detailed Deployment Steps

### Backend Deployment

1. **Update Backend App Spec** (`app-backend.yaml`):
   ```yaml
   github:
     repo: your-username/your-repo-name
     branch: main
   ```

2. **Configure Environment Variables**:
   - Update all `your-*` placeholders with actual values
   - Set sensitive variables as `type: SECRET`
   - Ensure `BASE_URL` matches your deployed backend URL

3. **Deploy**:
   ```bash
   doctl apps create --spec app-backend.yaml
   ```

4. **Get Backend URL**:
   ```bash
   doctl apps list
   # Note the URL for your backend app
   ```

### Frontend Deployment

1. **Update Frontend App Spec** (`app-frontend.yaml`):
   ```yaml
   github:
     repo: your-username/your-repo-name
     branch: main
   envs:
   - key: NEXT_PUBLIC_API_URL
     value: "https://your-backend-url.ondigitalocean.app"
   ```

2. **Deploy**:
   ```bash
   doctl apps create --spec app-frontend.yaml
   ```

## 🔧 Configuration Details

### Backend Configuration

**Required Environment Variables:**
- `DATABASE_URL` - Database connection string
- `SENDGRID_API_KEY` - Email service API key
- `OPENAI_API_KEY` - AI service API key
- `CLERK_SECRET_KEY` - Authentication service key

**Optional but Recommended:**
- `ANTHROPIC_API_KEY` - Alternative AI service
- `APIFY_API_TOKEN` - Web scraping service
- `SUPABASE_SERVICE_ROLE_KEY` - Database service

### Frontend Configuration

**Required Environment Variables:**
- `NEXT_PUBLIC_API_URL` - Backend API URL
- `NODE_ENV` - Set to "production"

**Optional:**
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - Authentication
- `NEXT_PUBLIC_SUPABASE_URL` - Database service
- `NEXT_PUBLIC_GA_TRACKING_ID` - Analytics

## 🗄️ Database Setup

### Development (SQLite)
The backend uses SQLite by default, which is suitable for development and small-scale production.

### Production (PostgreSQL)
For production, use Digital Ocean's managed PostgreSQL:

1. **Create Database**:
   ```bash
   doctl databases create recruitment-db \
     --engine pg \
     --version 15 \
     --size db-s-1vcpu-1gb \
     --region nyc1
   ```

2. **Update Backend Environment**:
   ```yaml
   - key: DATABASE_URL
     value: "postgresql://username:password@host:port/database?sslmode=require"
     type: SECRET
   ```

## 🔒 Security Checklist

- [ ] All API keys are set as `type: SECRET`
- [ ] Database uses SSL connections
- [ ] CORS is properly configured
- [ ] No sensitive data in public environment variables
- [ ] HTTPS is enforced (automatic with App Platform)
- [ ] Authentication is properly configured

## 📊 Monitoring & Maintenance

### Health Checks
Both services include health check endpoints:
- Backend: `https://your-backend.ondigitalocean.app/health`
- Frontend: `https://your-frontend.ondigitalocean.app/`

### Viewing Logs
```bash
# Backend logs
doctl apps logs your-backend-app-id --type run

# Frontend logs
doctl apps logs your-frontend-app-id --type run
```

### Scaling
Update the `instance_count` in your app spec files and redeploy:
```bash
doctl apps update your-app-id --spec updated-app-spec.yaml
```

## 🚨 Troubleshooting

### Common Issues

1. **Backend "Module not found" error**:
   - Ensure `app.py` is in the repository root
   - Check `requirements.txt` includes all dependencies

2. **Frontend can't connect to backend**:
   - Verify `NEXT_PUBLIC_API_URL` is correct
   - Check CORS configuration in backend
   - Ensure backend is deployed and healthy

3. **Database connection issues**:
   - Verify `DATABASE_URL` format
   - Check database credentials
   - Ensure SSL mode is set for PostgreSQL

4. **Build failures**:
   - Check build logs: `doctl apps logs your-app-id --type build`
   - Verify all dependencies are listed
   - Check for syntax errors

### Debug Commands
```bash
# Check app status
doctl apps get your-app-id

# View deployments
doctl apps list-deployments your-app-id

# Restart app
doctl apps create-deployment your-app-id

# View real-time logs
doctl apps logs your-app-id --type run --follow
```

## 💰 Cost Optimization

### Instance Sizing
- Start with `basic-xxs` for both services
- Monitor resource usage and scale as needed
- Use horizontal scaling for high traffic

### Database
- Use SQLite for development/low traffic
- Upgrade to managed PostgreSQL for production
- Consider read replicas for high-read workloads

## 🔄 CI/CD Pipeline

### GitHub Actions
Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Digital Ocean

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Install doctl
      uses: digitalocean/action-doctl@v2
      with:
        token: ${{ secrets.DIGITALOCEAN_ACCESS_TOKEN }}
    - name: Deploy Backend
      run: doctl apps create-deployment ${{ secrets.BACKEND_APP_ID }}

  deploy-frontend:
    runs-on: ubuntu-latest
    needs: deploy-backend
    steps:
    - uses: actions/checkout@v2
    - name: Install doctl
      uses: digitalocean/action-doctl@v2
      with:
        token: ${{ secrets.DIGITALOCEAN_ACCESS_TOKEN }}
    - name: Deploy Frontend
      run: doctl apps create-deployment ${{ secrets.FRONTEND_APP_ID }}
```

### Required Secrets
Add these to your GitHub repository secrets:
- `DIGITALOCEAN_ACCESS_TOKEN`
- `BACKEND_APP_ID`
- `FRONTEND_APP_ID`

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review Digital Ocean App Platform documentation
3. Check service health endpoints
4. Review application logs

## 🎯 Next Steps

After successful deployment:
1. Set up custom domains
2. Configure monitoring and alerts
3. Implement backup strategies
4. Set up staging environments
5. Configure CDN for static assets