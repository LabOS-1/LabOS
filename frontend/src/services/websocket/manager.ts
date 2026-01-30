import { 
  createInitialState, 
  connect, 
  disconnect, 
  sendMessage, 
  setHandlers, 
  getStatus, 
  getStats,
  type WebSocketState 
} from './connection';
import type { 
  WebSocketMessage, 
  ConnectionStatus,
  WebSocketConfig 
} from './types';

// Global WebSocket state
let globalState: WebSocketState | null = null;
const messageHandlers = new Map<string, (message: WebSocketMessage) => void>();
const statusHandlers = new Set<(status: ConnectionStatus) => void>();

/**
 * Initialize WebSocket connection
 */
async function initializeWebSocket(config?: Partial<WebSocketConfig>): Promise<void> {
  if (globalState) {
    console.warn('⚠️ WebSocketManager: Already initialized');
    return;
  }

  console.log('🚀 WebSocketManager: Initializing...');
  
  globalState = createInitialState(config);
  
  // Set up event handlers
  setHandlers(globalState, {
    onOpen: (event) => {
      console.log('✅ WebSocketManager: Connection opened');
      notifyStatusHandlers('connected');
    },
    
    onMessage: (message) => {
      console.log('📨 WebSocketManager: Routing message:', message.type);
      routeMessage(message);
    },
    
    onClose: (event) => {
      console.log('🔌 WebSocketManager: Connection closed');
      notifyStatusHandlers('disconnected');
    },
    
    onError: (event) => {
      console.error('❌ WebSocketManager: Connection error');
      notifyStatusHandlers('error');
    },
    
    onReconnect: (attempt) => {
      console.log(`🔄 WebSocketManager: Reconnecting (attempt ${attempt})`);
      notifyStatusHandlers('reconnecting');
    }
  });

  // Connect
  await connect(globalState);
}

/**
 * Disconnect WebSocket
 */
function disconnectWebSocket(): void {
  if (globalState) {
    console.log('🔌 WebSocketManager: Disconnecting...');
    disconnect(globalState);
    globalState = null;
  }
}

/**
 * Send message
 */
function send(message: WebSocketMessage): boolean {
  if (!globalState) {
    console.warn('⚠️ WebSocketManager: Not initialized');
    return false;
  }
  
  return sendMessage(globalState, message);
}

/**
 * Subscribe to specific message types
 */
function subscribe(messageType: string, handler: (message: WebSocketMessage) => void): () => void {
  console.log(`📝 WebSocketManager: Subscribing to ${messageType}`);
  messageHandlers.set(messageType, handler);
  
  // Return unsubscribe function
  return () => {
    console.log(`📝 WebSocketManager: Unsubscribing from ${messageType}`);
    messageHandlers.delete(messageType);
  };
}

/**
 * Subscribe to connection status changes
 */
function subscribeToStatus(handler: (status: ConnectionStatus) => void): () => void {
  console.log('📝 WebSocketManager: Subscribing to status changes');
  statusHandlers.add(handler);
  
  // Return unsubscribe function
  return () => {
    console.log('📝 WebSocketManager: Unsubscribing from status changes');
    statusHandlers.delete(handler);
  };
}

/**
 * Get current connection status
 */
function getCurrentStatus(): ConnectionStatus {
  return globalState ? getStatus(globalState) : 'disconnected';
}

/**
 * Get connection statistics
 */
function getCurrentStats() {
  return globalState ? getStats(globalState) : null;
}

/**
 * Subscribe to a project room
 */
function subscribeToProject(projectId: string): void {
  if (!globalState) {
    console.warn('⚠️ WebSocketManager: Cannot subscribe to project - not initialized');
    return;
  }

  console.log(`📌 WebSocketManager: Subscribing to project ${projectId}`);
  send({
    type: 'subscribe_project',
    project_id: projectId
  });
}

/**
 * Unsubscribe from a project room
 */
function unsubscribeFromProject(projectId: string): void {
  if (!globalState) {
    console.warn('⚠️ WebSocketManager: Cannot unsubscribe from project - not initialized');
    return;
  }

  console.log(`📌 WebSocketManager: Unsubscribing from project ${projectId}`);
  send({
    type: 'unsubscribe_project',
    project_id: projectId
  });
}

/**
 * Route incoming messages to handlers
 */
function routeMessage(message: WebSocketMessage): void {
  // Check for wildcard handler first
  const wildcardHandler = messageHandlers.get('*');
  if (wildcardHandler) {
    try {
      wildcardHandler(message);
    } catch (error) {
      console.error(`❌ WebSocketManager: Error in wildcard handler:`, error);
    }
  }
  
  // Then check for specific handler
  const handler = messageHandlers.get(message.type);
  if (handler) {
    try {
      handler(message);
    } catch (error) {
      console.error(`❌ WebSocketManager: Error handling message ${message.type}:`, error);
    }
  } else if (!wildcardHandler) {
    console.warn(`⚠️ WebSocketManager: No handler for message type: ${message.type}`);
  }
}

/**
 * Notify status change handlers
 */
function notifyStatusHandlers(status: ConnectionStatus): void {
  statusHandlers.forEach(handler => {
    try {
      handler(status);
    } catch (error) {
      console.error('❌ WebSocketManager: Error in status handler:', error);
    }
  });
}

// Export WebSocket manager functions
export {
  initializeWebSocket,
  disconnectWebSocket,
  send,
  subscribe,
  subscribeToStatus,
  getCurrentStatus,
  getCurrentStats,
  subscribeToProject,
  unsubscribeFromProject
};