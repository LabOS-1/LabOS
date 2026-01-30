import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { config } from '../../config';
import type { 
  ChatProject, 
  CreateProjectRequest, 
  UpdateProjectRequest,
  ChatProjectResponse
} from '../../types/chatProjects';

interface ChatProjectsState {
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

const initialState: ChatProjectsState = {
  projects: [],
  currentProject: null,
  selectedProjectId: null,
  projectsLoading: false,
  createProjectLoading: false,
  updateProjectLoading: false,
  deleteProjectLoading: false,
  error: null,
};

// Async thunks for API calls
export const fetchProjects = createAsyncThunk(
  'chatProjects/fetchProjects',
  async (_, { rejectWithValue }) => {
    try {
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${config.api.baseUrl}/api/v1/chat/projects`, {
        headers,
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
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${config.api.baseUrl}/api/v1/chat/projects`, {
        method: 'POST',
        headers,
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
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${config.api.baseUrl}/api/v1/chat/projects/${projectId}`, {
        method: 'PUT',
        headers,
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
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${config.api.baseUrl}/api/v1/chat/projects/${projectId}`, {
        method: 'DELETE',
        headers,
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
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${config.api.baseUrl}/api/v1/chat/projects/${projectId}`, {
        method: 'GET',
        headers,
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
    
    // Local state updates
    updateProjectMessageCount: (state, action: PayloadAction<{ projectId: string; increment: number }>) => {
      const project = state.projects.find(p => p.id === action.payload.projectId);
      if (project) {
        project.message_count += action.payload.increment;
      }
      if (state.currentProject?.id === action.payload.projectId) {
        state.currentProject.message_count += action.payload.increment;
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
        state.error = null;
      })
      .addCase(fetchSingleProject.rejected, (state, action) => {
        state.projectsLoading = false;
        state.error = action.payload as string;
      });
  },
});

export const {
  setSelectedProject,
  clearError,
  updateProjectMessageCount,
} = chatProjectsSlice.actions;

export default chatProjectsSlice.reducer;
