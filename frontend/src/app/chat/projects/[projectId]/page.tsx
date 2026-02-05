'use client'

import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  Box,
  Button,
  Typography,
  useTheme,
  useMediaQuery,
  IconButton,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Folder as ProjectIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Chat as ChatIcon,
  Add as AddIcon,
  KeyboardArrowDown as ArrowDownIcon,
  Check as CheckIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Warning as WarningIcon,
  ChatBubbleOutline as EmptyChatIcon
} from '@mui/icons-material';
import { useRouter, useParams } from 'next/navigation';
import WorkflowPanel from '@/components/WorkflowPanel';
import ProjectMessageList from '@/components/Chat/ProjectMessageList';
import ChatInput from '@/components/Chat/ChatInput';
import { useProjectChat } from '@/hooks/useProjectChat';
import { useAppDispatch } from '@/store/hooks';
import { updateSession, deleteSession } from '@/store/slices/chatProjectsSlice';
import type { ChatSession } from '@/types/chatProjects';

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

  // Session dropdown state
  const [sessionMenuAnchor, setSessionMenuAnchor] = useState<null | HTMLElement>(null);
  const sessionMenuOpen = Boolean(sessionMenuAnchor);

  // Session edit/delete/create dialog state
  const dispatch = useAppDispatch();
  const [editSessionDialog, setEditSessionDialog] = useState<{ open: boolean; session: ChatSession | null }>({ open: false, session: null });
  const [deleteSessionDialog, setDeleteSessionDialog] = useState<{ open: boolean; session: ChatSession | null }>({ open: false, session: null });
  const [newSessionDialog, setNewSessionDialog] = useState(false);
  const [editSessionName, setEditSessionName] = useState('');
  const [newSessionName, setNewSessionName] = useState('');
  const [sessionActionLoading, setSessionActionLoading] = useState(false);

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
    sessions,
    currentSession,
    sessionId,
    chatLoading,
    isTyping,
    mode,
    sendMessage,
    sendMessageWithFiles,
    sendDemoVideo,
    stopProcessing,
    setMode,
    switchSession,
    createNewSession,
    projectExists
  } = useProjectChat(projectId);

  // Session dropdown handlers
  const handleSessionMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setSessionMenuAnchor(event.currentTarget);
  };

  const handleSessionMenuClose = () => {
    setSessionMenuAnchor(null);
  };

  const handleSessionSelect = (selectedSessionId: string) => {
    switchSession(selectedSessionId);
    handleSessionMenuClose();
  };

  const handleCreateNewSession = () => {
    handleSessionMenuClose();
    setNewSessionName('');
    setNewSessionDialog(true);
  };

  const handleNewSessionSave = async () => {
    const name = newSessionName.trim() || 'New Chat';
    setSessionActionLoading(true);
    try {
      await createNewSession(name);
      setNewSessionDialog(false);
      setNewSessionName('');
    } catch (error) {
      console.error('Failed to create session:', error);
    } finally {
      setSessionActionLoading(false);
    }
  };

  // Session edit/delete handlers
  const handleEditSession = (session: ChatSession, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditSessionName(session.name);
    setEditSessionDialog({ open: true, session });
    handleSessionMenuClose();
  };

  const handleDeleteSession = (session: ChatSession, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteSessionDialog({ open: true, session });
    handleSessionMenuClose();
  };

  const handleEditSessionSave = async () => {
    if (!editSessionDialog.session || !editSessionName.trim()) return;

    setSessionActionLoading(true);
    try {
      await dispatch(updateSession({
        projectId,
        sessionId: editSessionDialog.session.id,
        request: { name: editSessionName.trim() }
      }));
      setEditSessionDialog({ open: false, session: null });
    } catch (error) {
      console.error('Failed to update session:', error);
    } finally {
      setSessionActionLoading(false);
    }
  };

  const handleDeleteSessionConfirm = async () => {
    if (!deleteSessionDialog.session) return;

    setSessionActionLoading(true);
    try {
      await dispatch(deleteSession({
        projectId,
        sessionId: deleteSessionDialog.session.id
      }));
      setDeleteSessionDialog({ open: false, session: null });
    } catch (error) {
      console.error('Failed to delete session:', error);
    } finally {
      setSessionActionLoading(false);
    }
  };

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

        <Box sx={{ display: 'flex', alignItems: 'center', flex: 1, gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <ProjectIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="body1" color="text.secondary">
              {project?.name || 'Project Chat'}
            </Typography>
          </Box>

          {/* Session Dropdown */}
          {sessions.length > 0 && (
            <>
              <Button
                onClick={handleSessionMenuOpen}
                variant="text"
                size="small"
                endIcon={<ArrowDownIcon />}
                sx={{
                  color: 'text.primary',
                  textTransform: 'none',
                  fontWeight: 500,
                  px: 1.5,
                  '&:hover': {
                    bgcolor: 'action.hover'
                  }
                }}
              >
                <ChatIcon sx={{ fontSize: 18, mr: 0.75, color: 'primary.main' }} />
                {currentSession?.name || 'Select Chat'}
              </Button>
              <Menu
                anchorEl={sessionMenuAnchor}
                open={sessionMenuOpen}
                onClose={handleSessionMenuClose}
                anchorOrigin={{
                  vertical: 'bottom',
                  horizontal: 'left',
                }}
                transformOrigin={{
                  vertical: 'top',
                  horizontal: 'left',
                }}
                PaperProps={{
                  sx: {
                    minWidth: 280,
                    maxHeight: 350,
                    overflow: 'auto'
                  }
                }}
              >
                {sessions.map((session) => (
                  <MenuItem
                    key={session.id}
                    onClick={() => handleSessionSelect(session.id)}
                    selected={session.id === sessionId}
                    sx={{ pr: 1 }}
                  >
                    <ListItemIcon>
                      {session.id === sessionId ? (
                        <CheckIcon fontSize="small" color="primary" />
                      ) : (
                        <ChatIcon fontSize="small" />
                      )}
                    </ListItemIcon>
                    <ListItemText
                      primary={session.name}
                      sx={{ mr: 1 }}
                    />
                    <Box sx={{ display: 'flex', gap: 0.5, ml: 'auto' }}>
                      <IconButton
                        size="small"
                        onClick={(e) => handleEditSession(session, e)}
                        sx={{
                          p: 0.5,
                          opacity: 0.6,
                          '&:hover': { opacity: 1, bgcolor: 'action.hover' }
                        }}
                      >
                        <EditIcon sx={{ fontSize: 16 }} />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={(e) => handleDeleteSession(session, e)}
                        sx={{
                          p: 0.5,
                          opacity: 0.6,
                          '&:hover': { opacity: 1, bgcolor: 'error.light', color: 'error.main' }
                        }}
                      >
                        <DeleteIcon sx={{ fontSize: 16 }} />
                      </IconButton>
                    </Box>
                  </MenuItem>
                ))}
                <Divider />
                <MenuItem onClick={handleCreateNewSession}>
                  <ListItemIcon>
                    <AddIcon fontSize="small" color="primary" />
                  </ListItemIcon>
                  <ListItemText primary="New Chat" />
                </MenuItem>
              </Menu>
            </>
          )}

          {/* New Chat button when no sessions */}
          {sessions.length === 0 && (
            <Tooltip title="Create a new chat session">
              <IconButton
                onClick={handleCreateNewSession}
                size="small"
                color="primary"
              >
                <AddIcon />
              </IconButton>
            </Tooltip>
          )}
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
          <Box sx={{
            p: 2,
            display: 'flex',
            alignItems: 'center'
          }}>
            <Typography variant="h6" sx={{ fontWeight: 600, color: muiTheme.palette.text.primary }}>
              {project?.name || 'Project Chat'}
            </Typography>
          </Box>

          {/* Empty state when no sessions */}
          {sessions.length === 0 ? (
            <Box sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              p: 4
            }}>
              <EmptyChatIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={handleCreateNewSession}
                sx={{ px: 3, py: 1 }}
              >
                New Chat
              </Button>
            </Box>
          ) : (
            <>
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
            </>
          )}
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

      {/* Edit Session Dialog */}
      <Dialog
        open={editSessionDialog.open}
        onClose={() => !sessionActionLoading && setEditSessionDialog({ open: false, session: null })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <ChatIcon sx={{ mr: 2, color: 'primary.main' }} />
            Rename Chat
          </Box>
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Chat Name"
            value={editSessionName}
            onChange={(e) => setEditSessionName(e.target.value)}
            disabled={sessionActionLoading}
            sx={{ mt: 1 }}
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter' && editSessionName.trim()) {
                handleEditSessionSave();
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setEditSessionDialog({ open: false, session: null })}
            disabled={sessionActionLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleEditSessionSave}
            variant="contained"
            disabled={sessionActionLoading || !editSessionName.trim()}
            startIcon={sessionActionLoading ? <CircularProgress size={16} /> : <EditIcon />}
          >
            {sessionActionLoading ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Session Confirmation Dialog */}
      <Dialog
        open={deleteSessionDialog.open}
        onClose={() => !sessionActionLoading && setDeleteSessionDialog({ open: false, session: null })}
        maxWidth="sm"
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <WarningIcon sx={{ mr: 2, color: 'error.main' }} />
            Delete Chat
          </Box>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Are you sure you want to delete "<strong>{deleteSessionDialog.session?.name}</strong>"?
          </Typography>
          <Typography variant="body2" color="text.secondary">
            This will permanently delete all messages in this chat. This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setDeleteSessionDialog({ open: false, session: null })}
            disabled={sessionActionLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleDeleteSessionConfirm}
            variant="contained"
            color="error"
            disabled={sessionActionLoading}
            startIcon={sessionActionLoading ? <CircularProgress size={16} /> : <DeleteIcon />}
          >
            {sessionActionLoading ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* New Session Dialog */}
      <Dialog
        open={newSessionDialog}
        onClose={() => !sessionActionLoading && setNewSessionDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <AddIcon sx={{ mr: 2, color: 'primary.main' }} />
            New Chat
          </Box>
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Chat Name"
            placeholder="Enter a name for this chat"
            value={newSessionName}
            onChange={(e) => setNewSessionName(e.target.value)}
            disabled={sessionActionLoading}
            sx={{ mt: 1 }}
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleNewSessionSave();
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setNewSessionDialog(false)}
            disabled={sessionActionLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleNewSessionSave}
            variant="contained"
            disabled={sessionActionLoading}
            startIcon={sessionActionLoading ? <CircularProgress size={16} /> : <AddIcon />}
          >
            {sessionActionLoading ? 'Creating...' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ProjectChatPage;
