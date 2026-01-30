/**
 * UI state and component related types
 */

// Theme configuration
export interface UITheme {
  mode: 'light' | 'dark';
  primaryColor: string;
  accentColor: string;
  animations: boolean;
}

// Layout configuration
export interface UILayout {
  sidebarCollapsed: boolean;
  activeTab: string;
  chatPanelWidth: number;
  toolsPanelWidth: number;
}

// Notification item
export interface NotificationItem {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

// Component loading states
export interface LoadingState {
  loading: boolean;
  error?: string;
  lastUpdated?: string;
}

// Form validation state
export interface ValidationState {
  isValid: boolean;
  errors: Record<string, string>;
  touched: Record<string, boolean>;
}

// Modal state
export interface ModalState {
  visible: boolean;
  title?: string;
  content?: string;
  onConfirm?: () => void;
  onCancel?: () => void;
}

