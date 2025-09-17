# Frontend Deployment Guide - Digital Ocean

## Prerequisites
- Digital Ocean account
- Docker installed locally
- Digital Ocean CLI (doctl) installed and configured
- Backend service deployed and accessible

## Deployment Options

### Option 1: Digital Ocean App Platform (Recommended)

1. **Create App Spec File** (`app-frontend.yaml`):
```yaml
name: recruitment-frontend
services:
- name: web
  source_dir: /
  github:
    repo: your-username/your-repo
    branch: main
  build_command: npm run build
  run_command: npm start
  environment_slug: node-js
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 3000
  routes:
  - path: /
  envs:
  - key: NODE_ENV
    value: production
  - key: NEXT_PUBLIC_API_URL
    value: https://your-backend-app.ondigitalocean.app
  - key: PORT
    value: "3000"
```

2. **Deploy using doctl**:
```bash
doctl apps create --spec app-frontend.yaml
```

### Option 2: Static Site Deployment

Since Next.js can be exported as static files:

1. **Update next.config.js for static export**:
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true
  }
};

module.exports = nextConfig;
```

2. **Build and deploy to Digital Ocean Spaces**:
```bash
# Build static files
npm run build

# Upload to Digital Ocean Spaces (CDN)
doctl compute cdn create --origin spaces-bucket.nyc3.digitaloceanspaces.com
```

### Option 3: Digital Ocean Droplet with Docker

1. **Create a Droplet**:
```bash
doctl compute droplet create recruitment-frontend \
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

# Build and run the frontend
docker build -f Dockerfile.frontend -t recruitment-frontend .
docker run -d -p 3000:3000 --name frontend \
  -e NEXT_PUBLIC_API_URL=https://your-backend-app.ondigitalocean.app \
  recruitment-frontend
```

### Option 4: Digital Ocean Container Registry + App Platform

1. **Build and push to registry**:
```bash
# Build the image
docker build -f Dockerfile.frontend -t recruitment-frontend .

# Tag for Digital Ocean registry
docker tag recruitment-frontend registry.digitalocean.com/your-registry/recruitment-frontend:latest

# Push to registry
docker push registry.digitalocean.com/your-registry/recruitment-frontend:latest
```

2. **Create App Spec for container**:
```yaml
name: recruitment-frontend
services:
- name: web
  image:
    registry_type: DOCR
    repository: recruitment-frontend
    tag: latest
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 3000
  routes:
  - path: /
  envs:
  - key: NODE_ENV
    value: production
  - key: NEXT_PUBLIC_API_URL
    value: https://your-backend-app.ondigitalocean.app
```

## Environment Variables Setup

Create these environment variables in Digital Ocean App Platform:

### Required Variables:
- `NODE_ENV`: "production"
- `NEXT_PUBLIC_API_URL`: Your backend API URL
- `PORT`: "3000"

### Optional Variables:
- `NEXT_PUBLIC_SUPABASE_URL`: If using Supabase
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Supabase anonymous key
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`: Clerk authentication key

## Custom Domain Setup

1. **Add custom domain** in App Platform:
```bash
doctl apps update your-app-id --spec updated-app-spec.yaml
```

2. **Update DNS records**:
   - Add CNAME record pointing to your app's URL
   - SSL certificate will be automatically provisioned

3. **Example DNS configuration**:
```
Type: CNAME
Name: www
Value: your-app-hash.ondigitalocean.app
TTL: 3600
```

## Performance Optimization

### 1. Enable Compression
App Platform automatically enables gzip compression.

### 2. CDN Configuration
```yaml
# Add to your app spec
static_sites:
- name: assets
  source_dir: /public
  routes:
  - path: /static
  catchall_document: index.html
```

### 3. Caching Headers
Next.js automatically sets appropriate cache headers for static assets.

## Monitoring and Analytics

1. **View application logs**:
```bash
doctl apps logs your-app-id --type build
doctl apps logs your-app-id --type run
```

2. **Monitor performance**:
   - Use Digital Ocean's built-in monitoring
   - Set up alerts for response time and availability

3. **Analytics integration**:
   - Add Google Analytics or similar to your Next.js app
   - Monitor user behavior and performance metrics

## CI/CD Pipeline

### GitHub Actions Integration

1. **Create `.github/workflows/deploy.yml`**:
```yaml
name: Deploy to Digital Ocean

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Install doctl
      uses: digitalocean/action-doctl@v2
      with:
        token: ${{ secrets.DIGITALOCEAN_ACCESS_TOKEN }}
    
    - name: Deploy to App Platform
      run: |
        doctl apps create-deployment ${{ secrets.APP_ID }}
```

2. **Set up secrets** in GitHub:
   - `DIGITALOCEAN_ACCESS_TOKEN`
   - `APP_ID`

## Scaling and Load Balancing

### Horizontal Scaling
```yaml
# Update app spec
services:
- name: web
  instance_count: 3  # Scale to 3 instances
  instance_size_slug: basic-xs
```

### Auto-scaling (App Platform Pro)
```yaml
autoscaling:
  min_instance_count: 1
  max_instance_count: 5
  metrics:
  - type: cpu
    target: 70
```

## Troubleshooting

### Common Issues:

1. **Build failures**:
   - Check Node.js version compatibility
   - Verify all dependencies are in package.json
   - Review build logs for specific errors

2. **API connection issues**:
   - Verify NEXT_PUBLIC_API_URL is correct
   - Check CORS settings on backend
   - Ensure backend is accessible from frontend

3. **Static asset loading issues**:
   - Check public folder structure
   - Verify image optimization settings
   - Review Next.js configuration

### Debug Commands:
```bash
# Check app status
doctl apps get your-app-id

# View build logs
doctl apps logs your-app-id --type build --follow

# View runtime logs
doctl apps logs your-app-id --type run --follow

# Restart the app
doctl apps create-deployment your-app-id
```

## Security Considerations

1. **Environment Variables**:
   - Never expose sensitive keys in NEXT_PUBLIC_ variables
   - Use server-side API routes for sensitive operations

2. **Content Security Policy**:
   - Configure CSP headers in next.config.js
   - Restrict external resource loading

3. **HTTPS Enforcement**:
   - Digital Ocean App Platform enforces HTTPS by default
   - Redirect HTTP to HTTPS automatically

## Cost Optimization

1. **Right-sizing instances**:
   - Start with basic-xxs for low traffic
   - Monitor resource usage and scale as needed

2. **Static asset optimization**:
   - Use Next.js Image optimization
   - Implement proper caching strategies

3. **CDN usage**:
   - Leverage Digital Ocean Spaces for static assets
   - Reduce bandwidth costs with CDN