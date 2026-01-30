import { useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useRouter, usePathname } from 'next/navigation';
import { setUser, clearUser } from '@/store/slices/authSlice';
import { RootState } from '@/types/store';
import { config } from '@/config';

/**
 * Hook to poll user authentication status periodically
 * Handles status changes (waitlist -> approved) and token validation
 *
 * @param intervalMs - Polling interval in milliseconds (default: 10000 = 10 seconds)
 * @param enablePolling - Whether to enable polling (default: true)
 */
export const useAuthStatusPolling = (intervalMs: number = 10000, enablePolling: boolean = true) => {
  const dispatch = useDispatch();
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, user } = useSelector((state: RootState) => state.auth);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isPollingRef = useRef(false);

  const checkAuthStatus = async () => {
    // Prevent concurrent polling requests
    if (isPollingRef.current) {
      return;
    }

    try {
      isPollingRef.current = true;

      const token = localStorage.getItem('auth_token');
      if (!token) {
        console.log('📊 [Auth Polling] No token found, skipping status check');
        return;
      }

      const response = await fetch(`${config.api.baseUrl}/api/v1/auth/me`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        if (response.status === 401) {
          console.warn('📊 [Auth Polling] Token invalid (401), clearing auth state');
          // Clear invalid token
          localStorage.removeItem('auth_token');
          document.cookie = 'auth_token=; path=/; max-age=0';
          dispatch(clearUser());

          // Redirect to login
          if (pathname !== '/welcome') {
            router.push('/welcome');
          }
        }
        return;
      }

      const userData = await response.json();

      // Check if status has changed
      const currentStatus = user?.status || 'waitlist';
      const newStatus = userData.status || 'waitlist';

      if (currentStatus !== newStatus) {
        console.log(`📊 [Auth Polling] Status changed: ${currentStatus} → ${newStatus}`);

        // Update user data in Redux
        dispatch(setUser({
          id: userData.id || userData.sub || '',
          email: userData.email || '',
          name: userData.name || '',
          picture: userData.picture,
          email_verified: userData.email_verified,
          is_admin: userData.is_admin || false,
          status: newStatus,
        }));

        // Handle status-based redirects
        if (newStatus === 'approved') {
          console.log('✅ [Auth Polling] User approved! Redirecting to dashboard...');

          // Clear any stale state
          localStorage.setItem('user_status', 'approved');

          // Redirect from waitlist pages to dashboard
          if (pathname.includes('waitlist')) {
            router.push('/dashboard');
          }
        } else if (newStatus === 'rejected') {
          console.log('❌ [Auth Polling] User rejected, redirecting to waitlist page');
          router.push('/waitlist-pending?status=rejected');
        } else if (newStatus === 'suspended') {
          console.log('⚠️ [Auth Polling] User suspended, clearing auth');
          localStorage.removeItem('auth_token');
          document.cookie = 'auth_token=; path=/; max-age=0';
          dispatch(clearUser());
          router.push('/welcome');
        }
      } else {
        // Even if status didn't change, update other user data (admin flag, etc.)
        if (userData.is_admin !== user?.is_admin) {
          console.log(`📊 [Auth Polling] Admin status changed: ${user?.is_admin} → ${userData.is_admin}`);
          dispatch(setUser({
            id: userData.id || userData.sub || '',
            email: userData.email || '',
            name: userData.name || '',
            picture: userData.picture,
            email_verified: userData.email_verified,
            is_admin: userData.is_admin || false,
            status: newStatus,
          }));
        }
      }

    } catch (error) {
      console.error('📊 [Auth Polling] Error checking auth status:', error);
    } finally {
      isPollingRef.current = false;
    }
  };

  useEffect(() => {
    // Only poll if authenticated and polling is enabled
    if (!isAuthenticated || !enablePolling) {
      return;
    }

    // Initial check immediately
    checkAuthStatus();

    // Set up polling interval
    pollingIntervalRef.current = setInterval(() => {
      checkAuthStatus();
    }, intervalMs);

    console.log(`📊 [Auth Polling] Started polling every ${intervalMs}ms`);

    // Cleanup on unmount
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
        console.log('📊 [Auth Polling] Stopped polling');
      }
    };
  }, [isAuthenticated, enablePolling, intervalMs, pathname]);

  // Return manual refresh function
  return {
    refreshAuthStatus: checkAuthStatus,
  };
};

export default useAuthStatusPolling;
