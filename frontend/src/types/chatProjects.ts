/**
 * Chat Projects and Sessions Types
 */

export interface ChatProject {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  message_count: number;
}

// ChatSession removed - Projects now directly contain messages

// Request/Response types
export interface CreateProjectRequest {
  name: string;
  description?: string;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
}

// UI State types (simplified - no sessions)
export interface ChatProjectsUIState {
  selectedProjectId: string | null;
  projectSidebarOpen: boolean;
  createProjectModalOpen: boolean;
  isLoading: boolean;
  error: string | null;
}

// API Response types (matching simplified backend)
export interface ChatProjectResponse {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  message_count: number;
}
