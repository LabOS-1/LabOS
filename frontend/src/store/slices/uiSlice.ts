import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { UIState, UITheme, UILayout, NotificationItem } from '../../types';

const initialState: UIState = {
  theme: {
    mode: 'light',
    primaryColor: '#0ea5e9',
    accentColor: '#a855f7',
    animations: true,
  },
  layout: {
    sidebarCollapsed: false,
    activeTab: 'chat',
    chatPanelWidth: 400,
    toolsPanelWidth: 300,
  },
  notifications: [],
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    updateTheme: (state, action: PayloadAction<Partial<UITheme>>) => {
      state.theme = { ...state.theme, ...action.payload };
    },
    
    updateLayout: (state, action: PayloadAction<Partial<UILayout>>) => {
      state.layout = { ...state.layout, ...action.payload };
    },
    
    addNotification: (state, action: PayloadAction<Omit<NotificationItem, 'id'>>) => {
      const notification = {
        ...action.payload,
        id: Date.now().toString(),
      };
      state.notifications.push(notification);
    },
    
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(n => n.id !== action.payload);
    },
    
    markNotificationRead: (state, action: PayloadAction<string>) => {
      const notification = state.notifications.find(n => n.id === action.payload);
      if (notification) {
        notification.read = true;
      }
    },
  },
});

export const {
  updateTheme,
  updateLayout,
  addNotification,
  removeNotification,
  markNotificationRead,
} = uiSlice.actions;

export default uiSlice.reducer;
