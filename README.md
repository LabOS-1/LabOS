# LabOS

AI-powered laboratory operating system for biomedical research. Built with FastAPI + Next.js.

## Local Deployment

### Prerequisites

- Docker & Docker Compose
- Google Cloud SDK (`gcloud`) — for Cloud SQL Proxy
- Node.js 18+ (if running frontend without Docker)
- Python 3.9+ (if running backend without Docker)

### 1. Clone

```bash
git clone https://github.com/LabOS-1/LabOS.git
cd LabOS
```

### 2. Configure Environment

Copy and edit the backend `.env`:

```bash
cp backend/.env.example backend/.env
```

Required keys in `backend/.env`:

```
GOOGLE_API_KEY=your_google_api_key
ANTHROPIC_API_KEY=your_anthropic_key
AUTH0_CLIENT_ID=your_auth0_client_id
AUTH0_CLIENT_SECRET=your_auth0_secret
AUTH0_DOMAIN=your_auth0_domain
```

### 3. Start Cloud SQL Proxy

The database runs on Google Cloud SQL. Start the proxy before launching:

```bash
cloud_sql_proxy -instances=semiotic-sylph-470501-q5:us-central1:stella-db=tcp:5432 &
```

### 4. Run with Docker Compose

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Once running:
- Frontend: http://localhost:3000
- Backend: http://localhost:18800
- API Docs: http://localhost:18800/docs

### 5. Run Without Docker (alternative)

**Backend:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 18800 --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

## Production Deployment

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Production uses Nginx reverse proxy with SSL on the VM. See `deploy.sh` for details.

## Project Structure

```
LabOS/
├── backend/             # FastAPI backend
│   ├── app/
│   │   ├── api/         # API routes (v1, v2)
│   │   ├── core/        # Agents, tools, middleware
│   │   ├── services/    # Business logic
│   │   └── tools/       # Bio database queries, screening, analysis
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/            # Next.js frontend
│   ├── src/
│   │   ├── app/         # Pages (dashboard, chat, tools, files)
│   │   └── components/  # UI components
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml        # Base config
├── docker-compose.dev.yml    # Local dev override
├── docker-compose.prod.yml   # Production override
└── deploy.sh                 # VM deployment script
```
