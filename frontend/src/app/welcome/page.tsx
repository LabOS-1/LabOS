'use client'

import React from 'react';
import { config } from '@/config';
import { 
  Box, 
  Typography, 
  Button, 
  Grid, 
  Card, 
  CardContent,
  Container,
  alpha,
  useTheme,
  Chip,
  Stack
} from '@mui/material';
import {
  Login as LoginIcon,
  PersonAdd as RegisterIcon,
  Science as ScienceIcon,
  AutoAwesome as AIIcon,
  Biotech as BiotechIcon,
  Analytics as AnalyticsIcon,
  Security as SecurityIcon,
  Groups as GroupsIcon
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import Image from 'next/image';

const WelcomePage: React.FC = () => {
  const router = useRouter();
  const theme = useTheme();

  const features = [
    {
      title: 'AI-Powered Research',
      description: 'Advanced artificial intelligence to accelerate your biomedical research',
      icon: <AIIcon sx={{ fontSize: 40 }} />,
      color: theme.palette.primary.main,
    },
    {
      title: 'Laboratory Tools',
      description: 'Comprehensive suite of digital laboratory and analysis tools',
      icon: <ScienceIcon sx={{ fontSize: 40 }} />,
      color: theme.palette.secondary.main,
    },
    {
      title: 'Data Analytics',
      description: 'Powerful analytics and visualization for research data',
      icon: <AnalyticsIcon sx={{ fontSize: 40 }} />,
      color: theme.palette.success.main,
    },
    {
      title: 'Biotech Integration',
      description: 'Seamless integration with biotechnology workflows',
      icon: <BiotechIcon sx={{ fontSize: 40 }} />,
      color: theme.palette.info.main,
    },
    {
      title: 'Secure & Compliant',
      description: 'Enterprise-grade security for sensitive research data',
      icon: <SecurityIcon sx={{ fontSize: 40 }} />,
      color: theme.palette.warning.main,
    },
    {
      title: 'Collaboration',
      description: 'Team collaboration tools for research projects',
      icon: <GroupsIcon sx={{ fontSize: 40 }} />,
      color: theme.palette.text.secondary,
    },
  ];

  const handleLogin = () => {
    // Redirect to backend Auth0 login
    window.location.href = `${config.api.baseUrl}/api/v1/auth/login`;
  };



  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.1)} 0%, ${alpha(theme.palette.secondary.main, 0.05)} 100%)`,
        display: 'flex',
        flexDirection: 'column',
        py: { xs: 4, md: 6 }
      }}
    >
      <Container maxWidth="lg">
        {/* Header Section */}
        <motion.div
          initial={{ opacity: 0, y: -30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <Box sx={{ textAlign: 'center', mb: 6 }}>
            {/* Logo */}
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <Box sx={{ mb: 3, display: 'flex', justifyContent: 'center' }}>
                <Box
                  sx={{
                    width: 140,
                    height: 140,
                    borderRadius: 2,
                    overflow: 'hidden',
                    border: `4px solid ${theme.palette.primary.main}`,
                    boxShadow: `0 8px 32px ${alpha(theme.palette.primary.main, 0.3)}`,
                    bgcolor: '#ffffff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    p: 0
                  }}
                >
                  <Image
                    src="/logo.png"
                    alt="LabOS AI Logo"
                    width={120}
                    height={120}
                    style={{ objectFit: 'contain' }}
                  />
                </Box>
              </Box>
            </motion.div>

            {/* Title and Description */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            >
              <Typography
                variant="h1"
                component="h1"
                sx={{
                  fontWeight: 800,
                  mb: 3,
                  background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  fontSize: { xs: '2.75rem', md: '4.5rem' },
                  letterSpacing: '-0.02em',
                  lineHeight: 1.1
                }}
              >
                Welcome to LabOS
              </Typography>
              <Typography
                variant="h5"
                color="text.secondary"
                sx={{ 
                  mb: 5, 
                  maxWidth: 680, 
                  mx: 'auto', 
                  lineHeight: 1.6,
                  fontSize: { xs: '1.1rem', md: '1.25rem' },
                  fontWeight: 400
                }}
              >
                Your self-evolving intelligent laboratory assistant for advanced biomedical research. 
                Accelerate discoveries with AI-powered insights and automated workflows.
              </Typography>
            </motion.div>

            {/* Status Badge */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >

            </motion.div>

            {/* Auth Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
            >
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} justifyContent="center">
                <Button
                  variant="contained"
                  size="large"
                  startIcon={<LoginIcon />}
                  onClick={handleLogin}
                  sx={{
                    px: 4,
                    py: 2,
                    fontSize: '1.1rem',
                    borderRadius: 3,
                    boxShadow: `0 8px 24px ${alpha(theme.palette.primary.main, 0.3)}`,
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: `0 12px 32px ${alpha(theme.palette.primary.main, 0.4)}`,
                    },
                    transition: 'all 0.3s ease'
                  }}
                >
                  Start
                </Button>

              </Stack>
            </motion.div>
          </Box>
        </motion.div>

        {/* Features Grid */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
        >
          <Typography
            variant="h4"
            component="h2"
            sx={{ 
              textAlign: 'center', 
              mb: 2, 
              fontWeight: 600,
              color: 'text.primary' // Ensure primary text color for better visibility
            }}
          >
            Why Choose LabOS AI?
          </Typography>
          <Typography
            variant="body1"
            color="text.secondary"
            sx={{ textAlign: 'center', mb: 4, maxWidth: 700, mx: 'auto' }}
          >
            Join researchers worldwide who trust LabOS AI to accelerate their biomedical discoveries
          </Typography>

          <Grid container spacing={3}>
            {features.map((feature, index) => (
              <Grid size={{ xs: 12, sm: 6, md: 4 }} key={feature.title}>
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.7 + index * 0.1 }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Card
                    elevation={0}
                    sx={{
                      height: '100%',
                      minHeight: 220,
                      display: 'flex',
                      flexDirection: 'column',
                      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                      border: '1px solid',
                      borderColor: alpha(feature.color, 0.1),
                      bgcolor: 'background.paper',
                      borderRadius: 4,
                      overflow: 'visible',
                      '&:hover': {
                        boxShadow: `0 12px 40px ${alpha(feature.color, 0.15)}`,
                        borderColor: alpha(feature.color, 0.3),
                        transform: 'translateY(-8px)',
                      },
                    }}
                  >
                    <CardContent sx={{ 
                      p: 4, 
                      textAlign: 'left',
                      flex: 1, 
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 2
                    }}>
                      <Box
                        sx={{
                          width: 56,
                          height: 56,
                          borderRadius: 2,
                          bgcolor: alpha(feature.color, 0.1),
                          color: feature.color,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          mb: 1,
                          '& svg': {
                            fontSize: 28,
                            filter: 'none'
                          }
                        }}
                      >
                        {feature.icon}
                      </Box>
                      <Box>
                        <Typography variant="h6" component="h3" sx={{ mb: 1, fontWeight: 700, color: 'text.primary' }}>
                          {feature.title}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6, fontSize: '0.95rem' }}>
                          {feature.description}
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </motion.div>
              </Grid>
            ))}
          </Grid>
        </motion.div>

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 1.2 }}
        >
          <Box sx={{ textAlign: 'center', mt: 8, mb: 4 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Powered by advanced AI technology for biomedical research excellence
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Secure authentication powered by Auth0 • Enterprise-grade security
            </Typography>
            
            {/* Policy Links */}
            <Box sx={{ 
              display: 'flex', 
              justifyContent: 'center', 
              alignItems: 'center',
              gap: 2,
              flexWrap: 'wrap'
            }}>
              <Typography
                component="a"
                href="/terms"
                sx={{
                  color: 'text.secondary',
                  textDecoration: 'none',
                  fontSize: '0.875rem',
                  '&:hover': {
                    color: 'primary.main',
                    textDecoration: 'underline'
                  }
                }}
              >
                Terms of Service
              </Typography>
              <Typography variant="body2" color="text.disabled">•</Typography>
              <Typography
                component="a"
                href="/privacy"
                sx={{
                  color: 'text.secondary',
                  textDecoration: 'none',
                  fontSize: '0.875rem',
                  '&:hover': {
                    color: 'primary.main',
                    textDecoration: 'underline'
                  }
                }}
              >
                Privacy Policy
              </Typography>
              <Typography variant="body2" color="text.disabled">•</Typography>
              <Typography
                component="a"
                href="/cookies"
                sx={{
                  color: 'text.secondary',
                  textDecoration: 'none',
                  fontSize: '0.875rem',
                  '&:hover': {
                    color: 'primary.main',
                    textDecoration: 'underline'
                  }
                }}
              >
                Cookie Policy
              </Typography>
            </Box>
          </Box>
        </motion.div>
      </Container>
    </Box>
  );
};

export default WelcomePage;
