import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { config } from '../../config';
import type {
  ChatProject,
  ChatSession,
  CreateProjectRequest,
  UpdateProjectRequest,
  CreateSessionRequest,
  UpdateSessionRequest,
  ChatProjectResponse,
  ChatSessionResponse
} from '../../types/chatProjects';

// Helper function to get auth headers
const getAuthHeaders = (): Record<string, string> => {
  const token = localStorage.getItem('auth_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};

interface ChatProjectsState {
  // Data
  projects: ChatProject[];
  currentProject: ChatProject | null;
  currentSession: ChatSession | null;

  // UI State
  selectedProjectId: string | null;
  selectedSessionId: string | null;

  // Loading states
  projectsLoading: boolean;
  createProjectLoading: boolean;
  updateProjectLoading: boolean;
  deleteProjectLoading: boolean;
  sessionsLoading: boolean;
  createSessionLoading: boolean;

  // Error states
  error: string | null;
}

const initialState: ChatProjectsState = {
  projects: [],
  currentProject: null,
  currentSession: null,
  selectedProjectId: null,
  selectedSessionId: null,
  projectsLoading: false,
  createProjectLoading: false,
  updateProjectLoading: false,
  deleteProjectLoading: false,
  sessionsLoading: false,
  createSessionLoading: false,
  error: null,
};

// Async thunks for API calls
export const fetchProjects = createAsyncThunk(
  'chatProjects/fetchProjects',
  async (_, { rejectWithValue }) => {
    try {
      const response = await fetch(`${config.api.baseUrl}/api/v1/chat/projects`, {
        headers: getAuthHeaders(),
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch projects: ${response.statusText}`);
      }

      const projects: ChatProjectResponse[] = await response.json();
      return projects;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

export const createProject = createAsyncThunk(
  'chatProjects/createProject',
  async (request: CreateProjectRequest, { rejectWithValue }) => {
    try {
      const response = await fetch(`${config.api.baseUrl}/api/v1/chat/projects`, {
        method: 'POST',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`Failed to create project: ${response.statusText}`);
      }

      const project: ChatProjectResponse = await response.json();
      return project;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

export const updateProject = createAsyncThunk(
  'chatProjects/updateProject',
  async ({ projectId, request }: { projectId: string; request: UpdateProjectRequest }, { rejectWithValue }) => {
    try {
      const response = await fetch(`${config.api.baseUrl}/api/v1/chat/projects/${projectId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`Failed to update project: ${response.statusText}`);
      }

      const project: ChatProjectResponse = await response.json();
      return project;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

export const deleteProject = createAsyncThunk(
  'chatProjects/deleteProject',
  async (projectId: string, { rejectWithValue }) => {
    try {
      const response = await fetch(`${config.api.baseUrl}/api/v1/chat/projects/${projectId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to delete project: ${response.statusText}`);
      }

      return projectId;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

export const fetchSingleProject = createAsyncThunk(
  'chatProjects/fetchSingleProject',
  async (projectId: string, { rejectWithValue }) => {
    try {
      const response = await fetch(`${config.api.baseUrl}/api/v1/chat/projects/${projectId}`, {
        method: 'GET',
        headers: getAuthHeaders(),
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch project: ${response.statusText}`);
      }

      const project: ChatProjectResponse = await response.json();
      return project;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

// Session async thunks
export const createSession = createAsyncThunk(
  'chatProjects/createSession',
  async ({ projectId, request }: { projectId: string; request: CreateSessionRequest }, { rejectWithValue }) => {
    try {
      const response = await fetch(`${config.api.baseUrl}/api/v1/chat/projects/${projectId}/sessions`, {
        method: 'POST',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`Failed to create session: ${response.statusText}`);
      }

      const session: ChatSessionResponse = await response.json();
      return { projectId, session };
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

export const updateSession = createAsyncThunk(
  'chatProjects/updateSession',
  async ({ projectId, sessionId, request }: { projectId: string; sessionId: string; request: UpdateSessionRequest }, { rejectWithValue }) => {
    try {
      const response = await fetch(`${config.api.baseUrl}/api/v1/chat/projects/${projectId}/sessions/${sessionId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`Failed to update session: ${response.statusText}`);
      }

      const session: ChatSessionResponse = await response.json();
      return { projectId, sessionId, session };
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

export const deleteSession = createAsyncThunk(
  'chatProjects/deleteSession',
  async ({ projectId, sessionId }: { projectId: string; sessionId: string }, { rejectWithValue }) => {
    try {
      const response = await fetch(`${config.api.baseUrl}/api/v1/chat/projects/${projectId}/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to delete session: ${response.statusText}`);
      }

      return { projectId, sessionId };
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

const chatProjectsSlice = createSlice({
  name: 'chatProjects',
  initialState,
  reducers: {
    // UI Actions
    setSelectedProject: (state, action: PayloadAction<string | null>) => {
      state.selectedProjectId = action.payload;
      state.currentProject = action.payload 
        ? state.projects.find(p => p.id === action.payload) || null
        : null;
    },
    
    clearError: (state) => {
      state.error = null;
    },

    // Session management
    setSelectedSession: (state, action: PayloadAction<string | null>) => {
      state.selectedSessionId = action.payload;
      if (state.currentProject?.sessions) {
        state.currentSession = action.payload
          ? state.currentProject.sessions.find(s => s.id === action.payload) || null
          : null;
      }
    },

    // Local state updates for session message counts
    updateSessionMessageCount: (state, action: PayloadAction<{ sessionId: string; increment: number }>) => {
      if (state.currentProject?.sessions) {
        const session = state.currentProject.sessions.find(s => s.id === action.payload.sessionId);
        if (session) {
          session.message_count += action.payload.increment;
        }
      }
      if (state.currentSession?.id === action.payload.sessionId) {
        state.currentSession.message_count += action.payload.increment;
      }
    },
  },
  
  extraReducers: (builder) => {
    builder
      // Fetch Projects
      .addCase(fetchProjects.pending, (state) => {
        state.projectsLoading = true;
        state.error = null;
      })
      .addCase(fetchProjects.fulfilled, (state, action) => {
        state.projectsLoading = false;
        state.projects = action.payload;
        state.error = null;
      })
      .addCase(fetchProjects.rejected, (state, action) => {
        state.projectsLoading = false;
        state.error = action.payload as string;
      })
      
      // Create Project
      .addCase(createProject.pending, (state) => {
        state.createProjectLoading = true;
        state.error = null;
      })
      .addCase(createProject.fulfilled, (state, action) => {
        state.createProjectLoading = false;
        state.projects.unshift(action.payload);
        state.error = null;
      })
      .addCase(createProject.rejected, (state, action) => {
        state.createProjectLoading = false;
        state.error = action.payload as string;
      })
      
      // Update Project
      .addCase(updateProject.pending, (state) => {
        state.updateProjectLoading = true;
        state.error = null;
      })
      .addCase(updateProject.fulfilled, (state, action) => {
        state.updateProjectLoading = false;
        // Update project in the list
        const index = state.projects.findIndex(p => p.id === action.payload.id);
        if (index !== -1) {
          state.projects[index] = action.payload;
        }
        // Update current project if it's the same one
        if (state.currentProject?.id === action.payload.id) {
          state.currentProject = action.payload;
        }
        state.error = null;
      })
      .addCase(updateProject.rejected, (state, action) => {
        state.updateProjectLoading = false;
        state.error = action.payload as string;
      })
      
      // Delete Project
      .addCase(deleteProject.pending, (state) => {
        state.deleteProjectLoading = true;
        state.error = null;
      })
      .addCase(deleteProject.fulfilled, (state, action) => {
        state.deleteProjectLoading = false;
        // Remove project from the list
        state.projects = state.projects.filter(p => p.id !== action.payload);
        // Clear current project if it was deleted
        if (state.currentProject?.id === action.payload) {
          state.currentProject = null;
          state.selectedProjectId = null;
        }
        state.error = null;
      })
      .addCase(deleteProject.rejected, (state, action) => {
        state.deleteProjectLoading = false;
        state.error = action.payload as string;
      })

      // Fetch Single Project
      .addCase(fetchSingleProject.pending, (state) => {
        state.projectsLoading = true;
        state.error = null;
      })
      .addCase(fetchSingleProject.fulfilled, (state, action) => {
        state.projectsLoading = false;
        // Add or update project in the list
        const index = state.projects.findIndex(p => p.id === action.payload.id);
        if (index !== -1) {
          state.projects[index] = action.payload;
        } else {
          state.projects.push(action.payload);
        }
        // Update current project
        state.currentProject = action.payload;
        state.selectedProjectId = action.payload.id;
        // Auto-select first session if available
        if (action.payload.sessions && action.payload.sessions.length > 0) {
          state.selectedSessionId = action.payload.sessions[0].id;
          state.currentSession = action.payload.sessions[0];
        }
        state.error = null;
      })
      .addCase(fetchSingleProject.rejected, (state, action) => {
        state.projectsLoading = false;
        state.error = action.payload as string;
      })

      // Create Session
      .addCase(createSession.pending, (state) => {
        state.createSessionLoading = true;
        state.error = null;
      })
      .addCase(createSession.fulfilled, (state, action) => {
        state.createSessionLoading = false;
        const { projectId, session } = action.payload;
        // Add session to current project
        if (state.currentProject?.id === projectId) {
          if (!state.currentProject.sessions) {
            state.currentProject.sessions = [];
          }
          state.currentProject.sessions.unshift(session);
          state.currentProject.session_count += 1;
          // Auto-select the new session
          state.selectedSessionId = session.id;
          state.currentSession = session;
        }
        // Update in projects list
        const projectIndex = state.projects.findIndex(p => p.id === projectId);
        if (projectIndex !== -1) {
          if (!state.projects[projectIndex].sessions) {
            state.projects[projectIndex].sessions = [];
          }
          state.projects[projectIndex].sessions!.unshift(session);
          state.projects[projectIndex].session_count += 1;
        }
        state.error = null;
      })
      .addCase(createSession.rejected, (state, action) => {
        state.createSessionLoading = false;
        state.error = action.payload as string;
      })

      // Update Session
      .addCase(updateSession.pending, (state) => {
        state.sessionsLoading = true;
        state.error = null;
      })
      .addCase(updateSession.fulfilled, (state, action) => {
        state.sessionsLoading = false;
        const { projectId, sessionId, session } = action.payload;
        // Update session in current project
        if (state.currentProject?.id === projectId && state.currentProject.sessions) {
          const sessionIndex = state.currentProject.sessions.findIndex(s => s.id === sessionId);
          if (sessionIndex !== -1) {
            state.currentProject.sessions[sessionIndex] = session;
          }
        }
        // Update current session if it's the one being edited
        if (state.currentSession?.id === sessionId) {
          state.currentSession = session;
        }
        // Update in projects list
        const projectIndex = state.projects.findIndex(p => p.id === projectId);
        if (projectIndex !== -1 && state.projects[projectIndex].sessions) {
          const sessionIndex = state.projects[projectIndex].sessions!.findIndex(s => s.id === sessionId);
          if (sessionIndex !== -1) {
            state.projects[projectIndex].sessions![sessionIndex] = session;
          }
        }
        state.error = null;
      })
      .addCase(updateSession.rejected, (state, action) => {
        state.sessionsLoading = false;
        state.error = action.payload as string;
      })

      // Delete Session
      .addCase(deleteSession.pending, (state) => {
        state.sessionsLoading = true;
        state.error = null;
      })
      .addCase(deleteSession.fulfilled, (state, action) => {
        state.sessionsLoading = false;
        const { projectId, sessionId } = action.payload;
        // Remove session from current project
        if (state.currentProject?.id === projectId && state.currentProject.sessions) {
          state.currentProject.sessions = state.currentProject.sessions.filter(s => s.id !== sessionId);
          state.currentProject.session_count -= 1;
          // Clear current session if deleted
          if (state.selectedSessionId === sessionId) {
            state.selectedSessionId = state.currentProject.sessions[0]?.id || null;
            state.currentSession = state.currentProject.sessions[0] || null;
          }
        }
        // Update in projects list
        const projectIndex = state.projects.findIndex(p => p.id === projectId);
        if (projectIndex !== -1 && state.projects[projectIndex].sessions) {
          state.projects[projectIndex].sessions = state.projects[projectIndex].sessions!.filter(s => s.id !== sessionId);
          state.projects[projectIndex].session_count -= 1;
        }
        state.error = null;
      })
      .addCase(deleteSession.rejected, (state, action) => {
        state.sessionsLoading = false;
        state.error = action.payload as string;
      });
  },
});

export const {
  setSelectedProject,
  setSelectedSession,
  clearError,
  updateSessionMessageCount,
} = chatProjectsSlice.actions;

export default chatProjectsSlice.reducer;
