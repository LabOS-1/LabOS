import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { ChatState, ChatMessage, TaskExecution } from '../../types';

const initialState: ChatState = {
  messages: [],
  inputValue: '',
  isLoading: false,
  isTyping: false,
  currentExecution: null,
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addMessage: (state, action: PayloadAction<ChatMessage>) => {
      state.messages.push(action.payload);
    },
    
    setMessages: (state, action: PayloadAction<ChatMessage[]>) => {
      state.messages = [...action.payload];
    },
    
    clearMessages: (state) => {
      state.messages = [];
    },
    
    setInputValue: (state, action: PayloadAction<string>) => {
      state.inputValue = action.payload;
    },
    
    // Action for using a tool from tools page
    setToolQuery: (state, action: PayloadAction<{ toolName: string; description?: string }>) => {
      const { toolName, description } = action.payload;
      const formattedToolName = toolName.replace(/_/g, ' ');
      state.inputValue = `Please use the "${formattedToolName}" tool to help me.${description ? ` This tool: ${description}` : ''}`;
    },
    
    setIsLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    
    setIsTyping: (state, action: PayloadAction<boolean>) => {
      state.isTyping = action.payload;
    },
    
    setCurrentExecution: (state, action: PayloadAction<TaskExecution | null>) => {
      if (action.payload) {
        // Convert TaskExecution to SimpleTaskExecution for store compatibility
        const converted = {
          id: action.payload.id,
          task: action.payload.task,
          status: action.payload.status === 'failed' ? 'error' as const : action.payload.status as 'pending' | 'running' | 'completed',
          progress: 0 // Default progress since TaskExecution doesn't have progress
        };
        state.currentExecution = converted;
      } else {
        state.currentExecution = action.payload;
      }
    },

    // Update follow-up questions for the last assistant message (sent separately for faster UX)
    updateLastMessageFollowUp: (state, action: PayloadAction<string[]>) => {
      // Find the last assistant message and update its follow_up_questions
      for (let i = state.messages.length - 1; i >= 0; i--) {
        if (state.messages[i].type === 'assistant') {
          state.messages[i] = {
            ...state.messages[i],
            metadata: {
              ...state.messages[i].metadata,
              follow_up_questions: action.payload
            }
          };
          console.log('💡 ChatSlice: Updated follow-up questions for last assistant message');
          break;
        }
      }
    },
  },
});

export const {
  addMessage,
  setMessages,
  clearMessages,
  setInputValue,
  setToolQuery,
  setIsLoading,
  setIsTyping,
  setCurrentExecution,
  updateLastMessageFollowUp,
} = chatSlice.actions;

export default chatSlice.reducer;
