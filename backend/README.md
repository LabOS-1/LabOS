# LABOS AI Backend

FastAPI backend for LABOS (Self-Evolving Intelligent Laboratory Assistant) - Advanced AI for biomedical research.

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- pip or poetry
- Virtual environment (recommended)

### Installation

1. **Clone and navigate to backend directory:**
   ```bash
   cd labos-be
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

4. **Start the server:**
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 18800 --reload
   ```

5. **Verify installation:**
   ```bash
   curl http://localhost:18800/health
   ```

## 📦 Server Information

- **URL:** http://localhost:18800
- **API Docs:** http://localhost:18800/docs (Swagger UI)
- **ReDoc:** http://localhost:18800/redoc
- **Health Check:** http://localhost:18800/health

## 🏗️ Architecture

### Tech Stack

- **Framework:** FastAPI 0.100+
- **ASGI Server:** Uvicorn
- **WebSocket:** Native FastAPI WebSocket support
- **AI Integration:** LABOS AI system
- **Database:** File-based storage + Memory management
- **Language:** Python 3.9+

### Project Structure

```
labos-be/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/                 # API route modules
│   │   ├── chat.py          # Chat endpoints
│   │   ├── agents.py        # Agent management
│   │   ├── tools.py         # Tool management
│   │   ├── files.py         # File operations
│   │   ├── memory.py        # Memory/Knowledge base
│   │   ├── system.py        # System status & health
│   │   └── websocket.py     # WebSocket endpoints
│   └── services/            # Business logic services
│       ├── labos_service.py        # Core LABOS integration
│       ├── websocket_manager.py     # WebSocket connection management
│       ├── websocket_broadcast.py   # WebSocket broadcasting
│       └── workflow_service.py      # Workflow management
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── README.md               # This file
```

## 🔧 Configuration

### Environment Variables

Create `.env` file in the project root:

```bash
# API Configuration
HOST=0.0.0.0
PORT=18800
DEBUG=true

# Database Configuration
ENVIRONMENT=development  # or 'production'
DB_USER=labos-user
DB_PASSWORD=labos-secure-password-2024
CLOUD_SQL_CONNECTION_NAME=semiotic-sylph-470501-q5:us-central1:labos-db
DB_NAME=labos_chat          # Production database
DEV_DB_NAME=labos_chat_dev  # Development database

# LABOS AI Configuration
LABOS_API_KEY=your_api_key_here
LABOS_MODEL=gpt-4
LABOS_MAX_TOKENS=4096

# Logging
LOG_LEVEL=INFO
LOG_FILE=labos.log

# CORS Settings (for frontend)
CORS_ORIGINS=["http://localhost:3001", "http://localhost:3000"]
```

### Database Setup (Google Cloud SQL)

This project uses **Google Cloud SQL (PostgreSQL)** for data persistence.

#### Prerequisites

1. **Google Cloud SDK** installed and configured
2. **Cloud SQL Proxy** installed via gcloud
3. **Active GCP account** with Cloud SQL API enabled

#### Local Development Setup

**Step 1: Authenticate with Google Cloud**

```bash
# Login to Google Cloud
gcloud auth login

# Set your project
gcloud config set project semiotic-sylph-470501-q5

# Verify authentication
gcloud auth list
```

**Step 2: Install Cloud SQL Proxy**

```bash
# Install Cloud SQL Proxy component
gcloud components install cloud-sql-proxy

# Verify installation
cloud_sql_proxy --version
```

**Step 3: Start Cloud SQL Proxy**

Before running the backend server, you **MUST** start the Cloud SQL Proxy to enable local connection to Cloud SQL:

```bash
# Start Cloud SQL Proxy in the background
# This creates a local TCP connection on port 5432 that proxies to Cloud SQL
nohup cloud_sql_proxy -instances=semiotic-sylph-470501-q5:us-central1:labos-db=tcp:5432 > /tmp/cloud_sql_proxy.log 2>&1 &

# Verify Cloud SQL Proxy is running
ps aux | grep cloud_sql_proxy

# Check the logs if needed
tail -f /tmp/cloud_sql_proxy.log
```

**Step 4: Verify Database Connection**

```bash
# Test connection using psql (optional)
psql "host=localhost port=5432 user=labos-user dbname=labos_chat_dev password=labos-secure-password-2024"
```

