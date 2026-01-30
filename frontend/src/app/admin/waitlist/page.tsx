'use client'

import React, { useEffect, useState } from 'react';
import { 
  Box, 
  Typography, 
  Container, 
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Alert,
  Snackbar,
  Card,
  CardContent,
  Stack,
  useTheme
} from '@mui/material';
import {
  Check as ApproveIcon,
  Close as RejectIcon,
  Refresh as RefreshIcon,
  Groups as GroupsIcon,
  HourglassEmpty as WaitlistIcon,
  Block as BlockIcon,
  KeyboardArrowDown as ExpandMoreIcon,
  KeyboardArrowUp as ExpandLessIcon
} from '@mui/icons-material';
import { config } from '@/config';
import { useAppSelector } from '@/store/hooks';
import { useRouter } from 'next/navigation';

interface User {
  id: string;
  email: string;
  name: string | null;
  status: string;
  is_admin: boolean;
  // Waitlist application fields
  institution: string | null;
  research_field: string | null;
  application_reason: string | null;
  // Enhanced waitlist fields
  first_name: string | null;
  last_name: string | null;
  job_title: string | null;
  organization: string | null;
  country: string | null;
  experience_level: string | null;
  use_case: string | null;
  // Timestamps
  created_at: string;
  last_login: string | null;
  approved_at: string | null;
  approved_by: string | null;
  rejection_reason: string | null;
}

interface Stats {
  total_users: number;
  waitlist: number;
  approved: number;
  rejected: number;
  suspended: number;
}

