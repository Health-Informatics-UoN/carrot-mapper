/** @type {import('next').NextConfig} */

// Local BACKEND_ORIGIN="127.0.0.1:8000"
// Allows for multiple allowedOrigins in one environment
const allowedOrigins = process.env.BACKEND_ORIGIN?.split(",");

const nextConfig = {
  output: "standalone",
  experimental: {
    serverActions: {
      allowedOrigins: allowedOrigins,
    },
  },
  async redirects() {
    return [
      {
        source: "/",
        destination: "/projects",
        permanent: true,
      },
    ];
  },
};

module.exports = nextConfig;
