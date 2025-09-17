# DigitalOcean App Platform Deployment Guide

This guide explains how to deploy the AI-Driven Recruitment Platform using DigitalOcean's App Platform, which provides automatic deployment from GitHub.

## Overview

DigitalOcean App Platform is a Platform-as-a-Service (PaaS) that automatically builds, deploys, and scales your applications directly from your GitHub repository. It's different from the Docker-based Droplet deployment and offers several advantages:

### App Platform vs Droplet Deployment

| Feature | App Platform | Droplet (Docker) |
|---------|-------------|------------------|
| **Setup Complexity** | Simple | Complex |
| **Automatic Scaling** | ✅ Built-in | ❌ Manual |
| **SSL/TLS** | ✅ Automatic | ❌ Manual setup |
| **Load Balancing** | ✅ Built-in | ❌ Manual |
| **Database Management** | ✅ Managed | ❌ Self-managed |
| **Monitoring** | ✅ Built-in | ❌ Manual setup |
| **Cost** | Higher | Lower |
| **Control** | Limited | Full |

## Prerequisites

1. **GitHub Repository**: Your code must be in a GitHub repository
2. **DigitalOcean Account**: With billing enabled
3. **Environment Variables**: Prepared for production

## Quick Deployment Steps

### 1. Prepare Your Repository

Ensure your repository has the App Platform configuration file:

```bash
# The configuration file should be at one of these locations:
.do/app.yaml          # Preferred location
app.yaml              # Alternative location
```

### 2. Connect to DigitalOcean

1. Log in to your DigitalOcean account
2. Go to **Apps** in the control panel
3. Click **Create App**
4. Choose **GitHub** as your source
5. Authorize DigitalOcean to access your GitHub account
6. Select your repository and branch (usually `main`)

### 3. Configure Your App

DigitalOcean will automatically detect the `app.yaml` configuration file. Review the detected configuration:

- **Services**: API backend and web frontend
- **Database**: PostgreSQL database
- **Environment Variables**: Will need to be set

### 4. Set Environment Variables

In the App Platform dashboard, configure these environment variables:

#### Required Secrets
```env
JWT_SECRET_KEY=your_jwt_secret_here
OPENAI_API_KEY=your_openai_api_key
CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_SECRET_KEY=your_clerk_secret_key
CLERK_JWT_SECRET_BASE64=your_clerk_jwt_secret
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
REDIS_PASSWORD=your_redis_password
```

#### Optional Configuration
```env
CORS_ORIGINS=https://your-app-domain.com
APIFY_API_TOKEN=your_apify_token
GEMINI_API_KEY=your_gemini_api_key
```

### 5. Deploy

1. Click **Create Resources**
2. DigitalOcean will:
   - Create the database
   - Build your application
   - Run database migrations
   - Deploy your services
   - Assign a domain

### 6. Access Your Application

Once deployed, you'll get:
- **App URL**: `https://your-app-name-xxxxx.ondigitalocean.app`
- **API Endpoint**: `https://your-app-name-xxxxx.ondigitalocean.app/api`
- **Documentation**: `https://your-app-name-xxxxx.ondigitalocean.app/docs`

## Configuration Details

### App Platform Configuration (`app.yaml`)

The configuration includes:

#### Services
- **API Service**: FastAPI backend with health checks
- **Web Service**: Next.js frontend
- **Redis Service**: Caching layer

#### Database
- **PostgreSQL 15**: Managed database with automatic backups

#### Jobs
- **Pre-deploy Migration**: Runs database migrations before deployment

### Automatic Features

#### SSL/TLS Certificates
- Automatically provisioned and renewed
- Custom domains supported

#### Health Checks
- API: `GET /health`
- Web: `GET /`
- Automatic restart on failure

#### Scaling
- Automatic scaling based on traffic
- Manual scaling controls available

## Custom Domain Setup

### 1. Add Domain in App Platform
1. Go to your app's **Settings**
2. Click **Domains**
3. Add your custom domain
4. Note the CNAME record provided

### 2. Configure DNS
Add a CNAME record in your DNS provider:
```
Type: CNAME
Name: @ (or www)
Value: your-app-name-xxxxx.ondigitalocean.app
```

