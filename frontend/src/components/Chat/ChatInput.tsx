'use client'

import React, { useState, useRef } from 'react';
import {
  TextField,
  IconButton,
  Button,
  Paper,
  useTheme,
  Stack,
  Chip,
  Box,
  Typography,
  Tooltip,
  alpha
} from '@mui/material';
import {
  Send as SendIcon,
  AttachFile as AttachFileIcon,
  Close as CloseIcon,
  Stop as StopIcon,
  Bolt as BoltIcon,
  Psychology as PsychologyIcon
} from '@mui/icons-material';

// File upload limits
const MAX_FILES = 5;
const MAX_FILE_SIZES = {
  video: 100 * 1024 * 1024,   // 100MB for video
  image: 50 * 1024 * 1024,    // 50MB for images
  pdf: 100 * 1024 * 1024,     // 100MB for PDFs
  default: 50 * 1024 * 1024   // 50MB default
};

const getMaxFileSize = (file: File): number => {
  if (file.type.startsWith('video/')) return MAX_FILE_SIZES.video;
  if (file.type.startsWith('image/')) return MAX_FILE_SIZES.image;
  if (file.type === 'application/pdf') return MAX_FILE_SIZES.pdf;
  return MAX_FILE_SIZES.default;
};

const getFileIcon = (file: File): string => {
  if (file.type.startsWith('video/')) return '🎥';
  if (file.type.startsWith('image/')) return '🖼️';
  if (file.type === 'application/pdf') return '📄';
  return '📎';
};

