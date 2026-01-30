'use client'

import React, { useState, useEffect } from 'react';
import {
  Drawer,
  IconButton,
  Typography,
  Box,
  Badge,
  Avatar,
  Menu,
  MenuItem,
  Tooltip,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Notifications as BellIcon,
  Person as UserIcon,
  Logout as LogoutIcon,
  ChevronLeft as ChevronLeftIcon
} from '@mui/icons-material';
import { useRouter, usePathname } from 'next/navigation';
import { motion } from 'framer-motion';

import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { updateTheme, updateLayout } from '@/store/slices/uiSlice';
import { logout } from '@/store/slices/authSlice';
import NotificationPanel from '@/components/Common/NotificationPanel';
import SidebarContent from './SidebarContent';
import { useHealthCheck } from '@/hooks/useHealthCheck';
import HelpMenu from '@/components/Onboarding/HelpMenu';
import { MultiPageTour, WelcomeCard, useOnboardingStatus } from '@/components/Onboarding';

interface LayoutProps {
  children: React.ReactNode;
}

const DRAWER_WIDTH = 200;
const DRAWER_COLLAPSED_WIDTH = 64;

const AppLayout: React.FC<LayoutProps> = React.memo(({ children }) => {
  const router = useRouter();
  const pathname = usePathname();
  const muiTheme = useTheme();
  const [notificationVisible, setNotificationVisible] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  // Mobile detection and overlay state
  const isMobile = useMediaQuery(muiTheme.breakpoints.down('md'));
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  // Health check hook
  useHealthCheck();

  const dispatch = useAppDispatch();
  const { isAuthenticated, isLoading } = useAppSelector((state) => state.auth);
  const layout = useAppSelector((state) => state.ui.layout);
  const theme = useAppSelector((state) => state.ui.theme);
  const connected = useAppSelector((state) => state.system.connected);
  const notifications = useAppSelector((state) => state.ui.notifications);
  const systemStatus = useAppSelector((state) => state.system.systemStatus);

  // Onboarding state management (global across all pages)
  const { isCompleted } = useOnboardingStatus();
  const [showWelcome, setShowWelcome] = useState(false);
  const [startTour, setStartTour] = useState(false);

  // Check onboarding status and only show on dashboard
  useEffect(() => {
    const isDashboard = pathname === '/dashboard';
    const tourInProgress = localStorage.getItem('labos_tour_current_step');

    // Only show WelcomeCard if:
    // 1. We're on dashboard
    // 2. Onboarding is not completed
    // 3. Tour is NOT currently running
    if (isDashboard && !isCompleted && !tourInProgress) {
      setShowWelcome(true);
    } else {
      setShowWelcome(false);
    }
  }, [isCompleted, pathname]);

  const handleStartTour = () => {
    setShowWelcome(false);
    setStartTour(true);
  };

  const handleSkipTour = () => {
    setShowWelcome(false);
    localStorage.setItem('labos_onboarding_completed', 'true');
  };

  const handleRestartTour = () => {
    // Reset tour state
    setStartTour(false);
    setShowWelcome(false);

    // Clear onboarding completion status
    localStorage.removeItem('labos_onboarding_completed');
    localStorage.removeItem('labos_tour_current_step');

    // Navigate to dashboard if not already there
    const isDashboard = pathname === '/dashboard';
    if (!isDashboard) {
      router.push('/dashboard');
    }

    // Small delay to ensure state is cleared, then show welcome card
    setTimeout(() => {
      setShowWelcome(true);
    }, 100);
  };

  const toggleSidebar = () => {
    if (isMobile) {
      setMobileDrawerOpen(!mobileDrawerOpen);
    } else {
      dispatch(updateLayout({ sidebarCollapsed: !layout.sidebarCollapsed }));
    }
  };

  const handleMobileDrawerClose = () => {
    setMobileDrawerOpen(false);
  };

  const handleUserMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    dispatch(logout());
    setAnchorEl(null);
    router.push('/');
  };

  // Show loading state while auth is being checked
  if (isLoading) {
    return (
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        background: muiTheme.palette.background.default
      }}>
        <Typography variant="h6" color="text.secondary">
          Loading...
        </Typography>
      </Box>
    );
  }

  return (
    <>
      {/* Global Onboarding Components */}
      <WelcomeCard
        open={showWelcome}
        onStartTour={handleStartTour}
        onSkip={handleSkipTour}
      />

      <MultiPageTour
        autoStart={startTour}
        onComplete={() => setStartTour(false)}
      />

      <Box sx={{ display: 'flex', height: '100vh' }}>
        {/* Desktop Drawer */}
      {!isMobile && (
        <Drawer
          variant="permanent"
          anchor="left"
          sx={{
            width: layout.sidebarCollapsed ? DRAWER_COLLAPSED_WIDTH : DRAWER_WIDTH,
            flexShrink: 0,
            transition: 'width 0.3s ease',
            '& .MuiDrawer-paper': {
              width: layout.sidebarCollapsed ? DRAWER_COLLAPSED_WIDTH : DRAWER_WIDTH,
              boxSizing: 'border-box',
              borderRight: `1px solid ${muiTheme.palette.divider}`,
              background: muiTheme.palette.background.paper,
              backdropFilter: 'blur(10px)',
              transition: 'width 0.3s ease',
              overflowX: 'visible', // Allow floating button to overflow
              overflowY: 'visible', // Allow floating button to overflow
              position: 'relative'
            },
          }}
        >
          <SidebarContent 
            isCollapsed={layout.sidebarCollapsed} 
            isMobile={false}
            onToggleCollapse={toggleSidebar}
          />
        </Drawer>
      )}
      
      {/* Mobile Drawer with Overlay */}
      {isMobile && (
        <Drawer
          variant="temporary"
          anchor="left"
          open={mobileDrawerOpen}
          onClose={handleMobileDrawerClose}
          ModalProps={{
            keepMounted: true,
            BackdropProps: {
              sx: {
                backgroundColor: 'rgba(0, 0, 0, 0.6)',
                backdropFilter: 'blur(4px)',
              }
            }
          }}
          sx={{
            '& .MuiDrawer-paper': {
              width: DRAWER_WIDTH,
              boxSizing: 'border-box',
              borderRight: `1px solid ${muiTheme.palette.divider}`,
              background: muiTheme.palette.background.paper,
              backdropFilter: 'blur(10px)',
              boxShadow: `0 8px 32px rgba(0, 0, 0, 0.3)`,
            },
          }}
        >
          <SidebarContent 
            isCollapsed={false} // Always expanded on mobile
            isMobile={true}
            onNavigate={handleMobileDrawerClose}
          />
        </Drawer>
      )}

      {/* Main Content Area */}
      <Box sx={{ 
        flexGrow: 1, 
        display: 'flex',
        width: isMobile ? '100%' : 'auto',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Header - Fixed position to prevent content from affecting it */}
        <Box sx={{
          height: 75,
          minHeight: 75, // Force fixed height
          maxHeight: 75, // Prevent expansion
          borderBottom: `1px solid ${muiTheme.palette.divider}`,
          background: muiTheme.palette.background.paper,
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          px: 3, // Match page content padding
          flexShrink: 0, // Prevent header from shrinking
          position: 'relative',
          zIndex: 10 // Ensure header stays on top
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              {/* Mobile menu button */}
              {isMobile && (
                <IconButton
                  onClick={toggleSidebar}
                  edge="start"
                  sx={{ 
                    color: muiTheme.palette.text.primary,
                    ml: 1
                  }}
                  aria-label="toggle sidebar"
                >
                  <MenuIcon />
                </IconButton>
              )}
              
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Typography 
                  variant="h6" 
                  sx={{ 
                    fontWeight: 600,
                    color: muiTheme.palette.text.primary,
                    lineHeight: 1,
                    display: 'flex',
                    alignItems: 'center'
                  }}
                >
                  {pathname === '/' ? 'Welcome' : 
                   pathname === '/dashboard' ? 'Dashboard' :
                   pathname.startsWith('/chat') ? 'Chat' :
                   pathname === '/tools' ? 'Tools' :
                   pathname === '/files' ? 'Files' :
                   pathname === '/memory' ? 'Memory' :
                   pathname === '/settings' ? 'Settings' :
                   pathname === '/verify-email' ? 'Verify Email' :
                   'LabOS AI'}
                </Typography>
              </motion.div>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {/* Help Menu */}
              <HelpMenu onRestartTour={handleRestartTour} />

              {/* Notifications */}
              <Tooltip title="Notifications" arrow>
                <IconButton
                  onClick={() => setNotificationVisible(!notificationVisible)}
                  sx={{ color: muiTheme.palette.text.primary }}
                >
                  <Badge badgeContent={notifications.length} color="error">
                    <BellIcon />
                  </Badge>
                </IconButton>
              </Tooltip>

              {/* User Menu */}
              {isAuthenticated && (
                <Tooltip title="User menu" arrow>
                  <IconButton
                    onClick={handleUserMenuClick}
                    sx={{ color: muiTheme.palette.text.primary }}
                  >
                    <UserIcon />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
          </Box>
        </Box>

        {/* Page Content */}
        <Box sx={{ 
          flexGrow: 1, 
          overflow: 'auto',
          position: 'relative'
        }}>
          {children}
        </Box>

        {/* Notification Panel */}
        <NotificationPanel 
          visible={notificationVisible}
          onClose={() => setNotificationVisible(false)}
        />

        {/* User Menu */}
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleUserMenuClose}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        >
          <MenuItem onClick={() => { router.push('/profile'); handleUserMenuClose(); }}>
            <UserIcon sx={{ mr: 1 }} />
            Profile
          </MenuItem>
          <MenuItem onClick={handleLogout}>
            <LogoutIcon sx={{ mr: 1 }} />
            Logout
          </MenuItem>
        </Menu>
      </Box>
    </Box>
    </>
  );
});

AppLayout.displayName = 'AppLayout';

export default AppLayout;
