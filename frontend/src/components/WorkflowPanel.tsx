'use client'

import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  Box,
  Card,
  Tabs,
  Tab,
  Chip,
  Typography,
  Stack,
  Paper,
  IconButton,
  Dialog,
  DialogContent,
  DialogTitle,
  CircularProgress,
  useTheme,
  useMediaQuery
} from '@mui/material';
import {
  AccessTime as ClockIcon,
  Description as FileTextIcon,
  Settings as SettingsIcon,
  Bolt as ThunderboltIcon,
  Download as DownloadIcon,
  Launch as LaunchIcon,
  Close as CloseIcon,
  ZoomIn as ZoomInIcon,
  SmartToy as RobotIcon,
  Build as ToolIcon,
  Psychology as ThinkingIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  PlayArrow as StartIcon,
  Analytics as AnalyticsIcon,
  Bolt as BoltIcon,
  RocketLaunch as RocketIcon,
  TaskAlt as CompleteIcon
} from '@mui/icons-material';
import { WorkflowStep, ToolExecution } from '../types';
import { useSelector } from 'react-redux';
import { useRouter } from 'next/navigation';
import type { RootState } from '../store';
import { formatTime, formatTimeWithSeconds } from '@/utils/dateFormat';

interface WorkflowPanelProps {
  className?: string;
  projectId?: string;
}

/**
 * Expandable description component that truncates long text and allows expansion
 */
const ExpandableDescription: React.FC<{ description: string }> = ({ description }) => {
  const [expanded, setExpanded] = useState(false);
  const [shouldTruncate, setShouldTruncate] = useState(false);
  const textRef = React.useRef<HTMLDivElement>(null);
  const muiTheme = useTheme();

  // Check if content is actually truncated by measuring the element
  React.useEffect(() => {
    if (textRef.current) {
      // Compare scrollHeight (actual content height) with clientHeight (visible height)
      const isTruncated = textRef.current.scrollHeight > textRef.current.clientHeight;
      setShouldTruncate(isTruncated);
    }
  }, [description]);

  return (
    <>
      <Typography
        ref={textRef}
        variant="body2"
        sx={{
          color: muiTheme.palette.text.secondary,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          overflowWrap: 'break-word',
          // Use CSS line-clamp for visual truncation when not expanded
          display: expanded ? 'block' : '-webkit-box',
          WebkitLineClamp: expanded ? 'unset' : 3,
          WebkitBoxOrient: 'vertical',
          overflow: expanded ? 'visible' : 'hidden',
          textOverflow: 'ellipsis'
        }}
      >
        {description}
      </Typography>
      {shouldTruncate && (
        <Typography
          component="span"
          onClick={() => setExpanded(!expanded)}
          sx={{
            color: muiTheme.palette.primary.main,
            cursor: 'pointer',
            fontSize: '0.75rem',
            fontWeight: 500,
            display: 'block',
            mt: 0.5,
            '&:hover': {
              textDecoration: 'underline'
            }
          }}
        >
          {expanded ? 'Show less' : 'Show more'}
        </Typography>
      )}
    </>
  );
};

/**
 * Separate component for visualization image to follow React Hooks rules.
 * Cannot use hooks inside .map() - must be in a component at the top level.
 */
