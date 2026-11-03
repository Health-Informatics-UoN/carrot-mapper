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
  compiler: {
    // Strip noisy logs in production but keep warnings/errors so API
    // failures swallowed by catch blocks still show up in the server logs.
    removeConsole:
      process.env.NODE_ENV === "production"
        ? { exclude: ["error", "warn"] }
        : false,
  },
  // Enable build caching
  onDemandEntries: {
    maxInactiveAge: 25 * 1000,
    pagesBufferLength: 2,
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
