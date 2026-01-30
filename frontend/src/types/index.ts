/**
 * Main types index - Re-exports all type definitions
 * Organized by domain for better maintainability
 */

// Base types and utilities
export * from './base';

// API and communication types
export * from './api';

// Domain-specific types
export * from './agents';
export * from './tools';
export * from './chat';
export * from './workflow';
export * from './files';
export * from './system';
export * from './memory';
export * from './websocket';
export * from './ui';

// Store types (Redux state)
export * from './store';

// Legacy type aliases for backward compatibility
// These can be removed once all imports are updated
export type { 
  SimpleFileInfo as FileInfo
} from './files';

export type {
  SimpleSystemStatus as SystemStatus
} from './system';

export type {
  SimpleMemoryItem as MemoryItem
} from './memory';

// Common type unions for convenience
export type EntityId = string;
export type Timestamp = string;
export type EntityStatus = 'active' | 'inactive' | 'pending' | 'error';

// Utility types
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};