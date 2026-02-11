'use client'

import { useEffect } from 'react';
import { useAppDispatch } from '@/store/hooks';
import { setUser, clearUser, setLoading } from '@/store/slices/authSlice';
import { config } from '@/config';
import useAuthStatusPolling from '@/hooks/useAuthStatusPolling';

const AuthSync: React.FC = () => {
  const dispatch = useAppDispatch();

  // Enable status polling every 10 seconds for authenticated users
  useAuthStatusPolling(10000, true);

  useEffect(() => {
    let isMounted = true; // Prevent state updates if component unmounted
    const checkAuthStatus = async () => {
      // Check for auth token in URL (from Auth0 callback) FIRST
      const urlParams = new URLSearchParams(window.location.search);
      const authToken = urlParams.get('auth_token');
      
      let tokenToUse = null;
      
      if (authToken) {
        console.log('🎯 AuthSync: Found auth token in URL, storing it');
        localStorage.setItem('auth_token', authToken);
        // Also set as cookie for middleware access
        document.cookie = `auth_token=${authToken}; path=/; max-age=${60 * 60 * 24}; SameSite=Lax`;
        tokenToUse = authToken;
        // Clean up URL by removing the token parameter
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.delete('auth_token');
        window.history.replaceState({}, '', newUrl.toString());
      } else {
        // Get stored auth token
        tokenToUse = localStorage.getItem('auth_token');
        // Sync to cookie if exists in localStorage but not in cookie
        if (tokenToUse && !document.cookie.includes('auth_token=')) {
          document.cookie = `auth_token=${tokenToUse}; path=/; max-age=${60 * 60 * 24}; SameSite=Lax`;
        }
      }
      dispatch(setLoading(true));
      
      try {
        const authUrl = `${config.api.baseUrl}/api/v1/auth/me`;
        console.log('🔍 AuthSync: Checking auth status at:', authUrl);
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout for better reliability
        
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        };
        
        // Add Authorization header if we have a token
        if (tokenToUse) {
          headers['Authorization'] = `Bearer ${tokenToUse}`;
          console.log('🔑 AuthSync: Using auth token');
        } else {
          console.log('⚠️ AuthSync: No token available');
        }
        
        const response = await fetch(authUrl, {
          method: 'GET',
          credentials: 'include', // Include cookies for authentication (fallback)
          headers,
          signal: controller.signal,
          cache: 'no-cache', // Prevent caching issues
        });
        
        clearTimeout(timeoutId);
        
        console.log('📡 AuthSync: Response status:', response.status);
        
        if (response.ok) {
          const user = await response.json();
          console.log('✅ AuthSync: User authenticated:', user.email);
          dispatch(setUser({
            id: user.id || user.sub || '',
            email: user.email || '',
            name: user.name || '',
            picture: user.picture,
            email_verified: user.email_verified,
            is_admin: user.is_admin || false,
            status: user.status || 'waitlist',
          }));
        } else {
          // User not authenticated - clear stored token
          console.log('🚫 AuthSync: User not authenticated');
          if (tokenToUse) {
            console.log('🗑️ AuthSync: Clearing invalid token');
            localStorage.removeItem('auth_token');
            // Also clear cookie
            document.cookie = 'auth_token=; path=/; max-age=0';
          }
          dispatch(clearUser());
        }
      } catch (error) {
        console.error('❌ AuthSync: Auth check error:', error);
        console.error('🔧 AuthSync: Config API base URL:', config.api.baseUrl);
        
        // Type guard for error handling
        const errorMessage = error instanceof Error ? error.message : String(error);
        const errorName = error instanceof Error ? error.name : 'Unknown';
        const errorConstructor = error instanceof Error ? error.constructor.name : 'Unknown';
        
        console.error('🔧 AuthSync: Error type:', errorConstructor);
        console.error('🔧 AuthSync: Error message:', errorMessage);
        
        // Check different error types
        if (errorMessage === 'Failed to fetch') {
          console.error('🌐 AuthSync: Network error - backend may not be running or CORS issue');
          console.error('💡 AuthSync: Try starting backend with: uvicorn app.main:app --host 0.0.0.0 --port 18800');
        } else if (errorName === 'AbortError') {
          console.warn('⏱️ AuthSync: Request timeout - backend may be starting up');
        } else if (errorMessage.includes('CORS')) {
          console.error('🔒 AuthSync: CORS error - check backend CORS configuration');
        }
        
        dispatch(clearUser());
      } finally {
        if (isMounted) {
          dispatch(setLoading(false));
        }
      }
    };

    checkAuthStatus();
    
    // Cleanup function
    return () => {
      isMounted = false;
    };
  }, [dispatch]);

  return null; // This component only syncs state
};

export default AuthSync;
