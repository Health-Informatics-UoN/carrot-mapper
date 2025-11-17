// File size limit in bytes (configurable via env, default 30MB)
const MAX_FILE_SIZE_BYTES = process.env.NEXT_PUBLIC_BODY_SIZE_LIMIT
  ? parseInt(process.env.NEXT_PUBLIC_BODY_SIZE_LIMIT, 10)
  : 31457280; // 30MB in bytes

// Old file threshold in days - files older than this are auto-hidden in the UI
const OLD_FILE_THRESHOLD = process.env.NEXT_PUBLIC_OLD_FILE_THRESHOLD
  ? parseFloat(process.env.NEXT_PUBLIC_OLD_FILE_THRESHOLD)
  : 30;

module.exports = {
  MAX_FILE_SIZE_BYTES,
  OLD_FILE_THRESHOLD,
}; 