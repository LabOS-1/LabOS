'use client'

import React, { useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { 
  setConnectionStatus, 
  processWebSocketMessage, 
  updateLastPing, 
  setStatusMessage 
} from '../../store/slices/websocketSlice';
import type { AppDispatch, RootState } from '../../store';
import type { UnifiedWebSocketMessage } from '../../types/websocketUnified';

interface WebSocketProviderProps {
  children: React.ReactNode;
}

/**
 * WebSocket Provider Component
 * 
 * This component manages the global WebSocket connection at the application level.
 * It should be placed high in the component tree (ideally in layout.tsx).
 * 
 * Responsibilities:
 * 1. Initialize WebSocket connection once per app
 * 2. Subscribe to messages and route them to Redux
 * 3. Manage connection status and heartbeat
 * 4. Clean up connection on app unmount
 */
export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const dispatch = useDispatch<AppDispatch>();
  const connectionStatus = useSelector((state: RootState) => state.websocket.connectionStatus);
  const { isAuthenticated, isLoading } = useSelector((state: RootState) => state.auth); // Add auth state
  const isInitializedRef = useRef<boolean>(false);
  const unsubscribeRef = useRef<(() => void) | null>(null);
  const statusIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup WebSocket when user logs out
  useEffect(() => {
    if (!isAuthenticated && isInitializedRef.current) {
      console.log('🧹 WebSocketProvider: User logged out, cleaning up WebSocket');
      
      // Cleanup existing connections
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
      
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current);
        statusIntervalRef.current = null;
      }

      // WebSocket cleanup disabled for now
      console.log('🧹 WebSocketProvider: Cleanup called (WebSocket disabled)');
      isInitializedRef.current = false;
      dispatch(setConnectionStatus('disconnected'));
      dispatch(setStatusMessage('Disconnected - user logged out'));
    }
  }, [isAuthenticated, dispatch]);

  useEffect(() => {
    // Only initialize WebSocket if user is authenticated
    if (!isAuthenticated || isLoading) {
      return;
    }

    // Only initialize once per app lifecycle
    if (isInitializedRef.current) {
      return;
    }

    // Load WebSocket manager and initialize connection
    const initializeWebSocket = async () => {
      try {
        if (typeof window === 'undefined') {
          return; // Skip on server-side
        }

        console.log('🚀 WebSocketProvider: Loading WebSocket manager...');


        console.log('🚀 WebSocketProvider: Initializing global WebSocket connection');
        isInitializedRef.current = true;

        // Message type mapping
        const mapMessageType = (type: string): UnifiedWebSocketMessage['type'] => {
          switch (type) {
            case 'workflow_step':
            case 'step_added':
            case 'step_updated':
              return 'workflow_update';
            case 'progress_updated':
              return 'progress_update';
            case 'workflow_complete':
              return 'workflow_completed';
            case 'workflow_cleaned':
              return 'workflow_cleared';
            case 'chat_completed':
            case 'chat_response':
              return 'chat_completed';
            default:
              return type as UnifiedWebSocketMessage['type'];
          }
        };

        // Message handler for routing to Redux
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const handleMessage = (message: any) => {
          console.log('🎯 WebSocketProvider: handleMessage called with:', message.type);
          console.log('📨 WebSocketProvider: Received message:', {
            type: message.type,
            originalType: message.type,
            mappedType: mapMessageType(message.type),
            hasStepInfo: !!message.step_info,
            hasWorkflowId: !!message.workflow_id,
            messageKeys: Object.keys(message),
            fullMessage: message
          });
          
          // Map to unified message format
          const unifiedMessage: UnifiedWebSocketMessage = {
            ...message,
            // Extract data field for chat_response messages
            ...(message.type === 'chat_response' && message.data ? message.data : {}),
            type: mapMessageType(message.type),
            timestamp: message.timestamp || new Date().toISOString(),
            // Handle different message structures
            step_info: message.step || message.step_info || (
              message.type === 'workflow_step' ? {
                id: message.id || `step_${message.step_number || Date.now()}_${message.step_type || 'thinking'}`,
                type: message.step_type || 'thinking',
                title: message.title,
                description: message.description,
                tool_name: message.tool_name,
                tool_result: message.tool_result,
                step_number: message.step_number,
                observations: message.observations,
                timestamp: message.timestamp
              } : undefined
            ),
          };
          
          console.log('🔄 WebSocketProvider: Dispatching unified message:', unifiedMessage);
          
          // Route to Redux store
          dispatch(processWebSocketMessage(unifiedMessage));
        };

        // Initialize WebSocket connection using new service
        dispatch(setConnectionStatus('connecting'));
        dispatch(setStatusMessage('Connecting to WebSocket...'));

        // Import WebSocket manager and config dynamically
        const { initializeWebSocket, subscribeToStatus, subscribe } = await import('../../services/websocket');
        const { websocketConfig } = await import('../../config');
        
        // Subscribe to status changes
        const unsubscribeStatus = subscribeToStatus((status) => {
          dispatch(setConnectionStatus(status));
          switch (status) {
            case 'connected':
              dispatch(setStatusMessage('WebSocket connected successfully'));
              break;
            case 'disconnected':
              dispatch(setStatusMessage('WebSocket disconnected'));
              break;
            case 'reconnecting':
              dispatch(setStatusMessage('Reconnecting to WebSocket...'));
              break;
            case 'error':
              dispatch(setStatusMessage('WebSocket connection error'));
              break;
          }
        });

        // Subscribe to all WebSocket messages and route to Redux
        const unsubscribeMessages = subscribe('*', (message) => {
          console.log('📨 WebSocketProvider: Raw WebSocket message received:', message);
          
          const unifiedMessage = {
            // Copy all fields from original message first
            ...message,
            // Override with specific fields and mapped type
            type: mapMessageType(message.type),
            timestamp: message.timestamp || new Date().toISOString(),
          };
          
          console.log('🔄 WebSocketProvider: Dispatching unified message:', unifiedMessage);
          dispatch(processWebSocketMessage(unifiedMessage));
        });

        // Initialize the connection with config
        await initializeWebSocket({
          url: websocketConfig.url,
          reconnectAttempts: websocketConfig.reconnectAttempts,
          reconnectInterval: websocketConfig.reconnectDelay,
          heartbeatInterval: websocketConfig.heartbeatInterval,
        });
        
        // Store cleanup functions
        unsubscribeRef.current = () => {
          unsubscribeStatus();
          unsubscribeMessages();
        };

      } catch (error) {
        console.error('❌ WebSocketProvider: Initialization failed:', error);
        dispatch(setConnectionStatus('error'));
        dispatch(setStatusMessage(`Initialization failed: ${error}`));
      }
    };

    // Start the initialization
    initializeWebSocket();

    // Cleanup function
    return () => {
      console.log('🧹 WebSocketProvider: Cleaning up global WebSocket connection');
      
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
      
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current);
        statusIntervalRef.current = null;
      }

      // Disconnect WebSocket
      import('@/services/websocket').then(({ disconnectWebSocket }) => {
        disconnectWebSocket();
      });
      
      isInitializedRef.current = false;
      dispatch(setConnectionStatus('disconnected'));
      dispatch(setStatusMessage('Disconnected - component unmounted'));
    };
  }, [dispatch, isAuthenticated, isLoading]); // Remove connectionStatus to avoid infinite loops

  return <>{children}</>;
};

export default WebSocketProvider;