# Quick Start Guide - After Installing Docker Desktop

Follow these steps to get the Consulting Engine app running after you've installed Docker Desktop.

## Step 1: Verify Docker is Running

Open a terminal and check Docker is working:

```bash
docker --version
docker compose version
```

You should see version numbers. If you get errors, make sure Docker Desktop is running (look for the whale icon in your menu bar/taskbar).

## Step 2: Create Environment File

Create a `.env` file in the project root directory:

```bash
cd /Users/sidkancharapu/consulting-engine
touch .env
```

Then open `.env` in a text editor and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-your-actual-api-key-here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
```

**Important**: 
- Replace `sk-your-actual-api-key-here` with your real OpenAI API key
- Get your API key from: https://platform.openai.com/api-keys
- You need a paid OpenAI account with API access

## Step 3: Start All Services

Run this single command:

```bash
docker-compose up --build
```

**What this does:**
- Downloads Docker images (first time only, takes 2-3 minutes)
- Builds backend and frontend containers
- Starts PostgreSQL database
- Starts Backend API server
- Starts Frontend UI
- Initializes database automatically

**What you'll see:**
- Lots of output as images download and services start
- Eventually you'll see messages like:
  - `backend-1  | INFO:     Uvicorn running on http://0.0.0.0:8000`
  - `frontend-1 | VITE v5.0.8  ready in XXX ms`

**First run takes 2-3 minutes** - be patient!

## Step 4: Verify Everything is Running

Open a **new terminal window** (keep the first one running) and check:

```bash
docker-compose ps
```

You should see three services all "Up":
- `ai-consultant-db-1` (PostgreSQL)
- `ai-consultant-backend-1` (FastAPI)
- `ai-consultant-frontend-1` (React/Vite)

## Step 5: Access the Application

Open your web browser and go to:

- **Frontend UI**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

You should see the Upload Data page at http://localhost:5173

## Step 6: Test the App (First Time Usage)

### 1. Upload Sample Data

1. Go to http://localhost:5173
2. Click **"Select Files"**
3. Navigate to the `sample_data/` folder in your project
4. Select `gl_pnl_monthly.csv` (required)
5. Optionally select other CSV files: `payroll_summary.csv`, `vendor_spend.csv`, `revenue_by_segment.csv`
6. Click **"Upload"**

### 2. (Optional) Add Company Context

1. Click **"Company Context"** in the navigation bar
2. Fill in information about your company (all optional)
3. Click **"Save Company Context"**

### 3. Run Analysis

1. Click **"Results"** in the navigation bar
2. Click **"Run Analysis"** button
3. Wait 30-60 seconds for the pipeline to complete
4. You'll see ranked initiatives appear in a table

### 4. Download Reports

On the Results page:
- Click **"Download Memo (Markdown)"** for the executive memo
- Click **"Download Deck (PPTX)"** for the PowerPoint presentation

## Step 7: Stop Services (When Done)

Press `Ctrl+C` in the terminal where `docker-compose up` is running.

Or in a new terminal:

```bash
docker-compose down
```

To also delete database data:

```bash
docker-compose down -v
```

## Troubleshooting

### "Docker Desktop is not running"
- Open Docker Desktop application
- Wait for it to fully start (whale icon in menu bar)
- Try the commands again

### "Port already in use"
- Port 5173 (frontend), 8000 (backend), or 5432 (database) is taken
- Stop other applications using these ports
- Or change ports in `docker-compose.yml`

### "Cannot connect to the Docker daemon"
- Make sure Docker Desktop is running
- On macOS/Windows, Docker Desktop must be running
- Try restarting Docker Desktop

### Services won't start
```bash
# View logs to see what's wrong
docker-compose logs

# Restart from scratch
docker-compose down -v
docker-compose up --build
```

### "No GL/P&L data found" error
- You need to upload `gl_pnl_monthly.csv` first
- Go to Upload Data page and upload the file
- Then try Run Analysis again

### API key errors
- Make sure `.env` file exists with correct API key
- Check the key is valid at https://platform.openai.com/api-keys
- Restart Docker: `docker-compose restart backend`

## Next Steps

Once it's running:
- Read [README.md](README.md) for detailed usage
- Check API docs at http://localhost:8000/docs
- Review sample data formats in `sample_data/` directory

## Common Commands

```bash
# Start services
docker-compose up

# Start in background (detached mode)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View running containers
docker-compose ps

# Rebuild after code changes
docker-compose up --build
```

That's it! The app should now be running. 🎉
