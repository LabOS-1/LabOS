/**
 * Chat and messaging related types
 */

import { BaseEntity } from './base';
import { ToolCall } from './tools';
import { PerformanceMetrics } from './api';

// Chat message types
export type ChatMessageType = 'user' | 'assistant' | 'system' | 'tool';

// Chat message interface
export interface ChatMessage extends BaseEntity {
  type: ChatMessageType;
  content: string;
  timestamp: string;
  agent_id?: string;
  metadata?: ChatMessageMetadata;
}

// Chat message metadata
export interface ChatMessageMetadata {
  tool_calls?: ToolCall[];
  execution_id?: string;
  files_created?: string[];
  performance_metrics?: PerformanceMetrics;
  execution_time?: number;
  agent_id?: string;
  using_real_labos?: boolean;
  workflow_id?: string;
  project_id?: string;
  error?: boolean;
  follow_up_questions?: string[];
  attached_files?: Array<{
    filename: string;
    size: number;
    type: string;
    file_id?: string;
    content_type?: string;
    hash?: string;
  }>;
}

// Chat response from API
export interface ChatResponse {
  content: string;
  follow_up_questions?: string[];
  metadata?: {
    execution_time?: number;
    agent_id?: string;
    workflow_id?: string;
    using_real_labos?: boolean;
    follow_up_questions?: string[];
  };
}

// Chat session information
export interface ChatSession {
  id: string;
  title?: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  agents_involved: string[];
}
