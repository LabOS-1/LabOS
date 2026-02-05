/**
 * Chat Projects and Sessions Types
 */

export interface ChatSession {
  id: string;
  project_id: string;
  name: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatProject {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  session_count: number;
  sessions?: ChatSession[];
}

// Request/Response types
export interface CreateProjectRequest {
  name: string;
  description?: string;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
}

export interface CreateSessionRequest {
  name: string;
}

export interface UpdateSessionRequest {
  name?: string;
}

// UI State types
export interface ChatProjectsUIState {
  selectedProjectId: string | null;
  selectedSessionId: string | null;
  projectSidebarOpen: boolean;
  createProjectModalOpen: boolean;
  isLoading: boolean;
  error: string | null;
}

// API Response types
export interface ChatProjectResponse {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  session_count: number;
  sessions?: ChatSessionResponse[];
}

export interface ChatSessionResponse {
  id: string;
  project_id: string;
  name: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}
