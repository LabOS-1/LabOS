"""
LangChain WebSocket Callback Handler
Intercepts LangChain agent events and broadcasts them via WebSocket
Matches the Smolagents workflow format for frontend compatibility
"""

import json
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from langchain_core.callbacks.base import BaseCallbackHandler
from app.services.websocket_broadcast import websocket_broadcaster
from app.services.workflows.workflow_events import WorkflowEvent, WorkflowEventQueue


class LangChainWebSocketCallback(BaseCallbackHandler):
    """
    Callback handler that intercepts LangChain events and broadcasts them via WebSocket
    Compatible with existing Smolagents workflow format

    Design: Uses dependency injection for event_queue to enable:
    - Better testability (can inject mock queue)
    - Loose coupling (callback doesn't depend on global singleton)
    - Flexibility (can use different queue implementations)
    """

    def __init__(
        self,
        workflow_id: str,
        project_id: Optional[str] = None,
        event_queue: Optional[WorkflowEventQueue] = None
    ):
        """
        Initialize the callback handler

        Args:
            workflow_id: Unique identifier for this workflow execution
            project_id: Optional project ID for room-based broadcasting
            event_queue: Optional WorkflowEventQueue instance (if None, uses global singleton)

        Note:
            event_queue parameter enables dependency injection for testing and flexibility.
            In production, it defaults to the global workflow_event_queue singleton.
        """
        self.workflow_id = workflow_id
        self.project_id = project_id
        self.step_counter = 0
        self.current_tool_name = None
        self.current_tool_input = None
        self.collected_steps = []  # Collect steps for database persistence

        # Dependency injection: Use provided queue or fallback to global singleton
        if event_queue is not None:
            self.event_queue = event_queue
        else:
            # Import global singleton only if not provided (lazy import)
            from app.services.workflows.workflow_events import workflow_event_queue
            self.event_queue = workflow_event_queue

    def _increment_step(self) -> int:
        """Increment and return step counter"""
        self.step_counter += 1
        return self.step_counter

    def _extract_thinking(self, text: str) -> Optional[str]:
        """
        Extract agent thinking/reasoning from LLM output
        Looks for common reasoning patterns and extracts content before Action
        """
        # First try to extract content before "Action:" or "Action Input:"
        # This captures the thinking/reasoning that happens before tool calls
        action_split = re.split(r'\n(?:Action|Action Input):', text, maxsplit=1)
        if len(action_split) > 1:
            # There's an Action, so extract everything before it
            pre_action_text = action_split[0].strip()

            # Remove common prefixes like "Thought:", "Reasoning:", etc.
            cleaned_text = re.sub(r'^(?:Thought|Reasoning):\s*', '', pre_action_text, flags=re.IGNORECASE)

            if cleaned_text and len(cleaned_text) > 10:  # At least some meaningful content
                return cleaned_text

        # Fallback: Look for explicit thinking patterns
        patterns = [
            r"Thought:\s*(.+?)(?=\n(?:Action|Action Input):|$)",
            r"Reasoning:\s*(.+?)(?=\n(?:Action|Action Input):|$)",
            r"I need to\s*(.+?)(?=\n(?:Action|Action Input):|$)",
            r"Let me\s*(.+?)(?=\n(?:Action|Action Input):|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()

        return None

    def _extract_visualization_metadata(self, output: str) -> Optional[Dict[str, Any]]:
        """
        Extract visualization metadata from tool output
        Supports both structured JSON and text formats for backward compatibility

        Returns metadata in Smolagents-compatible format
        """
        # First try parsing as JSON (preferred method for LangChain tools)
        try:
            if output.strip().startswith('{') or output.strip().startswith('['):
                data = json.loads(output)

                # Check for structured visualization metadata
                if isinstance(data, dict):
                    # Check for visualization_metadata field (sandbox plotting tools use this)
                    if 'visualization_metadata' in data:
                        viz_data = data['visualization_metadata']
                        return {
                            'visualizations': [{
                                'type': viz_data.get('type', 'chart'),
                                'chart_type': viz_data.get('chart_type', 'generated'),
                                'title': viz_data.get('title', 'Visualization'),
                                'filename': data.get('file_path'),
                                'sandbox_path': data.get('sandbox_path'),
                                'base64': viz_data.get('base64'),  # Full base64 image data
                                'width': viz_data.get('width', 1000),
                                'height': viz_data.get('height', 600),
                                'format': viz_data.get('format', 'png'),
                            }]
                        }

                    # Check for visualization metadata field (legacy format)
                    if 'visualization' in data:
                        viz_data = data['visualization']
                        return {
                            'visualizations': [{
                                'type': viz_data.get('type', 'image'),
                                'chart_type': viz_data.get('chart_type', 'generated'),
                                'title': viz_data.get('title', 'Visualization'),
                                'file_id': viz_data.get('file_id'),
                                'filename': viz_data.get('filename'),
                                'url': viz_data.get('url'),
                                'data': viz_data.get('data')  # For inline data
                            }]
                        }

                    # Fallback: check for common image/plot keys
                    if any(k in data for k in ['image', 'image_url', 'image_path', 'file_id']):
                        return {
                            'visualizations': [{
                                'type': 'image',
                                'chart_type': 'generated',
                                'file_id': data.get('file_id'),
                                'filename': data.get('filename') or data.get('image_path'),
                                'url': data.get('image_url'),
                                'data': data.get('image')
                            }]
                        }

                    # Check for plot/chart data
                    if any(k in data for k in ['plot', 'chart', 'figure']):
                        return {
                            'visualizations': [{
                                'type': 'chart',
                                'chart_type': data.get('chart_type', 'plot'),
                                'data': data.get('plot') or data.get('chart') or data.get('figure')
                            }]
                        }
        except json.JSONDecodeError:
            pass

        # No visualization metadata found
        return None

    def _emit_event(self, step_type: str, step_data: Dict[str, Any]):
        """
        Emit workflow event using event queue pattern (matching Smolagents)
        This is cleaner and more robust than direct async broadcasting
        """
        # Map LangChain step_type to WorkflowEvent type
        event_type_map = {
            "thinking": "step",
            "tool_execution": "tool_call",
            "synthesis": "observation",
            "error": "step"
        }

        event = WorkflowEvent(
            workflow_id=self.workflow_id,
            event_type=event_type_map.get(step_type, "step"),
            timestamp=datetime.now(),
            step_number=step_data.get("step_number"),
            title=step_data.get("title"),
            description=step_data.get("description"),
            tool_name=step_data.get("tool_name"),
            tool_result=step_data.get("tool_result"),
            step_metadata=step_data.get("step_metadata")
        )

        # Put event in queue - listener will handle WebSocket broadcasting
        # Uses injected event_queue (dependency injection pattern)
        self.event_queue.put(event)
        print(f"📤 Emitted {step_type} event: {step_data.get('title')}")

        # Also collect step for database persistence
        self.collected_steps.append(step_data)

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Called when LLM starts generating"""
        print(f"🔔 LangChain Callback: on_llm_start called")

        # Don't emit placeholder - wait for actual LLM output in on_llm_end
        # This avoids showing "Analyzing your request..." placeholders
        print(f"  ⏳ Waiting for LLM to complete before emitting thinking event")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Called when LLM finishes generating - emit actual thinking content"""
        print(f"🔔 LangChain Callback: on_llm_end called")

        # Extract the actual LLM response text
        try:
            # LangChain response structure: response.generations[0][0].text
            if hasattr(response, 'generations') and response.generations:
                first_gen = response.generations[0]
                if first_gen and len(first_gen) > 0:
                    # Extract text content - try both .text and .message.content
                    llm_output = ""
                    if hasattr(first_gen[0], 'text'):
                        llm_output = first_gen[0].text

                    # In function calling mode, text might be empty but content is in message.content
                    if hasattr(first_gen[0], 'message') and hasattr(first_gen[0].message, 'content'):
                        message_content = first_gen[0].message.content
                        # Check if content is a non-empty string (not empty list, not just whitespace)
                        if message_content and (isinstance(message_content, str) and message_content.strip()):
                            llm_output = message_content
                        elif isinstance(message_content, list) and len(message_content) == 0:
                            # Empty list means function calling mode with no text content
                            # Gemini uses encrypted thought signatures - don't show raw objects
                            print(f"  ⏭️  Skipping thinking (empty content in function calling mode - thought signatures are encrypted)")
                            return

                    # Skip if llm_output is empty or looks like encrypted/internal data
                    if not llm_output or (isinstance(llm_output, str) and not llm_output.strip()):
                        print(f"  ⏭️  Skipping thinking (no text content available)")
                        return

                    # Don't show raw message objects with encrypted data
                    if isinstance(llm_output, str) and ('generation_info=' in llm_output or '__gemini_function_call_thought_signatures__' in llm_output):
                        print(f"  ⏭️  Skipping thinking (raw message object with encrypted data)")
                        return

                    # CRITICAL: Check if this is a final answer (no Action/tool call)
                    # Final answers should NOT be displayed as "Agent Reasoning" - they're handled by Complete step
                    has_action = 'Action:' in llm_output or 'Action Input:' in llm_output

                    # Also check if generation has tool calls (for function calling mode)
                    # In function calling mode, message.tool_calls will be present
                    has_tool_calls = False
                    if hasattr(first_gen[0], 'message'):
                        msg = first_gen[0].message
                        has_tool_calls = hasattr(msg, 'tool_calls') and msg.tool_calls and len(msg.tool_calls) > 0

                    if not has_action and not has_tool_calls:
                        # This is a final answer, not reasoning - skip it
                        # The Complete step will handle displaying the final response
                        print(f"  ⏭️  Skipping final answer (no Action/tool calls) - will be shown in Complete step")
                        return

                    # IMPORTANT: Even with tool_calls, we want to show the text content (thinking)
                    # This is the key to showing manager's reasoning while using function calling
                    print(f"  📝 LLM output length: {len(llm_output)}, has_tool_calls: {has_tool_calls}")

                    # Try to extract thinking/reasoning from the output
                    thinking = self._extract_thinking(llm_output)

                    if thinking:
                        # Emit thinking event with actual reasoning content
                        step_data = {
                            "step_type": "thinking",
                            "title": "Agent Reasoning",
                            "description": thinking,
                            "step_number": self._increment_step(),  # Increment for new step
                            "timestamp": datetime.now().isoformat()
                        }
                        self._emit_event("thinking", step_data)
                        print(f"  💭 Emitted thinking with actual reasoning: {thinking[:100]}...")
                    else:
                        # If no explicit thinking pattern found, show the LLM output
                        # In function calling mode, Gemini outputs reasoning without "Thought:" prefix
                        if len(llm_output.strip()) > 0:
                            # Limit description to reasonable length for UI display
                            description = llm_output.strip()
                            if len(description) > 1500:
                                description = description[:1500] + "..."

                            step_data = {
                                "step_type": "thinking",
                                "title": "Agent Reasoning",
                                "description": description,
                                "step_number": self._increment_step(),
                                "timestamp": datetime.now().isoformat()
                            }
                            self._emit_event("thinking", step_data)
                            print(f"  💭 Emitted thinking with LLM output: {description[:100]}...")
        except Exception as e:
            print(f"  ⚠️  Failed to extract thinking: {e}")

        print(f"  ✅ LLM generation complete")

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Called when tool execution starts"""
        print(f"🔔 LangChain Callback: on_tool_start called")

        tool_name = serialized.get("name", "unknown_tool")
        self.current_tool_name = tool_name
        self.current_tool_input = input_str

        print(f"  🔧 Tool: {tool_name}, Input: {input_str[:100]}...")

        # Simple description without showing full input parameters
        # This keeps the workflow clean and readable
        if tool_name == "python_interpreter":
            description = f"Executing Python code"
        elif tool_name.startswith("ask_"):
            # For delegation tools, just say which agent is being called
            agent_name = tool_name.replace("ask_", "").replace("_", " ").title()
            description = f"Delegating task to {agent_name} Agent"
        else:
            # For other tools, simple generic description
            description = f"Executing {tool_name}"

        step_data = {
            "step_type": "tool_execution",
            "title": f"Using Tool: {tool_name}",
            "description": description,
            "tool_name": tool_name,
            "tool_input": input_str,
            "step_number": self._increment_step(),
            "timestamp": datetime.now().isoformat()
        }

        self._emit_event("tool_execution", step_data)

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when tool execution ends"""
        print(f"🔔 LangChain Callback: on_tool_end called")
        print(f"  ✅ Tool result: {output[:200]}...")

        # Extract visualization metadata from tool output
        visualization_metadata = self._extract_visualization_metadata(output)
        print(f"  🎨 Visualization metadata extraction result: {visualization_metadata is not None}")

        # Show tool output details (matching V1's detailed display)
        # V1 shows full stdout/output, so V2 should too
        description = f"Completed {self.current_tool_name}"
        if output:
            description = f"Result:\n{output}"


        step_data = {
            "step_type": "tool_execution",
            "title": f"Tool Result: {self.current_tool_name}",
            "description": description,
            "tool_name": self.current_tool_name,
            "tool_result": output,
            "step_number": self._increment_step(),
            "timestamp": datetime.now().isoformat()
        }

        # Add visualization metadata if detected (Smolagents-compatible format)
        if visualization_metadata:
            step_data["step_metadata"] = visualization_metadata
            print(f"  🎨 Visualization metadata detected: {visualization_metadata}")

        self._emit_event("tool_execution", step_data)

        # Reset current tool tracking
        self.current_tool_name = None
        self.current_tool_input = None

    def on_agent_action(self, action: Any, **kwargs: Any) -> None:
        """Called when agent takes an action"""
        # Extract thinking from action log if available
        if hasattr(action, 'log'):
            thinking = self._extract_thinking(action.log)
            if thinking:
                step_data = {
                    "step_type": "thinking",
                    "title": "Agent Decision",
                    "description": thinking,
                    "step_number": self._increment_step(),
                    "timestamp": datetime.now().isoformat()
                }

                self._emit_event("thinking", step_data)

    def on_agent_finish(self, finish: Any, **kwargs: Any) -> None:
        """Called when agent finishes execution"""
        # Don't emit "Final Answer" step - the completion step is handled by multi_agent_system.py
        # This avoids duplicate/out-of-order completion messages
        print(f"🔔 LangChain Callback: on_agent_finish called (skipping emission - handled by multi_agent_system)")
        return

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when LLM encounters an error"""
        step_data = {
            "step_type": "error",
            "title": "Error",
            "description": f"LLM error: {str(error)}",
            "step_number": self._increment_step(),
            "timestamp": datetime.now().isoformat()
        }

        self._emit_event("error", step_data)

    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when tool encounters an error"""
        step_data = {
            "step_type": "error",
            "title": "Tool Error",
            "description": f"Tool {self.current_tool_name} error: {str(error)}",
            "tool_name": self.current_tool_name,
            "step_number": self._increment_step(),
            "timestamp": datetime.now().isoformat()
        }

        self._emit_event("error", step_data)
