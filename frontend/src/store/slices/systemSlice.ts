import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { SystemState, SimpleSystemStatus } from '../../types';

const initialState: SystemState = {
  systemStatus: null,
  connected: null,  // null = not yet checked
};

const systemSlice = createSlice({
  name: 'system',
  initialState,
  reducers: {
    setSystemStatus: (state, action: PayloadAction<SimpleSystemStatus>) => {
      state.systemStatus = action.payload;
    },
    
    setConnected: (state, action: PayloadAction<boolean | null>) => {
      state.connected = action.payload;
    },
  },
});

export const {
  setSystemStatus,
  setConnected,
} = systemSlice.actions;

export default systemSlice.reducer;
