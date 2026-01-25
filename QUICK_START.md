# Quick Start Guide

## For Your $10M Demo Tomorrow

### 1. Start Everything (One Command)
```bash
make up
```

This will:
- Start PostgreSQL database
- Start FastAPI backend (schema auto-created on startup via `create_all`)
- Start React frontend

### 2. Verify It's Working
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 3. Demo Flow
1. Go to http://localhost:5173
2. Create an organization (e.g., "Demo Restaurant")
3. Fill out the questionnaire
4. Click "Submit & Generate Results"
5. View the results page

### 4. If Something Breaks
```bash
# Stop everything
make down

# Restart (rebuild)
make up

# Check logs
make logs

# Schema changed? Reset DB (DESTRUCTIVE, loses all data)
make reset-db
```

### 5. Key Points for Demo
- ✅ Mock LLM mode (no API key needed)
- ✅ Deterministic results (same inputs = same outputs)
- ✅ No currency/percent symbols in output
- ✅ Exactly 5 core + 2 sandbox initiatives
- ✅ Signals are derived deterministically
- ✅ All recommendations cite questionnaire context

### 6. Environment Variables (Optional)
Create `.env` file if you want to use OpenAI:
```env
LLM_PROVIDER=openai
LLM_API_KEY=your_key_here
```

**For demo, you don't need this - mock mode works perfectly!**

## Troubleshooting

**Port already in use?**
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Find and kill process on port 5173
lsof -ti:5173 | xargs kill -9
```

**Database connection error?**
- API retries DB connection on startup (up to 20 attempts). If it still fails, run `make reset-db` to recreate the DB volume and restart.

**"Could not connect to API" / "Failed to fetch"?**
1. Restart everything: `make down && make up`
2. Wait ~30 seconds for the API to be ready
3. Verify API: `curl http://localhost:8000/` → should return `{"status":"ok",...}`
4. Open **http://localhost:5173** (not 127.0.0.1) and do a **hard refresh** (Ctrl+Shift+R or Cmd+Shift+R)

**Frontend won't load?**
- Check browser console for errors
- Verify backend is running: `curl http://localhost:8000/`
- Ensure all 3 containers are up: `docker compose ps`

## Success Indicators

✅ All three services running (`docker compose ps`)
✅ http://localhost:8000/ returns `{"status": "ok"}`
✅ http://localhost:5173 shows the home page
✅ No errors in `make logs`

Good luck with your demo! 🚀
