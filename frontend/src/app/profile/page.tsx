'use client'

import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Button,
  Avatar,
  Divider,
  Card,
  CardContent,
  Chip,
  TextField,
  MenuItem,
  Alert,
  CircularProgress,
  IconButton,
  Stack
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Person as PersonIcon,
  Email as EmailIcon,
  Verified as VerifiedIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Work as WorkIcon,
  Business as BusinessIcon,
  LocationOn as LocationIcon,
  School as SchoolIcon
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { useAppSelector } from '@/store/hooks';
import { config } from '@/config';

const ProfilePage: React.FC = () => {
  const router = useRouter();
  const { user } = useAppSelector((state) => state.auth);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [profileData, setProfileData] = useState({
    first_name: '',
    last_name: '',
    job_title: '',
    organization: '',
    country: '',
    experience_level: '',
    use_case: ''
  });

  // Load user profile data
  useEffect(() => {
    const fetchProfileData = async () => {
      try {
        const token = localStorage.getItem('auth_token');
        if (!token) return;

        const response = await fetch(`${config.api.baseUrl}/api/v1/auth/profile`, {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          credentials: 'include'
        });

        if (response.ok) {
          const data = await response.json();
          setProfileData({
            first_name: data.first_name || '',
            last_name: data.last_name || '',
            job_title: data.job_title || '',
            organization: data.organization || '',
            country: data.country || '',
            experience_level: data.experience_level || '',
            use_case: data.use_case || ''
          });
        }
      } catch (err) {
        console.error('Error loading profile:', err);
      }
    };

    fetchProfileData();
  }, []);

  const handleInputChange = (field: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setProfileData(prev => ({ ...prev, [field]: event.target.value }));
    setError('');
    setSuccess(false);
  };

  const handleSave = async () => {
    setLoading(true);
    setError('');
    setSuccess(false);

    try {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        setError('Not authenticated');
        setLoading(false);
        return;
      }

      const response = await fetch(`${config.api.baseUrl}/api/v1/auth/profile/update`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        credentials: 'include',
        body: JSON.stringify(profileData)
      });

      if (response.ok) {
        setSuccess(true);
        setIsEditing(false);
        setTimeout(() => setSuccess(false), 3000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update profile');
      }
    } catch (err) {
      console.error('Error updating profile:', err);
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setError('');
    setSuccess(false);
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => router.back()}
            sx={{ mb: 2 }}
          >
            Back
          </Button>
          
          <Typography variant="h4" component="h1" sx={{ fontWeight: 600, mb: 1, color: 'text.primary' }}>
            User Profile
          </Typography>
          
          <Typography variant="body1" sx={{ color: 'text.primary', opacity: 0.8 }}>
            Your account information and details
          </Typography>
        </Box>

        {!isEditing && (
          <Button
            variant="outlined"
            startIcon={<EditIcon />}
            onClick={() => setIsEditing(true)}
            sx={{ mt: 6 }}
          >
            Edit Profile
          </Button>
        )}
      </Box>

      {/* Alerts */}
      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Profile updated successfully!
        </Alert>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Basic Info Card */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <Avatar
              src={user?.picture}
              sx={{ 
                width: 80, 
                height: 80, 
                mr: 3,
                bgcolor: 'primary.main'
              }}
            >
              <PersonIcon sx={{ fontSize: 40 }} />
            </Avatar>
            
            <Box sx={{ flex: 1 }}>
              <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
                {user?.name || 'Anonymous User'}
              </Typography>
              
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <EmailIcon sx={{ mr: 1, color: 'primary.main', fontSize: 20 }} />
                <Typography variant="body1" sx={{ color: 'text.primary' }}>
                  {user?.email || 'No email'}
                </Typography>
                {user?.email_verified && (
                  <Chip
                    icon={<VerifiedIcon />}
                    label="Verified"
                    size="small"
                    color="success"
                    sx={{ ml: 2 }}
                  />
                )}
              </Box>
              
              <Typography variant="body2" sx={{ color: 'text.primary', opacity: 0.7 }}>
                User ID: {user?.id || 'Not available'}
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Profile Details Card */}
      <Card>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
            Profile Details
          </Typography>

          {isEditing ? (
            <>
              <Stack spacing={2}>
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <TextField
                    fullWidth
                    label="First Name"
                    value={profileData.first_name}
                    onChange={handleInputChange('first_name')}
                  />
                  <TextField
                    fullWidth
                    label="Last Name"
                    value={profileData.last_name}
                    onChange={handleInputChange('last_name')}
                  />
                </Box>
                
                <TextField
                  fullWidth
                  label="Job Title"
                  value={profileData.job_title}
                  onChange={handleInputChange('job_title')}
                />
                
                <TextField
                  fullWidth
                  label="Organization"
                  value={profileData.organization}
                  onChange={handleInputChange('organization')}
                />
                
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <TextField
                    fullWidth
                    label="Country"
                    value={profileData.country}
                    onChange={handleInputChange('country')}
                  />
                  <TextField
                    fullWidth
                    select
                    label="Experience Level"
                    value={profileData.experience_level}
                    onChange={handleInputChange('experience_level')}
                  >
                    <MenuItem value="beginner">Beginner</MenuItem>
                    <MenuItem value="intermediate">Intermediate</MenuItem>
                    <MenuItem value="advanced">Advanced</MenuItem>
                  </TextField>
                </Box>
                
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="How do you plan to use LabOS?"
                  value={profileData.use_case}
                  onChange={handleInputChange('use_case')}
                />
              </Stack>

              <Box sx={{ mt: 3, display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                <Button
                  variant="outlined"
                  startIcon={<CancelIcon />}
                  onClick={handleCancel}
                  disabled={loading}
                >
                  Cancel
                </Button>
                <Button
                  variant="contained"
                  startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
                  onClick={handleSave}
                  disabled={loading}
                >
                  {loading ? 'Saving...' : 'Save Changes'}
                </Button>
              </Box>
            </>
          ) : (
            <Box>
              {profileData.first_name || profileData.last_name ? (
                <Box sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
                  <PersonIcon sx={{ mr: 2, color: 'primary.main' }} />
                  <Box>
                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>Name</Typography>
                    <Typography variant="body1">{`${profileData.first_name} ${profileData.last_name}`}</Typography>
                  </Box>
                </Box>
              ) : null}

              {profileData.job_title && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Box sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
                    <WorkIcon sx={{ mr: 2, color: 'primary.main' }} />
                    <Box>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>Job Title</Typography>
                      <Typography variant="body1">{profileData.job_title}</Typography>
                    </Box>
                  </Box>
                </>
              )}

              {profileData.organization && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Box sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
                    <BusinessIcon sx={{ mr: 2, color: 'primary.main' }} />
                    <Box>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>Organization</Typography>
                      <Typography variant="body1">{profileData.organization}</Typography>
                    </Box>
                  </Box>
                </>
              )}

              {profileData.country && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Box sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
                    <LocationIcon sx={{ mr: 2, color: 'primary.main' }} />
                    <Box>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>Country</Typography>
                      <Typography variant="body1">{profileData.country}</Typography>
                    </Box>
                  </Box>
                </>
              )}

              {profileData.experience_level && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Box sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
                    <SchoolIcon sx={{ mr: 2, color: 'primary.main' }} />
                    <Box>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>Experience Level</Typography>
                      <Typography variant="body1" sx={{ textTransform: 'capitalize' }}>
                        {profileData.experience_level}
                      </Typography>
                    </Box>
                  </Box>
                </>
              )}

              {profileData.use_case && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Box>
                    <Typography variant="body2" sx={{ color: 'text.secondary', mb: 1 }}>Use Case</Typography>
                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                      {profileData.use_case}
                    </Typography>
                  </Box>
                </>
              )}

              {!profileData.first_name && !profileData.job_title && !profileData.organization && (
                <Typography variant="body2" sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
                  No profile details yet. Click "Edit Profile" to add your information.
                </Typography>
              )}
            </Box>
          )}
        </CardContent>
      </Card>

    </Container>
  );
};

export default ProfilePage;