"""
Simple Workflow Callback for smolagents
Uses official callback mechanism but with minimal, focused event emission.
"""

from typing import Any, Optional, Dict
from datetime import datetime
import logging

from smolagents.memory import ActionStep
from .workflow_context import (
    get_workflow_context,
    emit_tool_call_event,
    emit_observation_event,
    get_and_clear_thinking_steps,
    emit_agent_execution_start,
    update_agent_execution_result,
    add_tool_to_active_agent
)

# Use logger instead of print for smolagents callback
logger = logging.getLogger('smolagents.callback')


class AgentAwareWorkflowCallback:
    """
    Agent-aware workflow callback that tracks execution at Agent level.
    
    This callback:
    1. Detects Agent calls (dev_agent, critic_agent, etc.)
    2. Tracks tool executions within agent steps
    3. Records agent completion with results
    4. Maintains hierarchical workflow structure
    """
    
    def __call__(self, step: ActionStep) -> ActionStep:
        """Official smolagents callback function"""
        context = get_workflow_context()
        if not context:
            return step  # No workflow context, skip

        # Check if workflow was cancelled before processing this step
        try:
            from app.services.workflows.workflow_context import check_cancellation, is_workflow_cancelled, get_workflow_id

            # Debug: Check current state
            current_workflow_id = get_workflow_id()
            is_cancelled = is_workflow_cancelled()
            logger.info(f"🔍 Callback debug: workflow_id={current_workflow_id}, is_cancelled={is_cancelled}")

            check_cancellation()
        except Exception as e:
            if "cancelled" in str(e).lower():
                logger.info(f"🛑 Callback: Workflow cancelled, interrupting step processing")

                # Method 1: Set error to stop agent
                step.error = f"Workflow was cancelled by user: {str(e)}"

                # Method 2: Try to force agent to stop by setting step as final
                if hasattr(step, 'is_final_answer'):
                    step.is_final_answer = True
                    logger.info(f"🛑 Callback: Marked step as final answer to stop agent")

                # Method 3: Raise exception to interrupt agent execution
                from app.services.workflows.workflow_context import WorkflowCancelledException
                logger.info(f"🛑 Callback: Raising exception to interrupt agent")
                raise WorkflowCancelledException(f"Workflow {current_workflow_id} was cancelled")

                return step
            else:
                logger.info(f"🔍 Callback: Non-cancellation exception: {e}")

        # Debug logging (simplified)
        logger.info(f"📢 Workflow callback triggered")

        # STEP 0: Extract and broadcast Agent's Thought (reasoning) before code execution
        if hasattr(step, 'model_output') and step.model_output:
            thought = self._extract_thought(step.model_output)
            if thought:
                # Broadcast the thought as a workflow step
                emit_observation_event(
                    observation=thought,
                    tool_name="agent_thought"
                )
                logger.info(f"💭 Agent thought: {thought[:150]}...")
        
        # 1. Check if this is an Agent call or tool call
        if hasattr(step, 'tool_calls') and step.tool_calls:
            for tool_call in step.tool_calls:
                if hasattr(tool_call, 'name'):
                    tool_name = tool_call.name
                    logger.info(f"🔍 Processing tool: {tool_name}")
                    
                    # Handle python_interpreter specially - extract agent and tool calls
                    if tool_name == 'python_interpreter':
                        code = getattr(tool_call, 'arguments', '')

                        # Check if this is an agent call
                        agent_call = self._extract_agent_call(code)
                        if agent_call:
                            # This is an Agent delegation - record as Agent execution
                            emit_tool_call_event(agent_call['name'], {'task': agent_call['task']}, is_agent=True)
                            logger.info(f"🤖 Callback: Detected agent call: {agent_call['name']}")
                        else:
                            # Not an agent call - this is Manager executing code directly
                            logger.info(f"💻 Callback: Manager executing code directly")

                            # Emit python_interpreter call so user sees code execution
                            emit_tool_call_event('python_interpreter', {'code': code})

                            # Also check for direct tool usage in python_interpreter
                            direct_tools = self._extract_direct_tool_calls(code)
                            if direct_tools:
                                logger.info(f"🔧 Callback: Manager used {len(direct_tools)} tool(s) directly via python_interpreter")
                                # Emit each tool call event
                                for tool_name in direct_tools:
                                    emit_tool_call_event(tool_name, {'via': 'python_interpreter'})
                                # Store these for later when we get the observation
                                if not hasattr(step, '_manager_direct_tools'):
                                    step._manager_direct_tools = []
                                step._manager_direct_tools.extend(direct_tools)
                    else:
                        # Direct tool call (common in ToolCallingAgent like Manager Agent)
                        tool_args = getattr(tool_call, 'arguments', {})
                        
                        # Check if this is an agent call (tool name ends with _agent)
                        is_agent_call = tool_name.endswith('_agent')
                        
                        if is_agent_call:
                            # Extract task from arguments
                            task = tool_args.get('task', '') if isinstance(tool_args, dict) else str(tool_args)
                            emit_tool_call_event(tool_name, {'task': task}, is_agent=True)
                            logger.info(f"🤖 Callback: Direct agent call detected: {tool_name}")
                        else:
                            # Regular tool call
                            emit_tool_call_event(tool_name, tool_args)
                            logger.info(f"🛠️ Callback: Direct tool call detected: {tool_name}")
        else:
            logger.info(f"🔍 No tool calls to process")
        
        # 2. Process tool observations - collect for active agent OR detect agent completion
        if hasattr(step, 'observations') and step.observations:
            # Handle both list and string types
            observations_list = step.observations if isinstance(step.observations, list) else [step.observations]

            # Check if any observation contains agent completion message
            agent_completed = False
            for idx, obs in enumerate(observations_list):
                obs_str = str(obs)

                if 'final answer from your managed agent' in obs_str.lower():
                    agent_completed = True
                    logger.info(f"🎯 Detected agent completion")
                    break

            # If agent just completed, extract tools and visualizations
            if agent_completed:
                # Re-check context in case it changed
                current_ctx = get_workflow_context()

                if current_ctx and 'active_agent_steps' in current_ctx.metadata and current_ctx.metadata['active_agent_steps']:
                    active_agents = list(current_ctx.metadata['active_agent_steps'].keys())
                    if active_agents:
                        agent_name = active_agents[-1]

                        # Extract tools and visualizations
                        tools_used_from_obs = []
                        visualizations = []
                        result = ""

                        # Check if Manager used tools directly (stored in step._manager_direct_tools)
                        if hasattr(step, '_manager_direct_tools') and step._manager_direct_tools:
                            logger.info(f"🔧 Found {len(step._manager_direct_tools)} Manager direct tool(s): {step._manager_direct_tools}")
                            for tool_name in step._manager_direct_tools:
                                tools_used_from_obs.append({
                                    "name": tool_name,
                                    "status": "success",
                                    "description": f"Manager directly called {tool_name}"
                                })

                        import re
                        for obs in observations_list:
                            obs_str = str(obs)

                            if 'final answer from your managed agent' in obs_str.lower():
                                result = obs_str

                                # Parse structured format from agent's response
                                # Section 1: Task outcome (short version)
                                outcome_match = re.search(r'###\s*1\.\s*Task outcome.*?:\s*([^#]+?)(?=###|$)', obs_str, re.IGNORECASE | re.DOTALL)
                                task_outcome = outcome_match.group(1).strip() if outcome_match else ""

                                # Section 2: Detailed version - extract tools from here
                                detailed_match = re.search(r'###\s*2\.\s*Task outcome.*?detailed.*?:(.*?)(?=###|\Z)', obs_str, re.IGNORECASE | re.DOTALL)
                                detailed_section = detailed_match.group(1) if detailed_match else obs_str

                                # Extract tools from detailed section
                                # Look for tool mentions like "using the create_bar_chart tool" or "I created...using create_bar_chart"
                                tool_usage_patterns = [
                                    r'using\s+(?:the\s+)?(\w+)\s+tool',
                                    r'called?\s+(\w+)\s+(?:tool|function)',
                                    r'invoked?\s+(\w+)',
                                    r'used\s+(\w+)\s+to',
                                ]

                                found_tool_names = set()
                                for pattern in tool_usage_patterns:
                                    matches = re.findall(pattern, detailed_section, re.IGNORECASE)
                                    found_tool_names.update(m.lower() for m in matches if 'create' in m.lower() or 'save' in m.lower())

                                # Also directly search for known tool names
                                known_tools = [
                                    # Visualization tools
                                    'create_line_chart', 'create_bar_chart', 'create_pie_chart',
                                    'create_scatter_plot', 'create_heatmap', 'create_distribution_plot',
                                    # File tools
                                    'save_agent_file', 'read_project_file',
                                    # Search and research tools
                                    'query_pubmed', 'search_pubmed', 'search_google', 'search_arxiv',
                                    'enhanced_google_search', 'multi_source_search', 'visit_webpage',
                                    # GitHub tools
                                    'search_github_repositories', 'search_github_code',
                                    # Data tools
                                    'extract_pdf_content', 'extract_url_content'
                                ]
                                for tool in known_tools:
                                    if tool in obs_str.lower():
                                        found_tool_names.add(tool)

                                # Build tools_used list with context from detailed section
                                for tool_name in found_tool_names:
                                    # Try to extract context around the tool mention
                                    context_pattern = rf'([^.]*{tool_name}[^.]*\.)'
                                    context_match = re.search(context_pattern, detailed_section, re.IGNORECASE)
                                    tool_context = context_match.group(1).strip() if context_match else f"Used {tool_name}"  # Don't truncate

                                    tools_used_from_obs.append({
                                        "name": tool_name,
                                        "status": "success",
                                        "description": tool_context
                                    })

                                # Extract key technical details if present
                                tech_details = []
                                file_id_match = re.search(r'File ID:\s*([a-f0-9-]+)', obs_str, re.IGNORECASE)
                                if file_id_match:
                                    tech_details.append(f"File ID: {file_id_match.group(1)}")

                                file_size_match = re.search(r'File Size:\s*([\d,]+)\s*bytes', obs_str, re.IGNORECASE)
                                if file_size_match:
                                    tech_details.append(f"Size: {file_size_match.group(1)} bytes")

                                resolution_match = re.search(r'Resolution:\s*(\d+x\d+)', obs_str, re.IGNORECASE)
                                if resolution_match:
                                    tech_details.append(f"Resolution: {resolution_match.group(1)}")

                                key_details = " | ".join(tech_details) if tech_details else ""

                                # Use FULL observation string as result, not just task_outcome
                                # The frontend ExpandableDescription component will handle truncation
                                # Keeping full content ensures users can expand to see everything
                                result = obs_str  # Keep full content instead of just short summary

                                logger.info(f"📊 Parsed agent response: outcome={bool(task_outcome)}, tools={len(tools_used_from_obs)}, details={bool(key_details)}, full_length={len(result)}")

                            # Extract file_id
                            file_match = re.search(r'file ID\s+([a-f0-9-]+)', obs_str)
                            if not file_match:
                                file_match = re.search(r'\(file_id:\s*([a-f0-9-]+)\)', obs_str)

                            if file_match:
                                file_id = file_match.group(1)
                                filename_match = re.search(r'(?:saved as|chart has been saved as)\s*["\']?([^\s"\']+\.(?:png|jpg|jpeg))', obs_str, re.IGNORECASE)
                                filename = filename_match.group(1) if filename_match else "visualization.png"

                                visualizations.append({
                                    "type": "chart",
                                    "file_id": file_id,
                                    "title": filename.replace('.png', '').replace('_', ' ').title(),
                                    "filename": filename
                                })
                                logger.info(f"📊 Extracted visualization: {filename} (ID: {file_id})")

                        # Update agent's tools_used in context
                        if tools_used_from_obs:
                            current_ctx.metadata['active_agent_steps'][agent_name]['tools_used'] = tools_used_from_obs
                            logger.info(f"🔧 Extracted {len(tools_used_from_obs)} tools from agent response: {[t['name'] for t in tools_used_from_obs]}")

                        # Complete the agent execution
                        update_agent_execution_result(
                            agent_name=agent_name,
                            execution_result=result if result else "Agent completed",
                            visualizations=visualizations if visualizations else None
                        )
                        logger.info(f"✅ Completed agent execution: {agent_name} with {len(tools_used_from_obs)} tools")
            else:
                # Regular observation processing (not agent completion)
                for obs in observations_list:
                    tool_result = str(obs) if obs else ""

                    if hasattr(step, 'tool_calls') and step.tool_calls:
                        for tool_call in step.tool_calls:
                            if hasattr(tool_call, 'name'):
                                tool_name = tool_call.name
                                tool_args = getattr(tool_call, 'arguments', {})

                                # Skip agent calls and python_interpreter
                                if not tool_name.endswith('_agent') and tool_name != 'python_interpreter':
                                    # Try to add to active agent
                                    added = add_tool_to_active_agent(
                                        tool_name=tool_name,
                                        tool_args=tool_args,
                                        tool_result=tool_result
                                    )
                                    if added:
                                        logger.info(f"📝 Collected tool result for agent: {tool_name}")

        # 3. Retrieve and emit thinking steps accumulated during this step
        thinking_steps = get_and_clear_thinking_steps(context.workflow_id)
        if thinking_steps:
            logger.info(f"💭 Callback: Retrieved {len(thinking_steps)} thinking steps")
            for thinking_msg in thinking_steps:
                emit_observation_event(thinking_msg, tool_name="thinking")

        # 4. Process errors
        if hasattr(step, 'error') and step.error:
            emit_observation_event(
                observation=f"❌ Step error: {str(step.error)}",  # Don't truncate errors
                tool_name="step_error"
            )
            logger.info(f"❌ Callback: Error detected")

        return step  # Return unchanged
    
    def _extract_agent_call(self, code: str) -> Optional[Dict[str, str]]:
        """Extract agent call from python_interpreter code"""
        import re
        
        # Pattern to match agent calls like dev_agent(task="..." or task="""...""")
        # Handle both single and multi-line task strings
        agent_pattern = r'(\w+_agent)\s*\(\s*task\s*=\s*(?:["\']([^"\']*)["\']|["\'\'"]{3}(.*?)["\'\'"]{3})'
        match = re.search(agent_pattern, code, re.DOTALL)
        
        if match:
            agent_name = match.group(1)
            # Get task from either single-line (group 2) or multi-line (group 3) capture
            task = (match.group(2) or match.group(3) or "").strip()
            
            # Clean up multi-line task formatting
            if task:
                task = re.sub(r'\s+', ' ', task)  # Replace multiple whitespace with single space
                task = task.replace('\\n', ' ')  # Replace escaped newlines
                
            return {'name': agent_name, 'task': task}

        return None

    def _extract_direct_tool_calls(self, code: str) -> list:
        """
        Extract direct tool calls from python_interpreter code.
        Returns list of tool names that Manager called directly.
        """
        import re

        # Known visualization and file tools
        known_tools = [
            'create_bar_chart', 'create_line_chart', 'create_pie_chart',
            'create_scatter_plot', 'create_heatmap', 'create_distribution_plot',
            'save_agent_file', 'read_project_file'
        ]

        tools_found = []
        for tool in known_tools:
            # Pattern: tool_name(...) - function call
            pattern = rf'\b{tool}\s*\('
            if re.search(pattern, code):
                tools_found.append(tool)

        return tools_found

    def _extract_thought(self, model_output: str) -> Optional[str]:
        """
        Extract the Thought section from Agent's model output.

        Agent outputs follow this format (defined in prompt):
        Thought: <brief explanation of what agent is doing and why>
        Code:
        ```py
        <code here>
        ```

        This extracts ONLY the "Thought:" line - a single sentence explanation.

        Returns:
            Thought text if found, None otherwise
        """
        import re

        if not model_output or not isinstance(model_output, str):
            return None

        # Look for "Thought:" prefix followed by text until "Code:" or "<code>" markers
        # Support multi-line thoughts (e.g., Strategic Progress checklists)
        # Stop at: Code:, <code>, Action:, or {{code_block_opening_tag}}
        thought_pattern = r'Thought:\s*(.+?)(?=\n(?:Code:|Action:|<code>|{{code_block_opening_tag}})|$)'
        match = re.search(thought_pattern, model_output, re.IGNORECASE | re.DOTALL)

        if match:
            thought = match.group(1).strip()

            # Clean up excessive whitespace while preserving line breaks for lists
            thought = re.sub(r' +', ' ', thought)  # Collapse horizontal whitespace only
            thought = re.sub(r'\n{3,}', '\n\n', thought)  # Max 2 consecutive newlines

            # Don't truncate - frontend can handle expansion
            # Only return if meaningful (not too short)
            if len(thought) > 10:
                return thought

        return None


# Global callback instance
agent_aware_callback = AgentAwareWorkflowCallback()

# Use the new Agent-aware callback
simple_callback = AgentAwareWorkflowCallback()

def create_agent_with_simple_callbacks(agent_class, *args, **kwargs):
    """
    Create an agent with simple workflow callbacks.
    
    Usage:
        from smolagents import CodeAgent
        agent = create_agent_with_simple_callbacks(CodeAgent, tools=tools, model=model)
    """
    # Create the agent
    agent = agent_class(*args, **kwargs)
    
    # Set up callbacks using the official mechanism
    agent._setup_step_callbacks([simple_callback])
    
    logger.info(f"✅ Agent created with simple workflow callbacks")
    return agent
