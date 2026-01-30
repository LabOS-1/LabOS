
import { Middleware, Dispatch, UnknownAction } from '@reduxjs/toolkit';
import type { 
  UnifiedWebSocketMessage, 
  MessageRouteConfig,
  ConnectionStatus 
} from '../../types/websocketUnified';
import type { WorkflowStepType } from '../../types/workflow';

// Actions from websocket slice
import {
  setCurrentWorkflowId,
  addWorkflowStep,
  updateWorkflowProgress,
  setWorkflowActive,
  setChatLoading,
  setChatResponse,
  setChatError,
  clearWorkflowState,
  updateLastPing,
  updateStats,
  setStatusMessage,
  updateFollowUpQuestions,
} from '../slices/websocketSlice';

// Actions from chat slice (for updating follow-up questions)
import { updateLastMessageFollowUp } from '../slices/chatSlice';

interface PerformanceMetrics {
  messageCount: number;
  averageProcessingTime: number;
  errorCount: number;
  lastProcessingTime: number;
  startTime: number;
}

let performanceMetrics: PerformanceMetrics = {
  messageCount: 0,
  averageProcessingTime: 0,
  errorCount: 0,
  lastProcessingTime: 0,
  startTime: Date.now(),
};


// Global variable to track current project for isolation
let currentProjectId: string = '';

const workflowStepHandler = (message: UnifiedWebSocketMessage, dispatch: Dispatch<UnknownAction>) => {
  console.log('🔄 Middleware: Processing workflow step for Redux state sync', message.type, message);

  // Project isolation: only process workflow messages for current project
  // CRITICAL: Use project_id field for reliable isolation, not workflow_id string matching
  if (message.project_id && currentProjectId && message.project_id !== currentProjectId) {
    console.log('🚫 Middleware: Skipping workflow_step from different project:', message.project_id, 'current:', currentProjectId);
    return;
  }

  // Fallback to workflow_id string matching for backward compatibility
  if (!message.project_id && message.workflow_id && currentProjectId) {
    const isCurrentProject = message.workflow_id.includes(`project_${currentProjectId}_`);
    if (!isCurrentProject) {
      console.log('🚫 Middleware: Skipping workflow from different project (fallback):', message.workflow_id, 'current:', currentProjectId);
      return;
    }
  }

  if (currentProjectId) {
    console.log('✅ Middleware: Processing workflow for current project:', message.project_id || message.workflow_id, 'current:', currentProjectId);
  }

  if (message.workflow_id) {
    dispatch(setCurrentWorkflowId(message.workflow_id));
  }

  // For workflow_step messages, extract step info and add to Redux
  let stepInfo = message.step_info;
  if (!stepInfo && (message.type === 'workflow_step' || message.type === 'workflow_update')) {
    // Generate UNIQUE step ID to prevent conflicts
    const uniqueId = `step_${message.workflow_id}_${message.step_number || Date.now()}_${Date.now()}_${message.step_type || 'thinking'}`;
    
    stepInfo = {
      id: message.id || uniqueId,
      type: (message.step_type as WorkflowStepType) || 'thinking',
      title: message.title,
      description: message.description,
      tool_name: message.tool_name,
      tool_result: message.tool_result,
      step_number: message.step_number,
      observations: message.observations,
      timestamp: message.timestamp,
      step_metadata: message.step_metadata  // ✅ Include visualization metadata
    };
    console.log('🔧 Middleware: Created stepInfo with unique ID:', stepInfo.id, 'Title:', stepInfo.title, 'Has metadata:', !!message.step_metadata);
  }

  if (stepInfo) {
    const stepWithMetadata = {
      ...stepInfo,
      id: stepInfo.id || `step_${Date.now()}`,
      timestamp: message.timestamp,
      workflow_id: message.workflow_id,
    };
    console.log('🔧 Middleware: Dispatching addWorkflowStep with:', stepWithMetadata);
    dispatch(addWorkflowStep(stepWithMetadata));
  } else {
    console.log('⚠️ Middleware: No stepInfo created for message:', message.type, message);
  }

  // Update workflow progress and active state in Redux
  if (message.type === 'workflow_update' || message.type === 'workflow_step' ||
      message.type === 'progress_update' || message.type === 'workflow_progress') {
    dispatch(setWorkflowActive(true));

    // Update progress and step count if available
    if (message.progress !== undefined || message.current_step !== undefined || message.total_steps !== undefined) {
      dispatch(updateWorkflowProgress({
        progress: message.progress,
        currentStep: message.current_step,
        totalSteps: message.total_steps
      }));
    }
  }
};

