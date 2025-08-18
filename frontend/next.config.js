/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.BACKEND_URL ? `${process.env.BACKEND_URL}/:path*` : 'http://backend:8000/:path*',
      },
    ];
  },
  images: {
    domains: ['example.com'], // Add any external image domains you need
  },
};

module.exports = nextConfig; 