/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
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