# LabOS - Laboratory Operating System

**LabOS** (Laboratory Operating System) is an advanced AI-powered biomedical research assistant forked from STELLA. It provides intelligent tool selection, multi-agent collaboration, and specialized genomic reasoning capabilities.

## 🎯 Key Features

- **Multi-Agent System**: Manager, Critic, and Tool Creation agents working together
- **Genomic Reasoning**: Specialized prompts for CRISPR and genomic analysis
- **Dynamic Tool Loading**: Intelligent tool selection based on query analysis
- **Real-time Collaboration**: WebSocket-based progress updates and workflow tracking
- **Knowledge Management**: Memory system with Mem0 integration
- **Extensible Architecture**: Easy to add custom tools and agents

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Virtual environment (recommended)
- OpenRouter API key (for LLM access)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/LabOS-1/LabOS.git
   cd LabOS
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

5. **Start the server:**
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 18800 --reload
   ```

6. **Verify installation:**
   ```bash
   curl http://localhost:18800/health
   ```

## 📦 Configuration

### Required Environment Variables

Create a `.env` file in the project root:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=18800
ENVIRONMENT=development  # or 'production'

# API Keys
OPENROUTER_API_KEY_STRING=your_openrouter_api_key_here

# Model Configuration
LABOS_DEV_MODEL=anthropic/claude-sonnet-4
LABOS_MANAGER_MODEL=anthropic/claude-sonnet-4
LABOS_CRITIC_MODEL=anthropic/claude-sonnet-4
LABOS_TOOL_CREATION_MODEL=anthropic/claude-sonnet-4

# Prompt Version (v1, v2, or v3)
LABOS_PROMPT_VERSION=v3  # v3 includes GenomeBench MCQ enhancements

# Model Parameters
MODEL_TEMPERATURE=0.1
MODEL_MAX_TOKENS=4096
MANAGER_AGENT_MAX_STEPS=30
DEV_AGENT_MAX_STEPS=20

# Optional: Memory System
LABOS_USE_MEM0=true
MEM0_API_KEY=your_mem0_api_key_here

# Logging
LOG_LEVEL=INFO
```

## 🏗️ Architecture

### Tech Stack

- **Framework:** FastAPI 0.100+
- **ASGI Server:** Uvicorn
- **AI Framework:** smolagents
- **LLM Gateway:** OpenRouter (supports Claude, GPT-4, Gemini, etc.)
- **Memory:** Mem0 (optional)
- **Database:** PostgreSQL (Cloud SQL) / SQLite (local)

### Project Structure

```
LabOS/
├── app/
│   ├── main.py                  # FastAPI application entry
│   ├── api/                     # API endpoints
│   │   ├── chat_projects.py     # Project-based chat API
│   │   ├── agents.py            # Agent management
│   │   ├── tools.py             # Tool management
│   │   └── websocket.py         # Real-time updates
│   ├── core/                    # Core LabOS engine
│   │   ├── labos_engine.py      # Main engine initialization
│   │   ├── agents/              # Agent factory and configuration
│   │   ├── tool_manager/        # Dynamic tool loading
│   │   ├── memory_manager.py    # Knowledge and memory
│   │   └── integrations/        # External integrations (MCP)
│   ├── config/                  # Configuration
│   │   ├── settings.py          # Centralized config
│   │   └── prompts/             # Agent prompts (v1, v2, v3)
│   ├── services/                # Business logic
│   │   ├── labos_service.py     # Core LabOS service
│   │   └── workflows/           # Workflow management
│   └── tools/                   # Built-in tools
│       ├── core/                # Core tools (files, memory, eval)
│       ├── predefined.py        # Web search, GitHub, etc.
│       └── visualization/       # Plotting and charts
├── scripts/                     # Utility scripts
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🤖 LabOS Agents

### Manager Agent (CodeAgent)
- Coordinates all other agents
- Executes Python code with python_interpreter
- Uses prompt version from `LABOS_PROMPT_VERSION`
- Model: `LABOS_MANAGER_MODEL` (default: Claude Sonnet 4)

### Dev Agent (ToolCallingAgent)
- Handles research, web search, GitHub queries
- Visualization and charting
- File operations
- Model: `LABOS_DEV_MODEL`

### Critic Agent (ToolCallingAgent)
- Evaluates results and suggestions
- Quality assurance
- Model: `LABOS_CRITIC_MODEL`

### Tool Creation Agent (ToolCallingAgent)
- Creates new custom tools on demand
- Model: `LABOS_TOOL_CREATION_MODEL`

## 📋 Prompt Versions

### v1 - Original Prompt
- Comprehensive workflow with 7-step strategy
- Full feature set

### v2 - Optimized Prompt
- Streamlined for efficiency
- Reduced token usage
- Maintained all functionality

### v3 - GenomeBench Enhanced (Recommended)
- All v2 features
- **Added: Specialized genomic reasoning framework**
- **Added: 4-phase MCQ answering strategy**
- **Added: CRISPR protocol knowledge**
- **Best for:** Genomic analysis, CRISPR design, laboratory protocols

To use v3:
```bash
# In .env file
LABOS_PROMPT_VERSION=v3
```

## 📊 API Endpoints

### Health & System
- `GET /health` - Health check
- `GET /api/system/status` - System status

### Chat Projects
- `POST /api/chat/projects` - Create project
- `POST /api/chat/projects/{project_id}/messages` - Send message
- `GET /api/chat/projects/{project_id}/messages` - Get messages

### Tools & Agents
- `GET /api/tools` - List available tools
- `POST /api/tools/create` - Create custom tool
- `GET /api/agents` - List agents

### WebSocket
- `ws://localhost:18800/ws` - Real-time updates

## 🧬 GenomeBench Support

LabOS v3 includes specialized support for genomic reasoning tasks:

- **Library Preparation**: sgRNA synthesis, storage, QC
- **Viral Packaging**: Lentiviral systems, titer optimization
- **Molecular Cloning**: Vector design, restriction sites, Golden Gate
- **PCR & Sequencing**: Primer design, NGS library prep
- **DNA Handling**: Extraction protocols, purification
- **Selection & Screening**: Antibiotic markers, hit identification
- **Troubleshooting**: Off-target effects, efficiency issues

Example usage:
```python
# The v3 prompt automatically applies genomic reasoning
# to questions about CRISPR protocols and experiments
```

## 🛠️ Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/

# With coverage
pytest --cov=app tests/
```

### Adding Custom Tools

1. Create tool in `app/tools/`
2. Register in `labos_engine.py`
3. Tool will be automatically loaded based on query

### Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with auto-reload
python -m uvicorn app.main:app --host 0.0.0.0 --port 18800 --reload --log-level debug
```

## 🚀 Production Deployment

### Using Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
EXPOSE 18800

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "18800"]
```

### Using Docker Compose

```yaml
version: '3.8'
services:
  labos:
    build: .
    ports:
      - "18800:18800"
    env_file:
      - .env
    restart: unless-stopped
```

## 🔒 Security

- **API Keys**: Never commit `.env` file or hardcode keys
- **Environment Variables**: All sensitive data via environment
- **CORS**: Configure allowed origins in production
- **Rate Limiting**: Recommended for public deployments

## 📚 Resources

- [smolagents Documentation](https://github.com/huggingface/smolagents)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenRouter API](https://openrouter.ai/)
- [Mem0 Documentation](https://mem0.ai/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Forked from STELLA biomedical AI system
- Built with smolagents by HuggingFace
- LLM access via OpenRouter
- GenomeBench integration for genomic reasoning

---

**LabOS** - Empowering biomedical research through intelligent AI collaboration