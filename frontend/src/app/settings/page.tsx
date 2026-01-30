'use client'

import React from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/Auth/ProtectedRoute';
import { 
  Box, 
  Typography, 
  Switch, 
  Select, 
  MenuItem, 
  FormControl,
  FormControlLabel,
  InputLabel,
  Divider,
  Tooltip,
  Card,
  CardContent,
  CardHeader
} from '@mui/material';
import { Settings as SettingsIcon, AdminPanelSettings as AdminIcon } from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { updateTheme } from '@/store/slices/uiSlice';

interface SettingsFormValues {
  theme: 'light' | 'dark';
  language: 'en' | 'zh';
  animations: boolean;
  notifications: boolean;
}

const Settings: React.FC = () => {
  const router = useRouter();
  const theme = useAppSelector((state) => state.ui.theme);
  const { user } = useAppSelector((state) => state.auth);
  const dispatch = useAppDispatch();
  
  const isAdmin = (user as any)?.is_admin || false;
  
  const [formData, setFormData] = React.useState<SettingsFormValues>({
    theme: theme.mode,
    animations: theme.animations,
    language: 'en',
    notifications: true,
  });

  const handleInputChange = (field: keyof SettingsFormValues) => (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement> | { target: { value: unknown } }
  ) => {
    const value = 'checked' in event.target ? event.target.checked : event.target.value;
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Directly apply theme changes
    if (field === 'theme') {
      dispatch(updateTheme({
        mode: value as 'light' | 'dark',
        animations: formData.animations,
      }));
    }
    
    // Directly apply animation changes
    if (field === 'animations') {
      dispatch(updateTheme({
        mode: formData.theme,
        animations: value as boolean,
      }));
    }
  };


  return (
      <Box sx={{ p: 3, pt: 2 }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >

          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '2fr 1fr' }, gap: 2 }}>
            <Box>
              <Card>
                <CardHeader 
                  title={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <SettingsIcon />
                      <Typography variant="h6">General Settings</Typography>
                    </Box>
                  }
                />
                <CardContent>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
                      <Tooltip title="Choose between light and dark mode">
                        <FormControl fullWidth>
                          <InputLabel>Theme</InputLabel>
                          <Select
                            value={formData.theme}
                            label="Theme"
                            onChange={handleInputChange('theme')}
                          >
                            <MenuItem value="light">Light</MenuItem>
                            <MenuItem value="dark">Dark</MenuItem>
                          </Select>
                        </FormControl>
                      </Tooltip>
                      
                      <Tooltip title="Select your preferred language">
                        <FormControl fullWidth>
                          <InputLabel>Language</InputLabel>
                          <Select
                            value={formData.language}
                            label="Language"
                            onChange={handleInputChange('language')}
                          >
                            <MenuItem value="en">English</MenuItem>
                          </Select>
                        </FormControl>
                      </Tooltip>
                    </Box>

                    <Divider />

                    <Typography variant="h6" gutterBottom>
                      User Interface
                    </Typography>

                    <FormControlLabel
                      control={
                        <Switch 
                          checked={formData.animations}
                          onChange={handleInputChange('animations')}
                        />
                      }
                      label="Enable Animations"
                    />

                    <FormControlLabel
                      control={
                        <Switch 
                          checked={formData.notifications}
                          onChange={handleInputChange('notifications')}
                        />
                      }
                      label="Show Notifications"
                    />

                  </Box>
                </CardContent>
              </Card>
            </Box>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {isAdmin && (
                <Card>
                  <CardHeader 
                    title={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <AdminIcon />
                        <Typography variant="h6">Admin Panel</Typography>
                      </Box>
                    }
                  />
                  <CardContent>
                    <Card 
                      sx={{ 
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        '&:hover': {
                          boxShadow: 4,
                          transform: 'translateY(-2px)'
                        }
                      }}
                      onClick={() => router.push('/admin/waitlist')}
                    >
                      <CardContent>
                        <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                          User Waitlist Management
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Review and approve user access requests
                        </Typography>
                      </CardContent>
                    </Card>
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader title="About LabOS AI" />
                <CardContent>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" fontWeight="bold">Version:</Typography>
                      <Typography variant="body2">1.0.0</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" fontWeight="bold">Build:</Typography>
                      <Typography variant="body2">Next.js 15.5.0</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" fontWeight="bold">Backend:</Typography>
                      <Typography variant="body2">FastAPI</Typography>
                    </Box>
                    <Divider />
                    <Typography variant="body2" color="text.secondary">
                      LabOS AI is an intelligent research assistant designed to help with scientific research and data analysis.
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Box>
          </Box>
        </motion.div>
      </Box>
  );
};

const SettingsWithProtection: React.FC = () => {
  return (
    <ProtectedRoute>
      <Settings />
    </ProtectedRoute>
  );
};

export default SettingsWithProtection;

