'use client'

import React, { useEffect, useState } from 'react';
import { 
  Box, 
  Typography, 
  Container, 
  Paper,
  Button,
  alpha,
  useTheme
} from '@mui/material';
import {
  Block as BlockIcon,
  ExitToApp as LogoutIcon,
  Email as EmailIcon
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useRouter, useSearchParams } from 'next/navigation';
import { config } from '@/config';

const AccessDeniedPage: React.FC = () => {
  const theme = useTheme();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [reason, setReason] = useState<string>('');

  useEffect(() => {
    const reasonParam = searchParams.get('reason');
    if (reasonParam) {
      setReason(reasonParam);
    }
  }, [searchParams]);

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    window.location.href = `${config.api.baseUrl}/api/v1/auth/logout`;
  };

  const getReasonMessage = () => {
    switch (reason) {
      case 'rejected':
        return {
          title: 'Access Denied',
          message: 'Your application to access LabOS AI has been rejected. If you believe this is an error, please contact our support team.',
          icon: '❌'
        };
      case 'suspended':
        return {
          title: 'Account Suspended',
          message: 'Your account has been temporarily suspended. Please contact our support team for more information.',
          icon: '🚫'
        };
      default:
        return {
          title: 'Access Denied',
          message: 'You do not have permission to access this application. Please contact our support team for assistance.',
          icon: '⚠️'
        };
    }
  };

  const reasonInfo = getReasonMessage();

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: `linear-gradient(135deg, ${alpha(theme.palette.error.main, 0.1)} 0%, ${alpha(theme.palette.grey[500], 0.05)} 100%)`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        py: 4
      }}
    >
      <Container maxWidth="sm">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <Paper
            elevation={8}
            sx={{
              p: 4,
              textAlign: 'center',
              borderRadius: 3,
              border: `2px solid ${alpha(theme.palette.error.main, 0.3)}`
            }}
          >
            {/* Icon */}
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <Box sx={{ mb: 3 }}>
                <BlockIcon 
                  sx={{ 
                    fontSize: 80, 
                    color: theme.palette.error.main,
                    filter: `drop-shadow(0 4px 12px ${alpha(theme.palette.error.main, 0.4)})`
                  }} 
                />
              </Box>
            </motion.div>

            {/* Title */}
            <Typography 
              variant="h4" 
              component="h1" 
              sx={{ 
                fontWeight: 700, 
                mb: 2,
                color: theme.palette.text.primary
              }}
            >
              {reasonInfo.icon} {reasonInfo.title}
            </Typography>

            {/* Description */}
            <Typography 
              variant="body1" 
              color="text.secondary" 
              sx={{ mb: 3, lineHeight: 1.7 }}
            >
              {reasonInfo.message}
            </Typography>

            {/* Contact Info */}
            <Paper
              elevation={0}
              sx={{
                p: 2.5,
                mb: 3,
                bgcolor: alpha(theme.palette.info.main, 0.08),
                border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
                borderRadius: 2
              }}
            >
              <Typography 
                variant="body2" 
                color="text.secondary"
                sx={{ mb: 1, fontWeight: 500 }}
              >
                Need help?
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                <EmailIcon sx={{ color: theme.palette.info.main, fontSize: 20 }} />
                <Typography
                  component="a"
                  href="mailto:stella.agent2026@gmail.com"
                  sx={{
                    color: theme.palette.primary.main,
                    textDecoration: 'none',
                    fontWeight: 500,
                    fontSize: '0.95rem',
                    '&:hover': {
                      textDecoration: 'underline'
                    }
                  }}
                >
                  stella.agent2026@gmail.com
                </Typography>
              </Box>
            </Paper>

            {/* Action Button */}
            <Button
              variant="contained"
              size="large"
              startIcon={<LogoutIcon />}
              onClick={handleLogout}
              sx={{
                borderRadius: 2,
                py: 1.5,
                px: 4
              }}
            >
              Return to Login
            </Button>
          </Paper>
        </motion.div>
      </Container>
    </Box>
  );
};

export default AccessDeniedPage;

