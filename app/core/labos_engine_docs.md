# LabOS Engine - Code Navigation Guide

This document helps navigate the large `stella_engine.py` file (1640 lines).

## File Structure

### 1. Imports & Configuration (Lines 1-150)
- External library imports
- Configuration loading
- Model initialization
- Memory system setup

### 2. Utility Functions (Lines 151-241)
- `retry_on_failure()` - Retry mechanism (158-184)
- `create_memory_enabled_agent()` - Memory wrapper (186-240)

### 3. Tool Management Functions (Lines 242-1256)
Main tool management system - **THIS IS THE LARGEST SECTION**

#### 3.1 Dynamic Tool Discovery (242-351)
- `list_dynamic_tools()` - List available tools (242-258)
- `load_project_tools()` - Load from database (260-351)

#### 3.2 Tool Creation & Loading (353-584)
- `create_new_tool()` - Create new tool file (353-408)
- `load_dynamic_tool()` - Load tool into system (410-584)

#### 3.3 Tool Execution (586-817)
- `execute_tools_in_parallel()` - Parallel execution (586-817)

#### 3.4 Intelligent Tool Selection (819-1048)
- `analyze_query_and_load_relevant_tools()` - Smart loading (819-997)
- `_fallback_tool_selection()` - Fallback logic (999-1048)

#### 3.5 Tool Management Operations (1050-1256)
- `refresh_agent_tools()` - Refresh tool list (1050-1092)
- `add_tool_to_agents()` - Add tool to agents (1094-1140)
- `get_tool_signature()` - Get tool details (1142-1256)

### 4. MCP Integration (Lines 1258-1282)
- `setup_mcp_tools()` - MCP server connection (1258-1280)
- MCP tool initialization (1282)

### 5. Tool Permissions & Agent Setup (Lines 1284-1391)
- `dev_tool_management` - Dev agent tools (1286-1293)
- `manager_tool_management` - Manager agent tools (1296-1358)
- `base_tools` - Base tool list (1361-1387)
- `all_tools` - Combined tool list (1390)

### 6. Agent Initialization (Lines 1393-1640)
- `_load_agent_prompts_early()` - Load prompts (1393-1494)
- `initialize_stella()` - Main initialization (1496-1640)
  - Create dev_agent (lines ~1530)
  - Create critic_agent (lines ~1555)
  - Create tool_creation_agent (lines ~1580)
  - Create manager_agent (lines ~1600)
  - Initialize memory manager (lines ~1625)

## Quick Reference: Where to Find Things

| Task | Function | Line Range |
|------|----------|------------|
| Create a new tool | `create_new_tool()` | 353-408 |
| Load a tool | `load_dynamic_tool()` | 410-584 |
| Smart tool selection | `analyze_query_and_load_relevant_tools()` | 819-997 |
| Initialize system | `initialize_stella()` | 1496-1640 |
| Setup MCP | `setup_mcp_tools()` | 1258-1280 |

## Future Refactoring Notes

If this file needs to be split in the future, consider:

1. **Priority 1**: Extract tool management (lines 242-1256) → `tool_manager.py`
2. **Priority 2**: Extract MCP integration (lines 1258-1391) → `mcp_integration.py`
3. **Priority 3**: Extract agent initialization (lines 1496-1640) → `agent_factory.py`

This would reduce the main file from 1640 lines to ~500 lines.
