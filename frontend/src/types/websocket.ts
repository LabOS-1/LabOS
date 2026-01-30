/**
 * WebSocket communication related types
 */

import { JsonValue } from './base';
import { AgentStatusInfo } from './agents';
import { SystemStatus } from './system';
import { WorkflowStep, ExecutionStep } from './workflow';
import { ChatResponse } from './chat';

// WebSocket message types
export type WebSocketMessageType = 
  | 'workflow_step' 
  | 'progress_update' 
  | 'progress_updated' 
  | 'workflow_completed' 
  | 'workflow_complete' 
  | 'workflow_cleaned' 
  | 'heartbeat' 
  | 'pong' 
  | 'ping' 
  | 'initial_state' 
  | 'step_added' 
  | 'step_updated' 
  | 'chat_started' 
  | 'chat_completed' 
  | 'chat_error'
  | 'execution_start'
  | 'execution_step'
  | 'execution_complete'
  | 'agent_status'
  | 'system_status'
  | 'error';

// WebSocket event data types
export interface ExecutionStartData {
  execution_id: string;
  task: string;
  agent_id: string;
}

export interface ExecutionStepData {
  execution_id: string;
  step: ExecutionStep;
}

export interface ExecutionCompleteData {
  execution_id: string;
  result: string;
  performance_metrics: {
    execution_time: number;
    memory_usage: number;
    cpu_usage: number;
    success_rate: number;
    error_count: number;
  };
}

export interface AgentStatusData {
  agent_id: string;
  status: AgentStatusInfo;
}

export interface SystemStatusData {
  system_status: SystemStatus;
}

export interface ErrorData {
  error: string;
  context?: Record<string, JsonValue>;
}

// Union type for WebSocket event data
export type WebSocketEventData = 
  | ExecutionStartData
  | ExecutionStepData  
  | ExecutionCompleteData
  | AgentStatusData
  | SystemStatusData
  | ErrorData;

// Main WebSocket event interface
export interface WebSocketEvent {
  type: WebSocketMessageType;
  data: WebSocketEventData;
  timestamp: string;
}

// Workflow WebSocket data
export interface WorkflowWebSocketData {
  type: WebSocketMessageType;
  step?: WorkflowStep;
  steps?: WorkflowStep[];
  progress?: number;
  workflow_id?: string;
  timestamp?: string;
  message?: string;
  status?: string;
  response?: ChatResponse | null;
  error?: string;
}

// WebSocket connection state
export interface WebSocketState {
  connected: boolean;
  reconnecting: boolean;
  last_ping?: string;
  connection_count: number;
}
