'use client'

import React, { useEffect, useState } from 'react';
import ProtectedRoute from '@/components/Auth/ProtectedRoute';
import { 
  Card,
  CardContent,
  Typography, 
  Table, 
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Box, 
  Chip,
  IconButton,
  TablePagination,
  Alert,
  Snackbar,
  CircularProgress
} from '@mui/material';
import { 
  InsertDriveFile as FileIcon, 
  Download as DownloadIcon, 
  Delete as DeleteIcon
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { setFiles, setSelectedFile } from '@/store/slices/filesSlice';
import { SimpleFileInfo } from '@/types';
import { config } from '@/config';

const Files: React.FC = () => {
  const dispatch = useAppDispatch();
  const files = useAppSelector((state) => state.files.files);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info'}>({
    open: false,
    message: '',
    severity: 'info'
  });
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState<Record<string, string>>({});  // project_id -> project_name

  // Fetch files and projects from API
  const fetchFiles = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${config.api.baseUrl}/api/v1/files/user`, {
        headers,
        credentials: 'include'
      });
      
      const result = await response.json();
      
      if (result.success && result.data) {
        const transformedFiles = result.data.map((file: any) => ({
          id: file.id,
          name: file.original_filename,
          path: file.id,
          size: file.file_size,
          modified: file.updated_at,
          fileType: file.file_type,
          category: file.category,
          createdBy: file.created_by_agent,
          projectId: file.project_id 
        }));
        
        console.log('📁 Files loaded:', transformedFiles.length);
        console.log('📁 Sample file:', transformedFiles[0]);
        
        dispatch(setFiles(transformedFiles));

        const projectIds = [...new Set(transformedFiles.map((f: any) => f.projectId).filter(Boolean))];
        console.log('🔍 Unique project IDs:', projectIds);
        
        if (projectIds.length > 0) {
          const projectsResponse = await fetch(`${config.api.baseUrl}/api/v1/chat/projects`, {
            headers,
            credentials: 'include'
          });
          
          if (projectsResponse.ok) {
            const projectsResult = await projectsResponse.json();
            
            // API returns array directly (not wrapped in {success, data})
            const projectsArray = Array.isArray(projectsResult) ? projectsResult : [];
            
            const projectMap: Record<string, string> = {};
            projectsArray.forEach((project: any) => {
              projectMap[project.id] = project.name;
            });
            setProjects(projectMap);
            console.log('📋 Loaded projects:', projectMap);
          }
        }
      } else {
        showSnackbar('Failed to load files', 'error');
      }
    } catch (err) {
      console.error('Error fetching files:', err);
      showSnackbar('Error loading files', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (fileId: string, filename: string) => {
    try {
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {};
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${config.api.baseUrl}/api/v1/files/${fileId}/download`, {
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
      
      showSnackbar(`Downloaded ${filename}`, 'success');
    } catch (err) {
      console.error('Download error:', err);
      showSnackbar('Failed to download file', 'error');
    }
  };



  const handleDelete = async (fileId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }

    try {
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {};
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${config.api.baseUrl}/api/v1/files/${fileId}`, {
        method: 'DELETE',
        headers,
        credentials: 'include'
      });
      
      const result = await response.json();
      
      if (result.success) {
        showSnackbar('File deleted successfully', 'success');
        fetchFiles(); 
      } else {
        showSnackbar(result.error || 'Failed to delete file', 'error');
      }
    } catch (err) {
      console.error('Delete error:', err);
      showSnackbar('Failed to delete file', 'error');
    }
  };


  const showSnackbar = (message: string, severity: 'success' | 'error' | 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  // Load files on component mount
  useEffect(() => {
    fetchFiles();
  }, []);

  const allFiles = files;

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const paginatedFiles = allFiles.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileTypeColor = (filename: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    const extension = filename.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'txt': return 'error';
      case 'csv': return 'success';
      case 'json': return 'secondary';
      case 'py': return 'warning';
      case 'js': return 'warning';
      case 'png':
      case 'jpg':
      case 'jpeg': return 'info';
      default: return 'primary';
    }
  };

  return (
      <Box sx={{ p: 3, pt: 2 }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Box sx={{ mb: 4 }}>

            <Typography variant="body1" color="text.secondary">
              Manage files uploaded in your chat conversations
            </Typography>
          </Box>

          <Card className="files-management-section">
            <CardContent sx={{ p: 0 }}>
              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : allFiles.length === 0 ? (
                <Box sx={{ textAlign: 'center', p: 4 }}>
                  <Typography variant="body1" color="text.secondary">
                    No files yet. Upload your first file!
                  </Typography>
                </Box>
              ) : (
                <>
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Name</TableCell>
                          <TableCell>Source</TableCell>
                          <TableCell>Project</TableCell>
                          <TableCell>Size</TableCell>
                          <TableCell>Modified</TableCell>
                          <TableCell>Actions</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {paginatedFiles.map((file) => {
                          const extension = file.name.split('.').pop()?.toLowerCase() || 'unknown';
                          const isAgentGenerated = (file as any).createdBy !== 'user';
                          const projectName = (file as any).projectId ? projects[(file as any).projectId] : null;
                          
                          return (
                            <TableRow key={file.id} hover>
                              <TableCell>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  <FileIcon />
                                  <Typography variant="body2">{file.name}</Typography>
                                  <Chip 
                                    label={extension} 
                                    color={getFileTypeColor(file.name)} 
                                    size="small" 
                                  />
                                </Box>
                              </TableCell>
                              <TableCell>
                                <Chip 
                                  label={isAgentGenerated ? '🤖 Agent' : '👤 User'} 
                                  color={isAgentGenerated ? 'secondary' : 'default'}
                                  size="small"
                                  variant="outlined"
                                />
                              </TableCell>
                              <TableCell>
                                {projectName ? (
                                  <Typography variant="body2" color="primary">
                                    {projectName}
                                  </Typography>
                                ) : (
                                  <Typography variant="body2" color="text.secondary">
                                    -
                                  </Typography>
                                )}
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2">
                                  {formatFileSize(file.size)}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2">
                                  {new Date(file.modified).toLocaleDateString()}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Box sx={{ display: 'flex', gap: 1 }}>
                                  <IconButton 
                                    size="small" 
                                    color="primary"
                                    onClick={() => handleDownload(file.id, file.name)}
                                    title="Download file"
                                  >
                                    <DownloadIcon />
                                  </IconButton>
                                  <IconButton 
                                    size="small" 
                                    color="error"
                                    onClick={() => handleDelete(file.id, file.name)}
                                    title="Delete file"
                                  >
                                    <DeleteIcon />
                                  </IconButton>
                                </Box>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                  <TablePagination
                    rowsPerPageOptions={[5, 10, 25]}
                    component="div"
                    count={allFiles.length}
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
        <Snackbar
          open={snackbar.open}
          autoHideDuration={4000}
          onClose={handleCloseSnackbar}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Box>
  );
};

const FilesWithProtection: React.FC = () => {
  return (
    <ProtectedRoute>
      <Files />
    </ProtectedRoute>
  );
};

export default FilesWithProtection;
