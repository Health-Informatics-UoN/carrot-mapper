// File size limit in bytes (configurable via env, default 30MB)
const MAX_FILE_SIZE_BYTES = process.env.NEXT_PUBLIC_BODY_SIZE_LIMIT
  ? parseInt(process.env.NEXT_PUBLIC_BODY_SIZE_LIMIT, 10)
  : 31457280; // 30MB in bytes

// File retention period in days (configurable via env, default 6 hours for testing)
// 6 hours = 0.25 days
const FILE_RETENTION_DAYS = process.env.NEXT_PUBLIC_FILE_RETENTION_DAYS
  ? parseFloat(process.env.NEXT_PUBLIC_FILE_RETENTION_DAYS)
  : 0.25;

module.exports = {
  MAX_FILE_SIZE_BYTES,
  FILE_RETENTION_DAYS,
}; 