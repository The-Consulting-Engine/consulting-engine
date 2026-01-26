# Consulting Engine MVP 0.1

An AI-native consulting replacement for restaurants. This MVP is questionnaire-only (no uploads, no scraping, no analytics). It outputs **Top 4 Core initiatives** + **3 Sandbox experiments** based on structured questionnaire responses.

## What This System Does

1. **Collects** structured questionnaire responses from restaurant owners
2. **Derives** deterministic signals (flags and scores) from responses
3. **Scores** 10 fixed micro-playbook categories using LLM
4. **Selects** top 4 categories for core initiatives
5. **Generates** detailed core initiatives and sandbox experiments using LLM
6. **Presents** results in an owner-friendly format

## System Flow

```
User Input → Questionnaire → Signal Derivation → Category Scoring → Initiative Generation → Results
```

### Step-by-Step Process

1. **Questionnaire Intake**
   - User creates an organization and cycle
   - Completes structured questionnaire (Business Profile, Context, What's Broken, etc.)
   - Responses are saved to database

2. **Signal Derivation** (Deterministic)
   - System evaluates responses against signal map rules
   - Generates **flags** (binary truths, e.g., `B1_drags_labor_too_high`)
   - Generates **scores** (0-1 intensity, e.g., `score_urgency: 0.75`)
   - Stores derived signals with responses

3. **Category Scoring** (LLM)
   - LLM scores 10 fixed micro-playbook categories (e.g., `labor_scheduling`, `discounting_discipline`)
   - Uses structured consultant brief (formatted responses + signals)
   - Returns scores 0-1 for each category
   - Scores saved to database

4. **Top 4 Selection** (Deterministic)
   - Categories sorted by score
   - Top 4 selected for core initiatives

5. **Core Initiative Expansion** (LLM)
   - LLM expands each top category into a detailed initiative
   - Includes: title, why_now, what_to_do, how_to_measure, assumptions, confidence
   - 4 core initiatives generated

6. **Sandbox Generation** (LLM)
   - LLM generates 3 speculative experiments
   - Based on questionnaire context but lower confidence
   - Includes same structure as core initiatives

7. **Results Display**
   - Frontend displays all 7 initiatives (4 core + 3 sandbox)
   - Organized by rank and type

## Key Concepts

### Signals

**Signals** are structured insights derived from questionnaire responses. They come in two types:

- **Flags**: Binary truths (e.g., `profile_concept_qsr`, `B1_drags_labor_too_high`)
- **Scores**: Soft intensity 0-1 (e.g., `score_urgency: 0.75`, `score_complexity: 0.4`)

Signals are created deterministically using rules in `questionnaire_signal_map_v0_1.json`. They are **not** pain signals themselves—they're building blocks that inform category scoring and initiative wording.

### Micro-Playbook Categories

10 fixed categories that represent common restaurant operational areas:

1. `labor_scheduling`
2. `discounting_discipline`
3. `manager_cadence`
4. `service_speed`
5. `marketing_ownership`
6. `menu_optimization`
7. `inventory_control`
8. `customer_feedback`
9. `staff_training`
10. `cost_tracking`

Each category is scored 0-1 by the LLM based on questionnaire responses and derived signals.

### Initiatives

**Core Initiatives** (4):
- Top-scoring categories expanded into actionable initiatives
- High confidence, immediate focus areas
- Include detailed steps, measurement, assumptions

**Sandbox Experiments** (3):
- Speculative experiments for testing
- Lower confidence, exploratory
- Based on context but not top categories

## Architecture

### Backend (FastAPI + PostgreSQL)

```
backend/app/
├── main.py                 # FastAPI app, CORS, lifespan events
├── api/routes/             # API endpoints
│   ├── orgs.py            # Organization CRUD
│   ├── cycles.py          # Cycle CRUD
│   ├── questionnaire.py   # Questionnaire get/save
│   ├── generate.py        # Generation trigger
│   └── results.py         # Results retrieval
├── db/
│   ├── models.py          # SQLAlchemy ORM models
│   ├── session.py         # DB session management
│   └── bootstrap.py       # Schema creation on startup
├── questionnaire/
│   ├── loader.py          # Load questionnaire/signal map JSON
│   └── evaluator.py       # Evaluate responses → signals
├── generation/
│   ├── category_scoring.py    # LLM category scoring
│   └── initiative_expansion.py # LLM initiative generation
├── llm/
│   ├── client.py          # OpenAI client wrapper
│   ├── prompts.py         # Prompt construction
│   └── json_guard.py      # JSON validation + mock fallback
├── schemas/               # JSON schemas for validation
│   ├── category_scores.schema.json
│   ├── core_initiatives.schema.json
│   └── sandbox_initiatives.schema.json
└── seed/                  # Seed data
    ├── questionnaire_restaurant_v0_1.json
    ├── questionnaire_signal_map_v0_1.json
    └── micro_playbook_categories_v0_1.json
```

### Frontend (React + Vite + TypeScript)

```
frontend/src/
├── App.tsx                # Router setup
├── pages/
│   ├── HomePage.tsx       # Create organization
│   ├── QuestionsPage.tsx  # Questionnaire form
│   └── ResultsPage.tsx    # Display initiatives
└── api/
    └── client.ts          # API client
```

### Database Schema

- **organizations**: Restaurant organizations
- **cycles**: Analysis cycles (one per organization run)
- **questionnaire_responses**: Responses + derived_signals (JSON)
- **category_scores**: LLM scores for 10 categories (JSON)
- **initiatives**: Core (4) and sandbox (3) initiatives

Schema is auto-created on API startup using `Base.metadata.create_all()` (no Alembic during MVP).

### Docker Services

- **db**: PostgreSQL 15
- **api**: FastAPI backend (port 8000)
- **web**: React frontend (port 5173)

## Quick Start

1. **Start the application:**
   ```bash
   make up
   ```

2. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

3. **Create an organization and complete the questionnaire:**
   - Go to http://localhost:5173
   - Create an organization
   - Fill out the questionnaire
   - Click "Submit & Generate Results"
   - View the results

## Environment Variables

Create a `.env` file in the root directory:

```env
LLM_PROVIDER=openai  # or "mock" for testing
OPENAI_API_KEY=your_key_here  # required if LLM_PROVIDER=openai
LLM_MODEL=gpt-4o  # or gpt-4o-mini for faster responses
```

## Make Commands

- `make up` - Start all services (`docker compose up --build -d`)
- `make down` - Stop all services
- `make logs` - View logs
- `make reset-db` - **(DESTRUCTIVE)** Drop DB volume, rebuild, and start. Use when schema changes during MVP; all data is lost.

## API Endpoints

- `POST /api/orgs` - Create organization
- `GET /api/orgs/{org_id}` - Get organization
- `POST /api/cycles` - Create cycle
- `GET /api/cycles/{cycle_id}` - Get cycle
- `GET /api/cycles/{cycle_id}/questionnaire` - Get questionnaire
- `POST /api/cycles/{cycle_id}/questionnaire` - Save responses
- `POST /api/cycles/{cycle_id}/generate` - Generate results (4 core + 3 sandbox initiatives)
- `GET /api/cycles/{cycle_id}/results` - Get results

## Question Types

The questionnaire supports:
- **single_select**: Dropdown selection
- **multi_select**: Multiple checkboxes (with max_selected limit)
- **ranking**: Drag-and-drop ranking (stores as ordered array)
- **likert_1_5**: 1-5 scale rating
- **short_text**: Short text input
- **long_text**: Long text area

## LLM Integration

### Model Configuration

- **Default**: `gpt-4o` (supports Structured Outputs for reliable JSON)
- **Alternative**: `gpt-4o-mini` (faster, lower cost)
- **Timeout**: 120 seconds per LLM call
- **Fallback**: Mock mode if OpenAI fails or `LLM_PROVIDER=mock`

### Structured Outputs

For `gpt-4o` models, the system uses OpenAI's Structured Outputs feature:
- Ensures JSON schema compliance
- Automatically wraps array schemas in objects
- Recursively adds `additionalProperties: false` to all objects
- Unwraps responses back to expected format

### Generation Stages

1. **Category Scoring**: LLM scores 10 categories (1 LLM call)
2. **Core Expansion**: LLM expands top 4 categories (1 LLM call)
3. **Sandbox Generation**: LLM generates 3 experiments (1 LLM call)

Total: **3 LLM calls** per generation cycle.

### Prompt Engineering

Prompts use a "consultant brief" format:
- Structured, ordered questionnaire responses
- Derived signals (flags + scores)
- Explicit instructions for JSON output
- Examples and formatting rules

See `backend/app/llm/prompts.py` for details.

## Data Flow Example

1. User answers: "Labor costs are too high" (question `B1_drags`)
2. Signal map rule triggers: `B1_drags_labor_too_high` flag
3. LLM sees flag in consultant brief, scores `labor_scheduling` category high (0.9)
4. `labor_scheduling` selected in top 4
5. LLM expands into: "Tighten labor schedules to match demand" initiative
6. User sees actionable initiative with steps and measurement

## Development

The application runs in Docker Compose for local development. The backend API auto-reloads on code changes, and the frontend uses Vite's hot module replacement.

**Schema changes during MVP:** Tables are created from SQLAlchemy models on startup. If you change models, run `make reset-db` to drop the DB volume and recreate tables. See `backend/REINTRODUCE_ALEMBIC.md` for the plan to bring back migrations later.

## Key Files

- **Questionnaire Definition**: `backend/app/seed/questionnaire_restaurant_v0_1.json`
- **Signal Map Rules**: `backend/app/seed/questionnaire_signal_map_v0_1.json`
- **Category Definitions**: `backend/app/seed/micro_playbook_categories_v0_1.json`
- **LLM Prompts**: `backend/app/llm/prompts.py`
- **Signal Evaluation**: `backend/app/questionnaire/evaluator.py`
- **Generation Logic**: `backend/app/generation/`

## Troubleshooting

**Generation hanging or timing out?**
- Check backend logs: `docker compose logs -f api`
- Look for `[GENERATE]` or `[OPENAI]` messages
- Ensure `LLM_MODEL=gpt-4o` (supports Structured Outputs)
- Verify API key is set: `docker compose exec api python -c "from app.llm.client import LLMClient; print(LLMClient().provider)"`

**OpenAI API errors?**
- Verify your API key is set correctly in `.env`
- Check you have API credits available
- Test connection: http://localhost:8000/api/debug/test-openai

**Database connection errors?**
- Wait 10-15 seconds for PostgreSQL to fully initialize
- Restart with: `docker compose restart api`

**Frontend can't connect to backend?**
- Check backend logs: `docker compose logs api`
- Verify backend is running: http://localhost:8000/docs

## MVP 0.1 Features

✅ Questionnaire-based intake with Business Profile section  
✅ Deterministic signal derivation (flags and scores)  
✅ LLM-powered category scoring (10 fixed categories)  
✅ Top 4 core initiatives generation  
✅ 3 sandbox experiments generation  
✅ Structured consultant brief for LLM context  
✅ Numeric guardrails (no $, %, or large numbers)  
✅ OpenAI Structured Outputs support (gpt-4o)  
✅ Mock LLM mode for local development  
✅ Full Docker setup  

## Future Enhancements

- Alembic migrations (see `backend/REINTRODUCE_ALEMBIC.md`)
- Additional verticals (currently `restaurant_v0_1` only)
- CSV data uploads
- Analytics integration
- Report generation (memos, decks)
