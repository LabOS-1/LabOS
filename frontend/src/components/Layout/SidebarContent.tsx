'use client'

import React, { useState } from 'react';
import {
  List,
  ListItem,
  ListItemButton,
  Typography,
  Box,
  useTheme,
  IconButton
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Chat as MessageIcon,
  Build as ToolIcon,
  Folder as FileIcon,
  Storage as DatabaseIcon,
  Settings as SettingsIcon,
  Wifi as WifiIcon,
  WifiOff as DisconnectIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
} from '@mui/icons-material';
import { useRouter, usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import { useAppSelector } from '@/store/hooks';

interface SidebarContentProps {
  isCollapsed?: boolean;
  isMobile?: boolean;
  onNavigate?: () => void; // Callback for mobile drawer close
  onToggleCollapse?: () => void; // Callback for sidebar collapse/expand
}

const SidebarContent: React.FC<SidebarContentProps> = ({ 
  isCollapsed = false, 
  isMobile = false,
  onNavigate,
  onToggleCollapse
}) => {
  const router = useRouter();
  const pathname = usePathname();
  const muiTheme = useTheme();
  const [isHovered, setIsHovered] = useState(false);
  
  const connected = useAppSelector((state) => state.system.connected);
  const systemStatus = useAppSelector((state) => state.system.systemStatus);

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardIcon />,
      label: 'Dashboard',
    },
    {
      key: '/chat',
      icon: <MessageIcon />,
      label: 'Chat',
    },
    {
      key: '/tools',
      icon: <ToolIcon />,
      label: 'Tools',
    },
    {
      key: '/files',
      icon: <FileIcon />,
      label: 'Files',
    },
    {
      key: '/memory',
      icon: <DatabaseIcon />,
      label: 'Memory',
    },
    {
      key: '/settings',
      icon: <SettingsIcon />,
      label: 'Settings',
    },
  ];

  const handleMenuClick = (key: string) => {
    router.push(key);
    if (isMobile && onNavigate) {
      onNavigate(); // Close mobile drawer
    }
  };

  return (
    <Box 
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      sx={{ height: '100%', position: 'relative' }}
    >
      {/* Logo */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          height: 75,
          borderBottom: `1px solid ${muiTheme.palette.divider}`,
          px: 2,
          position: 'relative',
          cursor: isCollapsed && !isMobile ? 'pointer' : 'default',
          '&:hover': isCollapsed && !isMobile ? {
            backgroundColor: muiTheme.palette.action.hover + '50',
          } : {},
          transition: 'background-color 0.3s ease'
        }}
        onClick={isCollapsed && !isMobile && onToggleCollapse ? onToggleCollapse : undefined}
      >
          {/* Fixed Icon Column */}
          <Box sx={{
            position: 'absolute',
            left: isCollapsed ? 32 : 45,
            transform: 'translateX(-50%)',
            display: 'flex',
            alignItems: 'center',
            transition: 'left 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
          }}>
            <Box
              component="img"
              src="/logo.png"
              alt="LabOS AI Logo"
              sx={{
                width: isCollapsed ? 48 : 65,
                height: isCollapsed ? 48 : 65,
                borderRadius: 2,
                objectFit: 'contain',
                display: 'block',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
              }}
              onError={(e: React.SyntheticEvent<HTMLImageElement, Event>) => {
                // Fallback if image fails
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
            {/* Fallback text logo if image is hidden/failed or just as placeholder logic */}
            <Box
              sx={{
                width: 50,
                height: 50,
                borderRadius: 1,
                background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                display: 'none', // Logic to show this if img fails needs state, keeping simple for now
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <Typography variant="h6" sx={{ color: 'white', fontWeight: 'bold' }}>
                S
              </Typography>
            </Box>
          </Box>

          {/* Text Content */}
          <Box sx={{
            ml: 9, // Increased margin to give more space
            opacity: (isCollapsed && !isMobile) ? 0 : 1,
            transform: (isCollapsed && !isMobile) ? 'translateX(-20px)' : 'translateX(0)',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            overflow: 'hidden',
            whiteSpace: 'nowrap'
          }}>
            <Typography variant="h6" sx={{ 
              fontWeight: 'bold', 
              background: 'linear-gradient(135deg, #3b82f6, #a855f7)', 
              WebkitBackgroundClip: 'text', 
              WebkitTextFillColor: 'transparent' 
            }}>
              LabOS AI
            </Typography>
          </Box>
      </Box>

      {/* Floating Toggle Button */}
      {!isMobile && onToggleCollapse && (
        <Box
          onClick={onToggleCollapse}
          sx={{
            position: 'absolute',
            top: '50%', // Center vertically
            right: -12, // Hang off the edge slightly
            transform: 'translateY(-50%)',
            zIndex: 1200,
            opacity: isHovered || isCollapsed ? 1 : 0,
            transition: 'opacity 0.2s ease, transform 0.2s ease',
            cursor: 'pointer',
          }}
        >
          <Box
            sx={{
              bgcolor: 'background.paper',
              border: `1px solid ${muiTheme.palette.divider}`,
              borderRadius: '50%',
              width: 24,
              height: 24,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              '&:hover': {
                bgcolor: muiTheme.palette.action.hover,
                transform: 'scale(1.1)'
              }
            }}
          >
            {isCollapsed ? (
              <ChevronRightIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
            ) : (
              <ChevronLeftIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
            )}
          </Box>
        </Box>
      )}

      {/* Navigation Menu */}
      <List sx={{ px: 1, py: 2 }}>
        {menuItems.map((item) => (
          <ListItem
            key={item.key}
            disablePadding
            sx={{ mb: 0.5 }}
          >
            <Box
              data-tour-id={item.key.replace('/', '')}
              sx={{ width: '100%' }}
            >
              <ListItemButton
                selected={pathname === item.key || pathname?.startsWith(`${item.key}/`)}
                onClick={() => handleMenuClick(item.key)}
                sx={{
                  borderRadius: 2,
                  position: 'relative',
                  px: 2,
                  py: 1.5,
                  mb: 0.5,
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    backgroundColor: muiTheme.palette.action.hover,
                    transform: 'translateX(4px)',
                  },
                  '&.Mui-selected': {
                    backgroundColor: muiTheme.palette.primary.main + '15',
                    '&:hover': {
                      backgroundColor: muiTheme.palette.primary.main + '25',
                    },
                  },
                }}
              >
              {/* Fixed Icon Column */}
              <Box sx={{ 
                position: 'absolute',
                left: 24,
                transform: 'translateX(-50%)',
                display: 'flex', 
                alignItems: 'center'
              }}>
                <Box sx={{ 
                  color: pathname === item.key ? muiTheme.palette.primary.main : muiTheme.palette.text.secondary,
                  transition: 'color 0.3s ease',
                  display: 'flex',
                  alignItems: 'center'
                }}>
                  {item.icon}
                </Box>
              </Box>
              
              {/* Text Content */}
              <Box sx={{ 
                ml: 6, // 64px from left to align with logo text
                opacity: (isCollapsed && !isMobile) ? 0 : 1,
                transform: (isCollapsed && !isMobile) ? 'translateX(-20px)' : 'translateX(0)',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                overflow: 'hidden',
                whiteSpace: 'nowrap'
              }}>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    fontWeight: pathname === item.key ? 600 : 400,
                    color: pathname === item.key ? muiTheme.palette.primary.main : muiTheme.palette.text.primary,
                    transition: 'color 0.3s ease'
                  }}
                >
                  {item.label}
                </Typography>
              </Box>
            </ListItemButton>
            </Box>
          </ListItem>
        ))}
      </List>

      {/* Status and Actions */}
      <Box sx={{ position: 'absolute', bottom: 12, left: 0, right: 16 }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.4 }}
        >
          {/* Connection Status - Not wrapped in button */}
          <Box sx={{ 
            px: 2, 
            py: 1.5,
            mx: 1,
            mb: 2,
            borderRadius: 1,
            backgroundColor: muiTheme.palette.action.hover + '30',
            position: 'relative'
          }}>
            {/* Fixed Icon Column */}
            <Box sx={{
              position: 'absolute',
              left: 24,
              top: '50%',
              transform: 'translate(-50%, -50%)',
              display: 'flex',
              alignItems: 'center'
            }}>
              {connected === null ? (
                <WifiIcon sx={{ fontSize: 20, color: 'text.disabled', transition: 'color 0.3s ease' }} />
              ) : connected ? (
                <WifiIcon sx={{ fontSize: 20, color: 'success.main', transition: 'color 0.3s ease' }} />
              ) : (
                <DisconnectIcon sx={{ fontSize: 20, color: 'error.main', transition: 'color 0.3s ease' }} />
              )}
            </Box>

            {/* Text Content */}
            <Box sx={{
              ml: 6, // Match menu items text position
              opacity: (isCollapsed && !isMobile) ? 0 : 1,
              transform: (isCollapsed && !isMobile) ? 'translateX(-20px)' : 'translateX(0)',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              overflow: 'hidden',
              whiteSpace: 'nowrap',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              height: '100%'
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography
                  variant="caption"
                  sx={{ color: connected === null ? 'text.disabled' : connected ? 'success.main' : 'error.main' }}
                >
                  {connected === null ? 'Checking...' : connected ? 'Online' : 'Offline'}
                </Typography>
              </Box>
              {systemStatus && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mt: 0.5 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption">CPU</Typography>
                    <Typography variant="caption">
                      {systemStatus.resources?.cpu_usage ? `${systemStatus.resources.cpu_usage.toFixed(1)}%` : 'N/A'}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption">Memory</Typography>
                    <Typography variant="caption">
                      {systemStatus.resources?.memory_usage ? `${systemStatus.resources.memory_usage.toFixed(1)}%` : 'N/A'}
                    </Typography>
                  </Box>
                </Box>
              )}
            </Box>
          </Box>
        </motion.div>
      </Box>
    </Box>
  );
};

export default SidebarContent;
