/**
 * Unified WebSocket Redux state management
 * Centrally manage all WebSocket related state to avoid duplication
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { 
  UnifiedWebSocketState, 
  ConnectionStatus,
  UnifiedWebSocketMessage 
} from '../../types/websocketUnified';
import type { WorkflowStep, CreatedFile } from '../../types/workflow';
import type { ChatResponse } from '../../types/chat';

// Initial state
const initialState: UnifiedWebSocketState = {
  // Connection management
  connectionStatus: 'disconnected',
  isConnected: false,
  lastPingTime: null,
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
  
  // Workflow state
  currentWorkflowId: null,
  workflowSteps: [],
  workflowGroups: [],
  workflowProgress: 0,
  currentStepIndex: 0,
  totalSteps: 0,
  isWorkflowActive: false,
  
  // Chat state
  isChatLoading: false,
  lastChatResponse: null,
  chatError: null,
  
  // Statistics and monitoring
  messageCount: 0,
  lastMessageTime: null,
  createdFiles: [],
  lastStatusMessage: 'WebSocket disconnected',
  
  // Performance monitoring
  averageResponseTime: 0,
  totalMessages: 0,
  errorCount: 0,
};

const websocketSlice = createSlice({
  name: 'websocket',
  initialState,
  reducers: {
    setConnectionStatus: (state, action: PayloadAction<ConnectionStatus>) => {
      state.connectionStatus = action.payload;
      state.isConnected = action.payload === 'connected';
      
      if (action.payload === 'connected') {
        state.reconnectAttempts = 0;
        state.lastStatusMessage = 'Connected to WebSocket server';
      } else if (action.payload === 'disconnected') {
        state.lastStatusMessage = 'Disconnected from WebSocket server';
      } else if (action.payload === 'reconnecting') {
        state.lastStatusMessage = `Reconnecting... (attempt ${state.reconnectAttempts + 1}/${state.maxReconnectAttempts})`;
      } else if (action.payload === 'error') {
        state.lastStatusMessage = 'WebSocket connection error';
      }
    },

    setConnected: (state, action: PayloadAction<boolean>) => {
      state.isConnected = action.payload;
      state.connectionStatus = action.payload ? 'connected' : 'disconnected';
    },

    incrementReconnectAttempts: (state) => {
      state.reconnectAttempts += 1;
      state.lastStatusMessage = `Reconnecting... (attempt ${state.reconnectAttempts}/${state.maxReconnectAttempts})`;
    },

    resetReconnectAttempts: (state) => {
      state.reconnectAttempts = 0;
    },

    updateLastPing: (state, action: PayloadAction<string>) => {
      state.lastPingTime = action.payload;
    },

    setCurrentWorkflowId: (state, action: PayloadAction<string | null>) => {
      state.currentWorkflowId = action.payload;
      if (action.payload) {
        state.lastStatusMessage = `Started workflow: ${action.payload}`;
      }
    },

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    addWorkflowStep: (state, action: PayloadAction<any>) => {
      const newStep = action.payload;
      const workflowId = newStep.workflow_id || state.currentWorkflowId;
      
      if (!workflowId) {
        console.warn('🔧 Redux addWorkflowStep: No workflow ID found, skipping step');
        return;
      }
      
      // Only check for exact ID match - don't use step_number or title matching
      // This prevents legitimate new steps from being treated as duplicates
      const existingIndex = state.workflowSteps.findIndex(
        step => step.id === newStep.id
      );

      if (existingIndex >= 0) {
        state.workflowSteps[existingIndex] = newStep;
      } else {
        // Insert step in correct position based on step_number
        if (newStep.step_number) {
          const insertIndex = state.workflowSteps.findIndex(step => 
            step.step_number && step.step_number > newStep.step_number
          );
          if (insertIndex >= 0) {
            state.workflowSteps.splice(insertIndex, 0, newStep);
          } else {
            state.workflowSteps.push(newStep);
          }
        } else {
          state.workflowSteps.push(newStep);
        }
      }

      let group = state.workflowGroups.find(g => g.workflowId === workflowId);
      if (!group) {
        group = {
          workflowId,
          steps: [],
          startTime: newStep.timestamp || new Date().toISOString(),
          isActive: true,
          progress: 0
        };
        state.workflowGroups.push(group);
        console.log('🔧 Redux: Created new workflow group:', workflowId);
      }

      // Only check for exact ID match in groups too
      const groupStepIndex = group.steps.findIndex(
        step => step.id === newStep.id
      );

      if (groupStepIndex >= 0) {
        group.steps[groupStepIndex] = newStep;
        console.log('🔧 Redux: Updated step in group:', workflowId);
      } else {
        // Show all workflow steps (removed filtering to ensure all steps are visible)
        // Insert step in correct position in group
        if (newStep.step_number) {
          const insertIndex = group.steps.findIndex(step =>
            step.step_number && step.step_number > newStep.step_number
          );
          if (insertIndex >= 0) {
            group.steps.splice(insertIndex, 0, newStep);
          } else {
            group.steps.push(newStep);
          }
        } else {
          group.steps.push(newStep);
        }
        console.log('🔧 Redux: Added new step to group:', workflowId, 'Total steps in group:', group.steps.length);
      }

      group.isActive = state.isWorkflowActive;

      // Update step index
      if (newStep.step_number) {
        state.currentStepIndex = Math.max(state.currentStepIndex, newStep.step_number);
      }

      state.lastStatusMessage = `Added workflow step: ${newStep.type}`;
    },

    updateWorkflowStep: (state, action: PayloadAction<{ stepId: string; updates: Partial<WorkflowStep> }>) => {
      const { stepId, updates } = action.payload;
      const stepIndex = state.workflowSteps.findIndex(step => step.id === stepId);
      
      if (stepIndex >= 0) {
        Object.assign(state.workflowSteps[stepIndex], updates);
        state.lastStatusMessage = `Updated workflow step: ${stepId}`;
      }
    },

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    setWorkflowSteps: (state, action: PayloadAction<any[]>) => {
      state.workflowSteps = action.payload;
      state.totalSteps = action.payload.length;
      state.lastStatusMessage = `Set ${action.payload.length} workflow steps`;
    },

    setWorkflowProgress: (state, action: PayloadAction<number>) => {
      state.workflowProgress = Math.max(0, Math.min(100, action.payload));
      state.lastStatusMessage = `Workflow progress: ${state.workflowProgress}%`;
    },

    updateWorkflowProgress: (state, action: PayloadAction<{ 
      progress?: number; 
      currentStep?: number; 
      totalSteps?: number; 
    }>) => {
      const { progress, currentStep, totalSteps } = action.payload;
      
      if (progress !== undefined) {
        state.workflowProgress = Math.max(0, Math.min(100, progress));
      }
      if (currentStep !== undefined) {
        state.currentStepIndex = currentStep;
      }
      if (totalSteps !== undefined) {
        state.totalSteps = totalSteps;
      }
      
      state.lastStatusMessage = `Progress: ${state.workflowProgress}% (${state.currentStepIndex}/${state.totalSteps})`;
    },

    setWorkflowActive: (state, action: PayloadAction<boolean>) => {
      state.isWorkflowActive = action.payload;
      state.lastStatusMessage = action.payload ? 'Workflow started' : 'Workflow completed';
      
      if (!action.payload) {
        state.workflowProgress = 100;
      }
    },

    clearWorkflowState: (state) => {
      state.currentWorkflowId = null;
      state.workflowSteps = [];
      state.workflowGroups = []; // 清理workflowGroups！
      state.workflowProgress = 0;
      state.currentStepIndex = 0;
      state.totalSteps = 0;
      state.isWorkflowActive = false;
      state.isChatLoading = false; // Also clear chat loading state
      state.createdFiles = [];
      state.lastStatusMessage = 'Workflow cleared';
      console.log('🧹 Cleared all workflow state including groups and chat loading');
    },

    setChatLoading: (state, action: PayloadAction<boolean>) => {
      state.isChatLoading = action.payload;
      state.chatError = null; 
      state.lastStatusMessage = action.payload ? 'Processing chat message...' : 'Chat ready';
    },

    setChatResponse: (state, action: PayloadAction<ChatResponse | null>) => {
      state.lastChatResponse = action.payload;
      state.isChatLoading = false;
      state.chatError = null;
      
      if (action.payload) {
        state.lastStatusMessage = 'Received chat response';
      }
    },

    setChatError: (state, action: PayloadAction<string | null>) => {
      state.chatError = action.payload;
      state.isChatLoading = false;
      
      if (action.payload) {
        state.errorCount += 1;
        state.lastStatusMessage = `Chat error: ${action.payload}`;
      }
    },

    // Statistics and monitoring
    incrementMessageCount: (state) => {
      state.messageCount += 1;
      state.totalMessages += 1;
      state.lastMessageTime = new Date().toISOString();
    },

    setLastMessageTime: (state, action: PayloadAction<string>) => {
      state.lastMessageTime = action.payload;
    },

    addCreatedFile: (state, action: PayloadAction<CreatedFile>) => {
      const newFile = action.payload;
      
      const exists = state.createdFiles.some(file => file.path === newFile.path);
      if (!exists) {
        state.createdFiles.push(newFile);
        state.lastStatusMessage = `Created file: ${newFile.name}`;
      }
    },

    setStatusMessage: (state, action: PayloadAction<string>) => {
      state.lastStatusMessage = action.payload;
    },

    updateStats: (state, action: PayloadAction<{
      averageResponseTime?: number;
      errorCount?: number;
    }>) => {
      const { averageResponseTime, errorCount } = action.payload;
      
      if (averageResponseTime !== undefined) {
        state.averageResponseTime = averageResponseTime;
      }
      if (errorCount !== undefined) {
        state.errorCount = errorCount;
      }
    },

    processWebSocketMessage: (state, action: PayloadAction<UnifiedWebSocketMessage>) => {
      const message = action.payload;
      
      state.messageCount += 1;
      state.totalMessages += 1;
      state.lastMessageTime = message.timestamp;

      switch (message.type) {
        case 'workflow_update':
          // Workflow processing is handled by middleware to prevent duplicates
          // Only update connection status here
          state.lastStatusMessage = `Workflow update received`;
          if (message.workflow_id) {
            state.currentWorkflowId = message.workflow_id;
          }
          break;

        case 'progress_update':
          if (message.progress !== undefined) {
            state.workflowProgress = Math.max(0, Math.min(100, message.progress));
          }
          if (message.current_step !== undefined) {
            state.currentStepIndex = message.current_step;
          }
          if (message.total_steps !== undefined) {
            state.totalSteps = message.total_steps;
          }
          state.lastStatusMessage = `Progress: ${state.workflowProgress}%`;
          break;

        case 'chat_completed':
          // Chat completion is handled by middleware to prevent duplicate processing
          // Only update basic status here
          state.lastStatusMessage = 'Chat completed';
          console.log('💬 Redux: Chat completed status updated (detailed processing in middleware)');
          break;

        case 'chat_started':
          state.isChatLoading = true;
          state.isWorkflowActive = true;
          state.chatError = null;
          
          // Don't automatically clear workflow steps on chat_started
          // Let the project switching logic handle clearing when needed
          console.log('🔄 Chat started - preserving existing workflow steps');
          state.workflowProgress = 0;
          state.currentStepIndex = 0;
          state.totalSteps = 0;
          
          if (message.workflow_id) {
            state.currentWorkflowId = message.workflow_id;
          }
          state.lastStatusMessage = 'Chat started';
          break;

        case 'chat_error':
          state.isChatLoading = false;
          state.chatError = message.error || 'Unknown chat error';
          state.errorCount += 1;
          state.lastStatusMessage = `Chat error: ${state.chatError}`;
          break;

        case 'workflow_completed':
          state.isWorkflowActive = false;
          state.workflowProgress = 100;
          state.lastStatusMessage = 'Workflow completed';
          break;
        
        case 'workflow_cancelled':
          // Handle workflow cancellation
          state.isWorkflowActive = false;
          state.isChatLoading = false;
          state.workflowProgress = 0;
          state.lastStatusMessage = message.message || 'Workflow cancelled';
          console.log('🛑 Workflow cancelled:', message.workflow_id);
          
          // Mark current workflow group as cancelled
          if (state.workflowGroups.length > 0) {
            const lastGroup = state.workflowGroups[state.workflowGroups.length - 1];
            if (lastGroup.isActive) {
              lastGroup.isActive = false;
              lastGroup.endTime = new Date().toISOString();
            }
          }
          break;

        case 'workflow_cleared':

          state.workflowSteps = [];
          state.workflowProgress = 0;
          state.currentStepIndex = 0;
          state.totalSteps = 0;
          state.isWorkflowActive = false;
          state.currentWorkflowId = null;
          state.createdFiles = [];
          state.lastStatusMessage = 'Workflow cleared';
          break;

        case 'pong':
          state.lastPingTime = message.timestamp;
          state.lastStatusMessage = 'Heartbeat received';
          break;

        case 'error':
          state.errorCount += 1;
          state.lastStatusMessage = `Error: ${message.error || 'Unknown error'}`;
          break;

        default:
          state.lastStatusMessage = `Received: ${message.type}`;
      }
    },

    resetWebSocketState: (state) => {
      Object.assign(state, initialState);
    },

    clearChatResponse: (state) => {
      state.lastChatResponse = null;
      state.isChatLoading = false;
      state.chatError = null;
    },

    // Update follow-up questions for the last chat response (sent separately for faster UX)
    updateFollowUpQuestions: (state, action: PayloadAction<{
      workflow_id?: string;
      project_id?: string;
      follow_up_questions: string[];
    }>) => {
      if (state.lastChatResponse) {
        // Update the existing response with follow-up questions
        state.lastChatResponse = {
          ...state.lastChatResponse,
          follow_up_questions: action.payload.follow_up_questions
        };
        state.lastStatusMessage = 'Follow-up questions received';
        console.log('💡 Redux: Updated follow-up questions:', action.payload.follow_up_questions);
      }
    },
  },
});

export const {

  setConnectionStatus,
  setConnected,
  incrementReconnectAttempts,
  resetReconnectAttempts,
  updateLastPing,

  // Workflow management
  setCurrentWorkflowId,
  addWorkflowStep,
  updateWorkflowStep,
  setWorkflowSteps,
  setWorkflowProgress,
  updateWorkflowProgress,
  setWorkflowActive,
  clearWorkflowState,

  // Chat management
  setChatLoading,
  setChatResponse,
  setChatError,

  // Statistics and monitoring
  incrementMessageCount,
  setLastMessageTime,
  addCreatedFile,
  setStatusMessage,
  updateStats,

  // Message processing
  processWebSocketMessage,
  resetWebSocketState,
  clearChatResponse,
  updateFollowUpQuestions,
} = websocketSlice.actions;

export default websocketSlice.reducer;
