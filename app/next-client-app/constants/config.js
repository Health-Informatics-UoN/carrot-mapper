// File size limit in bytes (configurable via env, default 30MB)
const MAX_FILE_SIZE_BYTES = process.env.NEXT_PUBLIC_BODY_SIZE_LIMIT
  ? parseInt(process.env.NEXT_PUBLIC_BODY_SIZE_LIMIT, 10)
  : 31457280; // 30MB in bytes

module.exports = {
  MAX_FILE_SIZE_BYTES,
}; 