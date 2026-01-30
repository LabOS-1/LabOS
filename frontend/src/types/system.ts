/**
 * System status and monitoring related types
 */

import { AgentStatusInfo } from './agents';

// System resource information
export interface SystemResources {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  gpu_available: boolean;
  gpu_usage?: number;
}

// System performance metrics
export interface SystemPerformance {
  uptime: number;
  total_tasks: number;
  successful_tasks: number;
  failed_tasks: number;
  avg_response_time: number;
}

// Memory/knowledge base statistics
export interface MemoryStats {
  total_items: number;
  public_insights: number;
  private_insights: number;
  pathways: number;
  evidence: number;
}

// Complete system status
export interface SystemStatus {
  status?: string;
  uptime: number;
  agents: {
    manager: AgentStatusInfo;
    dev: AgentStatusInfo;
    critic?: AgentStatusInfo;
  };
  memory: MemoryStats;
  performance: SystemPerformance;
  resources: SystemResources;
}

// Simple system status for store compatibility
export interface SimpleSystemStatus {
  status: string;
  uptime: number;
  resources: {
    cpu_usage: number;
    memory_usage: number;
  };
}

// Health check response
export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  checks: {
    database: boolean;
    websocket: boolean;
    agents: boolean;
  };
  message?: string;
}

