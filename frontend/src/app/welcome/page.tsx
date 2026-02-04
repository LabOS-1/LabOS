'use client'

import React from 'react';
import { config } from '@/config';
import {
  Box,
  Typography,
  Button,
  Container,
  Stack,
} from '@mui/material';
import {
  Visibility as SeeIcon,
  Psychology as ReasonIcon,
  ElectricBolt as ActIcon,
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import Image from 'next/image';

// Design tokens from ai4labos.com
const ws = {
  bg: '#f7f9ff',
  surface: '#ffffff',
  text: '#1f2937',
  muted: '#6b7280',
  primary: '#4f46e5',
  accent: '#22d3ee',
  grad: 'linear-gradient(90deg, #8b5cf6, #22d3ee)',
  radius: '12px',
  shadow: '0 8px 28px rgba(16, 24, 40, 0.08)',
  footerBg: '#0b1220',
  maxW: 1160,
};

const features = [
  {
    title: 'See',
    description: 'Advanced computer vision and XR integration for real-time laboratory observation and spatial data capture.',
    icon: SeeIcon,
    color: '#8b5cf6',
  },
  {
    title: 'Reason',
    description: 'AI-powered analysis and reasoning over experimental data, protocols, and scientific literature.',
    icon: ReasonIcon,
    color: '#4f46e5',
  },
  {
    title: 'Act',
    description: 'Automated workflow execution, dynamic tool creation, and intelligent laboratory operations.',
    icon: ActIcon,
    color: '#22d3ee',
  },
];

const policyLinks = [
  { label: 'Terms of Service', href: '/terms' },
  { label: 'Privacy Policy', href: '/privacy' },
  { label: 'Cookie Policy', href: '/cookies' },
];

const WelcomePage: React.FC = () => {
  const handleLogin = () => {
    window.location.href = `${config.api.baseUrl}/api/v1/auth/login`;
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: ws.bg, display: 'flex', flexDirection: 'column' }}>
      {/* ── Glassmorphic Header ── */}
      <Box
        component="header"
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 100,
          backdropFilter: 'blur(12px)',
          bgcolor: 'rgba(255, 255, 255, 0.72)',
          borderBottom: '1px solid rgba(0, 0, 0, 0.06)',
        }}
      >
        <Container maxWidth={false} sx={{ maxWidth: ws.maxW }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: 64 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Image src="/logo.png" alt="LabOS" width={36} height={36} style={{ borderRadius: 8 }} />
              <Typography sx={{ fontWeight: 700, fontSize: '1.25rem', color: ws.text, letterSpacing: '-0.02em' }}>
                LabOS
              </Typography>
            </Box>
            <Stack direction="row" spacing={1.5}>
              <Button
                onClick={handleLogin}
                sx={{
                  color: ws.text,
                  fontWeight: 600,
                  textTransform: 'none',
                  fontSize: '0.9rem',
                  px: 2.5,
                  borderRadius: '8px',
                  '&:hover': { bgcolor: 'rgba(0,0,0,0.04)' },
                }}
              >
                Login
              </Button>
              <Button
                onClick={handleLogin}
                sx={{
                  background: ws.grad,
                  color: '#fff',
                  fontWeight: 600,
                  textTransform: 'none',
                  fontSize: '0.9rem',
                  px: 2.5,
                  borderRadius: '8px',
                  '&:hover': { opacity: 0.9 },
                }}
              >
                Register
              </Button>
            </Stack>
          </Box>
        </Container>
      </Box>

      {/* ── Hero Section with Video Background ── */}
      <Box
        sx={{
          position: 'relative',
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
        }}
      >
        {/* Video */}
        <Box
          component="video"
          autoPlay
          muted
          loop
          playsInline
          sx={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            zIndex: 0,
          }}
        >
          <source src="/demos/demo1.mp4" type="video/mp4" />
        </Box>

        {/* Dark overlay */}
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(180deg, rgba(15,23,42,0.65) 0%, rgba(15,23,42,0.85) 100%)',
            zIndex: 1,
          }}
        />

        {/* Hero content */}
        <Container
          maxWidth={false}
          sx={{ maxWidth: ws.maxW, position: 'relative', zIndex: 2, textAlign: 'center', py: 4 }}
        >
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
            <Typography
              component="h1"
              sx={{
                fontSize: { xs: '3rem', md: '4.5rem' },
                fontWeight: 800,
                color: '#c4b5fd',
                mb: 1,
                letterSpacing: '-0.03em',
                lineHeight: 1.1,
              }}
            >
              LabOS
            </Typography>
            <Typography
              component="p"
              sx={{
                fontSize: { xs: '1.5rem', md: '2.5rem' },
                fontWeight: 700,
                color: '#ffffff',
                mb: 3,
                letterSpacing: '-0.02em',
                lineHeight: 1.2,
              }}
            >
              The AI-XR Co-Scientist
            </Typography>
            <Typography
              sx={{
                fontSize: { xs: '1rem', md: '1.15rem' },
                color: 'rgba(255,255,255,0.8)',
                mb: 5,
                maxWidth: 620,
                mx: 'auto',
                lineHeight: 1.7,
              }}
            >
              Your self-evolving intelligent laboratory assistant.
              See, Reason, and Act with AI-powered insights for advanced biomedical research.
            </Typography>

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} justifyContent="center">
              <Button
                onClick={handleLogin}
                sx={{
                  background: ws.grad,
                  color: '#fff',
                  fontWeight: 600,
                  textTransform: 'none',
                  fontSize: '1.05rem',
                  px: 4,
                  py: 1.5,
                  borderRadius: '10px',
                  boxShadow: '0 4px 20px rgba(139, 92, 246, 0.3)',
                  '&:hover': {
                    boxShadow: '0 6px 28px rgba(139, 92, 246, 0.45)',
                    transform: 'translateY(-1px)',
                  },
                  transition: 'all 0.3s ease',
                }}
              >
                Get Started
              </Button>
              <Button
                onClick={() => document.getElementById('about')?.scrollIntoView({ behavior: 'smooth' })}
                sx={{
                  bgcolor: 'rgba(255,255,255,0.12)',
                  color: '#fff',
                  fontWeight: 600,
                  textTransform: 'none',
                  fontSize: '1.05rem',
                  px: 4,
                  py: 1.5,
                  borderRadius: '10px',
                  border: '1px solid rgba(255,255,255,0.2)',
                  backdropFilter: 'blur(4px)',
                  '&:hover': { bgcolor: 'rgba(255,255,255,0.18)', borderColor: 'rgba(255,255,255,0.35)' },
                  transition: 'all 0.3s ease',
                }}
              >
                Learn More
              </Button>
            </Stack>
          </motion.div>
        </Container>
      </Box>

      {/* ── About Section ── */}
      <Box id="about" sx={{ py: { xs: 8, md: 12 }, bgcolor: ws.bg }}>
        <Container maxWidth={false} sx={{ maxWidth: ws.maxW }}>
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <Typography
              component="h2"
              sx={{
                fontSize: { xs: '2rem', md: '2.5rem' },
                fontWeight: 800,
                textAlign: 'center',
                mb: 2,
                background: ws.grad,
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: '-0.02em',
              }}
            >
              About LabOS
            </Typography>
            <Typography
              sx={{
                fontSize: '1.1rem',
                color: ws.muted,
                textAlign: 'center',
                mb: 8,
                maxWidth: 700,
                mx: 'auto',
                lineHeight: 1.7,
              }}
            >
              An AI-XR co-scientist platform that sees, reasons, and acts to accelerate biomedical research.
            </Typography>
          </motion.div>

          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' }, gap: 3 }}>
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.15 }}
                >
                  <Box
                    sx={{
                      bgcolor: ws.surface,
                      borderRadius: ws.radius,
                      border: '1px solid #eef2ff',
                      boxShadow: ws.shadow,
                      p: 4,
                      height: '100%',
                      transition: 'all 0.3s ease',
                      '&:hover': {
                        transform: 'translateY(-4px)',
                        boxShadow: '0 12px 40px rgba(16, 24, 40, 0.12)',
                      },
                    }}
                  >
                    <Box
                      sx={{
                        width: 56,
                        height: 56,
                        borderRadius: '12px',
                        bgcolor: `${feature.color}14`,
                        color: feature.color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        mb: 2.5,
                      }}
                    >
                      <Icon sx={{ fontSize: 28 }} />
                    </Box>
                    <Typography sx={{ fontSize: '1.25rem', fontWeight: 700, color: ws.text, mb: 1.5 }}>
                      {feature.title}
                    </Typography>
                    <Typography sx={{ fontSize: '0.95rem', color: ws.muted, lineHeight: 1.7 }}>
                      {feature.description}
                    </Typography>
                  </Box>
                </motion.div>
              );
            })}
          </Box>
        </Container>
      </Box>

      {/* ── Footer ── */}
      <Box component="footer" sx={{ bgcolor: ws.footerBg, py: 5, mt: 'auto' }}>
        <Container maxWidth={false} sx={{ maxWidth: ws.maxW }}>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: 2,
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Image src="/logo.png" alt="LabOS" width={28} height={28} style={{ borderRadius: 6 }} />
              <Typography sx={{ color: 'rgba(255,255,255,0.7)', fontWeight: 600, fontSize: '0.95rem' }}>
                LabOS
              </Typography>
            </Box>

            <Stack direction="row" spacing={3}>
              {policyLinks.map((link) => (
                <Typography
                  key={link.label}
                  component="a"
                  href={link.href}
                  sx={{
                    color: 'rgba(255,255,255,0.5)',
                    textDecoration: 'none',
                    fontSize: '0.85rem',
                    '&:hover': { color: 'rgba(255,255,255,0.8)' },
                    transition: 'color 0.2s',
                  }}
                >
                  {link.label}
                </Typography>
              ))}
            </Stack>

            <Typography sx={{ color: 'rgba(255,255,255,0.35)', fontSize: '0.85rem' }}>
              2025 LabOS. All rights reserved.
            </Typography>
          </Box>
        </Container>
      </Box>
    </Box>
  );
};

export default WelcomePage;
