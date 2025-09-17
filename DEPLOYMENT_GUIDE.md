# Deployment Guide - Separate Frontend & Backend

This guide covers deploying the AI Recruitment Platform with separate frontend (Vercel) and backend (Digital Ocean) deployments.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │
│   (Vercel)      │◄──►│ (Digital Ocean) │
│   Next.js       │    │   FastAPI       │
│   Port: 3000    │    │   Port: 8000    │
└─────────────────┘    └─────────────────┘
```

## 📁 Project Structure

After separation, you have two independent deployable projects:

```
├── backend_new/          # Deploy to Digital Ocean
│   ├── app/             # FastAPI application
│   ├── requirements.txt # Python dependencies
│   ├── Dockerfile       # Docker configuration
│   ├── backend-app.yaml # Digital Ocean App Platform config
│   └── README.md        # Backend documentation
│
└── frontend_new/        # Deploy to Vercel
    ├── app/            # Next.js application
    ├── package.json    # Node.js dependencies
    ├── vercel.json     # Vercel configuration
    └── README.md       # Frontend documentation
```

## 🚀 Backend Deployment (Digital Ocean)

### Prerequisites
- Digital Ocean account
- Docker installed (for local testing)
- Domain name (optional)

### Method 1: Digital Ocean App Platform (Recommended)

1. **Prepare Repository**
   ```bash
   cd backend_new
   git init
   git add .
   git commit -m "Initial backend commit"
   git remote add origin https://github.com/yourusername/your-backend-repo.git
   git push -u origin main
   ```

2. **Create App on Digital Ocean**
   - Go to Digital Ocean App Platform
   - Click "Create App"
   - Connect your GitHub repository
   - Select the `backend_new` directory as source
   - Use the `backend-app.yaml` configuration

3. **Configure Environment Variables**
   ```bash
   DATABASE_URL=postgresql://user:pass@host:port/db
   OPENAI_API_KEY=your-openai-key
   SENDGRID_API_KEY=your-sendgrid-key
   APIFY_API_TOKEN=your-apify-token
   ```

4. **Deploy**
   - Click "Create Resources"
   - Wait for deployment to complete
   - Note your backend URL (e.g., `https://your-app.ondigitalocean.app`)

### Method 2: Digital Ocean Droplet with Docker

1. **Create Droplet**
   ```bash
   # Create Ubuntu 22.04 droplet
   # SSH into your droplet
   ssh root@your-droplet-ip
   ```

2. **Install Docker**
   ```bash
   apt update
   apt install docker.io docker-compose -y
   systemctl start docker
   systemctl enable docker
   ```

3. **Deploy Application**
   ```bash
   git clone https://github.com/yourusername/your-backend-repo.git
   cd your-backend-repo/backend_new
   
   # Build and run
   docker build -t recruitment-backend .
   docker run -d -p 8000:8000 --env-file .env recruitment-backend
   ```

## 🌐 Frontend Deployment (Vercel)

### Prerequisites
- Vercel account
- GitHub repository
- Backend URL from previous step

### Method 1: Vercel Dashboard (Recommended)

1. **Prepare Repository**
   ```bash
   cd frontend_new
   git init
   git add .
   git commit -m "Initial frontend commit"
   git remote add origin https://github.com/yourusername/your-frontend-repo.git
   git push -u origin main
   ```

2. **Deploy on Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your GitHub repository
   - Select `frontend_new` as root directory
   - Configure environment variables:
     ```bash
     NEXT_PUBLIC_API_URL=https://your-backend-url.ondigitalocean.app
     NEXTAUTH_URL=https://your-frontend-domain.vercel.app
     NEXTAUTH_SECRET=your-secret-key
     ```
   - Click "Deploy"

### Method 2: Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **Deploy**
   ```bash
   cd frontend_new
   vercel
   # Follow the prompts
   ```

## 🔧 Configuration

### Backend Configuration

1. **CORS Settings**
   Update `app/core/config.py`:
   ```python
   ALLOWED_HOSTS = [
       "https://your-frontend-domain.vercel.app",
       "http://localhost:3000"  # for development
   ]
   ```

2. **Database Setup**
   ```bash
   # In your backend
   alembic upgrade head
   ```

### Frontend Configuration

1. **API Integration**
   Update `frontend_new/.env.local`:
   ```bash
   NEXT_PUBLIC_API_URL=https://your-backend-url.ondigitalocean.app
   ```

2. **Build Configuration**
   The `vercel.json` handles:
   - API proxying
   - Environment variables
   - Build optimization

## 🔍 Testing Deployment

### Backend Testing
```bash
curl https://your-backend-url.ondigitalocean.app/health
curl https://your-backend-url.ondigitalocean.app/docs
```

### Frontend Testing
```bash
# Visit your Vercel URL
https://your-frontend-domain.vercel.app

# Check API connectivity in browser console
fetch('/api/health')
```

## 🚨 Troubleshooting

### Common Backend Issues

1. **Database Connection**
   ```bash
   # Check DATABASE_URL format
   postgresql://username:password@host:port/database
   ```

2. **Environment Variables**
   ```bash
   # Verify all required vars are set
   echo $OPENAI_API_KEY
   ```

3. **Port Issues**
   ```bash
   # Ensure app runs on 0.0.0.0:8000
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

### Common Frontend Issues

1. **API Connection**
   - Check CORS settings in backend
   - Verify `NEXT_PUBLIC_API_URL` is correct
   - Ensure backend is accessible

2. **Build Errors**
   ```bash
   # Check build logs in Vercel dashboard
   # Verify all dependencies in package.json
   ```

3. **Environment Variables**
   - Ensure all `NEXT_PUBLIC_*` vars are set in Vercel
   - Check variable names match exactly

## 📊 Monitoring & Maintenance

### Backend Monitoring
- Digital Ocean App Platform provides built-in monitoring
- Set up alerts for CPU/memory usage
- Monitor API response times

### Frontend Monitoring
- Vercel provides analytics and performance metrics
- Monitor Core Web Vitals
- Set up error tracking (Sentry)

## 🔄 CI/CD Pipeline

### Automatic Deployments

1. **Backend**: Digital Ocean auto-deploys on git push to main
2. **Frontend**: Vercel auto-deploys on git push to main

### Manual Deployments

```bash
# Backend
git push origin main  # Triggers DO deployment

# Frontend  
git push origin main  # Triggers Vercel deployment
```

## 💰 Cost Estimation

### Digital Ocean (Backend)
- Basic App: $5-12/month
- Professional App: $12-24/month
- Database: $15-25/month

### Vercel (Frontend)
- Hobby: Free (with limits)
- Pro: $20/month per user
- Enterprise: Custom pricing

## 🔐 Security Considerations

1. **Environment Variables**: Never commit secrets to git
2. **CORS**: Configure properly for production domains
3. **HTTPS**: Both platforms provide SSL certificates
4. **API Keys**: Rotate regularly and use least privilege
5. **Database**: Use connection pooling and proper authentication

## 📚 Additional Resources

- [Digital Ocean App Platform Docs](https://docs.digitalocean.com/products/app-platform/)
- [Vercel Deployment Docs](https://vercel.com/docs)
- [Next.js Deployment Guide](https://nextjs.org/docs/deployment)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)

## 🆘 Support

If you encounter issues:

1. Check deployment logs in respective platforms
2. Verify environment variables
3. Test API endpoints individually
4. Check network connectivity between services
5. Review CORS and authentication settings

---

**Success!** 🎉 Your AI Recruitment Platform is now deployed with separate, scalable frontend and backend services!