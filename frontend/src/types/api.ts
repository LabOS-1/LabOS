/**
 * API related types and interfaces
 */

import { JsonValue } from './base';

// Generic API response wrapper
export interface ApiResponse<T = JsonValue> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// Paginated response for list endpoints
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// Performance metrics for API responses
export interface PerformanceMetrics {
  execution_time: number;
  memory_usage: number;
  cpu_usage: number;
  success_rate: number;
  error_count: number;
}

// Tool execution result
export interface ToolExecutionResult {
  success: boolean;
  data?: JsonValue;
  error?: string;
  metadata?: Record<string, JsonValue>;
}

// API error structure
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, JsonValue>;
  timestamp: string;
}

