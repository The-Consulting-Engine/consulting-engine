# Consulting Engine MVP 0.1

AI-native consulting replacement for restaurants. This MVP is questionnaire-only (no uploads, no scraping, no analytics). It outputs Top 4 Core initiatives + 3 Sandbox experiments.

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

## Architecture

### Backend (FastAPI)
- **Database**: PostgreSQL with SQLAlchemy. Schema is **auto-created on startup** via `Base.metadata.create_all` (no Alembic during MVP).
- **LLM**: Configurable provider (OpenAI or mock mode)
- **Structure**:
  - `app/api/routes/` - API endpoints
  - `app/db/` - Database models and session
  - `app/questionnaire/` - Questionnaire loading and signal evaluation
  - `app/generation/` - LLM-based generation modules
  - `app/llm/` - LLM client and prompts
  - `app/schemas/` - JSON validation schemas
  - `app/seed/` - Seed data (questionnaires, signal maps, categories)

### Frontend (React + Vite + TypeScript)
- **Pages**:
  - HomePage: Create organization
  - QuestionsPage: Complete questionnaire
  - ResultsPage: View generated initiatives and memo

### Docker
- 3 services: `db`, `api`, `web`
- Schema bootstrap on API startup (tables created if missing). No migrations.
- Hot reload for development

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

## MVP 0.1 Features

✅ Questionnaire-based intake
✅ Deterministic signal derivation
✅ LLM-powered category scoring (10 fixed categories)
✅ Top 4 core initiatives generation
✅ 3 sandbox experiments generation
✅ Numeric guardrails (no $, %, or large numbers)
✅ Mock LLM mode for local development
✅ Full Docker setup

## Data Model

- **organizations**: Organizations
- **cycles**: Analysis cycles per organization
- **questionnaire_responses**: Questionnaire answers + derived signals
- **category_scores**: LLM-scored categories
- **initiatives**: Core and sandbox initiatives

## API Endpoints

- `POST /api/orgs` - Create organization
- `GET /api/orgs/{org_id}` - Get organization
- `POST /api/cycles` - Create cycle
- `GET /api/cycles/{cycle_id}` - Get cycle
- `GET /api/cycles/{cycle_id}/questionnaire` - Get questionnaire
- `POST /api/cycles/{cycle_id}/questionnaire` - Save responses
- `POST /api/cycles/{cycle_id}/generate` - Generate results (4 core + 3 sandbox initiatives)
- `GET /api/cycles/{cycle_id}/results` - Get results

## Development

The application runs in Docker Compose for local development. The backend API auto-reloads on code changes, and the frontend uses Vite's hot module replacement.

**Schema changes during MVP:** Tables are created from SQLAlchemy models on startup. If you change models, run `make reset-db` to drop the DB volume and recreate tables. See `backend/REINTRODUCE_ALEMBIC.md` for the plan to bring back migrations later.

## Question Types

The questionnaire supports:
- **single_select**: Dropdown selection
- **multi_select**: Multiple checkboxes (with max_selected limit)
- **ranking**: Drag-and-drop ranking (stores as ordered array)
- **likert_1_5**: 1-5 scale rating
- **short_text**: Short text input
- **long_text**: Long text area

## LLM Configuration

- **Model**: Defaults to `gpt-4o` (supports Structured Outputs for reliable JSON)
- **Structured Outputs**: Automatically used for `gpt-4o` models to ensure schema compliance
- **Timeout**: 120 seconds per LLM call
- **Fallback**: Mock mode if OpenAI fails or `LLM_PROVIDER=mock`
