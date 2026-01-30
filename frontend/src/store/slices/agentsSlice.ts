import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { AgentsState, LabOSAgent } from '../../types';

const initialState: AgentsState = {
  agents: {},
  activeAgent: null,
};

const agentsSlice = createSlice({
  name: 'agents',
  initialState,
  reducers: {
    setAgents: (state, action: PayloadAction<Record<string, LabOSAgent>>) => {
      state.agents = action.payload;
    },
    
    updateAgent: (state, action: PayloadAction<{ id: string; updates: Partial<LabOSAgent> }>) => {
      const { id, updates } = action.payload;
      if (state.agents[id]) {
        state.agents[id] = { ...state.agents[id], ...updates };
      }
    },
    
    setActiveAgent: (state, action: PayloadAction<string | null>) => {
      state.activeAgent = action.payload;
    },
  },
});

export const {
  setAgents,
  updateAgent,
  setActiveAgent,
} = agentsSlice.actions;

export default agentsSlice.reducer;
