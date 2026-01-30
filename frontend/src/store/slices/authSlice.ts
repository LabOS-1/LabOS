import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { config } from '@/config';

export interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
  email_verified?: boolean;
  is_admin?: boolean;
  status?: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  isLoading: true, // Start with loading to check auth status
  error: null,
};

// Async thunk to check authentication status
export const checkAuthStatus = createAsyncThunk(
  'auth/checkStatus',
  async () => {
    const authUrl = `${config.api.baseUrl}/api/v1/auth/me`;
    console.log('🔍 AuthSlice: Checking auth status at:', authUrl);
    
    const response = await fetch(authUrl, {
      credentials: 'include', // Include cookies for authentication
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    console.log('📡 AuthSlice: Response status:', response.status);
    
    if (response.ok) {
      const user = await response.json();
      console.log('✅ AuthSlice: User authenticated:', user.email);
      return user;
    }
    
    console.log('🚫 AuthSlice: User not authenticated');
    throw new Error('Not authenticated');
  }
);

// Async thunk to logout
export const logout = createAsyncThunk(
  'auth/logout',
  async () => {
    // Clear local authentication data first
    localStorage.removeItem('auth_token');
    
    // Then redirect to backend Auth0 logout
    window.location.href = `${config.api.baseUrl}/api/v1/auth/logout`;
  }
);

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setUser: (state, action: PayloadAction<User>) => {
      state.user = action.payload;
      state.isAuthenticated = true;
      state.isLoading = false;
      state.error = null;
    },
    clearUser: (state) => {
      state.user = null;
      state.isAuthenticated = false;
      state.isLoading = false;
      state.error = null;
      // Also clear localStorage when clearing user state
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token');
      }
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
      state.isLoading = false;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(checkAuthStatus.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(checkAuthStatus.fulfilled, (state, action) => {
        state.user = action.payload;
        state.isAuthenticated = true;
        state.isLoading = false;
        state.error = null;
      })
      .addCase(checkAuthStatus.rejected, (state) => {
        state.user = null;
        state.isAuthenticated = false;
        state.isLoading = false;
        state.error = null; // Don't show error for unauthenticated state
      })
      .addCase(logout.pending, (state) => {
        state.isLoading = true;
      });
  },
});

export const { setUser, clearUser, setLoading, setError } = authSlice.actions;
export default authSlice.reducer;
