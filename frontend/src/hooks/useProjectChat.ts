import { useState, useEffect, useCallback, useRef } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { useSelector } from 'react-redux';
import { clearMessages, addMessage, setMessages, setIsLoading } from '@/store/slices/chatSlice';
import { setSelectedProject } from '@/store/slices/chatProjectsSlice';
import { setCurrentWorkflowId as setWebSocketWorkflowId, clearWorkflowState, clearChatResponse, addWorkflowStep } from '@/store/slices/websocketSlice';
import { config } from '@/config';
import { ChatMessage } from '@/types/chat';
import { shouldUseGCSUpload, uploadLargeFile } from '@/services/gcs';

// Message state machine for avoiding race conditions
enum MessageState {
  IDLE = 'idle',
  SENDING = 'sending',
  LOADING_HISTORY = 'loading_history'
}

export const useProjectChat = (projectId: string) => {
  const dispatch = useAppDispatch();
  const [currentWorkflowId, setCurrentWorkflowId] = useState<string>('');
  const [processedResponseIds, setProcessedResponseIds] = useState<Set<string>>(new Set());
  const [messageState, setMessageState] = useState<MessageState>(MessageState.IDLE);
  const [mode, setMode] = useState<'fast' | 'deep'>('deep'); // Mode: fast (quick) or deep (full workflow)
  const isSendingRef = useRef(false); // Use ref to track sending state across async operations
  const previousProjectIdRef = useRef<string>(projectId); // Track previous projectId

  // Reset local state when projectId changes (switching projects)
  useEffect(() => {
    if (previousProjectIdRef.current !== projectId) {
      console.log(`🔄 Project changed from ${previousProjectIdRef.current} to ${projectId}, resetting state`);

      // Reset all local state to initial values
      setCurrentWorkflowId('');
      setProcessedResponseIds(new Set());
      setMessageState(MessageState.IDLE);
      setMode('deep'); // Reset to default mode
      isSendingRef.current = false;

      // Update the ref
      previousProjectIdRef.current = projectId;
    }
  }, [projectId]);

  const { 
    messages, 
    isLoading: chatLoading,
    isTyping 
  } = useAppSelector((state) => state.chat);
  
  const {
    projects
  } = useAppSelector((state) => state.chatProjects);
  
  // WebSocket state for AI responses
  const websocketState = useSelector((state: any) => state.websocket);

  // Load project data and messages
  const loadProjectData = useCallback(async () => {
      if (projectId) {
        // Skip entire loading process if in SENDING state (use ref for reliability)
        if (messageState === MessageState.SENDING || isSendingRef.current) {
          console.log('🔒 Skipping project data load - currently sending message');
          return; // Exit immediately, don't touch any state
        }

        console.log('🔄 Loading project data in IDLE state');
        setMessageState(MessageState.LOADING_HISTORY);

        // Load project info first (to get project name and details)
        try {
          const { fetchSingleProject } = await import('@/store/slices/chatProjectsSlice');
          await dispatch(fetchSingleProject(projectId));
          console.log('✅ Loaded project info for:', projectId);
        } catch (error) {
          console.error('❌ Failed to load project info:', error);
        }

        // Set current project
        dispatch(setSelectedProject(projectId));

        // Set loading state to prevent showing welcome screen
        dispatch(setIsLoading(true));

        // Clear previous messages
        dispatch(clearMessages());



        const { clearChatResponse } = await import('@/store/slices/websocketSlice');
        dispatch(clearChatResponse());
        console.log('🧹 Cleared chat response for new project');
        
        console.log('🧹 Cleared messages for project:', projectId);
        
        // Set current project for middleware workflow isolation
        try {
          const { setCurrentProjectForWorkflow } = await import('@/store/middleware/websocketMiddleware');
          setCurrentProjectForWorkflow(projectId);
          console.log('🎯 Set middleware to filter workflow for project:', projectId);
        } catch (e) {
          console.error('Failed to set middleware project filter:', e);
        }
      
      // Load project's message history
      try {
        const token = localStorage.getItem('auth_token');
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        };
        
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }

          const response = await fetch(`${config.api.baseUrl}/api/v1/chat/projects/${projectId}/messages`, {
            headers,
            credentials: 'include',
          });

          if (response.ok) {
            const messagesData = await response.json();
            // Convert backend format to frontend format
            const convertedMessages = messagesData.map((msg: any) => ({
              id: msg.id,
              type: msg.role, // backend uses 'role', frontend uses 'type'
              content: msg.content,
              timestamp: msg.created_at,
              metadata: msg.message_metadata
            }));
            
            // Double check before applying messages (final protection)
            if (!isSendingRef.current) {
              dispatch(setMessages(convertedMessages));
              // Clear loading state immediately after setting messages
              dispatch(setIsLoading(false));
              console.log(`✅ Loaded ${convertedMessages.length} messages for project`);
            } else {
              console.log('🔒 Skipped setMessages - user is sending a message');
              dispatch(setIsLoading(false));
            }

          // Load project workflow history
          // Note: Workflow steps are primarily received via WebSocket for real-time updates
          // Historical workflow data is available but steps may be empty if not properly saved
          await loadProjectWorkflows(projectId, headers);
        } else {
          console.error('Failed to load project messages');
          // Clear loading state even if no messages
          dispatch(setIsLoading(false));
        }
      } catch (error) {
        console.error('Error loading project messages:', error);
        // Clear loading state on error
        dispatch(setIsLoading(false));
      }

      // Return to IDLE state after loading
      setMessageState(MessageState.IDLE);
      console.log('✅ Project data loaded, returned to IDLE state');
    }
  }, [dispatch, projectId, messageState]);

  // Send message to project
  const sendMessage = useCallback(async (messageContent: string) => {
    // Enter SENDING state to protect message from being cleared
    console.log('📤 Entering SENDING state');
    setMessageState(MessageState.SENDING);
    isSendingRef.current = true; // Set ref immediately
    
    const userMessage = {
      id: `user_${Date.now()}`,
      type: 'user' as const,
      content: messageContent,
      timestamp: new Date().toISOString()
    };

    // Add user message to UI immediately
    dispatch(addMessage(userMessage));
    dispatch(setIsLoading(true));
    
    // Don't clear workflow state when sending new messages in same project
    // Only clear when switching projects
    
    // If this is the first message in a new project, prevent loadProjectData from clearing it
    if (messages.length === 0) {
      console.log('🆕 First message in new project - will skip history loading');
    }

    try {
      // 1. Determine which API to use based on engine
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // V2: Use LangChain API (project-based messages with chat history)
      console.log('🚀 Using LangChain V2 API (with chat history)');
      const response = await fetch(`${config.api.baseUrl}/api/v2/chat/projects/${projectId}/messages`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          content: messageContent,
          role: 'user',
          mode: mode  // Pass mode (fast/deep) to backend
        }),
      });

      if (response.ok) {
        console.log('✅ Message sent successfully');

        // Parse response
        try {
          const responseData = await response.json();

          // V2 response format: {success, data: {workflow_id, ...}}
          if (responseData.data && responseData.data.workflow_id) {
            console.log('🆔 Setting workflow ID from V2 API:', responseData.data.workflow_id);
            setCurrentWorkflowId(responseData.data.workflow_id);
            dispatch(setWebSocketWorkflowId(responseData.data.workflow_id));
          }

          // AI processing is triggered by the V2 project message API automatically
          // AI response will arrive via WebSocket and be saved to database
          console.log('✅ V2 message sent, AI processing started automatically with chat history');
        } catch (e) {
          console.log('⚠️ Could not parse API response:', e);
        }

        // Return to IDLE state after successful send
        setMessageState(MessageState.IDLE);
        isSendingRef.current = false; // Clear ref
        console.log('✅ Returned to IDLE state after sending message');
      } else {
        console.error('Failed to send message');
        dispatch(setIsLoading(false));
        setMessageState(MessageState.IDLE);
        isSendingRef.current = false; // Clear ref on error
      }
    } catch (error) {
      console.error('Error sending message:', error);
      dispatch(setIsLoading(false));
      setMessageState(MessageState.IDLE);
      isSendingRef.current = false; // Clear ref on error
    }
  }, [dispatch, projectId, mode, messages.length]);

  // Send message with multiple files to project
  // Uses existing single-file API, sends first file with message, rest are uploaded separately
  // Optional previewUrls can be provided for files that have accessible URLs (like demo videos)
  const sendMessageWithFiles = useCallback(async (
    messageContent: string,
    files: File[],
    options?: { previewUrls?: string[] }
  ) => {
    // Enter SENDING state to protect message from being cleared
    console.log(`📎 Entering SENDING state for ${files.length} file(s)`);
    setMessageState(MessageState.SENDING);
    isSendingRef.current = true; // Set ref immediately

    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      type: 'user' as const,
      content: messageContent,
      timestamp: new Date().toISOString(),
      metadata: {
        attached_files: files.map((file, index) => ({
          filename: file.name,
          size: file.size,
          type: file.type,
          previewUrl: options?.previewUrls?.[index] // Store preview URL for videos
        }))
      }
    };

    // Add user message to UI immediately
    dispatch(addMessage(userMessage));
    dispatch(setIsLoading(true));

    try {
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {};

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Get user ID from token for GCS upload
      let userId = 'anonymous';
      if (token) {
        try {
          const decoded = JSON.parse(atob(token));
          userId = decoded.sub || decoded.id || 'anonymous';
        } catch {
          // Keep anonymous
        }
      }

      // Check if any file needs GCS upload (large files)
      const largeFiles = files.filter(f => shouldUseGCSUpload(f));
      const smallFiles = files.filter(f => !shouldUseGCSUpload(f));

      // Upload large files to GCS first and collect file_ids
      const gcsFileIds: string[] = [];
      for (const largeFile of largeFiles) {
        console.log(`📤 Large file detected: ${largeFile.name} (${(largeFile.size / (1024 * 1024)).toFixed(1)}MB), using GCS upload`);

        const { file_id, gcs_uri } = await uploadLargeFile(
          largeFile,
          userId,
          projectId,
          (progress) => {
            console.log(`📤 Upload progress for ${largeFile.name}: ${progress.percentage}%`);
          }
        );

        if (file_id) {
          console.log(`✅ ${largeFile.name} uploaded to GCS:`, gcs_uri, 'file_id:', file_id);
          gcsFileIds.push(file_id);
        }
      }

      // Build form data for multi-file upload
      const formData = new FormData();
      formData.append('message', messageContent);
      formData.append('mode', mode);
      formData.append('use_multi_agent', 'true');

      // Add GCS file IDs (comma-separated)
      if (gcsFileIds.length > 0) {
        formData.append('file_ids', gcsFileIds.join(','));
      }

      // Add small files directly
      for (const smallFile of smallFiles) {
        console.log(`📎 Small file: ${smallFile.name} (${(smallFile.size / (1024 * 1024)).toFixed(1)}MB), direct upload`);
        formData.append('files', smallFile);
      }

      // Use files endpoint (supports 1-5 files)
      // For large file uploads, bypass Next.js proxy and call backend directly
      // This avoids the proxy body size limit issue
      const fileUploadBaseUrl = process.env.NEXT_PUBLIC_BACKEND_DIRECT_URL || config.api.baseUrl;
      const response = await fetch(`${fileUploadBaseUrl}/api/v2/chat/projects/${projectId}/messages/with-files`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: formData,
      });

      if (response.ok) {
        console.log(`✅ Message with ${files.length} file(s) sent successfully`);
        try {
          const responseData = await response.json();
          if (responseData.data && responseData.data.workflow_id) {
            console.log('🆔 Setting workflow ID:', responseData.data.workflow_id);
            setCurrentWorkflowId(responseData.data.workflow_id);
          }
        } catch (e) {
          console.log('⚠️ Could not parse API response');
        }
        setMessageState(MessageState.IDLE);
        isSendingRef.current = false;
      } else {
        const errorData = await response.json();
        console.error('Failed to send message with files:', errorData);
        dispatch(setIsLoading(false));
        setMessageState(MessageState.IDLE);
        isSendingRef.current = false;
      }
    } catch (error) {
      console.error('Error sending message with files:', error);
      dispatch(setIsLoading(false));
      setMessageState(MessageState.IDLE);
      isSendingRef.current = false;
    }
  }, [dispatch, projectId, mode]);

  // Send a demo video for analysis
  // Fetches the video from public URL and sends it with a prompt
  // Stores the original URL so the video can be previewed after sending
  const sendDemoVideo = useCallback(async (videoUrl: string, prompt: string) => {
    try {
      console.log(`📹 Fetching demo video from: ${videoUrl}`);

      // Fetch the video file from public URL
      const response = await fetch(videoUrl);
      if (!response.ok) {
        throw new Error(`Failed to fetch video: ${response.statusText}`);
      }

      const blob = await response.blob();

      // Extract filename from URL
      const filename = videoUrl.split('/').pop() || 'demo_video.mp4';

      // Create a File object from the blob
      const videoFile = new File([blob], filename, { type: 'video/mp4' });

      console.log(`📹 Demo video loaded: ${filename} (${(videoFile.size / (1024 * 1024)).toFixed(1)}MB)`);

      // Send the video with the prompt, including the preview URL so users can watch it later
      await sendMessageWithFiles(prompt, [videoFile], { previewUrls: [videoUrl] });

    } catch (error) {
      console.error('Error sending demo video:', error);
      dispatch(setIsLoading(false));
      setMessageState(MessageState.IDLE);
      isSendingRef.current = false;
    }
  }, [sendMessageWithFiles, dispatch]);

  // Load project workflow history
  const loadProjectWorkflows = useCallback(async (projectId: string, headers: Record<string, string>) => {
    try {
      const workflowResponse = await fetch(`${config.api.baseUrl}/api/v1/chat/projects/${projectId}/workflows`, {
        headers,
        credentials: 'include',
      });

      if (workflowResponse.ok) {
        const workflowData = await workflowResponse.json();
        if (workflowData.success && workflowData.data && workflowData.data.workflows) {
          let totalSteps = 0;
          workflowData.data.workflows.forEach((workflow: any) => {
            // Ensure only processing workflow for current project
            if (workflow.workflow_id && workflow.workflow_id.includes(`project_${projectId}_`)) {
              if (workflow.steps && workflow.steps.length > 0) {
                workflow.steps.forEach((step: any) => {
                  const workflowStep = {
                    id: step.id,
                    type: step.type || 'thinking',
                    title: step.title || step.type,
                    description: step.description,
                    tool_name: step.tool_name,
                    tool_result: step.tool_result,
                    step_number: step.step_index,
                    timestamp: step.started_at || workflow.started_at,
                    workflow_id: workflow.workflow_id,
                    status: step.status,
                    // Include new Agent-aware fields and visualization metadata
                    agent_name: step.agent_name,
                    agent_task: step.agent_task,
                    execution_result: step.execution_result,
                    execution_duration: step.execution_duration,
                    step_metadata: step.step_metadata // ✅ This contains visualizations!
                  };
                  dispatch(addWorkflowStep(workflowStep));
                  totalSteps++;
                });
                console.log(`✅ Loaded ${workflow.steps.length} workflow steps for workflow ${workflow.workflow_id}`);
              }
            } else {
              console.log(`🚫 Skipped workflow from different project: ${workflow.workflow_id}`);
            }
          });
          console.log(`✅ Loaded ${totalSteps} total workflow steps for project ${projectId}`);
        }
      } else {
        console.log('ℹ️ No workflow history found for project (or access denied)');
      }
    } catch (error) {
      console.error('Error loading project workflow history:', error);
    }
  }, [dispatch]);

  // Set workflow ID from WebSocket if not already set
  useEffect(() => {
    if (!currentWorkflowId && websocketState.currentWorkflowId && 
        websocketState.currentWorkflowId.includes(`project_${projectId}_`)) {
      console.log('🆔 Setting workflow ID from WebSocket:', websocketState.currentWorkflowId);
      setCurrentWorkflowId(websocketState.currentWorkflowId);
    }
  }, [websocketState.currentWorkflowId, currentWorkflowId, projectId]);

  // Handle WebSocket AI responses for projects
  useEffect(() => {
    console.log('🔍 useProjectChat: Checking WebSocket response:', {
      lastChatResponse: websocketState.lastChatResponse,
      currentWorkflowId: websocketState.currentWorkflowId,
      expectedWorkflowId: currentWorkflowId,
      projectId
    });

    if (websocketState.lastChatResponse && 
        websocketState.currentWorkflowId && 
        websocketState.currentWorkflowId === currentWorkflowId) {

      const response = websocketState.lastChatResponse;
      console.log('📨 useProjectChat: Processing WebSocket response:', response);
      
      // Check if we've already processed this response
      const responseId = response.id || response.workflow_id || `${response.timestamp}_${response.content?.substring(0, 50)}`;
      if (processedResponseIds.has(responseId)) {
        console.log('⚠️ useProjectChat: Response already processed, skipping:', responseId);
        return;
      }
      
      // Check if this is a project-related response
      if (response.project_id === projectId && response.action === 'project_updated') {
        console.log('🔄 Project updated via WebSocket, adding AI response...');
        // Don't reload all data, just add the new AI response
        const assistantMessage = {
          id: response.id || `assistant_${Date.now()}`,
          type: 'assistant' as const,
          content: response.content || response.response || response.message || 'Response received via WebSocket',
          timestamp: response.timestamp || new Date().toISOString(),
          metadata: {
            execution_time: response.metadata?.execution_time || 0,
            using_real_labos: true,
            agent_id: response.metadata?.agent_id,
            workflow_id: websocketState.currentWorkflowId,
            project_id: response.project_id,
            follow_up_questions: response.follow_up_questions || []
          }
        };

        console.log('📝 useProjectChat: Adding message with follow-up questions:', response.follow_up_questions);
        dispatch(addMessage(assistantMessage));
        dispatch(setIsLoading(false));
        setCurrentWorkflowId(''); // Clear workflow ID

        // Mark response as processed
        setProcessedResponseIds(prev => new Set(prev).add(responseId));

        // Clear the processed response to prevent re-processing
        dispatch(clearChatResponse());
      } else if (websocketState.currentWorkflowId === currentWorkflowId) {
        console.log('📝 useProjectChat: Handling response directly (fallback)');
        // Fallback: Handle response directly (for backward compatibility)
        const assistantMessage = {
          id: `assistant_${Date.now()}`,
          type: 'assistant' as const,
          content: response.content || response.response || response.message || 'Response received via WebSocket',
          timestamp: new Date().toISOString(),
          metadata: {
            execution_time: response.metadata?.execution_time || 0,
            using_real_labos: true,
            agent_id: response.metadata?.agent_id,
            workflow_id: websocketState.currentWorkflowId,
            follow_up_questions: response.follow_up_questions || []
          }
        };

        dispatch(addMessage(assistantMessage));
        dispatch(setIsLoading(false));
        setCurrentWorkflowId(''); // Clear workflow ID
        
        // Mark response as processed
        setProcessedResponseIds(prev => new Set(prev).add(responseId));
        
        // Clear the processed response to prevent re-processing
        dispatch(clearChatResponse());
      } else {
        console.log('❌ useProjectChat: Response conditions not met:', {
          responseProjectId: response.project_id,
          expectedProjectId: projectId,
          responseAction: response.action,
          workflowMatches: websocketState.currentWorkflowId === currentWorkflowId
        });
      }
    } else {
      console.log('❌ useProjectChat: WebSocket response conditions not met');
    }
  }, [websocketState.lastChatResponse, websocketState.currentWorkflowId, currentWorkflowId, dispatch, projectId]);

  // Subscribe to project WebSocket room when projectId changes
  useEffect(() => {
    if (!projectId) return;

    console.log('📌 Subscribing to project WebSocket room:', projectId);

    // Flag to track if subscription is active
    let isSubscribed = false;

    // Import and subscribe
    import('@/services/websocket/manager').then(({ subscribeToProject }) => {
      subscribeToProject(projectId);
      isSubscribed = true;
    });

    // Cleanup: unsubscribe when component unmounts or projectId changes
    return () => {
      if (isSubscribed) {
        console.log('📌 Unsubscribing from project WebSocket room:', projectId);
        import('@/services/websocket/manager').then(({ unsubscribeFromProject }) => {
          unsubscribeFromProject(projectId);
        });
      }
    };
  }, [projectId]);

  // Load project data only when projectId changes (not when other dependencies change)
  useEffect(() => {
    console.log('🔍 useEffect triggered - projectId changed to:', projectId);
    loadProjectData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]); // Only depend on projectId to avoid clearing messages when sending

  // Stop current processing
  const stopProcessing = useCallback(async () => {
    // Always clear local states first
    dispatch(setIsLoading(false));
    dispatch(clearWorkflowState());
    console.log('🧹 Cleared local loading states');
    
    if (!websocketState.currentWorkflowId) {
      console.warn('⚠️ No currentWorkflowId, but cleared local states');
      return;
    }

    console.log('🛑 Stopping workflow:', websocketState.currentWorkflowId);
    
    try {
      // Prepare headers with auth token
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      // Use relative path, Next.js will rewrite to backend
      const response = await fetch(
        `/api/v1/chat/projects/${projectId}/workflows/${websocketState.currentWorkflowId}/cancel`,
        {
          method: 'POST',
          credentials: 'include',
          headers
        }
      );

      if (response.ok) {
        console.log('✅ Successfully stopped backend workflow');
        
        // Clear the workflow ID
        setCurrentWorkflowId('');
      } else {
        console.warn('⚠️ Failed to stop backend workflow:', await response.text());
      }
    } catch (error) {
      console.error('❌ Error stopping workflow:', error);
    }
  }, [websocketState.currentWorkflowId, projectId, dispatch]);

  // Check if current project still exists
  const projectExists = projects.some(p => p.id === projectId);

  const project = projects.find(p => p.id === projectId);

  return {
    // Data
    messages,
    project,

    // States
    chatLoading,
    isTyping,
    mode,

    // Actions
    sendMessage,
    sendMessageWithFiles,
    sendDemoVideo,
    stopProcessing,
    loadProjectData,
    setMode,

    // Computed
    projectExists
  };
};
