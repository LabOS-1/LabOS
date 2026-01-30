
import { JsonValue } from './base';
import { WorkflowStep, CreatedFile } from './workflow';
import { ChatResponse } from './chat';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error' | 'reconnecting';

export type UnifiedWebSocketMessageType =
  | 'workflow_update'
  | 'workflow_step'
  | 'progress_update'
  | 'workflow_progress'
  | 'chat_completed'
  | 'chat_started'
  | 'chat_error'
  | 'workflow_completed'
  | 'workflow_cancelled'
  | 'workflow_cleared'
  | 'follow_up_questions'  // Sent separately after chat_completed for faster UX
  | 'heartbeat'
  | 'ping'
  | 'pong'
  | 'connection_status'
  | 'error';            

// Unified WebSocket message interface  
export interface UnifiedWebSocketMessage {
  type: UnifiedWebSocketMessageType;
  workflow_id?: string;
  timestamp: string;
  
  // Workflow related data
  step_info?: Partial<WorkflowStep>;
  steps?: WorkflowStep[];
  progress?: number;
  current_step?: number;
  total_steps?: number;
  
  // Workflow step specific fields (for workflow_step messages)
  id?: string;
  step_number?: number;
  step_type?: string;
  title?: string;
  description?: string;
  tool_name?: string;
  tool_result?: string;
  observations?: string[];
  step_metadata?: any; // Visualization and other metadata
  
  // Chat related data
  chat_response?: ChatResponse;
  response?: any; // Backend response data
  message?: string;
  follow_up_questions?: string[]; // AI-generated follow-up questions
  
  // Project related data
  project_id?: string;
  action?: string;
  
  // Error and status
  error?: string;
  status?: string;
  
  // Other data
  data?: Record<string, JsonValue>;
}

// Workflow group interface
export interface WorkflowGroup {
  workflowId: string;
  steps: WorkflowStep[];
  startTime: string;
  endTime?: string;
  isActive: boolean;
  progress: number;
}

// Unified WebSocket state interface
export interface UnifiedWebSocketState {
  // 连接管理
  connectionStatus: ConnectionStatus;
  isConnected: boolean;
  lastPingTime: string | null;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
  
  // Workflow state
  currentWorkflowId: string | null;
  workflowSteps: WorkflowStep[]; // 保留兼容性
  workflowGroups: WorkflowGroup[]; // 新的分组结构
  workflowProgress: number;
  currentStepIndex: number;
  totalSteps: number;
  isWorkflowActive: boolean;
  
  // Chat state
  isChatLoading: boolean;
  lastChatResponse: ChatResponse | null;
  chatError: string | null;
  
  // Statistics and monitoring
  messageCount: number;
  lastMessageTime: string | null;
  createdFiles: CreatedFile[];
  lastStatusMessage: string;
  
  // Performance monitoring
  averageResponseTime: number;
  totalMessages: number;
  errorCount: number;
}

// WebSocket event handler type
export type WebSocketMessageHandler = (message: UnifiedWebSocketMessage) => void;

// WebSocket connection configuration
export interface WebSocketConfig {
  url: string;
  reconnectInterval: number;
  maxReconnectAttempts: number;
  heartbeatInterval: number;
  connectionTimeout: number;
}

// WebSocket Manager interface
export interface IWebSocketManager {
  // Connection management
  connect(): Promise<boolean>;
  disconnect(): void;
  reconnect(): Promise<boolean>;
  
  // Message processing
  subscribe(handler: WebSocketMessageHandler): () => void;
  send(message: Record<string, JsonValue>): boolean;
  
  // Status
  getConnectionStatus(): ConnectionStatus;
  isConnected(): boolean;
  getState(): UnifiedWebSocketState;
  
  // Workflow management
  clearWorkflowState(): void;
  setCurrentWorkflowId(workflowId: string): void;
  
  // Statistics information
  getStats(): {
    messageCount: number;
    errorCount: number;
    averageResponseTime: number;
    uptime: number;
  };
}

// Redux Actions type
export interface WebSocketActions {
  // Connection management
  setConnectionStatus: (status: ConnectionStatus) => void;
  setConnected: (connected: boolean) => void;
  incrementReconnectAttempts: () => void;
  resetReconnectAttempts: () => void;
  
  // Workflow management
  setCurrentWorkflowId: (id: string | null) => void;
  addWorkflowStep: (step: WorkflowStep) => void;
  updateWorkflowStep: (stepId: string, updates: Partial<WorkflowStep>) => void;
  setWorkflowSteps: (steps: WorkflowStep[]) => void;
  setWorkflowProgress: (progress: number) => void;
  setWorkflowActive: (active: boolean) => void;
  clearWorkflowState: () => void;
  
  // Chat management
  setChatLoading: (loading: boolean) => void;
  setChatResponse: (response: ChatResponse | null) => void;
  setChatError: (error: string | null) => void;
  
  // Statistics update
  incrementMessageCount: () => void;
  setLastMessageTime: (time: string) => void;
  updateStats: (stats: Partial<UnifiedWebSocketState>) => void;
  addCreatedFile: (file: CreatedFile) => void;
  setStatusMessage: (message: string) => void;
}

// Hook return type
export interface UseWebSocketReturn {
  // Status
  connectionStatus: ConnectionStatus;
  isConnected: boolean;
  workflowState: {
    currentWorkflowId: string | null;
    steps: WorkflowStep[];
    progress: number;
    isActive: boolean;
    currentStep: number;
    totalSteps: number;
    clearWorkflow: () => void;
  };
  chatState: {
    isLoading: boolean;
    lastResponse: ChatResponse | null;
    error: string | null;
  };
  stats: {
    messageCount: number;
    totalMessages: number;
    lastMessageTime: string | null;
    averageResponseTime: number;
    errorCount: number;
    createdFiles: CreatedFile[];
  };
  
  sendMessage: (message: Record<string, JsonValue>) => boolean;
  clearWorkflow: () => void;
  reconnect: () => Promise<boolean>;
  disconnect: () => void;
  setMessageHandler: (handler: WebSocketMessageHandler | null) => void;
  
  // Advanced access (optional)
  dispatch?: (action: unknown) => void;
}

export interface MessageRouteConfig {
  type: UnifiedWebSocketMessageType;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  handler: (message: UnifiedWebSocketMessage, dispatch: any) => void;
}
