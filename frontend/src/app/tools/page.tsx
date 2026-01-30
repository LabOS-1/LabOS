'use client'

import React, { useEffect, useState } from 'react';
import ProtectedRoute from '@/components/Auth/ProtectedRoute';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Box,
  CircularProgress,
  Alert,
  TextField,
  InputAdornment,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Pagination,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton
} from '@mui/material';
import {
  Build as ToolIcon,
  PlayArrow as PlayIcon,
  Search as SearchIcon,
  ExpandMore as ExpandMoreIcon,
  Public as PublicIcon,
  Person as PersonIcon,
  Settings as SettingsIcon,
  VerifiedUser as VerifiedIcon,
  Science as ScienceIcon,
  Code as CodeIcon,
  Storage as StorageIcon,
  Visibility as ViewIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setToolQuery } from '@/store/slices/chatSlice';
import { useRouter } from 'next/navigation';

interface ToolFromAPI {
  id?: string;
  name: string;
  description: string;
  type: string;
  category: string;
  ownership: 'system' | 'public' | 'personal';
  source: 'builtin' | 'database' | 'mcp';
  is_verified?: boolean;
  usage_count: number;
  last_used?: string;
  created_at?: string;
  created_by?: string;
}

interface APIResponse {
  success: boolean;
  data?: {
    builtin_tools: ToolFromAPI[];
    public_tools: ToolFromAPI[];
    my_tools: ToolFromAPI[];
    mcp_tools: ToolFromAPI[];
    total_count: number;
  };
  error?: string;
}

const ITEMS_PER_PAGE = 12;

