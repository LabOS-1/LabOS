'use client'

import React from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  Divider
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Gavel as LegalIcon
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';

const TermsPage: React.FC = () => {
  const router = useRouter();

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
              <LegalIcon sx={{ mr: 2, color: 'primary.main' }} />
              <Typography variant="h3" component="h1" sx={{ fontWeight: 600, color: 'text.primary' }}>
                Terms of Service
              </Typography>
            </Box>
            
            <Typography variant="body1" color="text.secondary">
              Last updated: {new Date().toLocaleDateString()}
            </Typography>
          </Box>

          {/* Content */}
          <Paper sx={{ p: 4 }}>
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              1. Acceptance of Terms
            </Typography>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7 }}>
              By accessing and using LabOS AI, you accept and agree to be bound by the terms 
              and provision of this agreement.
            </Typography>

            <Divider sx={{ my: 3 }} />

            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              2. Use License
            </Typography>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7 }}>
              Permission is granted to temporarily download one copy of LabOS AI per device 
              for personal, non-commercial transitory viewing only.
            </Typography>

            <Divider sx={{ my: 3 }} />

            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              3. Privacy and Data Protection
            </Typography>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7 }}>
              We are committed to protecting your privacy and research data. All data is 
              processed in accordance with our Privacy Policy and applicable data protection laws.
            </Typography>

            <Divider sx={{ my: 3 }} />

            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              4. Research Data Usage
            </Typography>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7 }}>
              Your research data remains your intellectual property. LabOS AI provides 
              analysis and insights but does not claim ownership of your data.
            </Typography>

            <Divider sx={{ my: 3 }} />

            <Typography variant="body2" color="text.secondary" sx={{ mt: 4 }}>
              For questions about these terms, please contact us at legal@labos-agent.com
            </Typography>
          </Paper>
        </motion.div>
      </Container>
    </Box>
  );
};

export default TermsPage;
