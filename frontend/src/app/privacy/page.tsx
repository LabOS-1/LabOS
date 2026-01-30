'use client'

import React from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  Divider,
  Alert
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Security as SecurityIcon,
  Warning as WarningIcon
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';

const PrivacyPage: React.FC = () => {
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
              <SecurityIcon sx={{ mr: 2, color: 'primary.main' }} />
              <Typography variant="h3" component="h1" sx={{ fontWeight: 600, color: 'text.primary' }}>
                Privacy Policy & Terms of Use
              </Typography>
            </Box>

            <Typography variant="body1" color="text.secondary">
              Last updated: January 14, 2026
            </Typography>
          </Box>

          {/* Critical Warning Banner */}
          <Alert
            severity="warning"
            icon={<WarningIcon />}
            sx={{ mb: 4, '& .MuiAlert-message': { width: '100%' } }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
              Important Notice - Please Read Carefully
            </Typography>
            <Typography variant="body2">
              LABOS is an AI-powered research assistant for informational purposes only. It is NOT a medical device,
              diagnostic tool, or clinical decision support system. Do not use LABOS outputs for medical diagnosis,
              treatment decisions, or any clinical purposes. Always consult qualified healthcare professionals for
              medical advice.
            </Typography>
          </Alert>

          {/* Content */}
          <Paper sx={{ p: 4 }}>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7, color: 'text.secondary' }}>
              LABOS ("we," "our," or "us") provides an AI-powered research assistance platform. This Privacy Policy
              and Terms of Use explains how we collect, use, and protect your information, as well as the limitations
              and appropriate use of our services.
            </Typography>

            <Divider sx={{ my: 4 }} />

            {/* AI Limitations and Disclaimer */}
            <Box sx={{ bgcolor: 'error.light', p: 3, borderRadius: 2, mb: 4, opacity: 0.9 }}>
              <Typography variant="h5" sx={{ mb: 2, fontWeight: 600, color: 'error.contrastText' }}>
                AI Limitations and Disclaimer
              </Typography>
              <Typography variant="body1" sx={{ mb: 2, lineHeight: 1.7, color: 'error.contrastText' }}>
                <strong>LABOS uses large language models (LLMs) that have inherent limitations:</strong>
              </Typography>
              <Box component="ul" sx={{ pl: 3, color: 'error.contrastText', mb: 2 }}>
                <Typography component="li" variant="body1" sx={{ mb: 1, lineHeight: 1.7 }}>
                  AI outputs may contain errors, inaccuracies, or "hallucinations" (plausible-sounding but incorrect information)
                </Typography>
                <Typography component="li" variant="body1" sx={{ mb: 1, lineHeight: 1.7 }}>
                  Generated content should always be independently verified before use
                </Typography>
                <Typography component="li" variant="body1" sx={{ mb: 1, lineHeight: 1.7 }}>
                  AI responses do not constitute professional advice of any kind
                </Typography>
                <Typography component="li" variant="body1" sx={{ mb: 1, lineHeight: 1.7 }}>
                  The system may produce outdated information or miss recent developments
                </Typography>
              </Box>
              <Typography variant="body1" sx={{ lineHeight: 1.7, color: 'error.contrastText', fontWeight: 600 }}>
                Users are solely responsible for verifying all AI-generated content and for any decisions made based on such content.
              </Typography>
            </Box>

            <Divider sx={{ my: 4 }} />

            {/* Not Medical/Clinical Advice */}
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              1. Not Medical or Clinical Advice
            </Typography>
            <Box sx={{ bgcolor: 'warning.light', p: 3, borderRadius: 2, mb: 3, opacity: 0.9 }}>
              <Typography variant="body1" sx={{ mb: 2, lineHeight: 1.7, color: 'warning.contrastText', fontWeight: 600 }}>
                LABOS IS NOT:
              </Typography>
              <Box component="ul" sx={{ pl: 3, color: 'warning.contrastText', mb: 2 }}>
                <Typography component="li" variant="body1" sx={{ mb: 1, lineHeight: 1.7 }}>
                  A medical device or diagnostic tool
                </Typography>
                <Typography component="li" variant="body1" sx={{ mb: 1, lineHeight: 1.7 }}>
                  A substitute for professional medical advice, diagnosis, or treatment
                </Typography>
                <Typography component="li" variant="body1" sx={{ mb: 1, lineHeight: 1.7 }}>
                  A clinical decision support system
                </Typography>
                <Typography component="li" variant="body1" sx={{ mb: 1, lineHeight: 1.7 }}>
                  Approved or cleared by any regulatory authority (FDA, EMA, etc.) for clinical use
                </Typography>
              </Box>
              <Typography variant="body1" sx={{ lineHeight: 1.7, color: 'warning.contrastText' }}>
                <strong>Do not use LABOS outputs to make medical, clinical, diagnostic, or treatment decisions.</strong> Always
                seek the advice of qualified healthcare professionals with any questions regarding medical conditions or treatments.
              </Typography>
            </Box>

            <Divider sx={{ my: 4 }} />

            {/* Research Use Only */}
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              2. Intended Use - Research Purposes Only
            </Typography>
            <Typography variant="body1" sx={{ mb: 3, lineHeight: 1.7, color: 'text.secondary' }}>
              LABOS is designed as a research assistance tool to help users explore scientific literature, analyze data,
              and generate hypotheses. Appropriate uses include:
            </Typography>
            <Box component="ul" sx={{ mb: 3, pl: 3, color: 'text.secondary' }}>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                Literature review and summarization for research purposes
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                Exploratory data analysis and visualization
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                Hypothesis generation and preliminary research ideation
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                Educational and learning purposes
              </Typography>
            </Box>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7, color: 'text.secondary', fontStyle: 'italic' }}>
              All outputs should be treated as preliminary and require validation through appropriate scientific methods
              and peer review before publication or practical application.
            </Typography>

            <Divider sx={{ my: 4 }} />

            {/* Protected Health Information Warning */}
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              3. Protected Health Information (PHI) and Sensitive Data
            </Typography>
            <Box sx={{ bgcolor: 'error.light', p: 3, borderRadius: 2, mb: 3, opacity: 0.9 }}>
              <Typography variant="body1" sx={{ mb: 2, lineHeight: 1.7, color: 'error.contrastText', fontWeight: 600 }}>
                DO NOT upload or input the following types of data:
              </Typography>
              <Box component="ul" sx={{ pl: 3, color: 'error.contrastText', mb: 2 }}>
                <Typography component="li" variant="body1" sx={{ mb: 1, lineHeight: 1.7 }}>
                  Protected Health Information (PHI) as defined under HIPAA
                </Typography>
                <Typography component="li" variant="body1" sx={{ mb: 1, lineHeight: 1.7 }}>
                  Personally identifiable patient data or medical records
                </Typography>
                <Typography component="li" variant="body1" sx={{ mb: 1, lineHeight: 1.7 }}>
                  Genetic data linked to identifiable individuals
                </Typography>
                <Typography component="li" variant="body1" sx={{ mb: 1, lineHeight: 1.7 }}>
                  Any data subject to HIPAA, GDPR special categories, or similar regulations without proper de-identification
                </Typography>
              </Box>
              <Typography variant="body1" sx={{ lineHeight: 1.7, color: 'error.contrastText' }}>
                <strong>LABOS is not HIPAA-compliant and should not be used to process protected health information.</strong> Users
                are solely responsible for ensuring compliance with applicable data protection regulations.
              </Typography>
            </Box>

            <Divider sx={{ my: 4 }} />

            {/* Information We Collect */}
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              4. Information We Collect
            </Typography>

            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: 'text.primary', fontSize: '1.1rem' }}>
              4.1 Account Information
            </Typography>
            <Typography variant="body1" sx={{ mb: 3, lineHeight: 1.7, color: 'text.secondary' }}>
              When you register for an account, we collect your name, email address, and authentication credentials.
              We use Auth0 for secure authentication services.
            </Typography>

            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: 'text.primary', fontSize: '1.1rem' }}>
              4.2 User-Provided Data
            </Typography>
            <Typography variant="body1" sx={{ mb: 3, lineHeight: 1.7, color: 'text.secondary' }}>
              We process data you upload or input, including documents, datasets, queries, and any files you provide
              to our AI assistant. You are responsible for ensuring you have the right to share this data with us.
            </Typography>

            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: 'text.primary', fontSize: '1.1rem' }}>
              4.3 Usage Information
            </Typography>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7, color: 'text.secondary' }}>
              We automatically collect information about your interactions with our services, including access times,
              features used, and system performance metrics for service improvement purposes.
            </Typography>

            <Divider sx={{ my: 4 }} />

            {/* How We Use Your Information */}
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              5. How We Use Your Information
            </Typography>
            <Typography variant="body1" sx={{ mb: 2, lineHeight: 1.7, color: 'text.secondary' }}>
              We use the collected information for the following purposes:
            </Typography>
            <Box component="ul" sx={{ mb: 4, pl: 3, color: 'text.secondary' }}>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                <strong>Service Provision:</strong> To provide, maintain, and improve our research assistance platform
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                <strong>Data Processing:</strong> To process your queries and generate responses using AI models
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                <strong>Communication:</strong> To send service-related notifications and respond to your inquiries
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                <strong>Security:</strong> To detect, prevent, and address technical issues and security threats
              </Typography>
            </Box>

            <Divider sx={{ my: 4 }} />

            {/* Data Storage and Security */}
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              6. Data Storage and Security
            </Typography>
            <Typography variant="body1" sx={{ mb: 3, lineHeight: 1.7, color: 'text.secondary' }}>
              We implement reasonable security measures to protect your information:
            </Typography>
            <Box component="ul" sx={{ mb: 3, pl: 3, color: 'text.secondary' }}>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                <strong>Encryption:</strong> Data is encrypted in transit using TLS/SSL protocols
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                <strong>Access Control:</strong> Access controls limit data access to authorized personnel
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                <strong>Infrastructure:</strong> Our services are hosted on cloud infrastructure providers
              </Typography>
            </Box>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7, color: 'text.secondary', fontStyle: 'italic' }}>
              While we strive to protect your data, no method of transmission or storage is 100% secure. We cannot
              guarantee absolute security of your information.
            </Typography>

            <Divider sx={{ my: 4 }} />

            {/* AI Model Training */}
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              7. AI Models and Third-Party Services
            </Typography>
            <Typography variant="body1" sx={{ mb: 3, lineHeight: 1.7, color: 'text.secondary' }}>
              LABOS uses third-party AI models and services to provide its functionality:
            </Typography>
            <Box component="ul" sx={{ mb: 3, pl: 3, color: 'text.secondary' }}>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                <strong>AI Model Providers:</strong> Your queries and data may be processed by third-party AI providers
                (such as Google, Anthropic, or OpenAI) subject to their respective terms and privacy policies
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                <strong>Auth0:</strong> For secure authentication and identity management
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                <strong>Cloud Infrastructure:</strong> For hosting and data storage services
              </Typography>
            </Box>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7, color: 'text.secondary' }}>
              We do not use your data to train our own AI models without explicit consent. However, third-party AI
              providers may have their own data usage policies which you should review.
            </Typography>

            <Divider sx={{ my: 4 }} />

            {/* Data Ownership */}
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              8. Data Ownership
            </Typography>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7, color: 'text.secondary' }}>
              You retain ownership of the data you upload to LABOS. By using our service, you grant us a limited
              license to process your data solely for the purpose of providing our services. We do not claim ownership
              of your research data or AI-generated outputs based on your inputs.
            </Typography>

            <Divider sx={{ my: 4 }} />

            {/* Data Retention */}
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              9. Data Retention
            </Typography>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7, color: 'text.secondary' }}>
              We retain your account information and data for as long as your account is active or as needed to provide
              our services. You may request deletion of your account and associated data at any time by contacting us.
              Upon deletion request, we will remove your data within 30 days, except where retention is required by law.
            </Typography>

            <Divider sx={{ my: 4 }} />

            {/* Your Rights */}
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              10. Your Rights
            </Typography>
            <Typography variant="body1" sx={{ mb: 2, lineHeight: 1.7, color: 'text.secondary' }}>
              Subject to applicable law, you may have the following rights:
            </Typography>
            <Box component="ul" sx={{ mb: 4, pl: 3, color: 'text.secondary' }}>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                <strong>Access:</strong> Request access to your personal information
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                <strong>Correction:</strong> Request correction of inaccurate information
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                <strong>Deletion:</strong> Request deletion of your account and data
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                <strong>Export:</strong> Request a copy of your data in a portable format
              </Typography>
            </Box>

            <Divider sx={{ my: 4 }} />

            {/* Limitation of Liability */}
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              11. Limitation of Liability
            </Typography>
            <Typography variant="body1" sx={{ mb: 3, lineHeight: 1.7, color: 'text.secondary' }}>
              TO THE MAXIMUM EXTENT PERMITTED BY LAW:
            </Typography>
            <Box component="ul" sx={{ mb: 3, pl: 3, color: 'text.secondary' }}>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                LABOS is provided "AS IS" without warranties of any kind, express or implied
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                We do not warrant that AI outputs will be accurate, complete, reliable, or error-free
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                We are not liable for any damages arising from your use of or reliance on AI-generated content
              </Typography>
              <Typography component="li" variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                You assume all risks associated with using AI-generated content for any purpose
              </Typography>
            </Box>

            <Divider sx={{ my: 4 }} />

            {/* Children's Privacy */}
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              12. Children's Privacy
            </Typography>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7, color: 'text.secondary' }}>
              Our services are not directed to individuals under the age of 18. We do not knowingly collect personal
              information from children. If you believe we have collected information from a child, please contact us immediately.
            </Typography>

            <Divider sx={{ my: 4 }} />

            {/* Changes */}
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              13. Changes to This Policy
            </Typography>
            <Typography variant="body1" sx={{ mb: 4, lineHeight: 1.7, color: 'text.secondary' }}>
              We may update this Privacy Policy and Terms of Use from time to time. We will notify you of material changes
              by posting the updated policy on this page. Your continued use of our services after such modifications
              constitutes your acceptance of the updated terms.
            </Typography>

            <Divider sx={{ my: 4 }} />

            {/* Contact */}
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
              14. Contact Us
            </Typography>
            <Typography variant="body1" sx={{ mb: 2, lineHeight: 1.7, color: 'text.secondary' }}>
              If you have any questions, concerns, or requests regarding this Privacy Policy or our practices,
              please contact us at:
            </Typography>
            <Box sx={{ mb: 4, p: 3, bgcolor: 'action.hover', borderRadius: 2 }}>
              <Typography variant="body1" sx={{ mb: 1, color: 'text.primary', fontWeight: 500 }}>
                LABOS Team
              </Typography>
              <Typography variant="body1" sx={{ mb: 1, color: 'text.secondary' }}>
                Email: <Typography component="a" href="mailto:labos.agent2026@gmail.com" sx={{ color: 'primary.main', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}>labos.agent2026@gmail.com</Typography>
              </Typography>
            </Box>

            {/* Final Acknowledgment */}
            <Box sx={{ bgcolor: 'grey.100', p: 3, borderRadius: 2, mt: 4 }}>
              <Typography variant="body2" sx={{ lineHeight: 1.7, color: 'text.secondary' }}>
                <strong>By using LABOS, you acknowledge that you have read and understood this Privacy Policy and Terms of Use,
                including the limitations of AI technology, the prohibition on clinical use, and your responsibility to verify
                all AI-generated content.</strong>
              </Typography>
            </Box>
          </Paper>
        </motion.div>
      </Container>
    </Box>
  );
};

export default PrivacyPage;
