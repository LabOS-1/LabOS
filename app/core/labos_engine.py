import os
import sys
import time
from pathlib import Path

# Import unified configuration
from ..config import (
    AI_MODELS, LabOS_CONFIG, EXTERNAL_APIS, PHOENIX_CONFIG,
    PERFORMANCE_CONFIG, MEMORY_CONFIG, TOOLS_CONFIG
)

# Smolagents imports
from smolagents import (
    CodeAgent,
    ToolCallingAgent,
    OpenAIServerModel,
    WebSearchTool,
    tool,
)
from smolagents.monitoring import LogLevel

# Import from refactored modules
from .tool_manager import (
    # Tool loading
    load_dynamic_tool,
    load_project_tools,
    refresh_agent_tools,
    add_tool_to_agents,
    # Tool creation
    create_new_tool,
    save_tool_to_database,
    # Tool registry
    list_dynamic_tools,
    get_tool_signature,
    dynamic_tools_registry,
    # Parallel execution
    execute_tools_in_parallel,
    # Intelligent selection
    analyze_query_and_load_relevant_tools,
)

from .agents import (
    create_all_agents,
    create_memory_enabled_agent,
    load_agent_prompts,
    get_authorized_imports,
)

from .integrations import setup_mcp_tools

# Import core tools
from ..tools.core import (
    # Memory tools
    auto_recall_experience,
    check_agent_performance,
    quick_tool_stats,
    # Evaluation tools
    evaluate_with_critic,
    # File access tools
    read_project_file,
    save_agent_file,
    analyze_media_file,
    analyze_gcs_media,  # For analyzing large files stored in GCS via signed URLs
)

# Import visualization tools
from ..tools.visualization import (
    create_line_plot,
    create_bar_chart,
    create_scatter_plot,
    create_heatmap,
    create_distribution_plot
)

# Import knowledge and collaboration tools
from ..tools.core.knowledge import (
    retrieve_similar_templates,
    save_successful_template,
    list_knowledge_base_status,
    search_templates_by_keyword,
    get_user_memories,
)

from ..tools.core.collaboration import (
    create_shared_workspace,
    add_workspace_memory,
    get_workspace_memories,
    create_task_breakdown,
    update_subtask_status,
    get_task_progress,
    get_agent_contributions,
)

# Import predefined tools
from ..tools.predefined import (
    # Enhanced search tools
    enhanced_google_search, search_google_basic, multi_source_search, 
    smart_search_router, search_with_serpapi, enhanced_knowledge_search, search_google,
    # Web and content tools
    visit_webpage, extract_url_content, extract_pdf_content,
    # GitHub tools
    search_github_repositories, search_github_code, get_github_repository_info,
    # Academic research tools
    fetch_supplementary_info_from_doi, query_arxiv, query_scholar, query_pubmed,
    # Development and system tools
    run_shell_command, create_conda_environment, install_packages_conda, 
    install_packages_pip, check_gpu_status, create_script, create_and_run_script, 
    run_script, create_requirements_file, monitor_training_logs
)

# Import AutoMemory System
from .auto_memory import AutoMemory, auto_memory

# Import knowledge base and memory manager (optional, may be unused)
from .knowledge_base import KnowledgeBase, Mem0EnhancedKnowledgeBase, MEM0_AVAILABLE
from .memory_manager import MemoryManager

# === Configuration ===
# API Keys
OPENROUTER_API_KEY_STRING = AI_MODELS["openrouter"]["api_key"]
MEM0_API_KEY = EXTERNAL_APIS["mem0"]["api_key"]

# Model configurations
openrouter_model_id = AI_MODELS["openrouter"]["models"]["dev_agent"]
manager_model_id = AI_MODELS["openrouter"]["models"]["manager_agent"] 
critic_model_id = AI_MODELS["openrouter"]["models"]["critic_agent"]
tool_creation_model_id = AI_MODELS["openrouter"]["models"]["tool_creation_agent"]

# Performance settings
DEFAULT_MAX_STEPS = AI_MODELS["parameters"]["max_steps"]["manager_agent"]

# Phoenix Configuration
if PHOENIX_CONFIG["enable_tracing"]:
    os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = PHOENIX_CONFIG["collector_endpoint"]

HTTP_REFERER_URL = "http://localhost:8000"
X_TITLE_APP_NAME = "LabOS AI System"

# Global memory manager instance
global_memory_manager = None
use_templates = False

# Global custom prompt templates
custom_prompt_templates = None

# Global agent instances
manager_agent = None
dev_agent = None
tool_creation_agent = None
critic_agent = None

# === Model Initialization ===
print("🤖 Model Configuration (from unified config):")
print(f"   Dev Agent: {openrouter_model_id}")
print(f"   Manager Agent: {manager_model_id}")
print(f"   Critic Agent: {critic_model_id}")
print(f"   Tool Creation Agent: {tool_creation_model_id}")

# Base model for dev agent
model = OpenAIServerModel(
    model_id=openrouter_model_id,
    api_base=AI_MODELS["openrouter"]["base_url"],
    api_key=OPENROUTER_API_KEY_STRING,
    temperature=AI_MODELS["parameters"]["temperature"],
)

# Claude model for dev agent
claude_model = OpenAIServerModel(
    model_id=openrouter_model_id,
    api_base=AI_MODELS["openrouter"]["base_url"],
    api_key=OPENROUTER_API_KEY_STRING,
    temperature=AI_MODELS["parameters"]["temperature"],
)

