'use client'

import React, { useEffect } from 'react';
import {
  Typography,
  Box,
  Card,
  CardContent,
  Button
} from '@mui/material';
import {
  Add as AddIcon,
  Folder as ProjectIcon
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { fetchProjects } from '@/store/slices/chatProjectsSlice';
import CreateProjectModal from '@/components/Chat/CreateProjectModal';
import ProjectMenuDropdown from '@/components/Chat/ProjectMenuDropdown';

const ChatProjectsPage: React.FC = () => {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const [createModalOpen, setCreateModalOpen] = React.useState(false);
  
  const {
    projects,
    projectsLoading,
    error
  } = useAppSelector((state) => state.chatProjects);

  useEffect(() => {
    dispatch(fetchProjects());
  }, [dispatch]);

  const handleCreateProject = () => {
    setCreateModalOpen(true);
  };

  const handleProjectCreated = (projectId: string) => {
    // Clear any existing chat state before navigating to new project
    // This prevents "ghost" content from previous sessions appearing in the new empty project
    import('@/store/slices/chatSlice').then(({ clearMessages, setIsLoading }) => {
      dispatch(clearMessages());
      // Set loading to true so we see a spinner instead of an empty state flash
      dispatch(setIsLoading(true));
    });
    
    import('@/store/slices/websocketSlice').then(({ clearChatResponse, clearWorkflowState }) => {
      dispatch(clearChatResponse());
      dispatch(clearWorkflowState());
    });

    // Navigate to the newly created project
    router.push(`/chat/projects/${projectId}`);
  };

  const handleOpenProject = async (projectId: string) => {
    // Immediately clear previous messages and chat state to prevent flash of old content
    import('@/store/slices/chatSlice').then(({ clearMessages, setIsLoading }) => {
      dispatch(clearMessages());
      // Force loading state to TRUE immediately to show spinner instead of empty state/examples
      dispatch(setIsLoading(true)); 
    });
    
    import('@/store/slices/websocketSlice').then(({ clearChatResponse, clearWorkflowState }) => {
      dispatch(clearChatResponse());
      dispatch(clearWorkflowState());
    });

    // Cancel ALL active workflows before switching projects
    console.log('🛑 Cancelling all active workflows before switching projects');
    try {
      // Prepare headers with auth token
      // V2: Workflow cleanup handled automatically by WebSocket disconnect
      // No need to explicitly cancel - WebSocket will disconnect on page navigation
      console.log('🔄 Navigating to project (workflows will auto-cleanup on disconnect)');
    } catch (error) {
      console.error('❌ Error during navigation:', error);
    }

    // Navigate to the project
    router.push(`/chat/projects/${projectId}`);
  };

  return (
    <Box sx={{ p: 3 }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" component="h1" sx={{ mb: 1, fontWeight: 600, color: 'text.primary' }}>
            Projects
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Organize your conversations into projects for better management and history tracking
          </Typography>
        </Box>

        {/* Quick Actions */}
        <Box sx={{ mb: 4 }}>
          <Button
            className="new-project-button"
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreateProject}
            size="large"
          >
            New Project
          </Button>
        </Box>

        {/* Projects Grid */}
        {projectsLoading ? (
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <Typography variant="h6" color="text.secondary">
              Loading projects...
            </Typography>
          </Box>
        ) : projects.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <ProjectIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" sx={{ mb: 2 }}>
              No Projects Yet
            </Typography>
            {/* <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Create your first project to start organizing your conversations
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleCreateProject}
            >
              Create First Project
            </Button> */}
          </Box>
        ) : (
          <Box
            className="chat-projects-section"
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: '1fr',
                sm: 'repeat(2, 1fr)',
                md: 'repeat(3, 1fr)'
              },
              gap: 3
            }}>
            {projects.map((project) => (
              <Box key={project.id}>
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.3 }}
                  whileHover={{ scale: 1.02 }}
                >
                  <Card
                    elevation={0}
                    sx={{
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      cursor: 'pointer',
                      border: '1px solid',
                      borderColor: 'divider',
                      borderRadius: 3,
                      transition: 'all 0.2s ease',
                      bgcolor: 'background.paper',
                      '&:hover': {
                        borderColor: 'primary.main',
                        bgcolor: 'action.hover',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.05)'
                      },
                    }}
                    onClick={(e) => {
                      // Don't navigate if clicking on menu or buttons
                      if (e.defaultPrevented) return;
                      handleOpenProject(project.id);
                    }}
                  >
                    <CardContent sx={{ flex: 1, p: 2.5 }}>
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flex: 1, minWidth: 0 }}>
                          <Box sx={{ 
                            p: 1, 
                            borderRadius: 2, 
                            bgcolor: 'primary.main', 
                            color: 'white',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                          }}>
                            <ProjectIcon sx={{ fontSize: 20 }} />
                          </Box>
                          <Box sx={{ minWidth: 0 }}>
                            <Typography variant="h6" component="h3" sx={{ 
                              fontWeight: 600, 
                              fontSize: '1.1rem',
                              overflow: 'hidden', 
                              textOverflow: 'ellipsis', 
                              whiteSpace: 'nowrap' 
                            }}>
                              {project.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {new Date(project.updated_at).toLocaleDateString(undefined, { 
                                year: 'numeric', 
                                month: 'short', 
                                day: 'numeric' 
                              })}
                            </Typography>
                          </Box>
                        </Box>
                        <ProjectMenuDropdown 
                          project={project}
                          onProjectDeleted={() => {
                            dispatch(fetchProjects());
                            console.log('🗑️ Project deleted, refreshing project list');
                          }}
                        />
                      </Box>
                      
                      {project.description && (
                        <Typography variant="body2" color="text.secondary" sx={{ 
                          mb: 2, 
                          lineHeight: 1.6,
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                          height: '3.2em' // Fixed height for alignment
                        }}>
                          {project.description}
                        </Typography>
                      )}
                      
                    </CardContent>
                  </Card>
                </motion.div>
              </Box>
            ))}
          </Box>
        )}

        {/* Error State */}
        {error && (
          <Box sx={{ mt: 4 }}>
            <Typography variant="body2" color="error">
              Error: {error}
            </Typography>
          </Box>
        )}
      </motion.div>

      {/* Create Project Modal */}
      <CreateProjectModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onProjectCreated={handleProjectCreated}
      />
    </Box>
  );
};

export default ChatProjectsPage;
