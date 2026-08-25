/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // Strip console.log/warn in production builds (keep console.error for debugging)
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production'
      ? { exclude: ['error'] }
      : false,
  },
  async rewrites() {
    // In Docker, use backend service name; locally use localhost
    const backendUrl = process.env.BACKEND_URL || 
                      (process.env.NODE_ENV === 'production' ? 'http://backend:8000' : 'http://backend:8000');
    
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
  images: {
    domains: ['example.com'], // Add any external image domains you need
  },
};

module.exports = nextConfig; 