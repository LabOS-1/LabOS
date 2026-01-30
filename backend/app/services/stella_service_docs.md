# LABOS Service - Code Navigation Guide

This document helps navigate `labos_service.py` (985 lines).

## File Structure

### 1. Class Definition & Initialization (Lines 1-100)
- `__init__()` - Initialize service (32-48)
- `initialize()` - Async initialization (49-75)
- `_initialize_labos_direct()` - Direct initialization (77-99)
- `is_initialized()` - Check status (101-103)

### 2. Message Processing (Lines 105-292)
Main workflow entry points

- `process_message_async()` - Async message handler (105-213)
  - Handles WebSocket communication
  - Manages workflow lifecycle
  - Sends real-time updates

- `process_message()` - Sync wrapper (215-291)
  - Database integration
  - Error handling
  - Response formatting

### 3. Core Workflow Execution (Lines 293-593)
**THE LARGEST AND MOST COMPLEX SECTION**

- `_process_with_labos()` - Main workflow executor (293-592)
  - Lines 293-373: Setup and initialization
  - Lines 374-418: Load conversation history from database
  - Lines 420-460: Agent execution in executor thread
  - Lines 462-485: Workflow timeout handling
  - Lines 487-544: Result processing and database saving
  - Lines 546-592: Cleanup and error handling

### 4. Database Operations (Lines 594-708)
- `_save_workflow_step_to_db()` - Save step (594-664)
- `_save_response_to_project()` - Save response (666-707)

### 5. System Status & Tools (Lines 709-774)
- `get_system_status()` - System info (709-725)
- `get_chat_history()` - DEPRECATED (727-734)
- `clear_chat_history()` - DEPRECATED (736-743)
- `get_tools()` - Tool list (745-749)
- `get_dynamic_tools()` - Dynamic tools (751-755)
- `get_agents()` - Agent info (757-773)

### 6. Workflow Management (Lines 775-820)
- `cancel_workflow()` - Cancel workflow (775-816)
- `get_active_workflows()` - List active (818-820)

### 7. File & Project Management (Lines 822-958)
- `_get_project_output_dir()` - Get output dir (822-844)
- `_auto_register_workflow_files()` - Register files (846-957)

### 8. Cleanup (Lines 959-985)
- `cleanup()` - Shutdown cleanup (959-985)

## Key Functions by Use Case

| Use Case | Function | Line Range |
|----------|----------|------------|
| **Process user message** | `process_message_async()` | 105-213 |
| **Execute workflow** | `_process_with_labos()` | 293-592 |
| **Cancel workflow** | `cancel_workflow()` | 775-816 |
| **Get system status** | `get_system_status()` | 709-725 |
| **Save to database** | `_save_response_to_project()` | 666-707 |

## Complex Areas

### 1. Workflow Execution (_process_with_labos)
This is the most complex function (300 lines):
- Manages workflow context
- Loads conversation history
- Executes agent in thread pool
- Handles cancellation
- Saves results to database
- Broadcasts WebSocket events

**Potential optimization**: Could be split into:
- `_prepare_workflow_context()`
- `_execute_agent_with_context()`
- `_save_workflow_results()`

### 2. Message Processing Flow
```
User Message
    ↓
process_message_async() ← WebSocket entry
    ↓
_process_with_labos() ← Core execution
    ↓
manager_agent.run() ← Agent execution
    ↓
_save_response_to_project() ← Save results
    ↓
WebSocket broadcast ← Send to frontend
```

## Memory Management Notes

✅ **Fixed Issues**:
- Removed `self.chat_history` (was causing memory leak)
- Added cleanup for `cancelled_workflows` set
- Proper cleanup in `finally` blocks

⚠️ **Watch These**:
- `self.active_workflows` - Cleaned in finally block
- `self.current_workflow_steps` - Cleared after each workflow
- Conversation history loaded per-request (not cached)

## Future Refactoring Suggestions

If this file needs to be split:

1. **Extract workflow execution** → `workflow_executor.py`
   - `_process_with_labos()`
   - `_prepare_workflow_context()`
   - `_execute_agent()`

2. **Extract database operations** → `workflow_persistence.py`
   - `_save_workflow_step_to_db()`
   - `_save_response_to_project()`
   - `_auto_register_workflow_files()`

3. **Extract conversation management** → `conversation_manager.py`
   - Load history logic
   - Format history for agent
   - Clear history operations (currently deprecated)

This would reduce the main file from 985 lines to ~400 lines.
