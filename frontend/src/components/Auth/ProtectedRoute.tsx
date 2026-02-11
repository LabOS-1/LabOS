'use client'

import React from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';
import { useAppSelector } from '@/store/hooks';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading, user } = useAppSelector((state) => state.auth);
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    // Not authenticated → redirect to welcome page
    if (!isAuthenticated) {
      router.push('/');
      return;
    }

    // Authenticated but not approved → redirect based on status
    if (user) {
      if (user.status === 'new' || user.status === 'waitlist') {
        // New user or waitlist user → redirect to waitlist form
        router.push(`/waitlist-pending?email=${encodeURIComponent(user.email)}`);
      } else if (user.status === 'rejected') {
        router.push('/access-denied?reason=rejected');
      } else if (user.status === 'suspended') {
        router.push('/access-denied?reason=suspended');
      }
    }
  }, [isAuthenticated, isLoading, user, router]);

  // Show loading while checking auth
  if (isLoading) {
    return (
      <Box
        sx={{
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 2
        }}
      >
        <CircularProgress />
        <Typography variant="body2" color="text.secondary">
          Checking authentication...
        </Typography>
      </Box>
    );
  }

  // Don't render children if not authenticated or not approved
  if (!isAuthenticated || !user || user.status !== 'approved') {
    return null;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
