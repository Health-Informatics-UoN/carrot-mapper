// File size limit in bytes (20MB)
export const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB in bytes

// Utility function to format file size
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// Utility function to validate file size
export const validateFileSize = (file: File): string | null => {
  if (file.size > MAX_FILE_SIZE) {
    return `File size (${formatFileSize(file.size)}) exceeds the maximum allowed size of 20MB`;
  }
  return null;
};

// Utility function to validate file type
export const validateFileType = (file: File, allowedTypes: string[]): string | null => {
  const fileExtension = file.name.split('.').pop()?.toLowerCase();
  if (!fileExtension || !allowedTypes.includes(`.${fileExtension}`)) {
    return `File type .${fileExtension} is not allowed. Allowed types: ${allowedTypes.join(', ')}`;
  }
  return null;
};

// Combined validation function
export const validateFile = (file: File, allowedTypes: string[]): string | null => {
  const sizeError = validateFileSize(file);
  if (sizeError) return sizeError;
  
  const typeError = validateFileType(file, allowedTypes);
  if (typeError) return typeError;
  
  return null;
}; 