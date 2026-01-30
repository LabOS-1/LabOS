/**
 * HelpMenu Component
 *
 * Dropdown menu in the top-right corner providing access to:
 * - Restart onboarding tour
 * - View usage examples
 * - Access documentation
 */

'use client';

import { useState } from 'react';
import {
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Tooltip,
} from '@mui/material';
import {
  HelpOutline as HelpIcon,
  School as TourIcon,
  Lightbulb as ExamplesIcon,
  Description as DocsIcon,
  VideoLibrary as VideoIcon,
} from '@mui/icons-material';
import ExamplesDialog from './ExamplesDialog';

interface HelpMenuProps {
  /**
   * Callback when "Restart Tour" is clicked
   */
  onRestartTour?: () => void;

  /**
   * Callback when user selects an example
   */
  onSelectExample?: (prompt: string) => void;
}

export default function HelpMenu({
  onRestartTour,
  onSelectExample,
}: HelpMenuProps) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [showExamples, setShowExamples] = useState(false);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleRestartTour = () => {
    handleClose();

    // Clear localStorage and notify listeners
    localStorage.removeItem('labos_onboarding_completed');
    window.dispatchEvent(new Event('onboarding-status-changed'));

    // Use callback if provided
    if (onRestartTour) {
      onRestartTour();
      return;
    }

    // Try global restart function
    if (typeof window !== 'undefined' && (window as any).restartOnboardingTour) {
      (window as any).restartOnboardingTour();
      return;
    }

    // If on dashboard, the hook will detect the change and show welcome card
    // If on other pages, reload to return to a state where tour can start
    const isDashboard = window.location.pathname === '/dashboard';
    if (!isDashboard) {
      window.location.href = '/dashboard';
    }
  };

  const handleShowExamples = () => {
    handleClose();
    setShowExamples(true);
  };

  // TODO: Add documentation and video links when available
  // const handleOpenDocs = () => {
  //   handleClose();
  //   window.open('https://github.com/your-org/labos-docs', '_blank');
  // };

  // const handleOpenVideos = () => {
  //   handleClose();
  //   window.open('https://youtube.com/labos-tutorials', '_blank');
  // };

  return (
    <>
      <Tooltip title="Help & Resources">
        <IconButton
          onClick={handleClick}
          size="medium"
          sx={{
            ml: 1,
            bgcolor: open ? 'action.selected' : 'transparent',
          }}
          aria-label="help menu"
          aria-controls={open ? 'help-menu' : undefined}
          aria-haspopup="true"
          aria-expanded={open ? 'true' : undefined}
        >
          <HelpIcon />
        </IconButton>
      </Tooltip>

      <Menu
        id="help-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        onClick={handleClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        PaperProps={{
          elevation: 3,
          sx: {
            minWidth: 220,
            mt: 1,
          },
        }}
      >
        <MenuItem onClick={handleRestartTour}>
          <ListItemIcon>
            <TourIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Restart Feature Tour</ListItemText>
        </MenuItem>

        <MenuItem onClick={handleShowExamples}>
          <ListItemIcon>
            <ExamplesIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>View Usage Examples</ListItemText>
        </MenuItem>

        {/* TODO: Add documentation and video tutorials links when available */}
        {/* <Divider />

        <MenuItem onClick={handleOpenDocs}>
          <ListItemIcon>
            <DocsIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Documentation</ListItemText>
        </MenuItem>

        <MenuItem onClick={handleOpenVideos}>
          <ListItemIcon>
            <VideoIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Video Tutorials</ListItemText>
        </MenuItem> */}
      </Menu>

      <ExamplesDialog
        open={showExamples}
        onClose={() => setShowExamples(false)}
        onSelectExample={onSelectExample}
      />
    </>
  );
}
