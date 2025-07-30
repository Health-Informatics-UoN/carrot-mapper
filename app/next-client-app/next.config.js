/** @type {import('next').NextConfig} */

// Local BACKEND_ORIGIN="127.0.0.1:8000"
// Allows for multiple allowedOrigins in one environment
const allowedOrigins = process.env.BACKEND_ORIGIN?.split(",");

// Import file size limit from constants
const { MAX_FILE_SIZE_BYTES } = require("./constants/config");

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
