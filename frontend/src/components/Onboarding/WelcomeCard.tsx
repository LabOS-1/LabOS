/**
 * WelcomeCard Component
 *
 * Optional welcome card shown before starting the onboarding tour.
 * Gives users a choice to start the tour or skip it.
 */

'use client';

import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Chip,
} from '@mui/material';
import {
  Rocket as RocketIcon,
  Close as CloseIcon,
} from '@mui/icons-material';

interface WelcomeCardProps {
  /**
   * Whether the dialog is open
   */
  open: boolean;

  /**
   * Callback when user clicks "Start Tour"
   */
  onStartTour: () => void;

  /**
   * Callback when user clicks "Skip" or closes dialog
   */
  onSkip: () => void;
}

export default function WelcomeCard({
  open,
  onStartTour,
  onSkip,
}: WelcomeCardProps) {
  return (
    <Dialog
      open={open}
      onClose={onSkip}
      maxWidth="sm"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            borderRadius: 2,
            bgcolor: 'background.paper',
            border: 1,
            borderColor: 'divider',
          },
        },
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={1}>
            <RocketIcon sx={{ fontSize: 32, color: 'primary.main' }} />
            <Typography variant="h5" component="span" fontWeight="bold">
              Welcome to LABOS
            </Typography>
          </Box>
          <Button
            onClick={onSkip}
            sx={{ color: 'text.secondary', minWidth: 'auto', p: 0.5 }}
          >
            <CloseIcon />
          </Button>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Typography variant="body1" sx={{ mb: 2, color: 'text.primary' }}>
          Your intelligent biomedical research assistant powered by multi-agent
          AI collaboration.
        </Typography>

        <Box sx={{ mb: 2 }}>
          <Typography
            variant="subtitle2"
            fontWeight="bold"
            sx={{ mb: 1, color: 'text.primary' }}
          >
            What makes LABOS special:
          </Typography>
          <Box display="flex" flexDirection="column" gap={1}>
            <Chip
              label="🤖 Multi-Agent System (Manager + Dev + Tool Creator + Critic)"
              sx={{
                bgcolor: 'action.selected',
                justifyContent: 'flex-start',
              }}
            />
            <Chip
              label="🛠️ 110+ Research Tools + Create Your Own"
              sx={{
                bgcolor: 'action.selected',
                justifyContent: 'flex-start',
              }}
            />
            <Chip
              label="📷 Analyze Images, Videos, and PDFs"
              sx={{
                bgcolor: 'action.selected',
                justifyContent: 'flex-start',
              }}
            />
            <Chip
              label="🔍 Transparent AI Workflow Visualization"
              sx={{
                bgcolor: 'action.selected',
                justifyContent: 'flex-start',
              }}
            />
          </Box>
        </Box>

        <Box sx={{ mb: 2, p: 1.5, bgcolor: 'action.hover', borderRadius: 1 }}>
          <Typography variant="body2" sx={{ mb: 1, fontWeight: 'bold', color: 'text.primary' }}>
            Your AI Team:
          </Typography>
          <Typography variant="body2" sx={{ fontSize: '0.85rem', color: 'text.secondary', lineHeight: 1.6 }}>
            <strong>Manager:</strong> Coordinates tasks and delegates to specialists<br/>
            <strong>Dev Agent:</strong> Executes research, visualization, and data analysis<br/>
            <strong>Tool Creator:</strong> Builds custom tools for your unique workflows<br/>
            <strong>Critic:</strong> Evaluates quality and suggests improvements
          </Typography>
        </Box>

        <Typography variant="body2" sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
          Take a quick 3-minute tour to discover all features, or skip and
          explore on your own.
        </Typography>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
        <Button
          onClick={onSkip}
          variant="outlined"
          color="inherit"
        >
          Skip for Now
        </Button>
        <Button
          onClick={onStartTour}
          variant="contained"
          color="primary"
          startIcon={<RocketIcon />}
        >
          Start Tour
        </Button>
      </DialogActions>
    </Dialog>
  );
}
