'use client'

import React, { useState } from 'react';
import {
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Typography,
  Box,
  CircularProgress
} from '@mui/material';
import {
  MoreVert as MoreVertIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Folder as ProjectIcon,
  Warning as WarningIcon
} from '@mui/icons-material';
import { useAppDispatch } from '@/store/hooks';
import { updateProject, deleteProject } from '@/store/slices/chatProjectsSlice';
import type { ChatProject, UpdateProjectRequest } from '@/types/chatProjects';

interface ProjectMenuDropdownProps {
  project: ChatProject;
  onProjectDeleted?: () => void; // Callback when project is deleted
}

const ProjectMenuDropdown: React.FC<ProjectMenuDropdownProps> = ({
  project,
  onProjectDeleted
}) => {
  const dispatch = useAppDispatch();
  
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const [editForm, setEditForm] = useState({
    name: project.name,
    description: project.description || ''
  });

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation(); // Prevent card click
    event.preventDefault(); // Prevent default behavior
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleEditClick = (event: React.MouseEvent) => {
    event.stopPropagation();
    setEditForm({
      name: project.name,
      description: project.description || ''
    });
    setEditDialogOpen(true);
    handleMenuClose();
  };

  const handleDeleteClick = (event: React.MouseEvent) => {
    event.stopPropagation();
    event.preventDefault();
    setDeleteDialogOpen(true);
    handleMenuClose();
  };

  const handleEditSave = async () => {
    if (!editForm.name.trim()) return;

    setLoading(true);
    try {
      const updateData: UpdateProjectRequest = {
        name: editForm.name.trim(),
        description: editForm.description.trim() || undefined
      };

      await dispatch(updateProject({ projectId: project.id, request: updateData }));
      setEditDialogOpen(false);
    } catch (error) {
      console.error('Failed to update project:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteConfirm = async () => {
    setLoading(true);
    try {
      console.log('🗑️ Starting project deletion:', project.id);
      const result = await dispatch(deleteProject(project.id));
      if (deleteProject.fulfilled.match(result)) {
        console.log('✅ Project deleted successfully:', project.id);
        setDeleteDialogOpen(false);
        onProjectDeleted?.();
      } else {
        console.error('❌ Project deletion failed:', result);
      }
    } catch (error) {
      console.error('Failed to delete project:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Three Dots Menu Button */}
      <IconButton
        onClick={handleMenuOpen}
        size="small"
        sx={{
          opacity: 0.7,
          '&:hover': {
            opacity: 1,
            backgroundColor: 'action.hover'
          }
        }}
      >
        <MoreVertIcon />
      </IconButton>

      {/* Dropdown Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        onClick={(e) => e.stopPropagation()} // Prevent menu clicks from bubbling to card
      >
        <MenuItem onClick={handleEditClick}>
          <ListItemIcon>
            <EditIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Edit Project</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleDeleteClick} sx={{ color: 'error.main' }}>
          <ListItemIcon>
            <DeleteIcon fontSize="small" color="error" />
          </ListItemIcon>
          <ListItemText>Delete Project</ListItemText>
        </MenuItem>
      </Menu>

      {/* Edit Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={() => !loading && setEditDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        onClick={(e) => e.stopPropagation()} // Prevent dialog clicks from bubbling to card
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <ProjectIcon sx={{ mr: 2, color: 'primary.main' }} />
            Edit Project
          </Box>
        </DialogTitle>
        <DialogContent onClick={(e) => e.stopPropagation()}>
          <TextField
            fullWidth
            label="Project Name"
            value={editForm.name}
            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
            onClick={(e) => e.stopPropagation()} // Prevent input click from bubbling
            disabled={loading}
            sx={{ mb: 3, mt: 1 }}
          />
          <TextField
            fullWidth
            label="Description (Optional)"
            value={editForm.description}
            onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
            onClick={(e) => e.stopPropagation()} // Prevent input click from bubbling
            multiline
            rows={3}
            disabled={loading}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)} disabled={loading}>
            Cancel
          </Button>
          <Button
            onClick={handleEditSave}
            variant="contained"
            disabled={loading || !editForm.name.trim()}
            startIcon={loading ? <CircularProgress size={16} /> : <EditIcon />}
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => !loading && setDeleteDialogOpen(false)}
        maxWidth="sm"
        onClick={(e) => e.stopPropagation()} // Prevent dialog clicks from bubbling to card
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <WarningIcon sx={{ mr: 2, color: 'error.main' }} />
            Delete Project
          </Box>
        </DialogTitle>
        <DialogContent onClick={(e) => e.stopPropagation()}>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Are you sure you want to delete "<strong>{project.name}</strong>"?
          </Typography>
          <Typography variant="body2" color="text.secondary">
            This will permanently delete all messages, conversations, and workflow history
            associated with this project. This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={loading}>
            Cancel
          </Button>
          <Button
            onClick={(e) => {
              e.stopPropagation();
              e.preventDefault();
              handleDeleteConfirm();
            }}
            variant="contained"
            color="error"
            disabled={loading}
            startIcon={loading ? <CircularProgress size={16} /> : <DeleteIcon />}
          >
            {loading ? 'Deleting...' : 'Delete Project'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default ProjectMenuDropdown;
