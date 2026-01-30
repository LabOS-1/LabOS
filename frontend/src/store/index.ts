import { configureStore } from '@reduxjs/toolkit';
import { persistStore, persistReducer } from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import { combineReducers } from '@reduxjs/toolkit';

// Import all slices
import agentsReducer from './slices/agentsSlice';
import toolsReducer from './slices/toolsSlice';
import chatReducer from './slices/chatSlice';
import chatProjectsReducer from './slices/chatProjectsSlice';
import websocketReducer from './slices/websocketSlice';
import systemReducer from './slices/systemSlice';
import filesReducer from './slices/filesSlice';
import uiReducer from './slices/uiSlice';
import authReducer from './slices/authSlice';

import type { RootState } from '../types';
import { websocketMiddleware } from './middleware/websocketMiddleware';

// Combine all reducers
const rootReducer = combineReducers({
  agents: agentsReducer,
  tools: toolsReducer,
  chat: chatReducer,
  chatProjects: chatProjectsReducer,
  websocket: websocketReducer,
  system: systemReducer,
  files: filesReducer,
  ui: uiReducer,
  auth: authReducer,
});

// Persist configuration - only persist UI settings like Zustand
const persistConfig = {
  key: 'labos-store',
  storage,
  whitelist: ['ui'], // Only persist UI (theme, layout)
};

const persistedReducer = persistReducer(persistConfig, rootReducer);

// Create store
export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
      },
    }).concat(websocketMiddleware),
  devTools: process.env.NODE_ENV !== 'production',
});

export const persistor = persistStore(store);

// Expose store globally for WebSocket manager
if (typeof window !== 'undefined') {
  (window as any).__REDUX_STORE__ = store;
}

// Export types
export type AppDispatch = typeof store.dispatch;
export type { RootState };

export default store;
