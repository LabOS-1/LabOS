// WebSocket Service Types
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error' | 'reconnecting';

export interface WebSocketConfig {
  url: string;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
  timeout?: number;
}

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: string;
  project_id?: string;
  workflow_id?: string;
  action?: string;
  response?: any;
  chat_response?: any;
  // Allow any additional fields from backend
  [key: string]: any;
}

export interface WebSocketEventHandlers {
  onOpen?: (event: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  onReconnect?: (attempt: number) => void;
}

export interface WebSocketStats {
  connectionCount: number;
  messageCount: number;
  errorCount: number;
  lastConnectedAt?: string;
  lastDisconnectedAt?: string;
  averageLatency?: number;
}
