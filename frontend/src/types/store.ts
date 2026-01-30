/**
 * Redux store state types
 */

import { LabOSAgent } from './agents';
import { SimpleSystemStatus } from './system';
import { SimpleFileInfo } from './files';
import { SimpleMemoryItem } from './memory';
import { UITheme, UILayout, NotificationItem } from './ui';
import { UnifiedWebSocketState } from './websocketUnified';
import type { ChatProject } from './chatProjects';

// Root state interface
export interface RootState {
  agents: AgentsState;
  tools: ToolsState;
  chat: ChatState;
  chatProjects: ChatProjectsState;
  websocket: UnifiedWebSocketState;
  system: SystemState;
  files: FilesState;
  ui: UIState;
  auth: AuthState;
}

// Auth state interface
export interface AuthState {
  user: {
    id: string;
    email: string;
    name: string;
    picture?: string;
    email_verified?: boolean;
    is_admin?: boolean;
    status?: 'waitlist' | 'approved' | 'rejected' | 'suspended';
  } | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

// Individual slice states
export interface AgentsState {
  agents: Record<string, LabOSAgent>;
  activeAgent: string | null;
}

// Simple tool for store compatibility
interface SimpleTool {
  id: string;
  name: string;
  description: string;
  category: string;
}

export interface ToolsState {
  tools: SimpleTool[];
  dynamicTools: SimpleTool[];
  toolsLoading: boolean;
}

// Simple chat message for store compatibility
interface SimpleChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: string;
  agent_id?: string;
  metadata?: {
    execution_time?: number;
    agent_id?: string;
    using_real_labos?: boolean;
    workflow_id?: string;
    project_id?: string;
    error?: boolean;
    follow_up_questions?: string[];
  };
}

// Simple task execution for store compatibility
interface SimpleTaskExecution {
  id: string;
  task: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  progress?: number;
}

export interface ChatState {
  messages: SimpleChatMessage[];
  inputValue: string;
  isLoading: boolean;
  isTyping: boolean;
  currentExecution: SimpleTaskExecution | null;
}

export interface SystemState {
  systemStatus: SimpleSystemStatus | null;
  connected: boolean | null;  // null = not yet checked, true = online, false = offline
}

export interface FilesState {
  files: SimpleFileInfo[];
  selectedFile: SimpleFileInfo | null;
  memoryItems: SimpleMemoryItem[];
  memoryStats: {
    total: number;
    public: number;
    private: number;
  };
}

export interface UIState {
  theme: UITheme;
  layout: UILayout;
  notifications: NotificationItem[];
}

export interface ChatProjectsState {
  // Data
  projects: ChatProject[];
  currentProject: ChatProject | null;
  
  // UI State
  selectedProjectId: string | null;
  
  // Loading states
  projectsLoading: boolean;
  createProjectLoading: boolean;
  updateProjectLoading: boolean;
  deleteProjectLoading: boolean;
  
  // Error states
  error: string | null;
}
