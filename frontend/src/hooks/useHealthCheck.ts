'use client'

import { useEffect } from 'react';
import { useAppDispatch } from '@/store/hooks';
import { setConnected } from '@/store/slices/systemSlice';

export const useHealthCheck = () => {
  const dispatch = useAppDispatch();

  useEffect(() => {
    let mounted = true;

    const checkHealth = async () => {
      try {
        const response = await fetch('/api/v1/system/health');
        if (response.ok && mounted) {
          const data = await response.json();
          console.log('Health check response:', data);

          const isHealthy = data.success && data.data && data.data.status === 'healthy';
          dispatch(setConnected(isHealthy));
          console.log('Setting connected to:', isHealthy);
        } else if (mounted) {
          console.log('Health check failed - response not ok');
          dispatch(setConnected(false));
        }
      } catch (error) {
        if (mounted) {
          console.error('Health check failed:', error);
          dispatch(setConnected(false));
        }
      }
    };

    // Initial check
    checkHealth();

    // Check every 30 seconds
    const interval = setInterval(checkHealth, 30000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [dispatch]);
};
