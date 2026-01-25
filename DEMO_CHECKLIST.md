# Demo Checklist - $10M Pitch

## Pre-Demo Setup

### 1. Environment Check
- [ ] Docker and Docker Compose installed
- [ ] Ports 5173, 8000, 5432 available
- [ ] `.env` file created (optional, defaults to mock mode)

### 2. Start Services
```bash
make up
```

Wait for all services to be healthy:
- [ ] Database is running (check logs: `docker compose logs db`)
- [ ] API is running (check http://localhost:8000); schema auto-created on startup
- [ ] Frontend is running (check http://localhost:5173)

### 3. Verify Endpoints
- [ ] `GET http://localhost:8000/` returns `{"status": "ok", "version": "0.1.0"}`
- [ ] `GET http://localhost:8000/docs` shows Swagger UI
- [ ] Frontend loads at http://localhost:5173

## Demo Flow

### Step 1: Create Organization
- [ ] Navigate to http://localhost:5173
- [ ] Enter organization name (e.g., "Demo Restaurant")
- [ ] Click "Create Organization & Start Cycle"
- [ ] Should redirect to questionnaire page

### Step 2: Complete Questionnaire
- [ ] All required questions are marked with *
- [ ] Can select single select options
- [ ] Can select multiple checkboxes (respects max_selected)
- [ ] Likert scale (1-5) works
- [ ] Text fields work (with character limits)
- [ ] Form validation prevents submission with missing required fields

### Step 3: Generate Results
- [ ] Click "Submit & Generate Results"
- [ ] Should show loading state
- [ ] Should redirect to results page
- [ ] Should display:
  - [ ] Top 5 Core Initiatives (numbered 1-5)
  - [ ] 2 Sandbox Experiments (labeled as "Sandbox / Experimental")
  - [ ] Memo with markdown rendering

### Step 4: Verify Results Quality
- [ ] No currency symbols ($, €, £) in memo
- [ ] No percent signs (%) in memo
- [ ] No large numbers (except "30 days" and "90 days")
- [ ] Initiatives cite questionnaire context (question IDs)
- [ ] Sandbox initiatives are clearly labeled as speculative
- [ ] All initiatives have measurement methods

## Critical Checks

### Backend
- [ ] All API endpoints return proper status codes
- [ ] Error handling works (try invalid cycle_id)
- [ ] Schema bootstrap completed on startup (tables exist)
- [ ] Mock LLM mode returns deterministic results

### Frontend
- [ ] No console errors in browser
- [ ] All pages load without errors
- [ ] Navigation works (back/forward)
- [ ] Results page handles empty states

### Data Integrity
- [ ] Signals are derived correctly from questionnaire
- [ ] Category scores are between 0-100
- [ ] Exactly 5 core initiatives
- [ ] Exactly 2 sandbox initiatives
- [ ] Memo is generated and stored

## Troubleshooting

### If services don't start:
```bash
make down
make up
```

### If database errors:
- API retries DB connection on startup. If it still fails, run `make reset-db` (DESTRUCTIVE).

### If frontend doesn't connect:
- Check `VITE_API_URL` in docker-compose.yml
- Verify backend is running on port 8000
- Check browser console for CORS errors

### If generation fails:
- Check API logs: `docker compose logs api`
- Verify LLM_PROVIDER is set to "mock" for demo
- Check that questionnaire was completed

## Demo Script

1. **Introduction** (30 sec)
   - "This is an AI-native consulting replacement for restaurants"
   - "MVP 0.1 focuses on questionnaire-based intake"

2. **Create Organization** (15 sec)
   - Show clean UI
   - Enter "Demo Restaurant"
   - Create cycle

3. **Questionnaire** (2 min)
   - "The questionnaire captures constraints, operations reality, and marketing channels"
   - Fill out key sections:
     - Context & Constraints
     - What's broken
     - Labor & Operations
     - Menu & Pricing
     - Marketing Channels
   - "Notice the deterministic signal derivation happening in the background"

4. **Generate Results** (30 sec)
   - Click submit
   - "The system scores 10 fixed categories, selects top 5, and generates initiatives"

5. **Show Results** (3 min)
   - **Top 5 Core Initiatives**
     - "Each initiative is grounded in questionnaire responses"
     - "Notice the citation of question IDs"
     - "No financial math, no dollar values - operator-friendly language"
   
   - **Sandbox Experiments**
     - "These are clearly labeled as speculative"
     - "Reversible in 30 days"
     - "Include stop conditions"
   
   - **Memo**
     - "Owner-friendly markdown memo"
     - "No currency symbols, no percentages"
     - "Includes assumptions and measurement guidance"

6. **Key Differentiators** (1 min)
   - "Deterministic signals, not AI guessing"
   - "Fixed categories, not invented"
   - "Constraint-aware recommendations"
   - "Traceable to questionnaire responses"

## Success Criteria

✅ All services start without errors
✅ Complete questionnaire flow works
✅ Results are generated successfully
✅ No currency/percent symbols in output
✅ Exactly 5 core + 2 sandbox initiatives
✅ Memo is readable and professional
✅ No console errors
✅ Fast response times (< 5 seconds for generation)

## Post-Demo

- [ ] Save demo data (optional)
- [ ] Document any issues encountered
- [ ] Note questions asked by investors