const messageRoutes: MessageRouteConfig[] = [
  {
    type: 'workflow_update',
    handler: workflowStepHandler,
  },

  {
    type: 'workflow_step',
    handler: workflowStepHandler,
  },

  {
    type: 'progress_update',
    handler: workflowStepHandler,
  },

  {
    type: 'workflow_progress',
    handler: workflowStepHandler,
  },
  
  {
    type: 'chat_started',
    handler: (message: UnifiedWebSocketMessage, dispatch: Dispatch<UnknownAction>) => {
      console.log('💬 Middleware: Processing chat_started', message);

      // Project isolation: only process chat messages for current project
      if (message.project_id && currentProjectId && message.project_id !== currentProjectId) {
        console.log('🚫 Middleware: Skipping chat_started from different project:', message.project_id, 'current:', currentProjectId);
        return;
      }

      dispatch(setChatLoading(true));
      dispatch(setChatError(null));
      dispatch(setWorkflowActive(true));

      if (message.workflow_id) {
        dispatch(setCurrentWorkflowId(message.workflow_id));
      }
    },
  },
  
  {
    type: 'chat_completed',
    handler: (message: UnifiedWebSocketMessage, dispatch: Dispatch<UnknownAction>) => {
      console.log('✅ Middleware: Processing chat_completed', message);
      console.log('✅ Middleware: Response data:', message.response);
      console.log('✅ Middleware: Project ID:', message.project_id);
      console.log('✅ Middleware: Action:', message.action);

      // Project isolation: only process chat messages for current project
      if (message.project_id && currentProjectId && message.project_id !== currentProjectId) {
        console.log('🚫 Middleware: Skipping chat_completed from different project:', message.project_id, 'current:', currentProjectId);
        return;
      }

      dispatch(setChatLoading(false));
      dispatch(setWorkflowActive(false));

      if (message.chat_response || message.response) {
        // Include project metadata in the response
        // Prioritize chat_response (object) over response (string) to avoid spreading string as array
        const responseWithMetadata = {
          ...(message.chat_response || message.response),
          project_id: message.project_id,
          action: message.action,
          workflow_id: message.workflow_id,
          follow_up_questions: message.follow_up_questions || []
        };
        console.log('✅ Middleware: Follow-up questions:', message.follow_up_questions);
        dispatch(setChatResponse(responseWithMetadata));
      }
    },
  },
  
  {
    type: 'chat_error',
    handler: (message: UnifiedWebSocketMessage, dispatch: Dispatch<UnknownAction>) => {
      console.log('❌ Middleware: Processing chat_error', message);

      // Project isolation: only process chat messages for current project
      if (message.project_id && currentProjectId && message.project_id !== currentProjectId) {
        console.log('🚫 Middleware: Skipping chat_error from different project:', message.project_id, 'current:', currentProjectId);
        return;
      }

      dispatch(setChatLoading(false));
      dispatch(setChatError(message.error || 'Unknown chat error'));
      dispatch(setWorkflowActive(false));
    },
  },
  
  {
    type: 'workflow_completed',
    handler: (message: UnifiedWebSocketMessage, dispatch: Dispatch<UnknownAction>) => {
      console.log('🎉 Middleware: Processing workflow_completed', message);

      dispatch(setWorkflowActive(false));
      dispatch(updateWorkflowProgress({ progress: 100 }));
    },
  },

  {
    type: 'follow_up_questions',
    handler: (message: UnifiedWebSocketMessage, dispatch: Dispatch<UnknownAction>) => {
      console.log('💡 Middleware: Processing follow_up_questions', message.follow_up_questions);

      // Project isolation
      if (message.project_id && currentProjectId && message.project_id !== currentProjectId) {
        console.log('🚫 Middleware: Skipping follow_up from different project');
        return;
      }

      // Update follow-up questions in both websocket state and chat messages
      if (message.follow_up_questions && message.follow_up_questions.length > 0) {
        // Update websocket state (for any components listening to lastChatResponse)
        dispatch(updateFollowUpQuestions({
          workflow_id: message.workflow_id,
          project_id: message.project_id,
          follow_up_questions: message.follow_up_questions
        }));

        // Update the last assistant message in chat state (for UI display)
        dispatch(updateLastMessageFollowUp(message.follow_up_questions));
      }
    },
  },

  {
    type: 'workflow_cancelled',
    handler: (message: UnifiedWebSocketMessage, dispatch: Dispatch<UnknownAction>) => {
      console.log('🛑 Middleware: Processing workflow_cancelled', message);
      
      // Just clean up state, don't show any message to user
      dispatch(setChatLoading(false));
      dispatch(setWorkflowActive(false));
      dispatch(updateWorkflowProgress({ progress: 0 }));
      
      console.log('🛑 Middleware: Workflow cancelled, UI state cleaned');
    },
  },
  
  {
    type: 'workflow_cleared',
    handler: (message: UnifiedWebSocketMessage, dispatch: Dispatch<UnknownAction>) => {
      console.log('🧹 Middleware: Processing workflow_cleared', message);
      
      dispatch(clearWorkflowState());
    },
  },
  
  {
    type: 'pong',
    handler: (message: UnifiedWebSocketMessage, dispatch: Dispatch<UnknownAction>) => {
      console.log('🏓 Middleware: Processing pong', message);
      
      dispatch(updateLastPing(message.timestamp));
    },
  },
  
  {
    type: 'heartbeat',
    handler: (message: UnifiedWebSocketMessage, dispatch: Dispatch<UnknownAction>) => {
      console.log('💓 Middleware: Processing heartbeat', message);
      
      dispatch(updateLastPing(message.timestamp));
    },
  },
  
  {
    type: 'error',
    handler: (message: UnifiedWebSocketMessage, dispatch: Dispatch<UnknownAction>) => {
      console.error('💥 Middleware: Processing error', message);
      
      performanceMetrics.errorCount++;
      
      dispatch(setStatusMessage(`Error: ${message.error || 'Unknown error'}`));
      
      if (message.error?.includes('workflow') || message.error?.includes('chat')) {
        dispatch(setChatLoading(false));
        dispatch(setWorkflowActive(false));
      }
    },
  },
];


