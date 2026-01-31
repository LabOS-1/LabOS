'use client'

import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  Box,
  Button,
  Typography,
  Paper,
  useTheme,
  useMediaQuery,
  Stack,
  IconButton,
  Tooltip
} from '@mui/material';
import { 
  ArrowBack as ArrowBackIcon, 
  Folder as ProjectIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon
} from '@mui/icons-material';
import { useRouter, useParams } from 'next/navigation';
import WorkflowPanel from '@/components/WorkflowPanel';
import ProjectMessageList from '@/components/Chat/ProjectMessageList';
import ChatInput from '@/components/Chat/ChatInput';
import { useProjectChat } from '@/hooks/useProjectChat';

const ProjectChatPage: React.FC = () => {
  const router = useRouter();
  const params = useParams();
  const muiTheme = useTheme();
  
  // Get projectId first
  const projectId = params.projectId as string;

  // Responsive design
  const isMobile = useMediaQuery(muiTheme.breakpoints.down('md'));
  const isVeryNarrow = useMediaQuery('(max-width:800px)');

  // Panel state - Start expanded by default (will be collapsed on narrow screens by useEffect)
  const [workflowCollapsed, setWorkflowCollapsed] = useState(false);
  const [chatWidth, setChatWidth] = useState(60); // Chat panel width percentage
  const [isResizing, setIsResizing] = useState(false);

  // Refs
  const containerRef = useRef<HTMLDivElement>(null);

  // Initialize and update workflow collapsed state based on screen width
  useEffect(() => {
    // On narrow screens, always keep collapsed
    if (isVeryNarrow) {
      setWorkflowCollapsed(true);
    } else {
      // On wider screens, allow it to be expanded (but start collapsed on first load)
      // This prevents auto-expansion when switching projects
    }
  }, [isVeryNarrow]);

  // When projectId changes, reset to collapsed state on narrow screens
  useEffect(() => {
    if (isVeryNarrow) {
      setWorkflowCollapsed(true);
    }
  }, [projectId, isVeryNarrow]);
  
  // Use custom hook for all project chat logic
  const {
    messages,
    project,
    chatLoading,
    isTyping,
    mode,
    sendMessage,
    sendMessageWithFiles,
    sendDemoVideo,
    stopProcessing,
    setMode,
    projectExists
  } = useProjectChat(projectId);

  // Handle mouse drag for resizing panels
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isResizing || !containerRef.current) return;
    
    const containerRect = containerRef.current.getBoundingClientRect();
    const newChatWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;
    
    // Calculate maximum chat width to ensure workflow panel has adequate space
    const workflowMinWidth = isVeryNarrow ? 280 : 350;
    const containerWidth = containerRect.width;
    const maxChatWidthPercent = Math.min(80, ((containerWidth - workflowMinWidth) / containerWidth) * 100);
    
    // Constrain between 30% and calculated maximum
    const constrainedWidth = Math.min(Math.max(newChatWidth, 30), maxChatWidthPercent);
    setChatWidth(constrainedWidth);
  }, [isResizing, isVeryNarrow]);

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
  }, []);

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing, handleMouseMove, handleMouseUp]);

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Navigation Bar */}
      <Box sx={{ 
        p: 2, 
        mb: 1,
        display: 'flex',
        alignItems: 'center',
        gap: 2
      }}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => {
            // Navigate back without stopping the workflow
            // The workflow will continue running in the background
            console.log('📍 Navigating back to projects list, workflow continues in background');
            router.push('/chat/projects');
          }}
          variant="outlined"
          size="small"
        >
          Back to Projects
        </Button>
        
        <Box sx={{ display: 'flex', alignItems: 'center', flex: 1 }}>
          <ProjectIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="body1" color="text.secondary">
            {project?.name || 'Project Chat'}
          </Typography>
        </Box>
      </Box>

      {/* Chat Interface with Resizable Panels */}
      <Box 
        ref={containerRef}
        sx={{ 
          flex: 1, 
          overflow: 'hidden', 
          display: 'flex',
          position: 'relative'
        }}
      >
        {/* Chat Messages Area - Resizable */}
        <Box sx={{ 
          width: workflowCollapsed ? (isVeryNarrow ? '100%' : 'calc(100% - 48px)') : `${chatWidth}%`,
          display: 'flex', 
          flexDirection: 'column', 
          bgcolor: muiTheme.palette.background.paper,
          transition: workflowCollapsed ? 'width 0.3s ease' : 'none'
        }}>
          {/* Chat header */}
          <Paper sx={{
            p: 2.5,
            borderRadius: 0,
            bgcolor: muiTheme.palette.background.paper,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 0, color: muiTheme.palette.text.primary }}>
                  {project?.name || 'Project Chat'}
                </Typography>
                <Typography variant="body2" sx={{ color: muiTheme.palette.text.secondary, fontSize: '14px' }}>
                  Project-based conversation with LabOS AI
                </Typography>
              </Box>
            </Stack>
          </Paper>

          {/* Messages List Component */}
          <ProjectMessageList
            messages={messages}
            isLoading={chatLoading}
            projectName={project?.name}
            onExampleClick={sendMessage}
            onVideoAnalyze={(example) => sendDemoVideo(example.videoUrl, example.prompt || 'Analyze this video')}
          />

          {/* Input Component */}
          <ChatInput
            onSendMessage={sendMessage}
            onSendMessageWithFiles={sendMessageWithFiles}
            onStopProcessing={stopProcessing}
            isLoading={chatLoading}
            mode={mode}
            onModeChange={setMode}
          />
        </Box>
        
        {/* Resizable Divider - Only show when not collapsed and not on mobile */}
        {!workflowCollapsed && !isVeryNarrow && (
          <Box
            onMouseDown={handleMouseDown}
            sx={{
              width: 4,
              bgcolor: 'transparent',
              cursor: 'col-resize',
              borderLeft: `2px solid ${muiTheme.palette.divider}`,
              '&:hover': {
                borderLeft: `2px solid ${muiTheme.palette.primary.main}`,
              },
              transition: 'border-color 0.2s ease'
            }}
          />
        )}

        {/* Backdrop for overlay mode */}
        {isVeryNarrow && !workflowCollapsed && (
          <Box
            onClick={() => setWorkflowCollapsed(true)}
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              bgcolor: 'rgba(0, 0, 0, 0.5)',
              zIndex: 999
            }}
          />
        )}

        {/* Collapse Toggle Button - Always visible */}
        {/* On narrow screens when collapsed: show on right edge */}
        {/* On narrow screens when expanded: show on workflow panel edge */}
        {/* On wide screens: show on workflow panel edge */}
        {(isVeryNarrow && workflowCollapsed) && (
          <Box sx={{
            position: 'absolute',
            right: 16,
            top: '50%',
            transform: 'translateY(-50%)',
            zIndex: 100
          }}>
            <Tooltip title="Show workflow" arrow>
              <IconButton
                onClick={() => setWorkflowCollapsed(false)}
                size="small"
                sx={{
                  bgcolor: muiTheme.palette.background.paper,
                  border: `1px solid ${muiTheme.palette.divider}`,
                  color: muiTheme.palette.text.secondary,
                  width: 32,
                  height: 32,
                  '&:hover': {
                    bgcolor: muiTheme.palette.action.hover,
                    color: muiTheme.palette.text.primary
                  }
                }}
              >
                <ChevronLeftIcon sx={{ fontSize: 20 }} />
              </IconButton>
            </Tooltip>
          </Box>
        )}

        {/* Workflow Panel - Collapsible and Resizable */}
        {/* On narrow screens: hide when collapsed, show as overlay when expanded */}
        {/* On wide screens: show as resizable sidebar */}
        {(!isVeryNarrow || !workflowCollapsed) && (
        <Box sx={{
          width: workflowCollapsed ? 48 : (isVeryNarrow ? 'calc(100% - 60px)' : `${100 - chatWidth}%`),
          maxWidth: workflowCollapsed ? 48 : (isVeryNarrow ? 320 : 'none'),
          display: 'flex',
          flexDirection: 'column',
          bgcolor: muiTheme.palette.background.paper,
          borderLeft: `1px solid ${muiTheme.palette.divider}`,
          transition: workflowCollapsed ? 'width 0.3s ease' : 'none',
          position: isVeryNarrow && !workflowCollapsed ? 'absolute' : 'relative',
          right: 0,
          top: 0,
          height: '100%',
          zIndex: isVeryNarrow && !workflowCollapsed ? 1000 : 'auto',
          boxShadow: isVeryNarrow && !workflowCollapsed ? `0 4px 20px ${muiTheme.palette.action.focus}` : 'none'
        }}>
          {/* Collapse button on workflow panel edge */}
          <Box sx={{
            position: 'absolute',
            left: workflowCollapsed ? 8 : -16,
            top: '50%',
            transform: 'translateY(-50%)',
            zIndex: isVeryNarrow && !workflowCollapsed ? 1001 : 10
          }}>
            <Tooltip title={workflowCollapsed ? "Expand workflow panel" : "Collapse workflow panel"} arrow>
              <IconButton
                className="workflow-panel-toggle"
                onClick={() => setWorkflowCollapsed(!workflowCollapsed)}
                size="small"
                sx={{
                  bgcolor: muiTheme.palette.background.paper,
                  border: `1px solid ${muiTheme.palette.divider}`,
                  color: muiTheme.palette.text.secondary,
                  width: 24,
                  height: 24,
                  '&:hover': {
                    bgcolor: muiTheme.palette.action.hover,
                    color: muiTheme.palette.text.primary
                  }
                }}
              >
                {workflowCollapsed ? <ChevronLeftIcon sx={{ fontSize: 16 }} /> : <ChevronRightIcon sx={{ fontSize: 16 }} />}
              </IconButton>
            </Tooltip>
          </Box>

          {workflowCollapsed && !isVeryNarrow ? (
            /* Collapsed state - just show icons */
            <Box sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              p: 1,
              pt: 3,
              height: '100%',
              gap: 2
            }}>
              <Tooltip title="Workflow Steps" arrow placement="left">
                <IconButton sx={{ color: muiTheme.palette.primary.main }}>
                  <Box sx={{ fontSize: '1.2rem' }}>⚡</Box>
                </IconButton>
              </Tooltip>
              <Tooltip title="Connection Status" arrow placement="left">
                <Box sx={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  bgcolor: muiTheme.palette.success.main
                }} />
              </Tooltip>
            </Box>
          ) : (
            <WorkflowPanel projectId={projectId} />
          )}
        </Box>
        )}
      </Box>
    </Box>
  );
};

export default ProjectChatPage;
