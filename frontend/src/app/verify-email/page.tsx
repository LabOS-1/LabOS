'use client'

import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  Email as EmailIcon,
  CheckCircle as CheckIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';

const VerifyEmailPage: React.FC = () => {
  const searchParams = useSearchParams();
  const email = searchParams.get('email');
  const [isChecking, setIsChecking] = useState(false);
  const [verificationSent, setVerificationSent] = useState(false);

  const handleResendVerification = async () => {
    setIsChecking(true);
    try {
      // Here you would call your backend to resend verification email
      // For now, just simulate the action
      await new Promise(resolve => setTimeout(resolve, 2000));
      setVerificationSent(true);
    } catch (error) {
      console.error('Failed to resend verification:', error);
    } finally {
      setIsChecking(false);
    }
  };

  const handleCheckVerification = () => {
    // Redirect back to login to check verification status
    window.location.href = '/api/v1/auth/login';
  };

  return (
    <Container maxWidth="sm" sx={{ mt: 8 }}>
      <Paper elevation={3} sx={{ p: 4, textAlign: 'center' }}>
        <EmailIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
        
        <Typography variant="h4" gutterBottom>
          Verify Your Email
        </Typography>
        
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Please verify your email address to continue using LabOS AI.
        </Typography>
        
        {email && (
          <Alert severity="info" sx={{ mb: 3, textAlign: 'left' }}>
            <Typography variant="body2">
              <strong>Email:</strong> {email}
            </Typography>
          </Alert>
        )}
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          We've sent a verification link to your email address. Please check your inbox 
          and click the verification link to activate your account.
        </Typography>
        
        {verificationSent && (
          <Alert severity="success" sx={{ mb: 3 }}>
            Verification email sent! Please check your inbox.
          </Alert>
        )}
        
        {/* <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Button
            variant="outlined"
            startIcon={isChecking ? <CircularProgress size={16} /> : <RefreshIcon />}
            onClick={handleResendVerification}
            disabled={isChecking}
          >
            {isChecking ? 'Sending...' : 'Resend Email'}
          </Button>
          
          <Button
            variant="contained"
            startIcon={<CheckIcon />}
            onClick={handleCheckVerification}
          >
            I've Verified
          </Button>
        </Box> */}
        
        <Typography variant="caption" color="text.secondary" sx={{ mt: 3, display: 'block' }}>
          Didn't receive the email? Check your spam folder or try resending.
        </Typography>
      </Paper>
    </Container>
  );
};

export default VerifyEmailPage;
