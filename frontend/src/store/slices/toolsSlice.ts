import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { ToolsState } from '../../types';

// Enhanced Tool type definition to match backend response
interface Tool {
  id: string;
  name: string;
  description: string;
  category: string;
  type?: 'base' | 'dynamic';
  usage_count?: number;
  last_used?: string;
  created_at?: string;
  updated_at?: string;
}

const initialState: ToolsState = {
  tools: [],
  dynamicTools: [],
  toolsLoading: false,
};

const toolsSlice = createSlice({
  name: 'tools',
  initialState,
  reducers: {
    setTools: (state, action: PayloadAction<Tool[]>) => {
      state.tools = action.payload;
    },
    
    addDynamicTool: (state, action: PayloadAction<Tool>) => {
      state.dynamicTools.push(action.payload);
    },
    
    setToolsLoading: (state, action: PayloadAction<boolean>) => {
      state.toolsLoading = action.payload;
    },
  },
});

export const {
  setTools,
  addDynamicTool,
  setToolsLoading,
} = toolsSlice.actions;

export default toolsSlice.reducer;
