/**
 * File management related types
 */

import { BaseEntity } from './base';

// File types supported by the system
export type FileType = 
  | 'python' 
  | 'javascript' 
  | 'typescript'
  | 'json' 
  | 'csv' 
  | 'txt' 
  | 'markdown'
  | 'image' 
  | 'pdf'
  | 'other';

// File information interface
export interface FileInfo extends BaseEntity {
  name: string;
  path: string;
  type: FileType;
  size: number;
  modified_at: string;
  content?: string;
  preview?: string;
  is_executable: boolean;
  dependencies?: string[];
  encoding?: string;
  mime_type?: string;
}

// Simplified file info for store compatibility
export interface SimpleFileInfo {
  id: string;
  name: string;
  path: string;
  size: number;
  modified: string;
}

// File upload progress
export interface FileUploadProgress {
  file_id: string;
  filename: string;
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  error?: string;
}

// File operation result
export interface FileOperationResult {
  success: boolean;
  file_id?: string;
  message?: string;
  error?: string;
}

