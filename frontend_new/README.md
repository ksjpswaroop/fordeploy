# AI Recruitment Platform - Frontend

A modern Next.js frontend for the AI-driven recruitment platform.

## Features

- **Next.js 14** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **Responsive Design** for all devices
- **Authentication** integration
- **Real-time Updates** 
- **Modern UI/UX** components

## Quick Start

### Local Development

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Environment Setup**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your configuration
   ```

3. **Run Development Server**
   ```bash
   npm run dev
   ```

   Open [http://localhost:3000](http://localhost:3000) in your browser.

### Vercel Deployment

#### Option 1: Deploy via Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **Deploy**
   ```bash
   vercel
   ```

#### Option 2: Deploy via GitHub Integration

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Frontend ready for deployment"
   git push origin main
   ```

2. **Connect to Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Configure environment variables
   - Deploy automatically

## Environment Variables

Set these in your Vercel dashboard or `.env.local`:

```bash
NEXT_PUBLIC_API_URL=https://your-backend-api.com
NEXTAUTH_URL=https://your-frontend-domain.com
NEXTAUTH_SECRET=your-secret-key
```

## Project Structure

```
frontend_new/
├── app/                    # Next.js App Router
│   ├── admin/             # Admin dashboard
│   ├── jobs/              # Job management
│   ├── login/             # Authentication
│   ├── pipeline/          # Recruitment pipeline
│   ├── search/            # Candidate search
│   ├── settings/          # User settings
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Home page
├── components/            # Reusable components
├── lib/                   # Utility functions
├── public/               # Static assets
├── styles/               # Global styles
├── package.json          # Dependencies
├── next.config.js        # Next.js configuration
├── tailwind.config.js    # Tailwind configuration
└── vercel.json           # Vercel deployment config
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript checks

## Deployment Configuration

The `vercel.json` file includes:
- Framework detection
- Environment variable mapping
- API route proxying to backend
- Build optimization

## Backend Integration

The frontend connects to the FastAPI backend via:
- API calls to `NEXT_PUBLIC_API_URL`
- Authentication token management
- Real-time data synchronization

## Development Tips

1. **API Integration**: Update `NEXT_PUBLIC_API_URL` to point to your backend
2. **Authentication**: Configure NextAuth.js for your auth provider
3. **Styling**: Use Tailwind CSS classes for consistent design
4. **Type Safety**: Leverage TypeScript for better development experience

## Production Deployment

1. **Build Optimization**: Next.js automatically optimizes for production
2. **Environment Variables**: Set all required env vars in Vercel dashboard
3. **Domain Configuration**: Configure custom domain in Vercel settings
4. **Performance**: Monitor Core Web Vitals in Vercel Analytics

## Support

For deployment issues:
- Check Vercel deployment logs
- Verify environment variables
- Ensure backend API is accessible
- Review CORS configuration