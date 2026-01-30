'use client'

import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Typography,
  CircularProgress
} from '@mui/material';
import {
  Folder as ProjectIcon,
  Close as CloseIcon
} from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { createProject } from '@/store/slices/chatProjectsSlice';
import type { CreateProjectRequest } from '@/types/chatProjects';

interface CreateProjectModalProps {
  open: boolean;
  onClose: () => void;
  onProjectCreated?: (projectId: string) => void;
}

const CreateProjectModal: React.FC<CreateProjectModalProps> = ({
  open,
  onClose,
  onProjectCreated
}) => {
  const dispatch = useAppDispatch();
  const { createProjectLoading } = useAppSelector((state) => state.chatProjects);
  
  const [formData, setFormData] = useState<CreateProjectRequest>({
    name: '',
    description: ''
  });
  
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleClose = () => {
    if (!createProjectLoading) {
      setFormData({ name: '', description: '' });
      setErrors({});
      onClose();
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'Project name is required';
    } else if (formData.name.trim().length < 3) {
      newErrors.name = 'Project name must be at least 3 characters';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;
    
    try {
      const result = await dispatch(createProject({
        name: formData.name.trim(),
        description: formData.description.trim() || undefined
      }));
      
      if (createProject.fulfilled.match(result)) {
        // Success
        const newProject = result.payload;
        onProjectCreated?.(newProject.id);
        handleClose();
      }
    } catch (error) {
      console.error('Failed to create project:', error);
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && event.metaKey) {
      handleSubmit();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 2 }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <ProjectIcon sx={{ mr: 2, color: 'primary.main' }} />
          <Typography variant="h6" component="span" sx={{ fontWeight: 600 }}>
            Create New Project
          </Typography>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <Box sx={{ pt: 1 }}>
          <TextField
            fullWidth
            label="Project Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            onKeyPress={handleKeyPress}
            error={!!errors.name}
            helperText={errors.name || 'Give your project a descriptive name'}
            autoFocus
            disabled={createProjectLoading}
            sx={{ mb: 3 }}
          />
          
          <TextField
            fullWidth
            label="Description (Optional)"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            onKeyPress={handleKeyPress}
            multiline
            rows={3}
            disabled={createProjectLoading}
            helperText="Briefly describe what this project is about"
          />
        </Box>
      </DialogContent>
      
      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button
          onClick={handleClose}
          disabled={createProjectLoading}
        >
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={createProjectLoading || !formData.name.trim()}
          startIcon={createProjectLoading ? <CircularProgress size={16} /> : <ProjectIcon />}
        >
          {createProjectLoading ? 'Creating...' : 'Create Project'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CreateProjectModal;
