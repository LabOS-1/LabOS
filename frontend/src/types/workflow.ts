/**
 * Workflow and execution related types
 */

import { BaseEntity, ExecutionStatus, JsonValue } from './base';
import { PerformanceMetrics, ToolExecutionResult } from './api';

// Workflow step types (Agent-aware)
export type WorkflowStepType = 
  | 'manager_start'
  | 'agent_execution' 
  | 'manager_synthesis'
  | 'workflow_complete'
  // Legacy types (for backward compatibility)
  | 'thinking' 
  | 'tool_execution' 
  | 'synthesis' 
  | 'api_call' 
  | 'step_start' 
  | 'step_complete' 
  | 'error' 
  | 'final_answer';

// Tool execution within agent steps
export interface ToolExecution {
  name: string;
  args: Record<string, any>;
  result: string;
  duration?: number;
  status: 'success' | 'error';
  timestamp?: string;
  metadata?: Record<string, any>;
}

// Extended step metadata for future features
export interface StepMetadata {
  visualizations?: Array<{
    type: string;
    data: any;
    title?: string;
  }>;
  code_blocks?: Array<{
    language: string;
    content: string;
    file_path?: string;
  }>;
  files_created?: string[];
  performance_metrics?: Record<string, any>;
}

// Observation item for workflow steps
export interface ObservationItem {
  type: 'info' | 'warning' | 'error' | 'debug';
  message: string;
  timestamp: string;
  data?: Record<string, JsonValue>;
}

// Workflow step interface (Agent-aware)
export interface WorkflowStep {
  id?: string;
  type: WorkflowStepType;
  step_number?: number;
  title?: string;
  description?: string;
  timestamp: string;
  workflow_id?: string;
  duration?: number;
  input_tokens?: number;
  output_tokens?: number;
  status?: string;
  
  // Legacy fields (for backward compatibility)
  tool_name?: string;
  tool_result?: string | ToolExecutionResult | null;
  parameters?: string;
  method?: string;
  url?: string;
  content?: string;
  observations?: string[] | ObservationItem[];
  raw_content?: string;
  
  // New Agent-aware fields
  agent_name?: string;
  agent_task?: string;
  tools_used?: ToolExecution[];
  execution_result?: string;
  execution_duration?: number;
  step_metadata?: StepMetadata;
}

// Execution step for tasks
export interface ExecutionStep extends BaseEntity {
  step_number: number;
  agent_id: string;
  tool_name?: string;
  tool_arguments?: Record<string, JsonValue>;
  status: ExecutionStatus;
  start_time: string;
  end_time?: string;
  duration?: number;
  output?: string;
  error?: string;
  observations?: string[];
}

// Task execution interface
export interface TaskExecution extends BaseEntity {
  task: string;
  status: ExecutionStatus;
  start_time: string;
  end_time?: string;
  duration?: number;
  steps: ExecutionStep[];
  result?: string;
  error?: string;
  files_created: string[];
  tools_used: string[];
  performance_metrics: PerformanceMetrics;
  progress?: number;
}

// Created file information
export interface CreatedFile {
  path: string;
  name: string;
  timestamp: string;
  size?: number;
  type?: string;
  modified?: string;
}

