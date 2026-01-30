/**
 * Base types and utilities for type safety
 */

// Base JSON types for type safety
export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

// Base entity interface
export interface BaseEntity {
  id: string;
  created_at?: string;
  updated_at?: string;
}

// Status types used across the application
export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed';
export type AgentStatus = 'idle' | 'thinking' | 'executing' | 'error';
export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error';

// Common metadata interface
export interface Metadata {
  [key: string]: JsonValue;
}

