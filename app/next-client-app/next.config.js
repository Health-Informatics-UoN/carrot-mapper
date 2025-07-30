/** @type {import('next').NextConfig} */

// Local BACKEND_ORIGIN="127.0.0.1:8000"
// Allows for multiple allowedOrigins in one environment
const allowedOrigins = process.env.BACKEND_ORIGIN?.split(",");

// File size limit in bytes (configurable via env, default 30MB)
const MAX_FILE_SIZE_BYTES = process.env.DATA_UPLOAD_MAX_MEMORY_SIZE
  ? parseInt(process.env.DATA_UPLOAD_MAX_MEMORY_SIZE, 10)
  : 31457280; // 30MB in bytes

const nextConfig = {
  output: "standalone",
  experimental: {
    serverActions: {
      allowedOrigins,
      bodySizeLimit: MAX_FILE_SIZE_BYTES,
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