const formatFileSize = (size: number): string => {
  if (size >= 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(1)}MB`;
  }
  return `${Math.round(size / 1024)}KB`;
};

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  onSendMessageWithFiles?: (message: string, files: File[]) => void;
  onStopProcessing?: () => void;
  isLoading?: boolean;
  placeholder?: string;
  mode?: 'fast' | 'deep';
  onModeChange?: (mode: 'fast' | 'deep') => void;
}

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  onSendMessageWithFiles,
  onStopProcessing,
  isLoading = false,
  placeholder = "Ask LabOS...",
  mode = 'deep',
  onModeChange
}) => {
  const muiTheme = useTheme();
  const [inputValue, setInputValue] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    if (inputValue.trim() && !isLoading) {
      if (selectedFiles.length > 0 && onSendMessageWithFiles) {
        onSendMessageWithFiles(inputValue.trim(), selectedFiles);
      } else {
        onSendMessage(inputValue.trim());
      }
      setInputValue('');
      setSelectedFiles([]);
    }
  };

  // Validate and add files
  const addFiles = (newFiles: File[]) => {
    const currentCount = selectedFiles.length;
    const availableSlots = MAX_FILES - currentCount;

    if (availableSlots <= 0) {
      alert(`Maximum ${MAX_FILES} files allowed`);
      return;
    }

    const filesToAdd: File[] = [];
    const errors: string[] = [];

    for (let i = 0; i < Math.min(newFiles.length, availableSlots); i++) {
      const file = newFiles[i];
      const maxSize = getMaxFileSize(file);
      const maxSizeMB = maxSize / (1024 * 1024);

      if (file.size > maxSize) {
        errors.push(`${file.name}: exceeds ${maxSizeMB}MB limit`);
      } else {
        // Check for duplicates
        const isDuplicate = selectedFiles.some(f => f.name === file.name && f.size === file.size);
        if (!isDuplicate) {
          filesToAdd.push(file);
        }
      }
    }

    if (newFiles.length > availableSlots) {
      errors.push(`Only ${availableSlots} more file(s) can be added (max ${MAX_FILES})`);
    }

    if (errors.length > 0) {
      alert(errors.join('\n'));
    }

    if (filesToAdd.length > 0) {
      setSelectedFiles(prev => [...prev, ...filesToAdd]);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      addFiles(Array.from(files));
    }
    // Reset input so same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleRemoveAllFiles = () => {
    setSelectedFiles([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleAttachClick = () => {
    fileInputRef.current?.click();
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  // Handle drag and drop
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      addFiles(Array.from(files));
    }
  };

  // Handle paste
  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData.items;
    const filesToAdd: File[] = [];

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === 'file') {
        const file = item.getAsFile();
        if (file) {
          filesToAdd.push(file);
        }
      }
    }

    if (filesToAdd.length > 0) {
      e.preventDefault();
      addFiles(filesToAdd);
    }
  };

  return (
    <Box sx={{
      p: 2,
      borderTop: `1px solid ${muiTheme.palette.divider}`,
      bgcolor: muiTheme.palette.background.paper
    }}>
      {/* File Attachments Display */}
      {selectedFiles.length > 0 && (
        <Box sx={{ mb: 1.5, mx: 1 }}>
          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ gap: 0.5 }}>
            {selectedFiles.map((file, index) => (
              <Chip
                key={`${file.name}-${index}`}
                label={`${getFileIcon(file)} ${file.name} (${formatFileSize(file.size)})`}
                onDelete={() => handleRemoveFile(index)}
                deleteIcon={<CloseIcon />}
                variant="outlined"
                size="small"
                sx={{
                  maxWidth: 200,
                  borderColor: muiTheme.palette.primary.main,
                  bgcolor: muiTheme.palette.action.hover,
                  color: muiTheme.palette.primary.main,
                  '& .MuiChip-label': {
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  },
                  '& .MuiChip-deleteIcon': {
                    color: muiTheme.palette.primary.main,
                    opacity: 0.7,
                    '&:hover': { opacity: 1 }
                  }
                }}
              />
            ))}
            {selectedFiles.length > 1 && (
              <Chip
                label="Clear all"
                onClick={handleRemoveAllFiles}
                size="small"
                sx={{
                  bgcolor: muiTheme.palette.error.light,
                  color: 'white',
                  '&:hover': { bgcolor: muiTheme.palette.error.main }
                }}
              />
            )}
          </Stack>
          <Typography variant="caption" sx={{ color: 'text.secondary', mt: 0.5, display: 'block' }}>
            {selectedFiles.length}/{MAX_FILES} files
          </Typography>
        </Box>
      )}

      {/* Hidden File Input - now supports multiple */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        style={{ display: 'none' }}
        multiple
        accept=".txt,.pdf,.doc,.docx,.csv,.json,.md,.py,.js,.ts,.html,.css,.mp4,.webm,.mov,.avi,.mkv,.m4v,.png,.jpg,.jpeg,.gif,.webp,.svg,video/*,image/*"
      />

      <Box
        className="message-input-area"
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        sx={{
          position: 'relative',
          border: `1px solid ${isDragging ? muiTheme.palette.primary.main : muiTheme.palette.divider}`,
          borderRadius: 2,
          bgcolor: isDragging ? alpha(muiTheme.palette.primary.main, 0.05) : muiTheme.palette.background.default,
          transition: 'all 0.2s',
          '&:focus-within': {
            borderColor: muiTheme.palette.primary.main,
            boxShadow: `0 0 0 2px ${muiTheme.palette.action.hover}`
          },
          display: 'flex',
          flexDirection: 'column'
        }}>
        <TextField
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          onPaste={handlePaste}
          placeholder={placeholder}
          multiline
          maxRows={6}
          disabled={isLoading}
          fullWidth
          variant="standard" // Remove default border
          InputProps={{
            disableUnderline: true,
            sx: {
              p: 1.5,
              pb: 6, // Leave space for bottom controls
              fontSize: '0.95rem',
              lineHeight: 1.5,
            }
          }}
        />

        {/* Bottom Toolbar inside the input box */}
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          sx={{
            position: 'absolute',
            bottom: 4,
            left: 4,
            right: 4
          }}
        >
          <Stack direction="row" spacing={1}>
            <Tooltip title={`Attach files (${selectedFiles.length}/${MAX_FILES})`}>
              <IconButton
                onClick={handleAttachClick}
                disabled={isLoading || selectedFiles.length >= MAX_FILES}
                size="small"
                sx={{
                  color: selectedFiles.length >= MAX_FILES ? muiTheme.palette.action.disabled : muiTheme.palette.text.secondary,
                  bgcolor: 'transparent',
                  '&:hover': { color: muiTheme.palette.primary.main, bgcolor: muiTheme.palette.action.hover }
                }}
              >
                <AttachFileIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>

          <Stack direction="row" spacing={1} alignItems="center">
            {/* Mode Toggle - compact pill buttons */}
            {onModeChange && (
              <Box
                sx={{
                  bgcolor: alpha(muiTheme.palette.background.paper, 0.6),
                  borderRadius: 3,
                  border: `1px solid ${alpha(muiTheme.palette.divider, 0.2)}`,
                  p: 0.4,
                  display: 'flex',
                  gap: 0.4
                }}
              >
                <Tooltip title="Fast Mode: Quick responses">
                  <Button
                    size="small"
                    onClick={() => onModeChange('fast')}
                    startIcon={<BoltIcon sx={{ fontSize: 16 }} />}
                    variant={mode === 'fast' ? 'contained' : 'text'}
                    sx={{
                      minWidth: 70,
                      height: 28,
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      textTransform: 'none',
                      borderRadius: 2.5,
                      bgcolor: mode === 'fast' ? muiTheme.palette.primary.main : 'transparent',
                      color: mode === 'fast' ? 'white' : muiTheme.palette.text.secondary,
                      '&:hover': {
                        bgcolor: mode === 'fast' ? muiTheme.palette.primary.dark : alpha(muiTheme.palette.primary.main, 0.1)
                      },
                      px: 1.2
                    }}
                  >
                    Fast
                  </Button>
                </Tooltip>
                <Tooltip title="Deep Mode: Full analysis">
                  <Button
                    size="small"
                    onClick={() => onModeChange('deep')}
                    startIcon={<PsychologyIcon sx={{ fontSize: 16 }} />}
                    variant={mode === 'deep' ? 'contained' : 'text'}
                    sx={{
                      minWidth: 70,
                      height: 28,
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      textTransform: 'none',
                      borderRadius: 2.5,
                      bgcolor: mode === 'deep' ? muiTheme.palette.primary.main : 'transparent',
                      color: mode === 'deep' ? 'white' : muiTheme.palette.text.secondary,
                      '&:hover': {
                        bgcolor: mode === 'deep' ? muiTheme.palette.primary.dark : alpha(muiTheme.palette.primary.main, 0.1)
                      },
                      px: 1.2
                    }}
                  >
                    Deep
                  </Button>
                </Tooltip>
              </Box>
            )}

            <Box>
            {isLoading ? (
               <Tooltip title="Stop generation">
                <IconButton
                  onClick={onStopProcessing}
                  size="small"
                  sx={{
                    bgcolor: muiTheme.palette.grey[800],
                    color: 'white',
                    width: 32,
                    height: 32,
                    '&:hover': { bgcolor: 'black' }
                  }}
                >
                  <StopIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            ) : (
              <IconButton
                onClick={handleSend}
                disabled={!inputValue.trim()}
                size="small"
                sx={{
                  bgcolor: inputValue.trim() ? muiTheme.palette.primary.main : muiTheme.palette.action.disabledBackground,
                  color: inputValue.trim() ? 'white' : muiTheme.palette.action.disabled,
                  width: 32,
                  height: 32,
                  transition: 'all 0.2s',
                  '&:hover': {
                    bgcolor: inputValue.trim() ? muiTheme.palette.primary.dark : muiTheme.palette.action.disabledBackground,
                    transform: inputValue.trim() ? 'scale(1.05)' : 'none'
                  }
                }}
              >
                <SendIcon fontSize="small" sx={{ fontSize: 18, ml: 0.5 }} />
              </IconButton>
            )}
            </Box>
          </Stack>
        </Stack>
      </Box>

      <Typography variant="caption" sx={{ display: 'block', textAlign: 'center', mt: 1, color: 'text.secondary', opacity: 0.7, fontSize: '0.7rem' }}>
        LabOS AI can make mistakes. Check{' '}
        <Typography
          component="a"
          href="/privacy"
          variant="caption"
          sx={{
            color: 'primary.main',
            textDecoration: 'none',
            fontSize: '0.7rem',
            '&:hover': {
              textDecoration: 'underline'
            }
          }}
        >
          important info
        </Typography>
        .
      </Typography>
    </Box>
  );
};

export default ChatInput;
