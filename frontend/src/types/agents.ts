/**
 * Agent related types and interfaces
 */

import { BaseEntity, AgentStatus, JsonValue } from './base';

// LabOS AI agent types
export type LabOSAgentType = 'manager' | 'dev' | 'critic';

// Main agent interface
export interface LabOSAgent extends BaseEntity {
  name: string;
  type: LabOSAgentType;
  status: AgentStatus;
  description: string;
  capabilities: string[];
  current_task?: string;
  last_activity?: string;
}

// Detailed agent status information
export interface AgentStatusInfo {
  status: AgentStatus;
  current_task?: string;
  last_activity: string;
  total_tasks: number;
  success_rate: number;
  avg_execution_time: number;
}

// Agent performance data
export interface AgentPerformance {
  agent_id: string;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  average_execution_time: number;
  last_execution?: string;
}

// Agent capabilities definition
export interface AgentCapability {
  name: string;
  description: string;
  enabled: boolean;
  config?: Record<string, JsonValue>;
}

