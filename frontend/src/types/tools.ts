/**
 * Tool related types and interfaces
 */

import { BaseEntity, JsonValue } from './base';
import { ToolExecutionResult } from './api';

// Tool categories
export type ToolCategory = 
  | 'analysis' 
  | 'visualization' 
  | 'data_processing' 
  | 'web' 
  | 'github' 
  | 'environment' 
  | 'custom';

// Tool parameter types
export type ToolParameterType = 'string' | 'number' | 'boolean' | 'object' | 'array';

// Tool parameter definition
export interface ToolParameter {
  name: string;
  type: ToolParameterType;
  description: string;
  required: boolean;
  default?: JsonValue;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
    enum?: JsonValue[];
  };
}

// Main tool interface
export interface Tool extends BaseEntity {
  name: string;
  description: string;
  category: ToolCategory;
  parameters: ToolParameter[];
  usage_count: number;
  success_rate: number;
  avg_execution_time: number;
  is_dynamic: boolean;
  version?: string;
  author?: string;
}

// Tool execution call
export interface ToolCall {
  tool_name: string;
  arguments: Record<string, JsonValue>;
  result?: ToolExecutionResult | null;
  error?: string;
  duration?: number;
  timestamp?: string;
}

// Tool execution context
export interface ToolExecutionContext {
  execution_id: string;
  agent_id: string;
  workflow_id?: string;
  environment?: Record<string, JsonValue>;
}

