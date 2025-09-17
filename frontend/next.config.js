/**
 * Next.js configuration adding a dev-time proxy so the frontend can call
 * relative /api/* paths without hardcoding the backend port.
 */
// Default backend port aligned with current dev uvicorn (8011). Override with BACKEND_URL env if needed.
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8011';

module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${BACKEND_URL}/api/:path*`,
      },
      {
        source: '/auth/:path*',
        destination: `${BACKEND_URL}/auth/:path*`,
      },
    ];
  },
};