**Step 5: Start the Backend Server**

```bash
cd labos-be
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 18800 --reload
```

#### Development vs Production

- **Development** (`ENVIRONMENT=development`):
  - Uses `labos_chat_dev` database
  - Connects via Cloud SQL Proxy on `localhost:5432` (TCP)
  - Requires Cloud SQL Proxy to be running locally
  
- **Production** (`ENVIRONMENT=production`):
  - Uses `labos_chat` database
  - Connects via Unix socket (`/cloudsql/...`)
  - No Cloud SQL Proxy needed (runs on GCP with direct socket connection)

#### Stopping Cloud SQL Proxy

```bash
# Find the process ID
ps aux | grep cloud_sql_proxy

# Kill the process
pkill -f cloud_sql_proxy

# Or kill by PID
kill <PID>
```

#### Troubleshooting Database Connection

1. **Connection Refused Error**
   ```
   ConnectionRefusedError: [Errno 61] Connection refused
   ```
   - **Solution**: Cloud SQL Proxy is not running. Start it using the command in Step 3.

2. **Cloud SQL Proxy Won't Start**
   ```bash
   # Check if port 5432 is already in use
   lsof -i :5432
   
   # Kill any existing process on that port
   kill -9 <PID>
   ```

3. **Authentication Errors**
   ```bash
   # Re-authenticate with Google Cloud
   gcloud auth login
   gcloud auth application-default login
   ```

4. **Database Not Found**
   - Ensure you're using the correct database name:
     - Development: `labos_chat_dev`
     - Production: `labos_chat`

## 📊 API Endpoints

### System & Health

- `GET /health` - Quick health check with connection count
- `GET /api/system/status` - Comprehensive system status
- `GET /api/system/health` - Detailed health information

### Chat & AI

- `POST /api/chat/send` - Send message to LABOS AI
  ```json
  {
    "message": "Hello, LABOS!",
    "workflow_id": "optional_workflow_id"
  }
  ```

### Agents

- `GET /api/agents` - List all available agents
- `GET /api/agents/{agent_id}` - Get specific agent details
- `POST /api/agents/{agent_id}/execute` - Execute agent task

### Tools

- `GET /api/tools` - List all available tools
- `GET /api/tools/{tool_id}` - Get specific tool details
- `POST /api/tools/create` - Create new dynamic tool

### Files

- `POST /api/files/upload` - Upload files for processing
- `GET /api/files` - List uploaded files
- `GET /api/files/{file_id}` - Get file details
- `DELETE /api/files/{file_id}` - Delete file

### Memory & Knowledge

- `GET /api/memory/search` - Search knowledge base
- `POST /api/memory/add` - Add to knowledge base
- `GET /api/memory/stats` - Get memory statistics

### WebSocket

- `WebSocket /ws` - Real-time communication
  - Send: `{"type": "ping"}` for keep-alive
  - Send: `{"type": "chat_message", "message": "Hello"}`
  - Receive: Workflow updates, progress, system status

## 🌊 WebSocket Events

### Incoming Events (Client → Server)

```json
{"type": "ping"}
{"type": "chat_message", "message": "Your message"}
{"type": "join_room", "room": "workflow_123"}
{"type": "request_system_status"}
```

### Outgoing Events (Server → Client)

```json
{"type": "pong", "timestamp": "2024-01-01T00:00:00Z"}
{"type": "workflow_step", "workflow_id": "123", "step_info": {...}}
{"type": "progress_update", "progress": 50, "current_step": 2, "total_steps": 4}
{"type": "connection_established", "message": "Connected to LABOS AI Backend"}
```

## 🤖 LABOS AI Integration

### Authentication

LABOS runs in two modes:

1. **Authentic Mode**: Full LABOS AI integration (requires API keys)
2. **Mock Mode**: Simulated responses (for development/demo)

### Workflow Processing

When a message is sent:
1. **Query Analysis** - LABOS analyzes the request
2. **Agent Selection** - Chooses appropriate specialist agent
3. **Tool Loading** - Loads relevant tools dynamically
4. **Task Execution** - Executes with real-time updates
5. **Memory Integration** - Saves results to knowledge base

### Real-time Updates