### 3. Update Environment Variables
Update `CORS_ORIGINS` and `NEXT_PUBLIC_API_BASE_URL` to use your custom domain.

## Monitoring and Logs

### Application Logs
- Access logs through the App Platform dashboard
- Real-time log streaming available
- Log retention for debugging

### Metrics
- CPU and memory usage
- Request rates and response times
- Error rates and availability

### Alerts
Configure alerts for:
- High CPU/memory usage
- Application restarts
- Error rates

## Database Management

### Managed PostgreSQL
- Automatic backups
- Point-in-time recovery
- Connection pooling
- SSL encryption

### Database Access
```bash
# Get connection details from App Platform dashboard
# Connect using psql or your preferred client
psql "postgresql://username:password@host:port/database?sslmode=require"
```

### Migrations
Migrations run automatically before each deployment via the pre-deploy job.

## Deployment Workflow

### Automatic Deployment
1. Push code to GitHub
2. App Platform detects changes
3. Builds new version
4. Runs pre-deploy jobs (migrations)
5. Deploys new version
6. Performs health checks
7. Routes traffic to new version

### Manual Deployment
- Force redeploy from App Platform dashboard
- Useful for environment variable changes

## Troubleshooting

### Common Issues

#### Build Failures
- Check build logs in App Platform dashboard
- Verify `requirements.txt` and `package.json`
- Ensure all dependencies are specified

#### Database Connection Issues
- Verify `DATABASE_URL` environment variable
- Check database service status
- Review connection limits

#### Environment Variable Issues
- Ensure all required secrets are set
- Check for typos in variable names
- Verify secret values are correct

### Debugging Steps

1. **Check Build Logs**
   ```
   App Platform Dashboard → Your App → Activity → Build Logs
   ```

2. **Review Runtime Logs**
   ```
   App Platform Dashboard → Your App → Runtime Logs
   ```

3. **Test Health Endpoints**
   ```bash
   curl https://your-app.ondigitalocean.app/health
   ```

4. **Database Connectivity**
   ```bash
   # From App Platform console
   python -c "import psycopg2; print('DB connection OK')"
   ```

## Cost Optimization

### Resource Sizing
- Start with `basic-xxs` instances
- Monitor usage and scale as needed
- Use horizontal scaling for high traffic

### Database Optimization
- Choose appropriate database size
- Enable connection pooling
- Monitor query performance

### Caching Strategy
- Use Redis for session storage
- Implement application-level caching
- Configure CDN for static assets

## Security Best Practices

### Environment Variables
- Use App Platform's secret management
- Never commit secrets to repository
- Rotate secrets regularly

### Database Security
- Use SSL connections (enabled by default)
- Implement proper access controls
- Regular security updates (automatic)

### Application Security
- Enable CORS properly
- Implement rate limiting
- Use HTTPS everywhere (automatic)

## Migration from Droplet

If migrating from a Droplet deployment:

### 1. Export Data
```bash
# Export database
pg_dump $DATABASE_URL > backup.sql

# Export uploaded files
tar -czf uploads.tar.gz uploads/
```

### 2. Import to App Platform
```bash
# Import database (after App Platform deployment)
psql $NEW_DATABASE_URL < backup.sql

# Upload files to new storage solution
```

### 3. Update DNS
Point your domain to the new App Platform URL.

## Support and Resources

### DigitalOcean Documentation
- [App Platform Documentation](https://docs.digitalocean.com/products/app-platform/)
- [App Platform Pricing](https://www.digitalocean.com/pricing/app-platform)

### Community Resources
- [DigitalOcean Community](https://www.digitalocean.com/community)
- [App Platform Tutorials](https://www.digitalocean.com/community/tags/app-platform)

### Getting Help
- DigitalOcean Support (for paid accounts)
- Community forums
- GitHub issues for application-specific problems

## Conclusion

DigitalOcean App Platform provides a streamlined deployment experience with automatic scaling, SSL, and database management. While it costs more than a Droplet, it significantly reduces operational overhead and provides enterprise-grade features out of the box.

The automatic deployment from GitHub makes it ideal for teams that want to focus on development rather than infrastructure management.