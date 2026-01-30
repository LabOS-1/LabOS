/**
 * Memory and knowledge base related types
 */

import { BaseEntity } from './base';

// Memory item types
export type MemoryItemType = 'insight' | 'pathway' | 'evidence';
export type MemorySource = 'public' | 'private';

// Memory item interface
export interface MemoryItem extends BaseEntity {
  type: MemoryItemType;
  content: string;
  category: string;
  confidence: number;
  tags: string[];
  related_items: string[];
  source: MemorySource;
}

// Simple memory item for store compatibility
export interface SimpleMemoryItem {
  id: string;
  content: string;
  type: 'public' | 'private';
  timestamp: string;
}

// Memory search query
export interface MemorySearchQuery {
  query: string;
  type?: MemoryItemType;
  source?: MemorySource;
  tags?: string[];
  confidence_threshold?: number;
  limit?: number;
}

// Memory search result
export interface MemorySearchResult {
  items: MemoryItem[];
  total: number;
  query: string;
  execution_time: number;
}