const routeMessage = (message: UnifiedWebSocketMessage, dispatch: Dispatch<UnknownAction>): boolean => {
  const route = messageRoutes.find(r => r.type === message.type);
  
  if (route) {
    try {
      const startTime = Date.now();
      route.handler(message, dispatch);
      const processingTime = Date.now() - startTime;
      
      updatePerformanceMetrics(processingTime);
      
      return true;
    } catch (error) {
      console.error(`❌ Middleware: Error processing ${message.type}:`, error);
      performanceMetrics.errorCount++;
      
      dispatch(setStatusMessage(`Processing error: ${error}`));
      return false;
    }
  }
  
  console.warn(`⚠️ Middleware: No handler for message type: ${message.type}`);
  return false;
};


const updatePerformanceMetrics = (processingTime: number) => {
  performanceMetrics.messageCount++;
  performanceMetrics.lastProcessingTime = processingTime;
  
  performanceMetrics.averageProcessingTime = 
    (performanceMetrics.averageProcessingTime * (performanceMetrics.messageCount - 1) + processingTime) 
    / performanceMetrics.messageCount;
};

export const getPerformanceStats = () => {
  const uptime = Date.now() - performanceMetrics.startTime;
  return {
    ...performanceMetrics,
    uptime,
    messagesPerSecond: performanceMetrics.messageCount / (uptime / 1000),
  };
};

export const resetPerformanceStats = () => {
  performanceMetrics = {
    messageCount: 0,
    averageProcessingTime: 0,
    errorCount: 0,
    lastProcessingTime: 0,
    startTime: Date.now(),
  };
};


// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const websocketMiddleware: Middleware = (api: any) => (next: any) => (action: any) => {
  // Process the action first
  const result = next(action);
  
  // Only handle WebSocket messages, avoid infinite loops
  if (action.type === 'websocket/processWebSocketMessage' && 'payload' in action) {
    const message: UnifiedWebSocketMessage = action.payload as UnifiedWebSocketMessage;
    
    console.log('🔀 Middleware: Intercepted WebSocket message:', message.type);
    
    // Use setTimeout to avoid infinite loops by dispatching in next tick
    setTimeout(() => {
      try {
        const handled = routeMessage(message, api.dispatch);
        
        if (handled) {
          const stats = getPerformanceStats();
          api.dispatch(updateStats({
            averageResponseTime: stats.averageProcessingTime,
            errorCount: stats.errorCount,
          }));
        }
        
        if (performanceMetrics.messageCount % 10 === 0) {
          const stats = getPerformanceStats();
          api.dispatch(updateStats({
            averageResponseTime: stats.averageProcessingTime,
            errorCount: stats.errorCount,
          }));
          
          console.log('📊 Middleware: Performance stats updated', stats);
        }
      } catch (error) {
        console.error('❌ Middleware: Error processing WebSocket message:', error);
      }
    }, 0);
  }
  
  if (action.type === 'websocket/setConnectionStatus' && 'payload' in action) {
    const status: ConnectionStatus = action.payload as ConnectionStatus;
    
    if (status === 'connected') {
      api.dispatch(setStatusMessage('WebSocket connected successfully'));
    } else if (status === 'disconnected') {
      api.dispatch(setStatusMessage('WebSocket disconnected'));
    } else if (status === 'error') {
      api.dispatch(setStatusMessage('WebSocket connection error'));
      performanceMetrics.errorCount++;
    }
  }
  
  return result;
};


export const registerMessageRoute = (route: MessageRouteConfig) => {

  const existingIndex = messageRoutes.findIndex(r => r.type === route.type);
  
  if (existingIndex >= 0) {

    messageRoutes[existingIndex] = route;
    console.log(`🔄 Middleware: Updated message route for ${route.type}`);
  } else {
    messageRoutes.push(route);
    console.log(` Middleware: Added message route for ${route.type}`);
  }
};


export const unregisterMessageRoute = (messageType: string) => {
  const index = messageRoutes.findIndex(r => r.type === messageType);
  
  if (index >= 0) {
    messageRoutes.splice(index, 1);
    console.log(` Middleware: Removed message route for ${messageType}`);
  }
};

// Export function to set current project for isolation
export const setCurrentProjectForWorkflow = (projectId: string) => {
  console.log('🎯 Middleware: Setting current project for workflow isolation:', projectId);
  currentProjectId = projectId;
};

export default websocketMiddleware;
