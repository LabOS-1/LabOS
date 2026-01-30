/** @type {import('next').NextConfig} */
const nextConfig = {
  // API proxy configuration
      async rewrites() {
        const backendUrl = process.env.NODE_ENV === 'production'
          ? process.env.NEXT_PUBLIC_BACKEND_URL || 'https://labos-backend-843173980594.us-central1.run.app'
          : process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:18800';

        return [
          // Proxy all /api/* requests to backend (no transformation)
          {
            source: '/api/:path*',
            destination: `${backendUrl}/api/:path*`,
          },
        ]
      },

  // WebSocket proxy (for development)
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET, POST, PUT, DELETE, OPTIONS' },
          { key: 'Access-Control-Allow-Headers', value: 'Content-Type, Authorization' },
        ],
      },
    ]
  },

  // Static file serving
  trailingSlash: false,
  
  // Image optimization
  images: {
    domains: ['localhost'],
  },

  // ESLint configuration for build
  eslint: {
    ignoreDuringBuilds: true,
  },

  // TypeScript configuration for build
  typescript: {
    ignoreBuildErrors: true,
  },

  // Turbopack configuration (replaces webpack config)
  experimental: {
    turbo: {
      rules: {
        // Any Turbopack-specific rules can go here
      }
    }
  },
}

module.exports = nextConfig