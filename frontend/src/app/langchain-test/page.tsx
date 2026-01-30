'use client'

import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  CircularProgress,
  ToggleButtonGroup,
  ToggleButton,
  Alert,
  Switch,
  FormControlLabel,
  Card,
  CardContent,
  Chip,
  Divider
} from '@mui/material';
import { ArrowBack, Psychology, Build, CheckCircle } from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { setCurrentWorkflowId, clearWorkflowState } from '@/store/slices/websocketSlice';

export default function LangChainTest() {
  const router = useRouter();
  const dispatch = useAppDispatch();

  const [query, setQuery] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [modelType, setModelType] = useState('gemini');
  const [useWebSocket, setUseWebSocket] = useState(false);
  const [workflowId, setWorkflowId] = useState<string | null>(null);

  // Get workflow steps from Redux store
  const workflowSteps = useAppSelector((state) => state.websocket.workflowSteps);
  const isConnected = useAppSelector((state) => state.websocket.isConnected);

  // Clear workflow state when starting new query
  useEffect(() => {
    if (loading && useWebSocket) {
      dispatch(clearWorkflowState());
    }
  }, [loading, useWebSocket, dispatch]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResponse('');
    setWorkflowId(null);

    try {
      const res = await fetch('/api/v2/chat/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          model_type: modelType,
          use_websocket: useWebSocket,
          project_id: 'langchain-test', // For WebSocket room isolation
        }),
      });

      const data = await res.json();

      if (data.success) {
        setResponse(data.output);

        // If WebSocket was used, set the workflow ID
        if (data.workflow_id) {
          setWorkflowId(data.workflow_id);
          dispatch(setCurrentWorkflowId(data.workflow_id));
        }
      } else {
        setError(data.error || 'Unknown error');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 900, mx: 'auto', p: 4 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => router.push('/dashboard')}
          sx={{ mr: 2 }}
        >
          Back
        </Button>
        <Typography variant="h4">
          LangChain API Test (V2)
        </Typography>
      </Box>

      <Alert severity="info" sx={{ mb: 3 }}>
        This page tests the new LangChain-based API (v2) with direct model integration (Gemini/Claude/GPT)
        {useWebSocket && isConnected && (
          <Typography variant="caption" display="block" sx={{ mt: 1 }}>
            WebSocket Connected - Real-time streaming enabled
          </Typography>
        )}
      </Alert>

      {/* Input Form */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <form onSubmit={handleSubmit}>
          {/* Model Selection */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Model
            </Typography>
            <ToggleButtonGroup
              value={modelType}
              exclusive
              onChange={(_, newModel) => newModel && setModelType(newModel)}
              aria-label="model type"
              size="small"
            >
              <ToggleButton value="gemini">Gemini</ToggleButton>
              <ToggleButton value="claude">Claude</ToggleButton>
              <ToggleButton value="gpt">GPT</ToggleButton>
            </ToggleButtonGroup>
          </Box>

          {/* WebSocket Toggle */}
          <Box sx={{ mb: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={useWebSocket}
                  onChange={(e) => setUseWebSocket(e.target.checked)}
                  disabled={!isConnected}
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2">
                    Enable WebSocket Streaming
                  </Typography>
                  {!isConnected && (
                    <Chip label="Offline" size="small" color="error" />
                  )}
                </Box>
              }
            />
            <Typography variant="caption" color="text.secondary" display="block">
              Shows step-by-step reasoning and tool execution in real-time
            </Typography>
          </Box>

          {/* Query Input */}
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Your Question"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., What is DNA made of?"
            sx={{ mb: 2 }}
          />

          {/* Submit Button */}
          <Button
            type="submit"
            variant="contained"
            disabled={loading || !query.trim()}
            fullWidth
            size="large"
          >
            {loading ? (
              <>
                <CircularProgress size={20} sx={{ mr: 1 }} />
                Processing...
              </>
            ) : (
              'Send to LangChain (V2)'
            )}
          </Button>
        </form>
      </Paper>

      {/* Workflow Steps Display */}
      {useWebSocket && workflowSteps.length > 0 && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Workflow Steps {workflowId && `(ID: ${workflowId.slice(0, 8)}...)`}
          </Typography>
          <Divider sx={{ mb: 2 }} />
          {workflowSteps.map((step, index) => (
            <Card key={index} sx={{ mb: 2, border: '1px solid', borderColor: 'divider' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  {step.type === 'thinking' && <Psychology color="primary" />}
                  {step.type === 'tool_execution' && <Build color="success" />}
                  {step.type === 'synthesis' && <CheckCircle color="info" />}
                  <Typography variant="subtitle1" fontWeight="bold">
                    {step.title || `Step ${step.step_number}`}
                  </Typography>
                  <Chip
                    label={step.type}
                    size="small"
                    color={
                      step.type === 'thinking' ? 'primary' :
                      step.type === 'tool_execution' ? 'success' : 'info'
                    }
                  />
                </Box>

                {step.description && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {step.description}
                  </Typography>
                )}

                {step.tool_name && (
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    <strong>Tool:</strong> {step.tool_name}
                  </Typography>
                )}

                {step.tool_result && (
                  <Paper sx={{ p: 2, bgcolor: 'grey.50', mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      Result:
                    </Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', mt: 0.5 }}>
                      {typeof step.tool_result === 'string'
                        ? step.tool_result
                        : JSON.stringify(step.tool_result, null, 2)}
                    </Typography>
                  </Paper>
                )}

                {step.observations && step.observations.length > 0 && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      Observations:
                    </Typography>
                    {step.observations.map((obs, i) => (
                      <Typography key={i} variant="body2" sx={{ ml: 2, fontStyle: 'italic' }}>
                        • {typeof obs === 'string' ? obs : obs.message}
                      </Typography>
                    ))}
                  </Box>
                )}

                {step.step_metadata?.visualizations && step.step_metadata.visualizations.length > 0 && (
                  <Alert severity="info" sx={{ mt: 1 }}>
                    Visualization: {step.step_metadata.visualizations[0].type}
                  </Alert>
                )}

                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                  {new Date(step.timestamp).toLocaleTimeString()}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </Paper>
      )}

      {/* Error Display */}
      {error && (
        <Paper sx={{ p: 3, mb: 3, bgcolor: 'error.light' }}>
          <Typography color="error" sx={{ whiteSpace: 'pre-wrap' }}>
            Error: {error}
          </Typography>
        </Paper>
      )}

      {/* Response Display */}
      {response && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Final Response:
          </Typography>
          <Typography sx={{ whiteSpace: 'pre-wrap' }}>
            {response}
          </Typography>
        </Paper>
      )}
    </Box>
  );
}
