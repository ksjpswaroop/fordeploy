# Vercel Deployment Guide for AI Recruitment Platform

This guide will help you deploy your AI-driven recruitment platform to Vercel, including both the Next.js frontend and FastAPI backend.

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **GitHub Repository**: Your code should be in a GitHub repository
3. **Database**: Set up a cloud database (recommended: Supabase)
4. **External Services**: API keys for OpenAI, Clerk, etc.

## Project Structure

```
ai_driven_recruitment_backend-main 2/
├── frontend/                 # Next.js frontend
│   ├── package.json
│   ├── next.config.mjs
│   ├── vercel.json          # Frontend-specific config
│   └── .env.local.example   # Frontend environment variables
├── app/                     # FastAPI backend
│   ├── main.py             # Main FastAPI application
│   └── ...
├── vercel_handler.py       # Vercel serverless handler
├── vercel.json            # Root deployment configuration
├── requirements.txt       # Python dependencies
├── .env.production.example # Backend environment variables
└── VERCEL_DEPLOYMENT.md   # This guide
```

## Step 1: Prepare Your Environment Variables

### Backend Environment Variables

Copy `.env.production.example` and set up these variables in your Vercel project:

**Required Variables:**
- `ENVIRONMENT=production`
- `SECRET_KEY` - Generate a secure secret key
- `DATABASE_URL` - Your PostgreSQL database URL
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase anon key
- `JWT_SECRET_KEY` - JWT signing key
- `OPENAI_API_KEY` - OpenAI API key

**Optional Variables:**
- `CLERK_SECRET_KEY` - If using Clerk authentication
- `SMTP_*` - Email configuration
- `REDIS_URL` - For caching (optional)

### Frontend Environment Variables

Create a `.env.local` file in the `frontend/` directory:

```bash
# Point to your deployed backend
NEXT_PUBLIC_API_BASE_URL=https://your-vercel-app.vercel.app/api

# Development token (if needed)
NEXT_PUBLIC_DEV_BEARER=your-dev-token
```

## Step 2: Deploy to Vercel

### Option A: Deploy via Vercel Dashboard

1. **Connect Repository**:
   - Go to [vercel.com/dashboard](https://vercel.com/dashboard)
   - Click "New Project"
   - Import your GitHub repository

2. **Configure Build Settings**:
   - **Framework Preset**: Other
   - **Root Directory**: Leave empty (uses root)
   - **Build Command**: Leave empty (handled by vercel.json)
   - **Output Directory**: Leave empty (handled by vercel.json)

3. **Add Environment Variables**:
   - In project settings, add all the environment variables from `.env.production.example`
   - Make sure to set `ENVIRONMENT=production`

4. **Deploy**:
   - Click "Deploy"
   - Wait for the build to complete

### Option B: Deploy via Vercel CLI

1. **Install Vercel CLI**:
   ```bash
   npm i -g vercel
   ```

2. **Login and Deploy**:
   ```bash
   vercel login
   vercel --prod
   ```

3. **Set Environment Variables**:
   ```bash
   vercel env add ENVIRONMENT production
   vercel env add SECRET_KEY your-secret-key
   vercel env add DATABASE_URL your-database-url
   # ... add all other variables
   ```

## Step 3: Configure Your Database

### Using Supabase (Recommended)

1. **Create Supabase Project**:
   - Go to [supabase.com](https://supabase.com)
   - Create a new project
   - Note your project URL and anon key

2. **Set Environment Variables**:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
   ```

3. **Run Migrations**:
   - Your FastAPI app will automatically create tables on startup
   - Or run migrations manually if needed

## Step 4: Verify Deployment

1. **Check Backend Health**:
   ```bash
   curl https://your-app.vercel.app/health
   ```

2. **Check Frontend**:
   - Visit `https://your-app.vercel.app`
   - Verify login functionality
   - Test API endpoints

3. **Check Logs**:
   - Go to Vercel dashboard → Functions tab
   - Monitor serverless function logs for errors

## Step 5: Custom Domain (Optional)

1. **Add Domain**:
   - In Vercel dashboard, go to Settings → Domains
   - Add your custom domain
   - Configure DNS records as instructed

2. **Update Environment Variables**:
   - Update `CORS_ORIGINS` to include your custom domain
   - Update `NEXT_PUBLIC_API_BASE_URL` if needed

## Troubleshooting

### Common Issues

1. **Build Failures**:
   - Check that all dependencies are in `requirements.txt`
   - Verify Python version compatibility (3.9)
   - Check for missing environment variables

2. **CORS Errors**:
   - Ensure `CORS_ORIGINS` includes your frontend domain
   - Check that credentials are properly configured

3. **Database Connection Issues**:
   - Verify `DATABASE_URL` format
   - Check database permissions
   - Ensure database is accessible from Vercel

4. **Authentication Issues**:
   - Verify JWT secret keys match
   - Check Clerk configuration if using
   - Ensure cookies are properly configured

### Performance Optimization

1. **Cold Start Optimization**:
   - Keep dependencies minimal
   - Use connection pooling for database
   - Consider warming functions with cron jobs

2. **Static File Handling**:
   - Use Vercel's CDN for static assets
   - Optimize images and documents

## Monitoring and Maintenance

1. **Set up Monitoring**:
   - Use Vercel Analytics
   - Monitor function execution times
   - Set up error alerting

2. **Regular Updates**:
   - Keep dependencies updated
   - Monitor security advisories
   - Test deployments in staging first

## Environment-Specific Configuration

### Development vs Production

The application automatically detects the environment:

- **Development**: Uses local backend proxy via Next.js rewrites
- **Production**: Uses `NEXT_PUBLIC_API_BASE_URL` for API calls

### Database Migrations

For production deployments:

1. **Automatic**: Tables are created on first startup
2. **Manual**: Use Alembic for complex migrations
3. **Backup**: Always backup before major updates

## Security Considerations

1. **Environment Variables**:
   - Never commit secrets to version control
   - Use Vercel's encrypted environment variables
   - Rotate keys regularly

2. **CORS Configuration**:
   - Use specific origins instead of "*" in production
   - Enable credentials only when necessary

3. **Authentication**:
   - Use strong JWT secrets
   - Implement proper session management
   - Consider rate limiting

## Support

If you encounter issues:

1. Check Vercel function logs
2. Review this deployment guide
3. Check the main README.md for application-specific help
4. Consult Vercel documentation for platform-specific issues

---

**Next Steps**: After successful deployment, consider setting up:
- Monitoring and alerting
- Automated testing pipeline
- Staging environment
- Database backups
- Performance monitoring