const AdminWaitlistPage: React.FC = () => {
  const theme = useTheme();
  const router = useRouter();
  const { user, isAuthenticated } = useAppSelector((state) => state.auth);
  
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [rejectionDialogOpen, setRejectionDialogOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error'}>({
    open: false,
    message: '',
    severity: 'success'
  });

  const toggleRow = (userId: string) => {
    setExpandedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(userId)) {
        newSet.delete(userId);
      } else {
        newSet.add(userId);
      }
      return newSet;
    });
  };

  useEffect(() => {
    // Check if user is admin
    if (isAuthenticated && user && !(user as any).is_admin) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, user, router]);

  useEffect(() => {
    fetchUsers();
    fetchStats();
  }, [statusFilter]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('auth_token');
      // Build URL with status filter (skip if 'all')
      const statusParam = statusFilter === 'all' ? '' : `?status=${statusFilter}`;
      const response = await fetch(
        `${config.api.baseUrl}/api/v1/admin/users/waitlist${statusParam}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        }
      );
      const result = await response.json();
      if (result.success) {
        setUsers(result.data);
      } else {
        showSnackbar('Failed to load users', 'error');
      }
    } catch (error) {
      console.error('Error fetching users:', error);
      showSnackbar('Error loading users', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`${config.api.baseUrl}/api/v1/admin/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        credentials: 'include'
      });
      const result = await response.json();
      if (result.success) {
        setStats(result.data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleApprove = async (userId: string) => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(
        `${config.api.baseUrl}/api/v1/admin/users/${userId}/approve`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        }
      );
      const result = await response.json();
      if (result.success) {
        showSnackbar(`User approved successfully`, 'success');
        fetchUsers();
        fetchStats();
      } else {
        showSnackbar('Failed to approve user', 'error');
      }
    } catch (error) {
      console.error('Error approving user:', error);
      showSnackbar('Error approving user', 'error');
    }
  };

  const handleRejectClick = (user: User) => {
    setSelectedUser(user);
    setRejectionDialogOpen(true);
  };

  const handleRejectConfirm = async () => {
    if (!selectedUser) return;
    
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(
        `${config.api.baseUrl}/api/v1/admin/users/${selectedUser.id}/reject?rejection_reason=${encodeURIComponent(rejectionReason)}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        }
      );
      const result = await response.json();
      if (result.success) {
        showSnackbar(`User rejected`, 'success');
        setRejectionDialogOpen(false);
        setRejectionReason('');
        setSelectedUser(null);
        fetchUsers();
        fetchStats();
      } else {
        showSnackbar('Failed to reject user', 'error');
      }
    } catch (error) {
      console.error('Error rejecting user:', error);
      showSnackbar('Error rejecting user', 'error');
    }
  };

  const showSnackbar = (message: string, severity: 'success' | 'error') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'waitlist': return 'warning';
      case 'approved': return 'success';
      case 'rejected': return 'error';
      case 'suspended': return 'default';
      default: return 'default';
    }
  };

  if (!isAuthenticated || !(user as any)?.is_admin) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h5">Access Denied</Typography>
        <Typography variant="body2" color="text.secondary">
          You do not have permission to access this page.
        </Typography>
      </Box>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h4"
          component="h1"
          sx={{
            mb: 1,
            fontWeight: 700,
            color: theme.palette.text.primary  // Use theme text color
          }}
        >
          Admin - User Waitlist Management
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Review and manage user access requests
        </Typography>
      </Box>

      {/* Stats Cards */}
      {stats && (
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 4 }}>
          <Box sx={{ flex: 1 }}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <GroupsIcon sx={{ fontSize: 40, color: theme.palette.primary.main }} />
                  <Box>
                    <Typography variant="h4">{stats.total_users}</Typography>
                    <Typography variant="body2" color="text.secondary">Total Users</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Box>
          <Box sx={{ flex: 1 }}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <WaitlistIcon sx={{ fontSize: 40, color: theme.palette.warning.main }} />
                  <Box>
                    <Typography variant="h4">{stats.waitlist}</Typography>
                    <Typography variant="body2" color="text.secondary">Waitlist</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Box>
          <Box sx={{ flex: 1 }}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <ApproveIcon sx={{ fontSize: 40, color: theme.palette.success.main }} />
                  <Box>
                    <Typography variant="h4">{stats.approved}</Typography>
                    <Typography variant="body2" color="text.secondary">Approved</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Box>
          <Box sx={{ flex: 1 }}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <BlockIcon sx={{ fontSize: 40, color: theme.palette.error.main }} />
                  <Box>
                    <Typography variant="h4">{stats.rejected}</Typography>
                    <Typography variant="body2" color="text.secondary">Rejected</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Box>
        </Stack>
      )}

      {/* Filters and Actions */}
      <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Status Filter</InputLabel>
          <Select
            value={statusFilter}
            label="Status Filter"
            onChange={(e) => setStatusFilter(e.target.value)}
            displayEmpty
          >
            <MenuItem value="all">All Users</MenuItem>
            <MenuItem value="waitlist">Waitlist</MenuItem>
            <MenuItem value="approved">Approved</MenuItem>
            <MenuItem value="rejected">Rejected</MenuItem>
            <MenuItem value="suspended">Suspended</MenuItem>
          </Select>
        </FormControl>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={() => { fetchUsers(); fetchStats(); }}
        >
          Refresh
        </Button>
      </Box>

      {/* Users Table */}
      <Paper>
        <TableContainer>
          {loading ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <CircularProgress />
            </Box>
          ) : users.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Typography variant="body1" color="text.secondary">
                No users found
              </Typography>
            </Box>
          ) : (
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell width="40px"></TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((user) => (
                  <React.Fragment key={user.id}>
                    <TableRow hover>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => toggleRow(user.id)}
                          title="View details"
                        >
                          {expandedRows.has(user.id) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                        </IconButton>
                      </TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>{user.name || '-'}</TableCell>
                      <TableCell>
                        <Chip
                          label={user.status}
                          color={getStatusColor(user.status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{new Date(user.created_at).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          {user.status === 'waitlist' && (
                            <>
                              <IconButton
                                size="small"
                                color="success"
                                onClick={() => handleApprove(user.id)}
                                title="Approve"
                              >
                                <ApproveIcon />
                              </IconButton>
                              <IconButton
                                size="small"
                                color="error"
                                onClick={() => handleRejectClick(user)}
                                title="Reject"
                              >
                                <RejectIcon />
                              </IconButton>
                            </>
                          )}
                          {user.status === 'approved' && (
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleRejectClick(user)}
                              title="Reject User"
                            >
                              <RejectIcon />
                            </IconButton>
                          )}
                          {user.status === 'rejected' && (
                            <IconButton
                              size="small"
                              color="success"
                              onClick={() => handleApprove(user.id)}
                              title="Approve User"
                            >
                              <ApproveIcon />
                            </IconButton>
                          )}
                        </Box>
                      </TableCell>
                    </TableRow>
                    {/* Expanded Details Row */}
                    {expandedRows.has(user.id) && (
                      <TableRow>
                        <TableCell colSpan={6} sx={{ bgcolor: theme.palette.action.hover, py: 2 }}>
                          <Box sx={{ px: 2 }}>
                            <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
                              User Details
                            </Typography>
                            <Stack spacing={1.5}>
                              {/* User ID */}
                              <Box sx={{ display: 'flex', gap: 2 }}>
                                <Typography variant="body2" sx={{ minWidth: 180, fontWeight: 500 }}>
                                  User ID:
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  {user.id}
                                </Typography>
                              </Box>

                              {/* Personal Information */}
                              {(user.first_name || user.last_name) && (
                                <Box sx={{ display: 'flex', gap: 2 }}>
                                  <Typography variant="body2" sx={{ minWidth: 180, fontWeight: 500 }}>
                                    Full Name:
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    {[user.first_name, user.last_name].filter(Boolean).join(' ')}
                                  </Typography>
                                </Box>
                              )}

                              {user.job_title && (
                                <Box sx={{ display: 'flex', gap: 2 }}>
                                  <Typography variant="body2" sx={{ minWidth: 180, fontWeight: 500 }}>
                                    Job Title:
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    {user.job_title}
                                  </Typography>
                                </Box>
                              )}

                              {user.organization && (
                                <Box sx={{ display: 'flex', gap: 2 }}>
                                  <Typography variant="body2" sx={{ minWidth: 180, fontWeight: 500 }}>
                                    Organization:
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    {user.organization}
                                  </Typography>
                                </Box>
                              )}

                              {user.country && (
                                <Box sx={{ display: 'flex', gap: 2 }}>
                                  <Typography variant="body2" sx={{ minWidth: 180, fontWeight: 500 }}>
                                    Country:
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    {user.country}
                                  </Typography>
                                </Box>
                              )}

                              {user.experience_level && (
                                <Box sx={{ display: 'flex', gap: 2 }}>
                                  <Typography variant="body2" sx={{ minWidth: 180, fontWeight: 500 }}>
                                    Experience Level:
                                  </Typography>
                                  <Chip
                                    label={user.experience_level}
                                    size="small"
                                    color={
                                      user.experience_level === 'advanced' ? 'success' :
                                      user.experience_level === 'intermediate' ? 'primary' : 'default'
                                    }
                                  />
                                </Box>
                              )}

                              {user.use_case && (
                                <Box sx={{ display: 'flex', gap: 2 }}>
                                  <Typography variant="body2" sx={{ minWidth: 180, fontWeight: 500 }}>
                                    Use Case:
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    {user.use_case}
                                  </Typography>
                                </Box>
                              )}

                              {user.application_reason && (
                                <Box sx={{ display: 'flex', gap: 2 }}>
                                  <Typography variant="body2" sx={{ minWidth: 180, fontWeight: 500 }}>
                                    Application Reason:
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    {user.application_reason}
                                  </Typography>
                                </Box>
                              )}

                              {/* Timestamps */}
                              <Box sx={{ display: 'flex', gap: 2 }}>
                                <Typography variant="body2" sx={{ minWidth: 180, fontWeight: 500 }}>
                                  Last Login:
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
                                </Typography>
                              </Box>

                              {user.approved_at && (
                                <Box sx={{ display: 'flex', gap: 2 }}>
                                  <Typography variant="body2" sx={{ minWidth: 180, fontWeight: 500 }}>
                                    Approved At:
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    {new Date(user.approved_at).toLocaleString()}
                                  </Typography>
                                </Box>
                              )}

                              {user.approved_by && (
                                <Box sx={{ display: 'flex', gap: 2 }}>
                                  <Typography variant="body2" sx={{ minWidth: 180, fontWeight: 500 }}>
                                    Approved By:
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    {user.approved_by}
                                  </Typography>
                                </Box>
                              )}

                              {user.rejection_reason && (
                                <Box sx={{ display: 'flex', gap: 2 }}>
                                  <Typography variant="body2" sx={{ minWidth: 180, fontWeight: 500 }}>
                                    Rejection Reason:
                                  </Typography>
                                  <Typography variant="body2" color="error.main">
                                    {user.rejection_reason}
                                  </Typography>
                                </Box>
                              )}

                              {/* Admin Status */}
                              <Box sx={{ display: 'flex', gap: 2 }}>
                                <Typography variant="body2" sx={{ minWidth: 180, fontWeight: 500 }}>
                                  Admin:
                                </Typography>
                                <Chip
                                  label={user.is_admin ? 'Yes' : 'No'}
                                  size="small"
                                  color={user.is_admin ? 'primary' : 'default'}
                                />
                              </Box>
                            </Stack>
                          </Box>
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          )}
        </TableContainer>
      </Paper>

      {/* Rejection Dialog */}
      <Dialog open={rejectionDialogOpen} onClose={() => setRejectionDialogOpen(false)}>
        <DialogTitle>Reject User</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Are you sure you want to reject {selectedUser?.email}?
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={3}
            label="Rejection Reason (Optional)"
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.target.value)}
            placeholder="Provide a reason for rejection..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRejectionDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleRejectConfirm} color="error" variant="contained">
            Reject
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default AdminWaitlistPage;