const VisualizationImage: React.FC<{ viz: any }> = React.memo(({ viz }) => {
  const [imageUrl, setImageUrl] = React.useState<string>(viz.base64 || '');
  const [imageLoading, setImageLoading] = React.useState(!viz.base64);

  React.useEffect(() => {
    if (!viz.file_id || viz.base64) return;

    const fetchImage = async () => {
      try {
        // Dynamically import config to avoid SSR issues
        const { config } = await import('@/config');
        
        const token = localStorage.getItem('auth_token');
        const headers: Record<string, string> = {
          'Accept': 'image/*'
        };
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${config.api.baseUrl}/api/v1/files/${viz.file_id}/download`, {
          headers,
          credentials: 'include'
        });

        if (response.ok) {
          const blob = await response.blob();
          const blobUrl = URL.createObjectURL(blob);
          setImageUrl(blobUrl);
        } else {
          console.error('Failed to load image:', viz.file_id, response.status);
        }
      } catch (error) {
        console.error('Error fetching image:', error);
      } finally {
        setImageLoading(false);
      }
    };

    fetchImage();

    // Cleanup blob URL on unmount
    return () => {
      if (imageUrl && imageUrl.startsWith('blob:')) {
        URL.revokeObjectURL(imageUrl);
      }
    };
  }, [viz.file_id, viz.base64]);

  if (imageLoading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '200px' }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  return (
    <img
      src={imageUrl}
      alt={viz.title || 'Visualization'}
      style={{
        width: '100%',
        height: 'auto',
        minHeight: '200px',
        borderRadius: '8px',
        display: 'block',
        objectFit: 'contain'
      }}
      onError={(e) => {
        console.error('Failed to load image:', viz.file_id);
        e.currentTarget.style.display = 'none';
      }}
    />
  );
});

const WorkflowPanel: React.FC<WorkflowPanelProps> = ({ className = '', projectId }) => {
  const muiTheme = useTheme();
  const isVeryNarrow = useMediaQuery('(max-width:800px)');
  const router = useRouter();
  const workflowEndRef = useRef<HTMLDivElement>(null);

  // State for project files
  const [projectFiles, setProjectFiles] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [imageModalOpen, setImageModalOpen] = useState(false);
  const [selectedImage, setSelectedImage] = useState<any>(null);

  // Redux selectors
  const connectionStatus = useSelector((state: RootState) => state.websocket.connectionStatus);
  const isConnected = useSelector((state: RootState) => state.websocket.isConnected);
  const steps = useSelector((state: RootState) => state.websocket.workflowSteps);
  const progress = useSelector((state: RootState) => state.websocket.workflowProgress);
  const isActive = useSelector((state: RootState) => state.websocket.isWorkflowActive);
  const currentWorkflowId = useSelector((state: RootState) => state.websocket.currentWorkflowId);
  const workflowGroups = useSelector((state: RootState) => state.websocket.workflowGroups);
  const messageCount = useSelector((state: RootState) => state.websocket.totalMessages);
  const lastMessageTime = useSelector((state: RootState) => state.websocket.lastPingTime);
  const createdFiles = useSelector((state: RootState) => state.websocket.createdFiles) || [];
  
  const allFiles = [...projectFiles, ...createdFiles];

  // Load project files function
  const loadProjectFiles = useCallback(async () => {
    if (!projectId) return;
    
    try {
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`/api/v1/files/user`, {
        headers,
        credentials: 'include',
      });

      if (response.ok) {
        const result = await response.json();
        
        if (result.success && result.data) {
          const transformedFiles = result.data
            .filter((file: any) => file.project_id === projectId)
            .map((file: any) => ({
              id: file.id,
              name: file.original_filename,
              size: file.file_size,
              modified: file.updated_at,
              category: file.category,
              contentType: file.content_type,
              createdBy: file.created_by_agent
            }));
            
          setProjectFiles(transformedFiles);
          console.log(`✅ Loaded ${transformedFiles.length} files for project ${projectId}`);
        }
      } else {
        console.warn('Failed to load project files');
        setProjectFiles([]);
      }
    } catch (error) {
      console.error('Error loading project files:', error);
      setProjectFiles([]);
    }
  }, [projectId]);

  // File download handler
  const handleDownload = async (fileId: string, filename: string) => {
    try {
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {};
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`/api/v1/files/${fileId}/download`, {
        headers,
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error('Download failed');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      console.log(`✅ Downloaded ${filename}`);
    } catch (err) {
      console.error('Download error:', err);
    }
  };

  // Load project files when projectId changes
  useEffect(() => {
    loadProjectFiles();
  }, [loadProjectFiles]);
  
  // Reload files when workflow completes (to catch newly created files)
  useEffect(() => {
    if (!isActive && currentWorkflowId) {
      const timer = setTimeout(() => {
        console.log('🔄 Workflow completed, reloading project files');
        loadProjectFiles();
      }, 1000);
      
      return () => clearTimeout(timer);
    }
  }, [isActive, currentWorkflowId, loadProjectFiles]);

  // Auto scroll to bottom when new steps are added
  useEffect(() => {
    workflowEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [workflowGroups, steps]);

  // Icon display removed - using emojis from title instead
  // const getStepIcon = (step: WorkflowStep) => {
  //   // Function removed to reduce visual clutter
  // };

  const getStepIcon = (step: WorkflowStep) => {
    // Check title for specific workflow stages (V2 multi-agent system)
    if (step.title) {
      if (step.title.includes('Start Multi-Agent') || step.title.includes('Start LABOS')) {
        return <RocketIcon sx={{ fontSize: 14, color: 'white' }} />;
      }
      if (step.title.includes('Processing Complete') || step.title.includes('Complete')) {
        return <CompleteIcon sx={{ fontSize: 14, color: 'white' }} />;
      }
    }

    // Fallback to type-based icons
    switch (step.type) {
      case 'manager_start': return <RocketIcon sx={{ fontSize: 14, color: 'white' }} />;
      case 'workflow_complete': return <CompleteIcon sx={{ fontSize: 14, color: 'white' }} />;
      case 'agent_execution': return <RobotIcon sx={{ fontSize: 14, color: 'white' }} />;
      case 'tool_execution': return <ToolIcon sx={{ fontSize: 14, color: 'white' }} />;
      case 'thinking': return <ThinkingIcon sx={{ fontSize: 14, color: 'white' }} />;
      case 'api_call': return <ThunderboltIcon sx={{ fontSize: 14, color: 'white' }} />;
      case 'manager_synthesis': return <AnalyticsIcon sx={{ fontSize: 14, color: 'white' }} />;
      default: return <BoltIcon sx={{ fontSize: 14, color: 'white' }} />;
    }
  };
  
  const getStepColor = (step: WorkflowStep) => {
    // Check title for specific workflow stages (V2 multi-agent system)
    if (step.title) {
      if (step.title.includes('Processing Complete') || step.title.includes('Complete')) {
        return muiTheme.palette.success.main; // Green for completion
      }
      if (step.title.includes('Start Multi-Agent') || step.title.includes('Start LABOS')) {
        return muiTheme.palette.primary.main; // Blue for start
      }
    }

    // Fallback to type-based colors
    switch (step.type) {
      case 'manager_start': return muiTheme.palette.primary.main;
      case 'workflow_complete': return muiTheme.palette.success.main;
      case 'agent_execution': return muiTheme.palette.secondary.main;
      case 'tool_execution': return muiTheme.palette.info.main;
      case 'thinking': return muiTheme.palette.warning.light;
      case 'manager_synthesis': return muiTheme.palette.info.dark;
      default: return muiTheme.palette.grey[500];
    }
  };

  const getStepTitle = (step: WorkflowStep) => {
    if (step.title) return step.title;
    
    switch (step.type) {
      // New Agent-aware types
      case 'manager_start':
        return 'Manager Agent Started';
      case 'agent_execution':
        return step.agent_name || step.tool_name || 'Agent Execution';
      case 'manager_synthesis':
        return 'Manager Synthesis';
      case 'workflow_complete':
        return 'Workflow Complete';
      // Legacy types
      case 'thinking':
        return 'Thinking Analysis';
      case 'tool_execution':
        // Check if this is actually an agent (has agent_name)
        if (step.agent_name) {
          return step.agent_name;
        }
        return step.tool_name || 'Tool Execution';
      case 'synthesis':
        return 'Comprehensive Processing';
      case 'api_call':
        return 'API Call';
      default:
        return 'Processing';
    }
  };

  const renderExecutionSteps = () => (
    <Box sx={{ 
      p: isVeryNarrow ? 1 : 2,
      px: isVeryNarrow ? 0.5 : 2,
      bgcolor: muiTheme.palette.background.default 
    }}>
      {workflowGroups.length === 0 && steps.length === 0 ? (
        <Box sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          color: muiTheme.palette.text.secondary,
          pt: 8
        }}>
          <Typography variant="h2" sx={{ fontSize: '3rem', mb: 2, opacity: 0.3 }}>⚡</Typography>
          <Typography variant="h6" sx={{ color: muiTheme.palette.text.primary, mb: 1 }}>Waiting for Workflow</Typography>
          <Typography variant="body2" sx={{ textAlign: 'center', maxWidth: '250px', color: muiTheme.palette.text.secondary, fontSize: '0.875rem' }}>
            AI processing steps will appear here in real-time
          </Typography>
        </Box>
      ) : (
        <Stack spacing={0}>
          {workflowGroups.length > 0 ? (
            [...workflowGroups]
              .sort((a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime())
              .map((group: any, groupIndex: number) => (
              <Box key={group.workflowId} sx={{ mb: 4 }}>
                {groupIndex > 0 && (
                  <Box sx={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    my: 3,
                    opacity: 0.5
                  }}>
                    <Box sx={{ flex: 1, height: '1px', bgcolor: 'divider' }} />
                    <Typography variant="caption" sx={{ px: 2, color: 'text.secondary' }}>
                      {formatTime(group.startTime)}
                    </Typography>
                    <Box sx={{ flex: 1, height: '1px', bgcolor: 'divider' }} />
                  </Box>
                )}

                <Box sx={{ position: 'relative', pl: 2 }}>
                  {/* Continuous Line */}
                  <Box sx={{ 
                    position: 'absolute', 
                    left: 11, 
                    top: 12, 
                    bottom: -12, 
                    width: '2px', 
                    bgcolor: muiTheme.palette.divider,
                    zIndex: 0
                  }} />

                  {group.steps.map((step: any, stepIndex: number) => {
                    const stepColor = getStepColor(step);
                    
                    return (
                      <Box key={`${group.workflowId}-${stepIndex}`} sx={{ mb: 3, position: 'relative' }}>
                        {/* Timeline Dot */}
                        <Box sx={{ 
                          position: 'absolute', 
                          left: -20, 
                          top: 0, 
                          width: 24, 
                          height: 24, 
                          borderRadius: '50%', 
                          bgcolor: stepColor,
                          display: 'flex', 
                          alignItems: 'center', 
                          justifyContent: 'center',
                          zIndex: 1,
                          boxShadow: `0 0 0 4px ${muiTheme.palette.background.default}`
                        }}>
                          {getStepIcon(step)}
                        </Box>

                        {/* Content */}
                        <Box sx={{ pl: 2 }}>
                          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
                            <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'text.primary', lineHeight: 1.2 }}>
                              {getStepTitle(step)}
                            </Typography>
                            <Typography variant="caption" sx={{ color: 'text.secondary', whiteSpace: 'nowrap', fontSize: '0.7rem' }}>
                              {formatTimeWithSeconds(step.timestamp)}
                            </Typography>
                          </Stack>

                          <Box sx={{ mt: 1 }}>
                            {step.description && (
                              <Box sx={{ mb: 1 }}>
                                <ExpandableDescription description={step.description} />
                              </Box>
                            )}
                            
                            {/* Agent task display */}
                            {step.agent_task && (
                              <Paper variant="outlined" sx={{ p: 1.5, mb: 1.5, bgcolor: 'background.paper', borderRadius: 2 }}>
                                <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'primary.main', mb: 0.5, display: 'block' }}>
                                  TASK
                                </Typography>
                                <ExpandableDescription description={step.agent_task} />
                              </Paper>
                            )}
                            
                            {/* Tools used display */}
                            {step.tools_used && step.tools_used.length > 0 && (
                              <Box sx={{ mt: 1 }}>
                                {step.tools_used.map((tool: ToolExecution, toolIndex: number) => (
                                  <Paper key={toolIndex} variant="outlined" sx={{ p: 1, mb: 1, borderRadius: 2, borderColor: 'divider' }}>
                                    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                                      <Chip
                                        label={tool.name}
                                        size="small"
                                        color={tool.status === 'success' ? 'success' : 'error'}
                                        sx={{ fontSize: '0.65rem', height: 20 }}
                                      />
                                      {tool.duration && (
                                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                                          {tool.duration}s
                                        </Typography>
                                      )}
                                    </Stack>
                                    {tool.result && (
                                      <Box sx={{ mt: 0.5, fontSize: '0.8rem' }}>
                                        <ExpandableDescription description={tool.result} />
                                      </Box>
                                    )}
                                  </Paper>
                                ))}
                              </Box>
                            )}

                            {/* Legacy tool display */}
                            {step.tool_name && !step.tools_used && step.tool_name !== 'agent_thought' && (
                              <Typography variant="body2" sx={{ color: 'text.secondary', mb: 0.5, fontSize: '0.85rem' }}>
                                Used tool: <Box component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>{step.tool_name}</Box>
                              </Typography>
                            )}
                            
                            {/* Visualizations */}
                            {step.step_metadata?.visualizations && step.step_metadata.visualizations.length > 0 && (
                              <Box sx={{ mt: 1.5 }}>
                                <Stack spacing={1}>
                                  {step.step_metadata.visualizations.map((viz: any, vizIndex: number) => (
                                    <Paper 
                                      key={vizIndex}
                                      variant="outlined"
                                      sx={{ 
                                        p: 1, 
                                        cursor: 'pointer',
                                        bgcolor: 'background.paper',
                                        borderRadius: 2,
                                        overflow: 'hidden',
                                        '&:hover': { borderColor: 'primary.main' }
                                      }}
                                      onClick={() => {
                                        setSelectedImage({ ...viz });
                                        setImageModalOpen(true);
                                      }}
                                    >
                                      <Box sx={{ position: 'relative', minHeight: 150 }}>
                                        <VisualizationImage viz={viz} />
                                      </Box>
                                      <Typography variant="caption" sx={{ display: 'block', mt: 1, fontWeight: 600, textAlign: 'center' }}>
                                        {viz.title || 'Visualization'}
                                      </Typography>
                                    </Paper>
                                  ))}
                                </Stack>
                              </Box>
                            )}
                            
                            {/* Execution result */}
                            {step.execution_result && (
                              <Box sx={{ mt: 1, p: 1.5, bgcolor: 'action.hover', borderRadius: 2, borderLeft: `3px solid ${stepColor}` }}>
                                <ExpandableDescription description={step.execution_result} />
                              </Box>
                            )}
                            
                            {/* Observations */}
                            {step.observations && step.observations.length > 0 && (
                              <Box sx={{ mt: 1.5 }}>
                                <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'text.secondary', mb: 0.5, display: 'block' }}>
                                  OBSERVATIONS
                                </Typography>
                                <Box component="ul" sx={{ pl: 2, m: 0, color: 'text.secondary', fontSize: '0.8rem' }}>
                                  {step.observations.map((obs: any, i: number) => (
                                    <li key={i} style={{ marginBottom: 4 }}>
                                      {typeof obs === 'string' ? obs : `${obs.type}: ${obs.message}`}
                                    </li>
                                  ))}
                                </Box>
                              </Box>
                            )}
                            
                            {/* Metadata footer */}
                            {(step.duration || (step.input_tokens && step.output_tokens)) && (
                              <Stack direction="row" spacing={2} sx={{ mt: 1, opacity: 0.7 }}>
                                {step.duration && (
                                  <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                    <ClockIcon sx={{ fontSize: 12 }} /> {step.duration}ms
                                  </Typography>
                                )}
                                {step.input_tokens && step.output_tokens && (
                                  <Typography variant="caption">
                                    Tokens: {step.input_tokens} → {step.output_tokens}
                                  </Typography>
                                )}
                              </Stack>
                            )}
                          </Box>
                        </Box>
                      </Box>
                    );
                  })}
                </Box>
              </Box>
            ))
          ) : (
            // Legacy steps support
            steps.map((step: any, index: number) => (
              <Box key={index} sx={{ mb: 2, pl: 2, borderLeft: `2px solid ${muiTheme.palette.divider}` }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>{getStepTitle(step)}</Typography>
                <Typography variant="body2" color="text.secondary">{step.description}</Typography>
              </Box>
            ))
          )}
          
          <div ref={workflowEndRef} />
        </Stack>
      )}
    </Box>
  );

  const renderProjectFiles = () => (
    <Box sx={{ 
      height: '100%', 
      overflow: 'auto', 
      p: isVeryNarrow ? 1 : 2, 
      px: isVeryNarrow ? 0.5 : 2,
      bgcolor: muiTheme.palette.background.default 
    }}>
      {allFiles.length === 0 ? (
        <Box sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '200px',
          color: muiTheme.palette.text.secondary
        }}>
          <Typography variant="h2" sx={{ fontSize: '3rem', mb: 1, opacity: 0.3 }}>📁</Typography>
          <Typography variant="body2" sx={{ color: muiTheme.palette.text.secondary }}>
            No files in this project
          </Typography>
        </Box>
      ) : (
        <Stack spacing={isVeryNarrow ? 0.5 : 1}>
          {projectFiles.length > 0 && (
            <Box>
              <Typography variant="caption" sx={{ 
                color: muiTheme.palette.text.secondary,
                fontWeight: 'bold',
                mb: 1,
                display: 'block'
              }}>
                PROJECT FILES ({projectFiles.length})
              </Typography>
              {projectFiles.map((file: any, index: number) => (
                <Paper 
                  key={`project-${index}`} 
                  sx={{ 
                    p: isVeryNarrow ? 1 : 1.5, 
                    mb: 1,
                    bgcolor: muiTheme.palette.background.paper, 
                    border: `1px solid ${muiTheme.palette.divider}`,
                    cursor: 'pointer',
                    '&:hover': {
                      bgcolor: muiTheme.palette.action.hover,
                      borderColor: muiTheme.palette.primary.main
                    }
                  }}
                >
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <FileTextIcon sx={{ color: muiTheme.palette.primary.main }} />
                    <Box sx={{ flex: 1 }} onClick={(e) => e.stopPropagation()}>
                      <Typography variant="body2" sx={{ fontWeight: 'bold', color: muiTheme.palette.text.primary }}>
                        {file.name}
                      </Typography>
                      <Typography variant="caption" sx={{ color: muiTheme.palette.text.secondary }}>
                        {Math.round((file.size || 0) / 1024)}KB • {file.contentType || 'Unknown type'}
                      </Typography>
                    </Box>
                    <Stack direction="row" spacing={0.5}>
                      <IconButton
                        size="small"
                        onClick={(e: any) => {
                          e.stopPropagation();
                          handleDownload(file.id, file.name);
                        }}
                        sx={{ color: muiTheme.palette.primary.main }}
                      >
                        <DownloadIcon sx={{ fontSize: '16px' }} />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={(e: any) => {
                          e.stopPropagation();
                          router.push('/files');
                        }}
                        sx={{ color: muiTheme.palette.text.secondary }}
                      >
                        <LaunchIcon sx={{ fontSize: '16px' }} />
                      </IconButton>
                    </Stack>
                  </Stack>
                </Paper>
              ))}
            </Box>
          )}
          
          {createdFiles.length > 0 && (
            <Box>
              <Typography variant="caption" sx={{ 
                color: muiTheme.palette.text.secondary,
                fontWeight: 'bold',
                mb: 1,
                display: 'block'
              }}>
                WORKFLOW CREATED ({createdFiles.length})
              </Typography>
              {createdFiles.map((file: any, index: number) => (
                <Paper 
                  key={`workflow-${index}`} 
                  sx={{ 
                    p: isVeryNarrow ? 1 : 1.5, 
                    mb: 1,
                    bgcolor: muiTheme.palette.background.paper, 
                    border: `1px solid ${muiTheme.palette.divider}`,
                    borderLeft: `3px solid ${muiTheme.palette.success.main}`
                  }}
                >
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <FileTextIcon sx={{ color: muiTheme.palette.success.main }} />
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 'bold', color: muiTheme.palette.text.primary }}>
                        {file.name || file.filename}
                      </Typography>
                      <Typography variant="caption" sx={{ color: muiTheme.palette.text.secondary }}>
                        {file.path} • {file.size || 'Unknown size'} • Just created
                      </Typography>
                    </Box>
                    <Chip 
                      label="NEW" 
                      size="small" 
                      color="success" 
                      sx={{ fontSize: '0.75rem' }}
                    />
                  </Stack>
                </Paper>
              ))}
            </Box>
          )}
        </Stack>
      )}
    </Box>
  );

  const renderMain = () => (
    <Box 
        sx={{ 
          height: '100%', 
          display: 'flex', 
          flexDirection: 'column', 
          bgcolor: muiTheme.palette.background.default, 
          color: muiTheme.palette.text.primary,
          border: `1px solid ${muiTheme.palette.divider}`,
          minWidth: isVeryNarrow ? 250 : 350,
          className 
        }}>
        <Paper sx={{ 
          p: isVeryNarrow ? 1 : 2, 
          borderBottom: `1px solid ${muiTheme.palette.divider}`, 
          bgcolor: muiTheme.palette.background.paper,
          borderRadius: 0
        }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <ThunderboltIcon sx={{ color: muiTheme.palette.primary.main }} />
            <Typography variant="h6" sx={{ fontWeight: 'bold', color: muiTheme.palette.text.primary }}>
              LabOS AI Workflow
            </Typography>
          </Stack>
        </Paper>

      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: isVeryNarrow ? 250 : 350, minHeight: 0 }}>
        <Tabs 
          value={activeTab} 
          onChange={(_, newValue) => setActiveTab(newValue)}
          variant="standard"
          sx={{ 
            borderBottom: `1px solid ${muiTheme.palette.divider}`,
            bgcolor: muiTheme.palette.background.paper,
            minHeight: 48,
            '& .MuiTab-root': {
              color: muiTheme.palette.text.secondary,
              fontSize: '0.875rem',
              minWidth: 80,
              minHeight: 48,
              padding: isVeryNarrow ? '8px 12px' : '12px 16px',
              '&.Mui-selected': {
                color: muiTheme.palette.primary.main
              }
            },
            '& .MuiTabs-indicator': {
              backgroundColor: muiTheme.palette.primary.main
            }
          }}
        >
          <Tab
            icon={<ThunderboltIcon sx={{ fontSize: '20px' }} />}
            label="Steps"
            iconPosition="start"
          />
          <Tab 
            icon={<FileTextIcon sx={{ fontSize: '20px' }} />} 
            label="Files"
            iconPosition="start"
          />
          <Tab 
            icon={<SettingsIcon sx={{ fontSize: '20px' }} />} 
            label="Status"
            iconPosition="start"
          />
        </Tabs>
        
        <Box sx={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
          {activeTab === 0 && renderExecutionSteps()}
          {activeTab === 1 && renderProjectFiles()}
          {activeTab === 2 && (
            <Box sx={{ height: '100%', overflow: 'auto', p: 2, bgcolor: muiTheme.palette.background.default }}>
              <Stack spacing={2}>
                <Paper sx={{ p: 1.5, bgcolor: muiTheme.palette.background.paper, border: `1px solid ${muiTheme.palette.divider}` }}>
                  <Typography variant="body2" sx={{ fontWeight: 'bold', color: muiTheme.palette.text.primary, mb: 1 }}>
                    Connection Status
                  </Typography>
                  <Stack spacing={1}>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" sx={{ color: muiTheme.palette.text.secondary }}>WebSocket Connection:</Typography>
                      <Chip 
                        icon={<Box sx={{ 
                          width: 8, 
                          height: 8, 
                          borderRadius: '50%', 
                          bgcolor: isConnected ? muiTheme.palette.success.main : muiTheme.palette.error.main 
                        }} />}
                        label={isConnected ? "Connected" : "Disconnected"}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: '0.75rem' }}
                      />
                    </Stack>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" sx={{ color: muiTheme.palette.text.secondary }}>Messages Received:</Typography>
                      <Typography variant="body2" sx={{ color: muiTheme.palette.text.primary }}>{messageCount}</Typography>
                    </Stack>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" sx={{ color: muiTheme.palette.text.secondary }}>Last Message:</Typography>
                      <Typography variant="caption" sx={{ color: muiTheme.palette.text.primary }}>
                        {lastMessageTime ? formatTime(lastMessageTime) : 'No messages'}
                      </Typography>
                    </Stack>
                  </Stack>
                </Paper>
              </Stack>
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );

  return (
    <>
      {renderMain()}
      
      {/* Image zoom modal */}
    <Dialog 
      open={imageModalOpen} 
      onClose={() => setImageModalOpen(false)}
      maxWidth="lg"
      fullWidth
    >
      <DialogTitle>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">
            {selectedImage?.title || 'Visualization'}
          </Typography>
          <IconButton onClick={() => setImageModalOpen(false)} size="small">
            <CloseIcon />
          </IconButton>
        </Stack>
      </DialogTitle>
      <DialogContent>
        {selectedImage && (
          <Box>
            <Box sx={{ borderRadius: '8px', overflow: 'hidden' }}>
              <VisualizationImage viz={selectedImage} />
            </Box>
            {selectedImage.chart_type && (
              <Typography variant="caption" sx={{ mt: 1, display: 'block', color: muiTheme.palette.text.secondary }}>
                Type: {selectedImage.chart_type}
                {selectedImage.filename && ` | File: ${selectedImage.filename}`}
              </Typography>
            )}
          </Box>
        )}
      </DialogContent>
    </Dialog>
  </>
  );
};

export default WorkflowPanel;