const Tools: React.FC = () => {
  const dispatch = useAppDispatch();
  const router = useRouter();

  // Get user info from Redux store
  const user = useAppSelector((state) => state.auth.user);

  const [builtinTools, setBuiltinTools] = useState<ToolFromAPI[]>([]);
  const [publicTools, setPublicTools] = useState<ToolFromAPI[]>([]);
  const [myTools, setMyTools] = useState<ToolFromAPI[]>([]);
  const [mcpTools, setMcpTools] = useState<ToolFromAPI[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'usage' | 'recent'>('name');
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [builtinPage, setBuiltinPage] = useState(1);
  const [publicPage, setPublicPage] = useState(1);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState<any>(null);
  const [toolDetails, setToolDetails] = useState<any>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  const handleViewTool = async (tool: ToolFromAPI) => {
    if (!tool.id) return;

    setSelectedTool(tool);
    setViewDialogOpen(true);
    setLoadingDetails(true);

    try {
      const response = await fetch(`/api/v1/tools/${tool.id}?user_id=${user?.id || ''}`);
      const result = await response.json();

      if (result.success) {
        setToolDetails(result.data);
      } else {
        console.error('Failed to fetch tool details:', result.error);
      }
    } catch (error) {
      console.error('Error fetching tool details:', error);
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleDeleteTool = async (tool: ToolFromAPI) => {
    if (!tool.id || !user?.id) return;

    if (!window.confirm(`Are you sure you want to delete tool "${tool.name}"?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/tools/${tool.id}?user_id=${encodeURIComponent(user.id)}`, {
        method: 'DELETE',
      });
      const result = await response.json();

      if (result.success) {
        // Refresh tools list
        await fetchTools();
      } else {
        alert(`Failed to delete tool: ${result.error}`);
      }
    } catch (error) {
      alert(`Error deleting tool: ${error}`);
    }
  };

  const handleUseTool = (tool: ToolFromAPI) => {
    dispatch(setToolQuery({
      toolName: tool.name,
      description: tool.description
    }));
    router.push('/chat');
  };

  const fetchTools = async () => {
    setLoading(true);
    setError(null);

    try {
      // Use user.id from Redux store (project_id is optional now)
      const userId = user?.id || '';

      console.log('🔍 Fetching tools with userId:', userId);

      // Note: project_id is optional - backend will return all user's tools
      const url = `/api/v1/tools?user_id=${encodeURIComponent(userId)}`;
      const response = await fetch(url);
      const result: APIResponse = await response.json();

      console.log('📦 Tools API response:', {
        builtin: result.data?.builtin_tools?.length || 0,
        public: result.data?.public_tools?.length || 0,
        my: result.data?.my_tools?.length || 0,
        mcp: result.data?.mcp_tools?.length || 0,
      });

      if (result.success && result.data) {
        setBuiltinTools(result.data.builtin_tools || []);
        setPublicTools(result.data.public_tools || []);
        setMyTools(result.data.my_tools || []);
        setMcpTools(result.data.mcp_tools || []);
      } else {
        setError(result.error || 'Failed to fetch tools');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Network error';
      setError(`Failed to connect to backend: ${errorMessage}`);
      console.error('Error fetching tools:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTools();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]); // Re-fetch when user changes

  const getCategories = (tools: ToolFromAPI[]) => {
    const categories = new Set(tools.map(t => t.category));
    return Array.from(categories).sort();
  };

  const getCategoryIcon = (category: string) => {
    const lowerCategory = category.toLowerCase();
    if (lowerCategory.includes('research') || lowerCategory.includes('search')) {
      return <SearchIcon fontSize="small" />;
    } else if (lowerCategory.includes('academic') || lowerCategory.includes('science')) {
      return <ScienceIcon fontSize="small" />;
    } else if (lowerCategory.includes('development') || lowerCategory.includes('code')) {
      return <CodeIcon fontSize="small" />;
    } else if (lowerCategory.includes('content') || lowerCategory.includes('extract')) {
      return <StorageIcon fontSize="small" />;
    } else if (lowerCategory.includes('environment')) {
      return <SettingsIcon fontSize="small" />;
    }
    return <ToolIcon fontSize="small" />;
  };

  const filterAndSortTools = (tools: ToolFromAPI[]) => {
    let filtered = tools.filter(tool => {
      const matchesSearch =
        tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        tool.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        tool.category.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesCategory = selectedCategories.length === 0 || selectedCategories.includes(tool.category);

      return matchesSearch && matchesCategory;
    });

    if (sortBy === 'name') {
      filtered.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === 'usage') {
      filtered.sort((a, b) => (b.usage_count || 0) - (a.usage_count || 0));
    } else if (sortBy === 'recent') {
      filtered.sort((a, b) => {
        const dateA = a.last_used || a.created_at || '';
        const dateB = b.last_used || b.created_at || '';
        return dateB.localeCompare(dateA);
      });
    }

    return filtered;
  };

  const renderToolCard = (tool: ToolFromAPI, index: number) => {
    const cardKey = tool.id || `${tool.name}_${index}`;

    return (
      <motion.div
        key={cardKey}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.02 * index }}
      >
        <Card
          elevation={0}
          sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
            minHeight: '180px',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 3,
            transition: 'all 0.2s ease',
            '&:hover': {
               borderColor: 'primary.main',
               transform: 'translateY(-2px)',
               boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
            }
          }}
        >
          <CardContent sx={{
            flexGrow: 1,
            display: 'flex',
            flexDirection: 'column',
            p: 2,
            '&:last-child': { pb: 2 }
          }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box sx={{
                      p: 1,
                      borderRadius: 2,
                      bgcolor: 'primary.50',
                      color: 'primary.main',
                display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
              }}>
                  {getCategoryIcon(tool.category)}
                   </Box>
                   <Box>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600, lineHeight: 1.2, fontSize: '0.95rem' }}>
                    {tool.name}
                  </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                         {tool.category}
                      </Typography>
                </Box>
                </Box>
                  {tool.is_verified && (
                   <VerifiedIcon color="success" fontSize="small" />
                  )}
              </Box>

                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                  mb: 2,
                  flexGrow: 1,
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                  lineHeight: 1.5
                  }}
                >
                  {tool.description}
                </Typography>

            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 'auto', pt: 1 }}>
               <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
                  {tool.usage_count || 0} uses
               </Typography>
               <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="contained"
                     size="small"
                     startIcon={<PlayIcon sx={{ fontSize: 16 }} />}
              onClick={() => handleUseTool(tool)}
              sx={{
                textTransform: 'none',
                        borderRadius: 2,
                        minWidth: '80px',
                        boxShadow: 'none',
                        fontSize: '0.8rem'
              }}
            >
                     Use
            </Button>
               </Box>
            </Box>
          </CardContent>
        </Card>
      </motion.div>
    );
  };

  const renderMyToolCard = (tool: ToolFromAPI, index: number) => {
    const cardKey = tool.id || `${tool.name}_${index}`;

    return (
      <motion.div
        key={cardKey}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.02 * index }}
      >
        <Card
          elevation={0}
          sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
            minHeight: '180px',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 3,
            transition: 'all 0.2s ease',
            '&:hover': {
               borderColor: 'primary.main',
               transform: 'translateY(-2px)',
               boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
            }
          }}
        >
          <CardContent sx={{
            flexGrow: 1,
            display: 'flex',
            flexDirection: 'column',
            p: 2,
            '&:last-child': { pb: 2 }
          }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box sx={{
                      p: 1,
                      borderRadius: 2,
                      bgcolor: 'secondary.50',
                      color: 'secondary.main',
                display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
              }}>
                  {getCategoryIcon(tool.category)}
                   </Box>
                   <Box>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600, lineHeight: 1.2, fontSize: '0.95rem' }}>
                    {tool.name}
                  </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                         {tool.category}
                      </Typography>
                </Box>
                </Box>
              </Box>

                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                  mb: 2,
                  flexGrow: 1,
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                  lineHeight: 1.5
                  }}
                >
                  {tool.description}
                </Typography>

            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 'auto', pt: 1 }}>
               <Typography variant="caption" color="text.secondary">
                  {new Date(tool.created_at || '').toLocaleDateString()}
               </Typography>
               <Box sx={{ display: 'flex', gap: 1 }}>
                  <IconButton
                  size="small"
                     onClick={() => handleDeleteTool(tool)}
              sx={{
                        border: '1px solid',
                        borderColor: 'error.light',
                        color: 'error.main',
                        p: 0.5,
                        '&:hover': { bgcolor: 'error.50' }
              }}
            >
                     <DeleteIcon fontSize="small" />
                  </IconButton>
            <IconButton
              size="small"
              onClick={() => handleViewTool(tool)}
                     sx={{
                        border: '1px solid',
                        borderColor: 'divider',
                        color: 'text.secondary',
                        p: 0.5
                     }}
            >
                     <ViewIcon fontSize="small" />
            </IconButton>
                  <Button
                     variant="contained"
              size="small"
                     startIcon={<PlayIcon sx={{ fontSize: 16 }} />}
                     onClick={() => handleUseTool(tool)}
                     sx={{
                        textTransform: 'none',
                        borderRadius: 2,
                        minWidth: '80px',
                        boxShadow: 'none',
                        fontSize: '0.8rem'
                     }}
            >
                     Use
                  </Button>
               </Box>
            </Box>
          </CardContent>
        </Card>
      </motion.div>
    );
  };

  const handleCategoryToggle = (category: string) => {
    setSelectedCategories(prev => {
      if (prev.includes(category)) {
        return prev.filter(c => c !== category);
      } else {
        return [...prev, category];
      }
    });
    setBuiltinPage(1);
  };

  const renderBuiltinToolsWithCategories = () => {
    const allCategories = getCategories(builtinTools);
    const filteredTools = filterAndSortTools(builtinTools);

    if (builtinTools.length === 0) return null;

    const toolsByCategory = allCategories.reduce((acc, category) => {
      acc[category] = builtinTools.filter(t => t.category === category);
      return acc;
    }, {} as Record<string, ToolFromAPI[]>);

    const totalPages = Math.ceil(filteredTools.length / ITEMS_PER_PAGE);
    const startIndex = (builtinPage - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;
    const paginatedTools = filteredTools.slice(startIndex, endIndex);

    return (
      <Accordion className="builtin-tools-section" defaultExpanded={true} sx={{ mb: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SettingsIcon color="primary" />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Built-in Tools
            </Typography>
            <Chip label={filteredTools.length} size="small" color="primary" />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {allCategories.map(cat => (
                <Chip
                  key={cat}
                  label={`${cat} (${toolsByCategory[cat].length})`}
                  onClick={() => handleCategoryToggle(cat)}
                  color={selectedCategories.includes(cat) ? 'primary' : 'default'}
                  variant={selectedCategories.includes(cat) ? 'filled' : 'outlined'}
                  sx={{ cursor: 'pointer' }}
                />
              ))}
            </Box>
          </Box>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: '1fr',
                md: 'repeat(auto-fill, minmax(280px, 1fr))'
              },
              gap: 2,
              mb: 3
            }}
          >
            {paginatedTools.map((tool, index) => renderToolCard(tool, index))}
          </Box>

          {totalPages > 1 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
              <Pagination
                count={totalPages}
                page={builtinPage}
                onChange={(_e, page) => setBuiltinPage(page)}
                color="primary"
              />
            </Box>
          )}
        </AccordionDetails>
      </Accordion>
    );
  };

  const renderToolSection = (
    title: string,
    icon: React.ReactNode,
    tools: ToolFromAPI[],
    defaultExpanded: boolean = false,
    page?: number,
    setPage?: (page: number) => void
  ) => {
    const filteredTools = filterAndSortTools(tools);

    if (tools.length === 0) return null;

    const totalPages = Math.ceil(filteredTools.length / ITEMS_PER_PAGE);
    const currentPage = page || 1;
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;
    const paginatedTools = filteredTools.slice(startIndex, endIndex);

    return (
      <Accordion defaultExpanded={defaultExpanded} sx={{ mb: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {icon}
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {title}
            </Typography>
            <Chip label={filteredTools.length} size="small" color="primary" />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          {filteredTools.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No tools match your search criteria
            </Typography>
          ) : (
            <>
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: {
                    xs: '1fr',
                    md: 'repeat(auto-fill, minmax(280px, 1fr))'
                  },
                  gap: 2,
                  mb: 3
                }}
              >
                {paginatedTools.map((tool, index) => renderToolCard(tool, index))}
              </Box>

              {totalPages > 1 && setPage && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                  <Pagination
                    count={totalPages}
                    page={currentPage}
                    onChange={(_e, newPage) => setPage(newPage)}
                    color="primary"
                  />
                </Box>
              )}
            </>
          )}
        </AccordionDetails>
      </Accordion>
    );
  };

  const renderMyToolsSection = () => {
    const filteredTools = filterAndSortTools(myTools);

    if (myTools.length === 0) return null;

    return (
      <Accordion className="custom-tools-section" defaultExpanded={false} sx={{ mb: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <PersonIcon color="secondary" />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              My Project Tools
            </Typography>
            <Chip label={filteredTools.length} size="small" color="primary" />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          {filteredTools.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No tools match your search criteria
            </Typography>
          ) : (
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: {
                  xs: '1fr',
                  md: 'repeat(auto-fill, minmax(280px, 1fr))'
                },
                gap: 2,
                mb: 3
              }}
            >
              {filteredTools.map((tool, index) => renderMyToolCard(tool, index))}
            </Box>
          )}
        </AccordionDetails>
      </Accordion>
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {error && (
          <Alert
            severity="error"
            sx={{ mb: 3 }}
            action={
              <Button color="inherit" size="small" onClick={fetchTools}>
                Retry
              </Button>
            }
          >
            {error}
          </Alert>
        )}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <Box sx={{ mb: 3, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <TextField
                placeholder="Search tools..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                size="small"
                sx={{ flexGrow: 1, minWidth: '200px' }}
                slotProps={{
                  input: {
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon />
                      </InputAdornment>
                    ),
                  }
                }}
              />
              <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>Sort By</InputLabel>
                <Select
                  value={sortBy}
                  label="Sort By"
                  onChange={(e) => setSortBy(e.target.value as any)}
                >
                  <MenuItem value="name">Name (A-Z)</MenuItem>
                  <MenuItem value="usage">Most Used</MenuItem>
                  <MenuItem value="recent">Recently Used</MenuItem>
                </Select>
              </FormControl>
            </Box>

            {renderBuiltinToolsWithCategories()}

            {renderToolSection(
              'Public Tools',
              <PublicIcon color="success" />,
              publicTools,
              false,
              publicPage,
              setPublicPage
            )}

            {renderMyToolsSection()}

            {renderToolSection(
              'MCP Tools',
              <ToolIcon color="info" />,
              mcpTools,
              false
            )}

            {builtinTools.length === 0 && publicTools.length === 0 && myTools.length === 0 && mcpTools.length === 0 && (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <ToolIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  No Tools Available
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  No tools are currently available. Check your backend connection.
                </Typography>
                <Button variant="outlined" onClick={fetchTools}>
                  Refresh
                </Button>
              </Box>
            )}
          </>
        )}

        {/* Tool Details Dialog */}
        <Dialog
          open={viewDialogOpen}
          onClose={() => setViewDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>
            {selectedTool?.name || 'Tool Details'}
          </DialogTitle>
          <DialogContent>
            {loadingDetails ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
              </Box>
            ) : toolDetails ? (
              <Box sx={{ pt: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Description:
                </Typography>
                <Typography variant="body2" paragraph>
                  {toolDetails.description}
                </Typography>

                <Typography variant="subtitle2" gutterBottom>
                  Category:
                </Typography>
                <Chip label={toolDetails.category} color="primary" size="small" sx={{ mb: 2 }} />

                <Typography variant="subtitle2" gutterBottom>
                  Tool Code:
                </Typography>
                <Box
                  sx={{
                    bgcolor: 'grey.100',
                    p: 2,
                    borderRadius: 1,
                    maxHeight: '400px',
                    overflow: 'auto',
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                    whiteSpace: 'pre-wrap',
                    mb: 2
                  }}
                >
                  {toolDetails.tool_code}
                </Box>

                <Typography variant="subtitle2" gutterBottom>
                  Metadata:
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Usage Count: {toolDetails.usage_count}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Status: {toolDetails.status}
                </Typography>
                {toolDetails.created_at && (
                  <Typography variant="body2" color="text.secondary">
                    Created: {new Date(toolDetails.created_at).toLocaleString()}
                  </Typography>
                )}
                {toolDetails.last_used_at && (
                  <Typography variant="body2" color="text.secondary">
                    Last Used: {new Date(toolDetails.last_used_at).toLocaleString()}
                  </Typography>
                )}
              </Box>
            ) : (
              <Alert severity="error">Failed to load tool details</Alert>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setViewDialogOpen(false)}>Close</Button>
          </DialogActions>
        </Dialog>
      </motion.div>
    </Box>
  );
};

const ToolsWithProtection: React.FC = () => {
  return (
    <ProtectedRoute>
      <Tools />
    </ProtectedRoute>
  );
};

export default ToolsWithProtection;