All LABOS operations broadcast real-time updates via WebSocket:
- Step-by-step progress
- Tool executions
- Thought processes
- Final results

## 🛠️ Development

### Running in Development

```bash
# With auto-reload
python -m uvicorn app.main:app --host 0.0.0.0 --port 18800 --reload

# With debug logging
LOG_LEVEL=DEBUG python -m uvicorn app.main:app --host 0.0.0.0 --port 18800 --reload
```

### Testing API

```bash
# Health check
curl http://localhost:18800/health

# Send chat message
curl -X POST http://localhost:18800/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello LABOS!"}'

# Get system status
curl http://localhost:18800/api/system/status
```

### Adding New Endpoints

1. Create route in appropriate `app/api/` module
2. Add business logic in `app/services/`
3. Update this README with new endpoint documentation
4. Test with Swagger UI at `/docs`

## 🔧 Dependencies

### Core Dependencies

```
fastapi>=0.100.0          # Web framework
uvicorn>=0.23.0            # ASGI server
websockets>=11.0.0         # WebSocket support
pydantic>=2.0.0            # Data validation
python-multipart>=0.0.6    # File upload support
```

### AI & Scientific Libraries

```
openai>=1.0.0              # OpenAI API
anthropic>=0.7.0           # Anthropic Claude API
requests>=2.31.0           # HTTP client
numpy>=1.24.0              # Numerical computing
pandas>=2.0.0              # Data analysis
```

### Utility Libraries

```
python-dotenv>=1.0.0       # Environment variables
pyyaml>=6.0                # YAML parsing
rich>=13.0.0               # Terminal formatting
typer>=0.9.0               # CLI interface
psutil>=5.9.0              # System monitoring
```

## 🐛 Troubleshooting

### Common Issues

1. **ImportError: No module named 'app'**
   ```bash
   # Make sure you're in the labos-be directory
   cd labos-be
   python -m uvicorn app.main:app --host 0.0.0.0 --port 18800 --reload
   ```

2. **PermissionError during LABOS initialization**
   - LABOS will automatically run in mock mode
   - Check file permissions in the current directory
   - Ensure virtual environment is activated

3. **Port 18800 already in use**
   ```bash
   # Find and kill the process
   lsof -i :18800
   kill -9 <PID>
   
   # Or use a different port
   python -m uvicorn app.main:app --host 0.0.0.0 --port 18801 --reload
   ```

4. **CORS errors from frontend**
   - Check CORS settings in `app/main.py`
   - Ensure frontend URL is in allowed origins

### Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with Python debugger
python -m pdb -m uvicorn app.main:app --host 0.0.0.0 --port 18800

# Check logs
tail -f labos.log
```

## 📊 System Monitoring

### Health Endpoints

- `/health` - Basic health with WebSocket count
- `/api/system/health` - Detailed health information
- `/api/system/status` - Full system status including LABOS state

### Metrics

The system tracks:
- Uptime
- WebSocket connections
- Active workflows
- LABOS initialization status
- Memory usage
- Request counts

## 🔒 Security Considerations

### API Security

- Input validation with Pydantic models
- CORS protection for web clients
- Rate limiting (recommended for production)
- API key authentication (for LABOS integration)

### WebSocket Security

- Connection validation
- Message type verification
- Automatic disconnection cleanup
- Room-based access control

## 🚀 Production Deployment

### Using Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ app/
EXPOSE 18800

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "18800"]
```

### Using Systemd

Create `/etc/systemd/system/labos-backend.service`:

```ini
[Unit]
Description=LABOS AI Backend
After=network.target

[Service]
Type=exec
User=labos
WorkingDirectory=/path/to/labos-be
ExecStart=/path/to/labos-be/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 18800
Restart=always

[Install]
WantedBy=multi-user.target
```

### Environment Setup

```bash
# Production environment
export ENVIRONMENT=production
export DEBUG=false
export LOG_LEVEL=INFO

# Start with gunicorn for production
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:18800
```

## 📚 Learn More

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn ASGI Server](https://www.uvicorn.org/)
- [Pydantic Data Validation](https://pydantic-docs.helpmanual.io/)
- [WebSocket with FastAPI](https://fastapi.tiangolo.com/advanced/websockets/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is part of the LABOS AI system for biomedical research.