import type { 
  WebSocketConfig, 
  WebSocketMessage, 
  WebSocketEventHandlers, 
  ConnectionStatus,
  WebSocketStats 
} from './types';

// WebSocket connection state
interface WebSocketState {
  ws: WebSocket | null;
  config: WebSocketConfig;
  handlers: WebSocketEventHandlers;
  reconnectTimer: NodeJS.Timeout | null;
  heartbeatTimer: NodeJS.Timeout | null;
  currentAttempt: number;
  isManualClose: boolean;
  stats: WebSocketStats;
}

// Create initial state
function createInitialState(config?: Partial<WebSocketConfig>): WebSocketState {
  // Import config dynamically to avoid circular dependencies
  const defaultUrl = typeof window !== 'undefined' 
    ? 'ws://localhost:18800/ws'  // Client-side default
    : 'ws://localhost:18800/ws'; // Server-side default
    
  return {
    ws: null,
    config: {
      url: config?.url || defaultUrl,
      reconnectAttempts: config?.reconnectAttempts || 5,
      reconnectInterval: config?.reconnectInterval || 3000,
      heartbeatInterval: config?.heartbeatInterval || 30000,
      timeout: config?.timeout || 10000,
    },
    handlers: {},
    reconnectTimer: null,
    heartbeatTimer: null,
    currentAttempt: 0,
    isManualClose: false,
    stats: {
      connectionCount: 0,
      messageCount: 0,
      errorCount: 0,
    },
  };
}

// Helper functions for WebSocket operations
function startHeartbeat(state: WebSocketState): void {
  state.heartbeatTimer = setInterval(() => {
    if (state.ws?.readyState === WebSocket.OPEN) {
      sendMessage(state, { type: 'ping', timestamp: new Date().toISOString() });
    }
  }, state.config.heartbeatInterval);
}

function stopHeartbeat(state: WebSocketState): void {
  if (state.heartbeatTimer) {
    clearInterval(state.heartbeatTimer);
    state.heartbeatTimer = null;
  }
}

function clearReconnectTimer(state: WebSocketState): void {
  if (state.reconnectTimer) {
    clearTimeout(state.reconnectTimer);
    state.reconnectTimer = null;
  }
}

function scheduleReconnect(state: WebSocketState): void {
  state.currentAttempt++;
  console.log(`🔄 WebSocket: Scheduling reconnect attempt ${state.currentAttempt}/${state.config.reconnectAttempts}`);
  
  state.handlers.onReconnect?.(state.currentAttempt);
  
  state.reconnectTimer = setTimeout(() => {
    connect(state).catch((error) => {
      console.error(`❌ WebSocket: Reconnect attempt ${state.currentAttempt} failed:`, error);
      
      if (state.currentAttempt >= state.config.reconnectAttempts!) {
        console.error('❌ WebSocket: Max reconnect attempts reached');
      }
    });
  }, state.config.reconnectInterval);
}

/**
 * Connect to WebSocket server
 */
function connect(state: WebSocketState): Promise<void> {
  return new Promise((resolve, reject) => {
    if (state.ws?.readyState === WebSocket.OPEN) {
      resolve();
      return;
    }

    state.isManualClose = false;
    console.log(`🔌 WebSocket: Connecting to ${state.config.url}`);

    try {
      state.ws = new WebSocket(state.config.url);
      
      // Connection timeout
      const timeout = setTimeout(() => {
        if (state.ws?.readyState !== WebSocket.OPEN) {
          state.ws?.close();
          reject(new Error('WebSocket connection timeout'));
        }
      }, state.config.timeout);

      state.ws.onopen = (event) => {
        clearTimeout(timeout);
        console.log('✅ WebSocket: Connected successfully');
        
        state.stats.connectionCount++;
        state.stats.lastConnectedAt = new Date().toISOString();
        state.currentAttempt = 0;
        
        startHeartbeat(state);
        state.handlers.onOpen?.(event);
        resolve();
      };

      state.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('📨 WebSocket: Received message:', message.type);
          
          state.stats.messageCount++;
          state.handlers.onMessage?.(message);
        } catch (error) {
          console.error('❌ WebSocket: Failed to parse message:', error);
          state.stats.errorCount++;
        }
      };

      state.ws.onclose = (event) => {
        clearTimeout(timeout);
        stopHeartbeat(state);
        state.stats.lastDisconnectedAt = new Date().toISOString();
        
        console.log(`🔌 WebSocket: Connection closed (code: ${event.code})`);
        state.handlers.onClose?.(event);

        // Auto-reconnect if not manually closed
        if (!state.isManualClose && state.currentAttempt < state.config.reconnectAttempts!) {
          scheduleReconnect(state);
        }
      };

      state.ws.onerror = (event) => {
        clearTimeout(timeout);
        console.error('❌ WebSocket: Connection error to', state.config.url, event);
        
        state.stats.errorCount++;
        state.handlers.onError?.(event);
        
        if (state.ws?.readyState !== WebSocket.OPEN) {
          reject(new Error(`WebSocket connection failed to ${state.config.url}`));
        }
      };

    } catch (error) {
      console.error('❌ WebSocket: Failed to create connection:', error);
      reject(error);
    }
  });
}

/**
 * Disconnect from WebSocket server
 */
function disconnect(state: WebSocketState): void {
  state.isManualClose = true;
  stopHeartbeat(state);
  clearReconnectTimer(state);
  
  if (state.ws) {
    console.log('🔌 WebSocket: Disconnecting...');
    state.ws.close(1000, 'Manual disconnect');
    state.ws = null;
  }
}

/**
 * Send message to WebSocket server
 */
function sendMessage(state: WebSocketState, message: WebSocketMessage): boolean {
  if (state.ws?.readyState === WebSocket.OPEN) {
    try {
      state.ws.send(JSON.stringify(message));
      console.log('📤 WebSocket: Sent message:', message.type);
      return true;
    } catch (error) {
      console.error('❌ WebSocket: Failed to send message:', error);
      state.stats.errorCount++;
      return false;
    }
  } else {
    console.warn('⚠️ WebSocket: Cannot send message - connection not open');
    return false;
  }
}

/**
 * Set event handlers
 */
function setHandlers(state: WebSocketState, handlers: WebSocketEventHandlers): void {
  state.handlers = { ...state.handlers, ...handlers };
}

/**
 * Get connection status
 */
function getStatus(state: WebSocketState): ConnectionStatus {
  if (!state.ws) return 'disconnected';
  
  switch (state.ws.readyState) {
    case WebSocket.CONNECTING:
      return 'connecting';
    case WebSocket.OPEN:
      return 'connected';
    case WebSocket.CLOSING:
    case WebSocket.CLOSED:
      return state.currentAttempt > 0 ? 'reconnecting' : 'disconnected';
    default:
      return 'error';
  }
}

/**
 * Get connection statistics
 */
function getStats(state: WebSocketState): WebSocketStats {
  return { ...state.stats };
}

// Export functions for WebSocket management
export {
  createInitialState,
  connect,
  disconnect,
  sendMessage,
  setHandlers,
  getStatus,
  getStats,
  type WebSocketState
};