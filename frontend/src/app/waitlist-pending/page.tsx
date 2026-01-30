'use client'

import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Container,
  Paper,
  Button,
  alpha,
  useTheme,
  CircularProgress,
  TextField,
  MenuItem,
  Alert
} from '@mui/material';
import {
  HourglassEmpty as WaitlistIcon,
  Email as EmailIcon,
  ExitToApp as LogoutIcon,
  Send as SendIcon
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useRouter, useSearchParams } from 'next/navigation';
import { useSelector } from 'react-redux';
import { RootState } from '@/types/store';
import { config } from '@/config';

const WaitlistPendingPage: React.FC = () => {
  const theme = useTheme();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState<string>('');
  const [showForm, setShowForm] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<boolean>(false);

  // Get user status from Redux
  const { user, isAuthenticated } = useSelector((state: RootState) => state.auth);
  
  // Form fields
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    job_title: '',
    organization: '',
    country: '',
    experience_level: '',
    use_case: ''
  });

  useEffect(() => {
    const emailParam = searchParams.get('email');
    if (emailParam) {
      setEmail(emailParam);
    }
  }, [searchParams]);

  // Auto-redirect if user status changes to approved
  useEffect(() => {
    if (isAuthenticated && user?.status === 'approved') {
      console.log('✅ [Waitlist Page] User approved, redirecting to dashboard...');
      router.push('/dashboard');
    } else if (user?.status === 'rejected') {
      console.log('❌ [Waitlist Page] User rejected');
      // Stay on page but could show rejection message
    }
  }, [isAuthenticated, user?.status, router]);

  const handleInputChange = (field: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, [field]: event.target.value }));
    setError(''); // Clear error when user types
  };
  
  const handleSubmit = async () => {
    // Validate all fields are filled
    const missingFields = Object.entries(formData)
      .filter(([_, value]) => !value || value.trim() === '')
      .map(([key, _]) => key);
    
    if (missingFields.length > 0) {
      setError('Please fill in all fields');
      return;
    }
    
    setSubmitting(true);
    setError('');
    
    try {
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const response = await fetch(`${config.api.baseUrl}/api/v1/auth/waitlist/submit`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify(formData),
      });
      
      if (response.ok) {
        setSuccess(true);
        setShowForm(false);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to submit application');
      }
    } catch (err) {
      console.error('Submit error:', err);
      setError('Network error. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = () => {
    // Clear local storage
    localStorage.removeItem('auth_token');
    
    // Redirect to logout endpoint
    window.location.href = `${config.api.baseUrl}/api/v1/auth/logout`;
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: `linear-gradient(135deg, ${alpha(theme.palette.warning.main, 0.1)} 0%, ${alpha(theme.palette.info.main, 0.05)} 100%)`,
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
              border: `2px solid ${alpha(theme.palette.warning.main, 0.3)}`
            }}
          >
            {/* Icon */}
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <Box sx={{ mb: 3 }}>
                <WaitlistIcon 
                  sx={{ 
                    fontSize: 80, 
                    color: theme.palette.warning.main,
                    filter: `drop-shadow(0 4px 12px ${alpha(theme.palette.warning.main, 0.4)})`
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
              {showForm ? 'Complete Your Application' : "You're on the Waitlist! 🎉"}
            </Typography>

            {/* Description */}
            <Typography 
              variant="body1" 
              color="text.secondary" 
              sx={{ mb: 3, lineHeight: 1.7 }}
            >
              {showForm 
                ? 'Please provide some additional information to help us understand your needs better.'
                : 'Thank you for signing up for LabOS AI!'}
            </Typography>

            {/* Email Display */}
            {email && (
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  mb: 3,
                  bgcolor: alpha(theme.palette.info.main, 0.1),
                  border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
                  borderRadius: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 1
                }}
              >
                <EmailIcon sx={{ color: theme.palette.info.main }} />
                <Typography 
                  variant="body2" 
                  sx={{ 
                    fontWeight: 500,
                    color: theme.palette.text.primary
                  }}
                >
                  {email}
                </Typography>
              </Paper>
            )}

            {/* Error Alert */}
            {error && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
              </Alert>
            )}
            
            {/* Application Form or Success Message */}
            {showForm ? (
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                  <TextField
                    fullWidth
                    label="First Name *"
                    value={formData.first_name}
                    onChange={handleInputChange('first_name')}
                    variant="outlined"
                  />
                  <TextField
                    fullWidth
                    label="Last Name *"
                    value={formData.last_name}
                    onChange={handleInputChange('last_name')}
                    variant="outlined"
                  />
                </Box>
                
                <TextField
                  fullWidth
                  label="Job Title *"
                  value={formData.job_title}
                  onChange={handleInputChange('job_title')}
                  variant="outlined"
                  sx={{ mb: 2 }}
                />
                
                <TextField
                  fullWidth
                  label="Affiliation/Organization *"
                  value={formData.organization}
                  onChange={handleInputChange('organization')}
                  variant="outlined"
                  sx={{ mb: 2 }}
                />
                
                <TextField
                  fullWidth
                  label="Country *"
                  value={formData.country}
                  onChange={handleInputChange('country')}
                  variant="outlined"
                  sx={{ mb: 2 }}
                />
                
                <TextField
                  fullWidth
                  select
                  label="Functional Screening Experience Level *"
                  value={formData.experience_level}
                  onChange={handleInputChange('experience_level')}
                  variant="outlined"
                  sx={{ mb: 2 }}
                >
                  <MenuItem value="beginner">Beginner</MenuItem>
                  <MenuItem value="intermediate">Intermediate</MenuItem>
                  <MenuItem value="advanced">Advanced</MenuItem>
                </TextField>
                
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="How do you plan to use LabOS? *"
                  value={formData.use_case}
                  onChange={handleInputChange('use_case')}
                  variant="outlined"
                  sx={{ mb: 2 }}
                />
              </Box>
            ) : (
              <Box
                sx={{
                  mb: 3,
                  p: 2.5,
                  bgcolor: alpha(theme.palette.warning.main, 0.08),
                  borderRadius: 2,
                  border: `1px dashed ${alpha(theme.palette.warning.main, 0.3)}`
                }}
              >
                <Typography 
                  variant="body2" 
                  color="text.secondary"
                  sx={{ mb: 1.5, fontWeight: 500 }}
                >
                  <strong>Current Status:</strong> Pending Approval
                </Typography>
                <Typography 
                  variant="body2" 
                  color="text.secondary"
                  sx={{ lineHeight: 1.6 }}
                >
                  Our team is reviewing your application. We'll notify you via email once your account is approved. This typically takes 1-2 business days.
                </Typography>
              </Box>
            )}

            {/* Action Buttons */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {showForm && (
                <Button
                  variant="contained"
                  size="large"
                  startIcon={submitting ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
                  onClick={handleSubmit}
                  disabled={submitting}
                  sx={{
                    borderRadius: 2,
                    py: 1.5,
                    bgcolor: theme.palette.primary.main,
                    '&:hover': {
                      bgcolor: theme.palette.primary.dark
                    }
                  }}
                >
                  {submitting ? 'Submitting...' : 'Submit Application'}
                </Button>
              )}
              
              <Button
                variant="outlined"
                size="large"
                startIcon={<LogoutIcon />}
                onClick={handleLogout}
                sx={{
                  borderRadius: 2,
                  py: 1.5,
                  borderColor: theme.palette.divider,
                  color: theme.palette.text.secondary,
                  '&:hover': {
                    borderColor: theme.palette.primary.main,
                    bgcolor: alpha(theme.palette.primary.main, 0.08)
                  }
                }}
              >
                Logout
              </Button>
            </Box>

            {/* Additional Info */}
            <Typography 
              variant="caption" 
              color="text.secondary"
              sx={{ 
                mt: 3, 
                display: 'block',
                fontSize: '0.75rem'
              }}
            >
              Need immediate access? Contact us at{' '}
              <Typography
                component="a"
                href="mailto:labos.agent2026@gmail.com"
                sx={{
                  color: theme.palette.primary.main,
                  textDecoration: 'none',
                  fontWeight: 500,
                  '&:hover': {
                    textDecoration: 'underline'
                  }
                }}
              >
                labos.agent2026@gmail.com
              </Typography>
            </Typography>
          </Paper>
        </motion.div>
      </Container>
    </Box>
  );
};

export default WaitlistPendingPage;