# Manager agent model (uses manager_model_id from settings)
manager_model = OpenAIServerModel(
    model_id=manager_model_id,
    api_base=AI_MODELS["openrouter"]["base_url"],
    api_key=OPENROUTER_API_KEY_STRING,
    temperature=AI_MODELS["parameters"]["temperature"],
)

# Tool creation agent model
gpt_model = OpenAIServerModel(
    model_id=tool_creation_model_id,
    api_base=AI_MODELS["openrouter"]["base_url"],
    api_key=OPENROUTER_API_KEY_STRING,
    temperature=AI_MODELS["parameters"]["temperature"],
)

# === Setup MCP Tools ===
mcp_tools = setup_mcp_tools()

# === Tool Permissions Setup ===
# Dev agent tools (basic)
dev_tool_management = [
    list_dynamic_tools,
    load_dynamic_tool,
    refresh_agent_tools,
    auto_recall_experience,
    quick_tool_stats,
]

# Manager agent tools (full set)
manager_tool_management = [
    analyze_query_and_load_relevant_tools,
    execute_tools_in_parallel,
    evaluate_with_critic,
    list_dynamic_tools,
    load_project_tools,
    create_new_tool,
    load_dynamic_tool,
    refresh_agent_tools,
    add_tool_to_agents,
    get_tool_signature,
    # Memory tools
    auto_recall_experience,
    check_agent_performance,
    quick_tool_stats,
    # File access tools
    read_project_file,
    save_agent_file,
    analyze_media_file,
    analyze_gcs_media,   # For analyzing large files stored in GCS via signed URLs
    # Enhanced search tools
    enhanced_google_search,
    search_google_basic,
    multi_source_search,
    smart_search_router,
    search_with_serpapi,
    enhanced_knowledge_search,
    search_google,
    WebSearchTool(),
    # Web and content tools
    visit_webpage,
    extract_url_content,
    extract_pdf_content,
    # GitHub tools
    search_github_repositories,
    search_github_code,
    get_github_repository_info,
    # Academic research tools
    fetch_supplementary_info_from_doi,
    query_arxiv,
    query_scholar,
    query_pubmed,
    # Knowledge Base Tools
    retrieve_similar_templates,
    save_successful_template,
    list_knowledge_base_status,
    search_templates_by_keyword,
    # Mem0-specific Tools
    get_user_memories,
    # Multi-Agent Collaboration Tools
    create_shared_workspace,
    add_workspace_memory,
    get_workspace_memories,
    create_task_breakdown,
    update_subtask_status,
    get_task_progress,
    get_agent_contributions,
]

# Base tools for dev_agent
base_tools = [
    # Core web and search tools
    WebSearchTool(),
    visit_webpage,
    # GitHub tools
    search_github_repositories,
    search_github_code,
    get_github_repository_info,
    # Development environment tools
    check_gpu_status,
    create_requirements_file,
    monitor_training_logs,
    # Visualization tools
    create_line_plot,
    create_bar_chart,
    create_scatter_plot,
    create_heatmap,
    create_distribution_plot,
] + dev_tool_management

# Combine base tools with MCP tools
all_tools = base_tools + mcp_tools

# === Agent Initialization Function ===
def initialize_stella(use_template=True, use_mem0=True):
    """Initialize LabOS without launching Gradio interface - for use by other UIs.

    Args:
        use_template: Whether to use custom prompt templates
        use_mem0: Whether to use Mem0 for enhanced memory

    Returns:
        Boolean indicating success
    """
    global global_memory_manager, use_templates, custom_prompt_templates
    global manager_agent, dev_agent, tool_creation_agent, critic_agent

    use_templates = use_template

    print("🚀 Initializing LabOS system...")
    print(f"📋 Using custom templates: {use_template}")
    print(f"🧠 Using Mem0 memory: {use_mem0}")

    try:
        # Create all agents using the factory
        models = {
            'claude_model': claude_model,
            'gpt_model': gpt_model,
            'manager_model': manager_model
        }

        dev_agent, tool_creation_agent, critic_agent, manager_agent = create_all_agents(
            models=models,
            base_tools=base_tools,
            mcp_tools=mcp_tools,
            manager_tools=manager_tool_management,
            use_template=use_template
        )

        print(f"✅ All agents created successfully")
        print(f"🔧 Dev agent: {len(dev_agent.tools)} tools")
        print(f"🔧 Tool creation agent: {len(tool_creation_agent.tools)} tools")
        print(f"🔧 Critic agent: {len(critic_agent.tools)} tools")
        print(f"🔧 Manager agent: {len(manager_agent.tools)} tools")

    except Exception as e:
        print(f"❌ Error creating agents: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Initialize memory system if requested
    if use_template:
        print("📚 Initializing knowledge base...")
        try:
            global_memory_manager = MemoryManager(
                gemini_model=manager_model,  # Pass manager_model for memory management
                use_mem0=use_mem0,
                mem0_api_key=MEM0_API_KEY,
                openrouter_api_key=OPENROUTER_API_KEY_STRING
            )
            print("✅ Memory system initialized")
        except Exception as e:
            print(f"❌ Memory system initialization failed: {str(e)}")

    print("✅ LabOS initialization complete")
    return manager_agent is not None

# === Auto-initialize on import (optional) ===
# Uncomment the following line to auto-initialize when module is imported
# initialize_stella(use_template=True, use_mem0=False)

