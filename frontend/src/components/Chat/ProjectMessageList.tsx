'use client'

import React, { useEffect, useRef } from 'react';
import Image from 'next/image';
import {
  Box,
  Paper,
  Typography,
  useTheme,
  CircularProgress,
  Avatar,
  Stack,
  Card,
  CardContent,
  Link,
  Fade,
  Chip
} from '@mui/material';
import {
  Description as DescriptionIcon,
  Biotech as BiotechIcon,
  Analytics as AnalyticsIcon,
  Person as PersonIcon,
  SmartToy as BotIcon,
  ContentCopy as CopyIcon,
  InsertDriveFile as FileIcon
} from '@mui/icons-material';
import dynamic from 'next/dynamic';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { formatTime } from '@/utils/dateFormat';

// Dynamically import ReactMarkdown to avoid SSR issues
const Markdown = dynamic(() => import('react-markdown'), {
  ssr: false,
  loading: () => <Typography>Loading...</Typography>
});

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: string;
  metadata?: any;
}

interface ProjectMessageListProps {
  messages: Message[];
  isLoading?: boolean;
  projectName?: string;
  onExampleClick?: (message: string) => void;
}

// Reference interface
interface Reference {
  number: string;
  citation: string;
  url?: string;
}

// Parse references from message content
const parseReferences = (content: string): { hasReferences: boolean; references: Reference[]; mainContent: string } => {
  // Check if there's a References section
  const refMatch = content.match(/##\s*References\s*\n([\s\S]*)/i);

  if (!refMatch) {
    return { hasReferences: false, references: [], mainContent: content };
  }

  // Extract references section
  const refSection = refMatch[1];
  const references: Reference[] = [];

  // Match pattern: [1] Author... \n  https://...
  // Split by [number] pattern
  const refItems = refSection.split(/\n(?=\[\d+\])/);

  for (const item of refItems) {
    const match = item.match(/\[(\d+)\]\s*([^\n]+)(?:\n\s*(https?:\/\/[^\s]+))?/);
    if (match) {
      references.push({
        number: match[1],
        citation: match[2].trim(),
        url: match[3]
      });
    }
  }

  // Remove References section from main content
  const mainContent = content.replace(/##\s*References[\s\S]*$/i, '').trim();

  return { hasReferences: true, references, mainContent };
};

const ProjectMessageList: React.FC<ProjectMessageListProps> = ({
  messages,
  isLoading = false,
  projectName,
  onExampleClick
}) => {
  const muiTheme = useTheme();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [loadingDuration, setLoadingDuration] = React.useState(0);

  // Auto-scroll to bottom when messages change or loading state changes
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  // Track loading duration
  useEffect(() => {
    if (isLoading) {
      setLoadingDuration(0);
      const interval = setInterval(() => {
        setLoadingDuration(prev => prev + 1);
      }, 1000);
      return () => clearInterval(interval);
    } else {
      setLoadingDuration(0);
    }
  }, [isLoading]);

  // Example prompts for users to get started
  const examplePrompts = [
    {
      icon: <DescriptionIcon />,
      title: "Generate DNA Data",
      prompt: "Generate a CSV file with 10 random DNA sequences"
    },
    {
      icon: <BiotechIcon />,
      title: "Search Research Papers",
      prompt: "Search for recent papers about CRISPR gene editing"
    },
    {
      icon: <AnalyticsIcon />,
      title: "DNA Composition Analysis",
      prompt: "Plot a bar chart showing the frequency of each nucleotide (A, C, G, T) in a DNA sequence"
    }
  ];

  // Render message with modern bubble style
  const renderMessage = (msg: Message) => {
    const isUser = msg.type === 'user';
    const attachedFiles = msg.metadata?.attached_files || [];
    
    return (
      <Box
        key={msg.id}
        sx={{
          mb: 3,
          display: 'flex',
          flexDirection: isUser ? 'row' : 'row',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          alignItems: 'flex-end', // Align items to the bottom
          gap: 2,
          px: { xs: 1, md: 2 }
        }}
      >
        {/* Assistant Avatar (Left) - Removed for cleaner UI */}
        {/* {!isUser && (
          <Avatar
            sx={{
              background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', // Modern gradient
              color: 'white',
              width: 36,
              height: 36,
              mb: 3, // Adjusted for better vertical alignment with bottom of bubble
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)' // Subtle shadow
            }}
          >
            <BotIcon fontSize="small" />
          </Avatar>
        )} */}

        <Box sx={{ 
          maxWidth: { xs: '85%', md: '75%' }, 
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: isUser ? 'flex-end' : 'flex-start'
        }}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              borderRadius: isUser ? '20px 20px 4px 20px' : '20px 20px 20px 4px',
              bgcolor: isUser 
                ? muiTheme.palette.primary.main 
                : muiTheme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'grey.50',
              color: isUser ? 'white' : 'text.primary',
              position: 'relative',
              border: isUser ? 'none' : `1px solid ${muiTheme.palette.divider}`
            }}
          >
            {/* Attached Files Display */}
            {attachedFiles.length > 0 && (
              <Stack direction="column" spacing={1} sx={{ mb: 1 }}>
                {attachedFiles.map((file: any, index: number) => (
                  <Box key={index} sx={{ display: 'flex' }}>
                    <Chip
                      icon={<FileIcon sx={{ fontSize: 16 }} />}
                      label={`${file.filename} (${file.size >= 1024 * 1024 ? `${(file.size / (1024 * 1024)).toFixed(1)}MB` : `${Math.round(file.size / 1024)}KB`})`}
                      variant="outlined"
                      size="small"
                      sx={{
                        color: 'inherit',
                        borderColor: isUser ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.12)',
                        bgcolor: isUser ? 'rgba(0,0,0,0.1)' : 'rgba(0,0,0,0.05)',
                        '& .MuiChip-icon': { color: 'inherit' },
                        maxWidth: '100%',
                        height: 28
                      }}
                    />
                  </Box>
                ))}
              </Stack>
            )}

          {msg.type === 'assistant' ? (
            // Render AI messages as Markdown
            (() => {
              const { hasReferences, references, mainContent } = parseReferences(msg.content);

              return (
                <Box
                    sx={{
                      // Prevent long strings (like DNA sequences) from breaking layout
                      wordBreak: 'break-word',
                      overflowWrap: 'break-word',
                      '& h1, & h2, & h3, & h4, & h5, & h6': {
                        color: 'inherit',
                        fontWeight: 'bold',
                        mt: 2,
                        mb: 1,
                        '&:first-of-type': { mt: 0 }
                      },
                      '& h1': { fontSize: '1.5rem' },
                      '& h2': { fontSize: '1.3rem' },
                      '& h3': { fontSize: '1.2rem' },
                '& p': {
                  color: 'inherit',
                  lineHeight: 1.6,
                  mb: 1,
                  '&:last-child': { mb: 0 },
                  wordBreak: 'break-word',
                  overflowWrap: 'break-word'
                },
                '& ul, & ol': {
                  color: 'inherit',
                  pl: 2,
                  mb: 1
                },
                '& li': {
                  mb: 0.5,
                  wordBreak: 'break-word',
                  overflowWrap: 'break-word'
                },
                '& code': {
                  bgcolor: muiTheme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)',
                  color: 'inherit',
                  px: 0.5,
                  py: 0.25,
                  borderRadius: 0.5,
                  fontSize: '0.875rem',
                  fontFamily: 'monospace',
                  wordBreak: 'break-all',
                  overflowWrap: 'break-word'
                },
                '& pre': {
                  bgcolor: muiTheme.palette.mode === 'dark' ? 'rgba(0,0,0,0.3)' : '#f8f9fa',
                  color: muiTheme.palette.text.primary,
                  p: 1.5,
                  borderRadius: 1,
                  overflow: 'auto',
                  mb: 1,
                  border: `1px solid ${muiTheme.palette.divider}`,
                  '& code': {
                    bgcolor: 'transparent',
                    color: 'inherit',
                    p: 0,
                    wordBreak: 'break-all',
                    overflowWrap: 'break-word'
                  }
                },
                '& blockquote': {
                  borderLeft: `3px solid ${muiTheme.palette.primary.main}`,
                  pl: 2,
                  ml: 0,
                  color: muiTheme.palette.text.secondary,
                  fontStyle: 'italic',
                  wordBreak: 'break-word',
                  overflowWrap: 'break-word'
                },
                '& strong': {
                  fontWeight: 'bold',
                  color: 'inherit'
                },
                // Link styling handled by Markdown components below
                    }}
                  >
                    <Markdown
                      remarkPlugins={[remarkGfm, remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                      components={{
                        // Make all links open in new tab with proper styling
                        a: ({node, ...props}) => (
                          <a
                            {...props}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              color: muiTheme.palette.primary.main,
                              textDecoration: 'underline',
                              cursor: 'pointer'
                            }}
                          />
                        ),
                        // Style inline code
                        code: ({node, inline, ...props}: any) => (
                          <code
                            {...props}
                            style={{
                              backgroundColor: muiTheme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)',
                              padding: inline ? '2px 6px' : '0',
                              borderRadius: inline ? '3px' : '0',
                              fontFamily: 'monospace',
                              fontSize: inline ? '0.9em' : '1em'
                            }}
                          />
                        ),
                        // Style code blocks (pre wraps code)
                        pre: ({node, ...props}: any) => (
                          <pre
                            {...props}
                            style={{
                              backgroundColor: muiTheme.palette.mode === 'dark' ? 'rgba(0,0,0,0.3)' : '#f8f9fa',
                              padding: '12px',
                              borderRadius: '6px',
                              overflow: 'auto',
                              margin: '8px 0',
                              border: `1px solid ${muiTheme.palette.divider}`
                            }}
                          />
                        )
                      }}
                    >
                      {mainContent}
                    </Markdown>

                  {/* Reference Cards - displayed below the answer */}
                  {hasReferences && references.length > 0 && (
                    <Box sx={{ mt: 2, pt: 2, borderTop: `1px solid ${muiTheme.palette.divider}` }}>
                      <Typography variant="caption" sx={{ color: 'text.secondary', mb: 1, display: 'block', fontWeight: 'bold' }}>
                        REFERENCES
                      </Typography>
                      <Stack spacing={1}>
                        {references.map((ref) => (
                          <Card
                            key={ref.number}
                            elevation={0}
                            sx={{
                              bgcolor: muiTheme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'white',
                              border: `1px solid ${muiTheme.palette.divider}`,
                              cursor: ref.url ? 'pointer' : 'default',
                              transition: 'all 0.2s',
                              '&:hover': ref.url ? {
                                borderColor: muiTheme.palette.primary.main,
                                transform: 'translateY(-2px)'
                              } : {}
                            }}
                            onClick={() => ref.url && window.open(ref.url, '_blank')}
                          >
                            <CardContent sx={{ py: 1, px: 2, '&:last-child': { pb: 1 } }}>
                              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                                <Typography
                                  variant="caption"
                                  sx={{
                                    color: muiTheme.palette.primary.main,
                                    fontWeight: 'bold',
                                    minWidth: '24px'
                                  }}
                                >
                                  [{ref.number}]
                                </Typography>
                                <Box sx={{ flex: 1 }}>
                                  <Typography variant="body2" sx={{ mb: 0, fontSize: '0.8rem', color: 'text.primary' }}>
                                    {ref.citation}
                                  </Typography>
                                  {ref.url && (
                                    <Link
                                      href={ref.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      sx={{
                                        fontSize: '0.7rem',
                                        color: muiTheme.palette.primary.main,
                                        textDecoration: 'none',
                                        '&:hover': {
                                          textDecoration: 'underline'
                                        }
                                      }}
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      {ref.url.length > 60 ? ref.url.substring(0, 60) + '...' : ref.url}
                                    </Link>
                                  )}
                                </Box>
                              </Box>
                            </CardContent>
                          </Card>
                        ))}
                      </Stack>
                    </Box>
                  )}

                  {/* Follow-up Questions - displayed below references */}
                  {msg.metadata?.follow_up_questions && msg.metadata.follow_up_questions.length > 0 && (
                    <Box sx={{ mt: 2, pt: 2, borderTop: `1px solid ${muiTheme.palette.divider}` }}>
                      <Typography variant="caption" sx={{ color: 'text.secondary', mb: 1.5, display: 'block', fontWeight: 'bold' }}>
                        SUGGESTED QUESTIONS
                      </Typography>
                      <Stack direction="row" flexWrap="wrap" gap={1}>
                        {msg.metadata.follow_up_questions.map((question: string, index: number) => (
                          <Chip
                            key={index}
                            label={question}
                            onClick={() => onExampleClick?.(question)}
                            clickable
                            variant="outlined"
                            size="small"
                            sx={{
                              borderColor: muiTheme.palette.primary.main,
                              color: muiTheme.palette.primary.main,
                              transition: 'all 0.15s ease-in-out',
                              '&:hover': {
                                bgcolor: 'rgba(25, 118, 210, 0.08)',
                                borderColor: muiTheme.palette.primary.dark,
                              },
                              '&:active': {
                                bgcolor: 'rgba(25, 118, 210, 0.16)',
                                transform: 'scale(0.98)',
                              },
                              maxWidth: '100%',
                              height: 'auto',
                              '& .MuiChip-label': {
                                whiteSpace: 'normal',
                                py: 0.5,
                              }
                            }}
                          />
                        ))}
                      </Stack>
                    </Box>
                  )}
                </Box>
              );
            })()
          ) : (
            // Render user messages as plain text
            <Typography 
              variant="body1" 
              sx={{ 
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                color: 'inherit',
                lineHeight: 1.6
              }}
            >
              {msg.content}
            </Typography>
          )}
          </Paper>
          
          {/* Timestamp outside bubble */}
          <Typography 
            variant="caption" 
            sx={{ 
              color: muiTheme.palette.text.secondary, 
              mt: 0.5, 
              mx: 1,
              fontSize: '0.7rem',
              opacity: 0.8
            }}
          >
            {formatTime(msg.timestamp)}
          </Typography>
        </Box>

        {/* User Avatar (Right) - Removed for cleaner UI */}
        {/* {isUser && (
          <Avatar
            sx={{
              bgcolor: muiTheme.palette.primary.main,
              width: 36,
              height: 36,
              mb: 3 // Adjusted for better vertical alignment with bottom of bubble
            }}
          >
            <PersonIcon fontSize="small" />
          </Avatar>
        )} */}
      </Box>
    );
  };

  return (
    <Box sx={{
      flex: 1,
      overflow: 'auto',
      p: 2.5,
      bgcolor: muiTheme.palette.background.default
    }}>
      {isLoading && messages.length === 0 ? (
        // Show loading state when loading history
        <Box sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 300,
          color: muiTheme.palette.text.secondary
        }}>
          <CircularProgress size={40} sx={{ mb: 2 }} />
          <Typography variant="body1">Loading...</Typography>
        </Box>
      ) : messages.length === 0 && !isLoading ? (
        // Only show welcome when no messages AND not loading
        <Box sx={{
          textAlign: 'center',
          color: muiTheme.palette.text.secondary,
          mt: 5
        }}>
          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
            <Image
              src="/logo.png"
              alt="LabOS AI Logo"
              width={120}
              height={120}
              style={{ borderRadius: '16px' }}
            />
          </Box>
          <Typography variant="h5" sx={{ mb: 1, fontWeight: 'medium', color: muiTheme.palette.text.secondary }}>
            Welcome to {projectName || 'Your Project'}
          </Typography>
          <Typography variant="body2" sx={{ color: muiTheme.palette.text.secondary, mb: 4 }}>
            Start chatting with LabOS AI or try one of these examples
          </Typography>

          {/* Example Prompts */}
          <Stack 
            direction={{ xs: 'column', sm: 'row' }} 
            spacing={2} 
            justifyContent="center"
            sx={{ mt: 3, maxWidth: 900, mx: 'auto' }}
          >
            {examplePrompts.map((example, index) => (
              <Paper
                key={index}
                elevation={0}
                sx={{
                  p: 2.5,
                  flex: 1,
                  cursor: onExampleClick ? 'pointer' : 'default',
                  border: `1px solid ${muiTheme.palette.divider}`,
                  borderRadius: 2,
                  transition: 'all 0.2s',
                  '&:hover': onExampleClick ? {
                    borderColor: muiTheme.palette.primary.main,
                    transform: 'translateY(-2px)',
                    boxShadow: muiTheme.shadows[4]
                  } : {}
                }}
                onClick={() => onExampleClick?.(example.prompt)}
              >
                <Box sx={{ 
                  color: muiTheme.palette.primary.main, 
                  mb: 1.5,
                  display: 'flex',
                  justifyContent: 'center'
                }}>
                  {example.icon}
                </Box>
                <Typography 
                  variant="subtitle2" 
                  sx={{ 
                    fontWeight: 'bold', 
                    mb: 1,
                    color: muiTheme.palette.text.primary
                  }}
                >
                  {example.title}
                </Typography>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    color: muiTheme.palette.text.secondary,
                    fontSize: '0.85rem',
                    lineHeight: 1.5
                  }}
                >
                  {example.prompt}
                </Typography>
              </Paper>
            ))}
          </Stack>
        </Box>
      ) : (
        <>
          {/* Show messages if any exist */}
          {messages.length > 0 && (
            <Box sx={{ pb: 2 }}>
              {messages.map(renderMessage)}
            </Box>
          )}

          {/* Show loading indicator when processing */}
          {isLoading && (
            <Box sx={{ textAlign: 'center', p: 2.5 }}>
              <CircularProgress size={40} sx={{ color: muiTheme.palette.primary.main }} />
              <Typography variant="body2" sx={{ color: muiTheme.palette.text.secondary, mt: 1.5 }}>
                {loadingDuration < 30 && 'LabOS is thinking...'}
                {loadingDuration >= 30 && loadingDuration < 60 && `LabOS is thinking... (${loadingDuration}s)`}
                {loadingDuration >= 60 && loadingDuration < 300 && `Still processing... (${Math.floor(loadingDuration / 60)}m ${loadingDuration % 60}s)`}
                {loadingDuration >= 300 && `Processing... (${Math.floor(loadingDuration / 60)}m ${loadingDuration % 60}s)`}
              </Typography>
              {loadingDuration >= 60 && loadingDuration < 300 && (
                <Typography variant="caption" sx={{ color: muiTheme.palette.text.disabled, mt: 0.5, display: 'block' }}>
                  Complex queries may take longer. Please wait...
                </Typography>
              )}
              {loadingDuration >= 300 && (
                <Typography
                  variant="body2"
                  sx={{
                    color: muiTheme.palette.warning.main,
                    mt: 1.5,
                    display: 'block',
                    fontWeight: 600
                  }}
                >
                  If the workflow hasn't updated for a while, you can refresh the page and try again.
                </Typography>
              )}
            </Box>
          )}

          {/* Invisible element at the end for auto-scrolling */}
          <div ref={messagesEndRef} />
        </>
      )}
    </Box>
  );
};

export default ProjectMessageList;
