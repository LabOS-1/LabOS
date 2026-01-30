'use client'

import React, { useEffect, useState } from 'react';
import ProtectedRoute from '@/components/Auth/ProtectedRoute';
import { 
  Card, 
  CardContent,
  Typography, 
  Button,
  Box, 
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  IconButton,
  TablePagination,
  CircularProgress
} from '@mui/material';
import { 
  Download as DownloadIcon,
  Chat as ChatIcon,
  AccountTree as WorkflowIcon,
  Folder as ProjectIcon,
  GetApp as ExportIcon,
  Storage as StorageIcon
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { fetchProjects } from '@/store/slices/chatProjectsSlice';
import { config } from '@/config';

const Memory: React.FC = () => {
  const dispatch = useAppDispatch();
  const projects = useAppSelector((state) => state.chatProjects.projects);
  const projectsLoading = useAppSelector((state) => state.chatProjects.projectsLoading);
  
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Auto-refresh projects when page loads
  useEffect(() => {
    dispatch(fetchProjects());
  }, [dispatch]);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Export functions
  const handleExportProject = async (projectId: string, projectName: string) => {
    try {
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {};
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${config.api.baseUrl}/api/v1/memory/export/project/${projectId}`, {
        headers,
        credentials: 'include',
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `labos_project_${projectName}_${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Error exporting project:', error);
    }
  };

  const handleExportChatHistory = async (projectId: string, projectName: string) => {
    try {
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {};
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${config.api.baseUrl}/api/v1/memory/export/project/${projectId}/chat-history`, {
        headers,
        credentials: 'include',
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `labos_chat_${projectName}_${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Error exporting chat history:', error);
    }
  };

  const handleExportWorkflows = async (projectId: string, projectName: string) => {
    try {
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {};
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${config.api.baseUrl}/api/v1/memory/export/project/${projectId}/workflows`, {
        headers,
        credentials: 'include',
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `labos_workflows_${projectName}_${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Error exporting workflows:', error);
    }
  };

  const stats = [
    {
      title: 'Total Projects',
      value: projects.length,
      icon: <ProjectIcon color="primary" />,
      color: 'primary.main',
    },
    {
      title: 'Total Messages',
      value: projects.reduce((total, project) => total + (project.message_count || 0), 0),
      icon: <ChatIcon color="success" />,
      color: 'success.main',
    },
    {
      title: 'Exportable',
      value: projects.filter(p => p.message_count > 0).length,
      icon: <ExportIcon color="info" />,
      color: 'info.main',
    }
  ];

  const paginatedProjects = projects.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  return (
      <Box sx={{ p: 3 }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {/* Header */}
          <Box sx={{ mb: 4 }}>
            <Typography variant="h4" component="h1" sx={{ mb: 1, fontWeight: 600, color: 'text.primary' }}>
              Memory & Exports
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Manage and export your project data, chat history, and workflow details.
            </Typography>
          </Box>

          {/* Stats Cards */}
          <Box 
            sx={{ 
              display: 'grid', 
              gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' }, 
              gap: 3,
              mb: 4
            }}
          >
            {stats.map((stat, index) => (
               <motion.div
               key={stat.title}
               initial={{ opacity: 0, y: 20 }}
               animate={{ opacity: 1, y: 0 }}
               transition={{ duration: 0.3, delay: 0.1 * index }}
          >
              <Card sx={{ height: '100%' }}>
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

          {/* Projects Table */}
            <Card>
            <CardContent sx={{ p: 0 }}>
              {projectsLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : projects.length === 0 ? (
                 <Box sx={{ textAlign: 'center', py: 8 }}>
                   <StorageIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
                   <Typography variant="h6" color="text.secondary" sx={{ mb: 2 }}>
                     No Projects Available
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                     Start a conversation to see projects here.
                    </Typography>
                  </Box>
              ) : (
                <>
                  <TableContainer>
                    <Table sx={{ minWidth: 650 }} aria-label="projects table">
                      <TableHead>
                        <TableRow>
                          <TableCell>Project Name</TableCell>
                          <TableCell>Statistics</TableCell>
                          <TableCell>Last Updated</TableCell>
                          <TableCell>Export Options</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {paginatedProjects.map((project) => (
                          <TableRow
                      key={project.id}
                            sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                            hover
                    >
                            <TableCell component="th" scope="row">
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                <Box sx={{ 
                                  p: 1, 
                                  borderRadius: 1, 
                                  bgcolor: 'primary.main', 
                                  color: 'common.white',
                                  display: 'flex'
                                }}>
                                  <ProjectIcon fontSize="small" />
                                </Box>
                                <Box>
                                  <Typography variant="subtitle2" fontWeight="600">
                                {project.name}
                              </Typography>
                              {project.description && (
                                    <Typography variant="caption" color="text.secondary" sx={{ 
                                      display: '-webkit-box',
                                      WebkitLineClamp: 1,
                                      WebkitBoxOrient: 'vertical',
                                      overflow: 'hidden',
                                      maxWidth: '200px'
                                    }}>
                                  {project.description}
                                </Typography>
                              )}
                                </Box>
                              </Box>
                            </TableCell>
                            <TableCell>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'text.secondary' }}>
                                    <ChatIcon fontSize="small" sx={{ fontSize: 16 }} />
                                    <Typography variant="body2">
                                    {project.message_count || 0} Msgs
                                    </Typography>
                            </Box>
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" color="text.secondary">
                                {new Date(project.updated_at).toLocaleDateString()}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button
                              variant="contained"
                                  size="small"
                              startIcon={<DownloadIcon />}
                              onClick={() => handleExportProject(project.id, project.name)}
                                  sx={{ textTransform: 'none' }}
                            >
                                  Export All
                            </Button>
                                <Tooltip title="Download Chat History Only">
                                  <IconButton 
                                    size="small" 
                                    color="primary" 
                              onClick={() => handleExportChatHistory(project.id, project.name)}
                                    sx={{ border: '1px solid', borderColor: 'divider' }}
                                  >
                                    <ChatIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                                <Tooltip title="Download Workflows Only">
                                  <IconButton 
                              size="small"
                                    color="primary"
                              onClick={() => handleExportWorkflows(project.id, project.name)}
                                    sx={{ border: '1px solid', borderColor: 'divider' }}
                                  >
                                    <WorkflowIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              </Box>
                            </TableCell>
                          </TableRow>
                  ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                  <TablePagination
                    rowsPerPageOptions={[5, 10, 25]}
                    component="div"
                    count={projects.length}
                    rowsPerPage={rowsPerPage}
                    page={page}
                    onPageChange={handleChangePage}
                    onRowsPerPageChange={handleChangeRowsPerPage}
                  />
                </>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </Box>
  );
};

const MemoryWithProtection: React.FC = () => {
  return (
    <ProtectedRoute>
      <Memory />
    </ProtectedRoute>
  );
};

export default MemoryWithProtection;
