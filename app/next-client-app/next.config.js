/** @type {import('next').NextConfig} */
const { makeEnvPublic } = require("next-runtime-env");
makeEnvPublic("NEXT_SERVER_ACTION_BODY_SIZE_LIMIT");

// Local BACKEND_ORIGIN="127.0.0.1:8000"
// Allows for multiple allowedOrigins in one environment
const allowedOrigins = process.env.BACKEND_ORIGIN?.split(",");

// Allows configuration of body size limit via env (in bytes)
const bodySizeLimit = process.env.NEXT_SERVER_ACTION_BODY_SIZE_LIMIT
  ? parseInt(process.env.NEXT_SERVER_ACTION_BODY_SIZE_LIMIT, 10)
  : 15728640; // Default to 15MB if not set

const nextConfig = {
  output: "standalone",
  experimental: {
    serverActions: {
      allowedOrigins,
      bodySizeLimit,
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
