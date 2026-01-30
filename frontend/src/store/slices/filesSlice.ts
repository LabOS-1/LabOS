import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { FilesState, SimpleFileInfo, SimpleMemoryItem } from '../../types';

const initialState: FilesState = {
  files: [],
  selectedFile: null,
  memoryItems: [],
  memoryStats: { total: 0, public: 0, private: 0 },
};

const filesSlice = createSlice({
  name: 'files',
  initialState,
  reducers: {
    setFiles: (state, action: PayloadAction<SimpleFileInfo[]>) => {
      state.files = action.payload;
    },
    
    addFile: (state, action: PayloadAction<SimpleFileInfo>) => {
      state.files.push(action.payload);
    },
    
    setSelectedFile: (state, action: PayloadAction<SimpleFileInfo | null>) => {
      state.selectedFile = action.payload;
    },
    
    setMemoryItems: (state, action: PayloadAction<SimpleMemoryItem[]>) => {
      state.memoryItems = action.payload;
    },
    
    updateMemoryStats: (state, action: PayloadAction<{ total: number; public: number; private: number }>) => {
      state.memoryStats = action.payload;
    },
  },
});

export const {
  setFiles,
  addFile,
  setSelectedFile,
  setMemoryItems,
  updateMemoryStats,
} = filesSlice.actions;

export default filesSlice.reducer;
