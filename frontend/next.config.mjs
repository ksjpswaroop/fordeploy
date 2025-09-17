/** Basic Next.js config */
const nextConfig = {
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  output: 'standalone', // Optimized for serverless deployment
  env: {
    // If not provided, we still use '/api' but component code now falls back to external API
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || '/api'
  },
  async rewrites() {
    // Dev convenience: proxy frontend /api/* -> backend http://localhost:<port>/api/*
    // In production, API calls should go to NEXT_PUBLIC_API_BASE_URL
    if (process.env.NODE_ENV === 'development') {
      const port = process.env.DEV_BACKEND_PORT || '8000'
      return [
        {
          source: '/api/:path*',
          destination: `http://localhost:${port}/api/:path*`
        },
        {
          source: '/auth/:path*',
          destination: `http://localhost:${port}/auth/:path*`
        },
        {
          source: '/health',
          destination: `http://localhost:${port}/health`
        }
      ]
    }
    return []
  }
};
export default nextConfig;
