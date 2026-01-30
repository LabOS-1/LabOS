'use client'

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Box, CircularProgress, Typography } from '@mui/material';
import ProtectedRoute from '@/components/Auth/ProtectedRoute';

const Chat: React.FC = () => {
  const router = useRouter();

  useEffect(() => {
    // Redirect to chat projects page
    router.push('/chat/projects');
  }, [router]);

  return (
    <ProtectedRoute>
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: 2
      }}>
        <CircularProgress />
        <Typography variant="body2" color="text.secondary">
          Redirecting to Chat Projects...
        </Typography>
      </Box>
    </ProtectedRoute>
  );
};

export default Chat;
