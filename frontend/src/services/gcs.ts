/**
 * GCS Upload Service
 * Handles direct upload to Google Cloud Storage via signed URLs
 * for large files that exceed Cloud Run's 32MB request limit
 */

import { config } from '@/config';

// File size thresholds
const GCS_UPLOAD_THRESHOLD = 30 * 1024 * 1024; // 30MB - use GCS for files larger than this
const MAX_FILE_SIZES = {
  video: 100 * 1024 * 1024,   // 100MB for video
  image: 50 * 1024 * 1024,    // 50MB for images
  pdf: 100 * 1024 * 1024,     // 100MB for PDFs
  default: 50 * 1024 * 1024,  // 50MB default
};

interface SignedUrlResponse {
  upload_url: string;
  gcs_uri: string;
  blob_name: string;
  expires_in: number;
}

interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

/**
 * Check if a file should be uploaded via GCS (for large files)
 */
export const shouldUseGCSUpload = (file: File): boolean => {
  return file.size > GCS_UPLOAD_THRESHOLD;
};

/**
 * Get maximum file size based on content type
 */
export const getMaxFileSize = (contentType: string): number => {
  if (contentType.startsWith('video/')) {
    return MAX_FILE_SIZES.video;
  } else if (contentType.startsWith('image/')) {
    return MAX_FILE_SIZES.image;
  } else if (contentType === 'application/pdf') {
    return MAX_FILE_SIZES.pdf;
  }
  return MAX_FILE_SIZES.default;
};

/**
 * Get a signed URL for uploading a file to GCS
 */
export const getSignedUploadUrl = async (
  file: File,
  userId: string,
  projectId: string
): Promise<SignedUrlResponse> => {
  const token = localStorage.getItem('auth_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${config.api.baseUrl}/api/v1/gcs/signed-url`, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify({
      filename: file.name,
      content_type: file.type,
      user_id: userId,
      project_id: projectId,
      file_size: file.size,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to get signed URL');
  }

  return response.json();
};

/**
 * Upload a file directly to GCS using a signed URL
 */
export const uploadToGCS = async (
  file: File,
  signedUrl: string,
  onProgress?: (progress: UploadProgress) => void
): Promise<void> => {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress({
          loaded: event.loaded,
          total: event.total,
          percentage: Math.round((event.loaded / event.total) * 100),
        });
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        console.error(`GCS upload failed: ${xhr.status} ${xhr.statusText}`, xhr.responseText);
        reject(new Error(`Upload failed with status ${xhr.status}: ${xhr.responseText}`));
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed due to network error'));
    });

    xhr.addEventListener('abort', () => {
      reject(new Error('Upload was aborted'));
    });

    xhr.open('PUT', signedUrl);
    xhr.setRequestHeader('Content-Type', file.type);
    xhr.send(file);
  });
};

/**
 * Confirm that a file has been uploaded to GCS
 */
export const confirmUploadComplete = async (
  blobName: string,
  gcsUri: string,
  userId: string,
  projectId: string,
  originalFilename: string,
  contentType: string
): Promise<{ success: boolean; file_id?: string; gcs_uri: string; message: string }> => {
  const token = localStorage.getItem('auth_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${config.api.baseUrl}/api/v1/gcs/upload-complete`, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify({
      blob_name: blobName,
      gcs_uri: gcsUri,
      user_id: userId,
      project_id: projectId,
      original_filename: originalFilename,
      content_type: contentType,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to confirm upload');
  }

  return response.json();
};

/**
 * Full GCS upload flow: get signed URL -> upload -> confirm
 */
export const uploadLargeFile = async (
  file: File,
  userId: string,
  projectId: string,
  onProgress?: (progress: UploadProgress) => void
): Promise<{ file_id?: string; gcs_uri: string; blob_name: string }> => {
  console.log(`Uploading large file via GCS: ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)}MB)`);

  // Step 1: Get signed URL
  console.log('Step 1: Getting signed URL...');
  const signedUrlResponse = await getSignedUploadUrl(file, userId, projectId);
  console.log('Signed URL obtained:', signedUrlResponse.blob_name);

  // Step 2: Upload to GCS
  console.log('Step 2: Uploading to GCS...');
  await uploadToGCS(file, signedUrlResponse.upload_url, onProgress);
  console.log('Upload to GCS complete');

  // Step 3: Confirm upload
  console.log('Step 3: Confirming upload...');
  const confirmResponse = await confirmUploadComplete(
    signedUrlResponse.blob_name,
    signedUrlResponse.gcs_uri,
    userId,
    projectId,
    file.name,
    file.type
  );
  console.log('Upload confirmed, file_id:', confirmResponse.file_id);

  return {
    file_id: confirmResponse.file_id,
    gcs_uri: signedUrlResponse.gcs_uri,
    blob_name: signedUrlResponse.blob_name,
  };
};

export default {
  shouldUseGCSUpload,
  getMaxFileSize,
  getSignedUploadUrl,
  uploadToGCS,
  confirmUploadComplete,
  uploadLargeFile,
  GCS_UPLOAD_THRESHOLD,
  MAX_FILE_SIZES,
};