# Setup Guide - Consulting Engine

This guide will walk you through setting up the Consulting Engine application step by step.

## Prerequisites

Before you begin, make sure you have:

1. **Docker Desktop** (version 20.10+) and **Docker Compose** (version 2.0+)
   - Download: https://www.docker.com/products/docker-desktop
   - Verify installation: `docker --version` and `docker compose version`

2. **OpenAI API Key** (required for initiative generation)
   - Get one at: https://platform.openai.com/api-keys
   - You'll need a paid OpenAI account with API access

## Quick Setup (Docker - Recommended)

This is the easiest way to get started. Docker will handle all dependencies automatically.

### Step 1: Clone or Navigate to the Project

```bash
cd consulting-engine
```

### Step 2: Create Environment File

Create a `.env` file in the root directory:

```bash
touch .env
```

Then open `.env` in a text editor and add:

```env
# Required: OpenAI API Key
OPENAI_API_KEY=sk-your-actual-api-key-here

# Optional: LLM Configuration (defaults shown)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview

# Optional: Anthropic (if using instead of OpenAI)
# ANTHROPIC_API_KEY=your-anthropic-key
# LLM_PROVIDER=anthropic
```

**Important**: Replace `sk-your-actual-api-key-here` with your real OpenAI API key.

### Step 3: Start All Services

```bash
docker-compose up --build
```

This command will:
- Download Docker images (first time only, ~2-3 minutes)
- Build backend and frontend containers
- Start PostgreSQL database
- Start Backend API server
- Start Frontend development server
- Initialize database schema automatically

**First run may take 2-3 minutes** to download images and install dependencies.

### Step 4: Verify Services Are Running

Open a new terminal and run:

```bash
docker-compose ps
```

You should see three services all in "Up" state:
- `db` (PostgreSQL)
- `backend` (FastAPI)
- `frontend` (React/Vite)

### Step 5: Access the Application

Once all services are running:

- **Frontend UI**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health

### Step 6: Stop Services (When Done)

```bash
docker-compose down
```

To also remove volumes (deletes database data):
```bash
docker-compose down -v
```

## Manual Setup (For Development)

If you prefer to run services manually without Docker:

### Step 1: Start Database

**Option A: Using Docker (easiest)**
```bash
docker run -d \
  --name ai-consultant-db \
  -e POSTGRES_USER=ai_consultant \
  -e POSTGRES_PASSWORD=ai_consultant_password \
  -e POSTGRES_DB=ai_consultant_db \
  -p 5432:5432 \
  postgres:15-alpine
```

**Option B: Local PostgreSQL Installation**
```bash
# Install PostgreSQL 15 first, then:
createdb ai_consultant_db
# Or use psql to create database
```

### Step 2: Setup Backend

```bash
cd backend

# Create virtual environment (Python 3.11 required)
python3.11 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://ai_consultant:ai_consultant_password@localhost:5432/ai_consultant_db
export OPENAI_API_KEY=your_key_here
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4-turbo-preview

# Initialize database schema
python -c "from app.storage.database import init_db; init_db()"

# Run development server (with auto-reload)
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000

### Step 3: Setup Frontend

Open a **new terminal window**:

```bash
cd frontend

# Install dependencies
npm install

# Set API URL (if backend is on different host/port)
export VITE_API_URL=http://localhost:8000

# Run development server
npm run dev
```

Frontend will be available at: http://localhost:5173

### Step 4: Verify Installation

1. **Check backend**: http://localhost:8000/docs (should show Swagger UI)
2. **Check frontend**: http://localhost:5173 (should show upload page)
3. **Check database connection**: Backend logs should show no connection errors

## First-Time Usage

Once the app is running:

### 1. Provide Company Context (Optional but Recommended)

1. Navigate to **Company Context** page: http://localhost:5173/context
2. Fill in information about your company
3. Click **"Save Company Context"**

This helps generate more relevant initiatives.

### 2. Upload Data

1. Navigate to **Upload Data** page: http://localhost:5173
2. Click **"Select Files"** and choose CSV files
3. **Required**: `gl_pnl_monthly.csv`
4. **Optional**: `payroll_summary.csv`, `vendor_spend.csv`, `revenue_by_segment.csv`
5. Click **"Upload"**

Sample CSV files are in the `sample_data/` directory.

### 3. Run Analysis

1. Navigate to **Results** page: http://localhost:5173/results
2. Click **"Run Analysis"** button
3. Wait for pipeline to complete (~30-60 seconds)

### 4. View Results & Download Reports

- View ranked initiatives table
- Click any initiative for details
- Download Executive Memo (Markdown)
- Download PowerPoint Deck (PPTX)

## Troubleshooting

### Docker Issues

**Services won't start:**
```bash
# Check Docker is running
docker ps

# View logs
docker-compose logs

# Rebuild from scratch
docker-compose down -v
docker-compose up --build
```

**Port already in use:**
- Change ports in `docker-compose.yml` if 5173, 8000, or 5432 are taken

### Backend Issues

**Database connection errors:**
- Verify PostgreSQL is running: `docker ps` (if using Docker)
- Check DATABASE_URL environment variable
- Ensure database exists and credentials are correct

**Module not found errors:**
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

**OpenAI API errors:**
- Verify OPENAI_API_KEY is set correctly
- Check API key is valid: https://platform.openai.com/api-keys
- Ensure you have API credits

### Frontend Issues

**npm install fails:**
- Clear cache: `npm cache clean --force`
- Delete `node_modules` and `package-lock.json`, then reinstall

**Can't connect to backend:**
- Check VITE_API_URL environment variable
- Verify backend is running on port 8000
- Check CORS settings in backend

### Common Errors

**"No GL/P&L data found":**
- Upload `gl_pnl_monthly.csv` first before running analysis

**"LLM API error":**
- Check OpenAI API key is valid
- Verify you have API credits
- Check network connection

**Database migration errors:**
- Drop and recreate database: `docker-compose down -v && docker-compose up`

## Next Steps

After setup:
1. Read the full [README.md](README.md) for detailed usage instructions
2. Check the API documentation at http://localhost:8000/docs
3. Review sample data in `sample_data/` directory
4. Customize ranking multipliers in `backend/app/initiatives/ranking_config.json`

## Need Help?

- Check the [README.md](README.md) for detailed documentation
- Review API docs at http://localhost:8000/docs
- Check logs: `docker-compose logs` or backend/frontend console output
