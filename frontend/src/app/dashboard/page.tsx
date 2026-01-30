'use client'

import React, { useEffect } from 'react';
import ProtectedRoute from '@/components/Auth/ProtectedRoute';
// Onboarding now handled globally in AppLayout
import { 
  Card, 
  CardContent,
  Typography, 
  Button, 
  Alert, 
  Box
} from '@mui/material';
import {
  Folder as ProjectIcon,
  Build as ToolIcon,
  InsertDriveFile as FileIcon,
  Person as UserIcon,
  Schedule as ClockIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { fetchProjects } from '@/store/slices/chatProjectsSlice';
import { setTools } from '@/store/slices/toolsSlice';
import { setAgents } from '@/store/slices/agentsSlice';
import { Progress } from '@/components/ui/progress';

const Dashboard: React.FC = () => {
  const dispatch = useAppDispatch();

  const systemStatus = useAppSelector((state) => state.system.systemStatus);
  const connected = useAppSelector((state) => state.system.connected);
  const agents = useAppSelector((state) => state.agents.agents);
  const tools = useAppSelector((state) => state.tools.tools);
  const files = useAppSelector((state) => state.files.files);
  const projects = useAppSelector((state) => state.chatProjects.projects);

  // Auto-refresh data when dashboard opens
  useEffect(() => {
    const refreshData = async () => {
      try {
        // Refresh projects data
        dispatch(fetchProjects());
        
        // Refresh tools data
        const refreshTools = async () => {
          try {
            const response = await fetch('/api/v1/tools');
            const result = await response.json();

            if (result.success && result.data) {
              const allToolsFromAPI = [
                ...(result.data.builtin_tools || []),
                ...(result.data.public_tools || []),
                ...(result.data.my_tools || []),
                ...(result.data.mcp_tools || [])
              ];

              const transformedTools = allToolsFromAPI.map((tool: any, index: number) => ({
                id: tool.id || `${tool.type}_${tool.name.toLowerCase().replace(/\s+/g, '_')}_${index}`,
                name: tool.name,
                description: tool.description,
                category: tool.category,
                type: tool.type,
                usage_count: tool.usage_count,
                last_used: tool.last_used,
                created_at: tool.created_at || new Date().toISOString(),
                updated_at: new Date().toISOString()
              }));

              dispatch(setTools(transformedTools));
            }
          } catch (err) {
            console.error('Error refreshing tools:', err);
          }
        };
        
        // Refresh agents data
        const refreshAgents = async () => {
          try {
            const response = await fetch('/api/v1/agents');
            const result = await response.json();
            
            if (result.success && result.data) {
              dispatch(setAgents(result.data));
            }
          } catch (err) {
            console.error('Error refreshing agents:', err);
          }
        };
        
        await refreshTools();
        await refreshAgents();
        
        console.log('📊 Dashboard data refreshed');
      } catch (error) {
        console.error('❌ Error refreshing dashboard data:', error);
      }
    };

    refreshData();
  }, [dispatch]);

  const stats = [
    {
      title: 'Chat Projects',
      value: projects.length,
      icon: <ProjectIcon color="primary" />,
      color: 'primary.main',
    },
    {
      title: 'Available Tools',
      value: tools.length,
      icon: <ToolIcon color="success" />,
      color: 'success.main',
    },
    {
      title: 'Files',
      value: files.length,
      icon: <FileIcon color="warning" />,
      color: 'warning.main',
    },
    {
      title: 'Active Agents',
      value: 4, // Fixed value: LABOS has 4 core agents
      icon: <UserIcon color="secondary" />,
      color: 'secondary.main',
    },
  ];

  return (
    <Box sx={{ p: 3, pt: 2 }}> {/* Reduce top padding to align with header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Box sx={{ mb: 4 }}>
            <Typography variant="body1" color="text.secondary">
              Welcome to LabOS - Your intelligent research assistant
            </Typography>
          </Box>

        {/* Connection Status */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <Box sx={{ mb: 3 }}>
            <Alert
              severity={connected === null ? "info" : connected ? "success" : "error"}
              action={
                <Button
                  size="small"
                  startIcon={<RefreshIcon />}
                  onClick={async () => {
                    try {
                      const response = await fetch('/api/v1/system/health');
                      const data = await response.json();
                      console.log('Manual health check:', data);
                      alert(`Health check result: ${JSON.stringify(data, null, 2)}`);
                    } catch (error) {
                      console.error('Manual health check failed:', error);
                      alert(`Health check failed: ${error}`);
                    }
                  }}
                >
                  Test Connection
                </Button>
              }
            >
              <Box>
                <Typography variant="body2" fontWeight="bold">
                  {connected === null ? "Checking Connection..." : connected ? "System Online" : "System Offline"}
                </Typography>
                <Typography variant="body2">
                  {connected === null ? "Verifying backend status" : connected ? "All systems are operational" : "Unable to connect to backend"}
                </Typography>
              </Box>
            </Alert>
          </Box>
        </motion.div>

        {/* Statistics Cards */}
        <Box 
          sx={{ 
            display: 'grid', 
            gridTemplateColumns: { 
              xs: '1fr', 
              sm: 'repeat(2, 1fr)', 
              md: 'repeat(4, 1fr)' 
            }, 
            gap: 2,
            mb: 3
          }}
        >
          {stats.map((stat, index) => (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.1 * (index + 1) }}
            >
              <Card 
                sx={{ height: '100%' }}
                className={stat.title === 'Active Agents' ? 'active-agents-stat-card' : ''}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    {stat.icon}
                    <Box>
                      <Typography variant="h4" component="div" sx={{ color: stat.color }}>
                        {stat.value}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {stat.title}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </Box>

        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '2fr 1fr' }, gap: 2 }}>
          {/* System Status */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.4 }}
          >
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
                  <ClockIcon />
                  <Typography variant="h6">System Status</Typography>
                </Box>
                
                {systemStatus ? (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                    <Box>
                      <Typography variant="body2" fontWeight="bold" gutterBottom>
                        CPU Usage
                      </Typography>
                      <Progress 
                        value={systemStatus.resources.cpu_usage} 
                        color={systemStatus.resources.cpu_usage > 80 ? 'error' : 'primary'}
                      />
                    </Box>
                    <Box>
                      <Typography variant="body2" fontWeight="bold" gutterBottom>
                        Memory Usage
                      </Typography>
                      <Progress 
                        value={systemStatus.resources.memory_usage} 
                        color={systemStatus.resources.memory_usage > 80 ? 'error' : 'primary'}
                      />
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" color="text.secondary">
                        Uptime: {Math.floor(systemStatus.uptime / 3600)}h
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Status: {systemStatus.status}
                      </Typography>
                    </Box>
                  </Box>
                ) : (
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      No system data available
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* Right column can be used for additional widgets in the future */}
          <Box></Box>
        </Box>
      </motion.div>
    </Box>
  );
};

const DashboardWithProtection: React.FC = () => {
  return (
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  );
};

export default DashboardWithProtection;
