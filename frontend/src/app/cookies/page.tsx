'use client'

import React from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Cookie as CookieIcon
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';

const CookiesPage: React.FC = () => {
  const router = useRouter();

  const cookieTypes = [
    {
      name: 'Authentication Cookies',
      purpose: 'Keep you logged in',
      duration: '24 hours',
      type: 'Essential'
    },
    {
      name: 'Preference Cookies',
      purpose: 'Remember your settings',
      duration: '30 days',
      type: 'Functional'
    },
    {
      name: 'Analytics Cookies',
      purpose: 'Improve our service',
      duration: '2 years',
      type: 'Performance'
    }
  ];

  return (
    <Box
      sx={{
        minHeight: '100vh',
        bgcolor: 'background.default',
        py: 4
      }}
    >
      <Container maxWidth="md">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <Box sx={{ mb: 4 }}>
            <Button
              startIcon={<ArrowBackIcon />}
              onClick={() => router.back()}
              sx={{ mb: 2 }}
            >
              Back
            </Button>
            
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <CookieIcon sx={{ mr: 2, color: 'primary.main' }} />
              <Typography variant="h3" component="h1" sx={{ fontWeight: 600, color: 'text.primary' }}>
                Cookie Policy
              </Typography>
            </Box>
            
            <Typography variant="body1" color="text.secondary">
              Last updated: {new Date().toLocaleDateString()}
            </Typography>
          </Box>

          {/* Content */}
          <Paper sx={{ p: 4 }}>
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              What Are Cookies?
            </Typography>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7 }}>
              Cookies are small text files that are placed on your computer or mobile device 
              when you visit our website. They help us provide you with a better experience.
            </Typography>

            <Divider sx={{ my: 3 }} />

            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              Cookies We Use
            </Typography>
            
            <TableContainer component={Paper} variant="outlined" sx={{ mb: 4 }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell><strong>Cookie Type</strong></TableCell>
                    <TableCell><strong>Purpose</strong></TableCell>
                    <TableCell><strong>Duration</strong></TableCell>
                    <TableCell><strong>Category</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {cookieTypes.map((cookie) => (
                    <TableRow key={cookie.name}>
                      <TableCell>{cookie.name}</TableCell>
                      <TableCell>{cookie.purpose}</TableCell>
                      <TableCell>{cookie.duration}</TableCell>
                      <TableCell>{cookie.type}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            <Divider sx={{ my: 3 }} />

            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              Managing Cookies
            </Typography>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7 }}>
              You can control and/or delete cookies as you wish. You can delete all cookies 
              that are already on your computer and you can set most browsers to prevent them 
              from being placed.
            </Typography>

            <Typography variant="body2" color="text.secondary" sx={{ mt: 4 }}>
              For questions about our cookie usage, please contact us at privacy@labos-agent.com
            </Typography>
          </Paper>
        </motion.div>
      </Container>
    </Box>
  );
};

export default CookiesPage;
