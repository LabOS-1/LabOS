'use client';

import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Dialog,
  DialogContent,
  DialogActions,
  Button,
  IconButton,
  CircularProgress,
  useTheme,
} from '@mui/material';
import {
  PlayCircleOutline as PlayIcon,
  Close as CloseIcon,
  Science as AnalyzeIcon,
} from '@mui/icons-material';

export interface VideoExample {
  id: string;
  title: string;
  description: string;
  videoUrl: string;
  thumbnailUrl: string;
  prompt?: string; // Optional prompt to send with the video
}

interface VideoExampleCardProps {
  example: VideoExample;
  onAnalyze: (example: VideoExample) => void;
  disabled?: boolean;
}

export default function VideoExampleCard({
  example,
  onAnalyze,
  disabled = false,
}: VideoExampleCardProps) {
  const theme = useTheme();
  const [previewOpen, setPreviewOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleCardClick = () => {
    if (!disabled) {
      setPreviewOpen(true);
    }
  };

  const handleAnalyze = async () => {
    setIsLoading(true);
    try {
      await onAnalyze(example);
      setPreviewOpen(false);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Video Card */}
      <Paper
        elevation={0}
        sx={{
          p: 0,
          flex: 1,
          cursor: disabled ? 'not-allowed' : 'pointer',
          border: `1px solid ${theme.palette.divider}`,
          borderRadius: 2,
          overflow: 'hidden',
          transition: 'all 0.2s',
          opacity: disabled ? 0.6 : 1,
          '&:hover': disabled
            ? {}
            : {
                borderColor: theme.palette.primary.main,
                transform: 'translateY(-2px)',
                boxShadow: theme.shadows[4],
              },
        }}
        onClick={handleCardClick}
      >
        {/* Thumbnail with play overlay */}
        <Box
          sx={{
            position: 'relative',
            width: '100%',
            paddingTop: '56.25%', // 16:9 aspect ratio
            bgcolor: 'grey.900',
          }}
        >
          <Box
            component="img"
            src={example.thumbnailUrl}
            alt={example.title}
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
          {/* Play button overlay */}
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              bgcolor: 'rgba(0,0,0,0.3)',
              transition: 'background-color 0.2s',
              '&:hover': {
                bgcolor: 'rgba(0,0,0,0.5)',
              },
            }}
          >
            <PlayIcon sx={{ fontSize: 64, color: 'white', opacity: 0.9 }} />
          </Box>
        </Box>

        {/* Card content */}
        <Box sx={{ p: 2 }}>
          <Typography
            variant="subtitle2"
            sx={{
              fontWeight: 'bold',
              mb: 0.5,
              color: theme.palette.text.primary,
            }}
          >
            {example.title}
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: theme.palette.text.secondary,
              fontSize: '0.85rem',
              lineHeight: 1.5,
            }}
          >
            {example.description}
          </Typography>
        </Box>
      </Paper>

      {/* Video Preview Dialog */}
      <Dialog
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 2,
            overflow: 'hidden',
          },
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            p: 2,
            borderBottom: `1px solid ${theme.palette.divider}`,
          }}
        >
          <Typography variant="h6">{example.title}</Typography>
          <IconButton onClick={() => setPreviewOpen(false)} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        <DialogContent sx={{ p: 0, bgcolor: 'black' }}>
          <video
            src={example.videoUrl}
            controls
            autoPlay
            style={{
              width: '100%',
              maxHeight: '60vh',
              display: 'block',
            }}
          />
        </DialogContent>

        <DialogActions sx={{ p: 2, justifyContent: 'space-between' }}>
          <Typography variant="body2" color="text.secondary">
            {example.description}
          </Typography>
          <Button
            variant="contained"
            startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <AnalyzeIcon />}
            onClick={handleAnalyze}
            disabled={isLoading}
            sx={{ minWidth: 160 }}
          >
            {isLoading ? 'Sending...' : 'Analyze Video'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
