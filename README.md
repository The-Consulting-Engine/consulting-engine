# Consulting Engine - Financial Diagnostics & Improvement System

An AI-native decision system that ingests company financial/operational data, reconstructs a canonical P&L, generates and ranks cost/EBITDA improvement initiatives, and produces executive-ready outputs.

## Overview

This MVP provides a guided decision workflow (not an autonomous agent) that:

1. **Ingests CSVs**: `gl_pnl_monthly.csv` (required), plus optional: payroll summary, vendor spend, revenue by segment
2. **Reconstructs P&L**: Builds a canonical monthly P&L (gross margin, EBITDA, EBITDA margin)
3. **Runs Diagnostics**: Deterministic analysis of margin bridges, outliers, data completeness
4. **Generates Initiatives**: Uses LLM to propose initiative hypotheses (no math, only suggestions)
5. **Sizes & Ranks**: Deterministically sizes and ranks initiatives (impact range, confidence, risk, time-to-value)
6. **Produces Outputs**: Markdown executive memo and PowerPoint deck (always generated, even with minimal data)

## How It Works

### System Flow

```
┌─────────────────┐
│  Upload CSVs    │  → User uploads gl_pnl_monthly.csv (required) + optional files
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Validate Data  │  → CSV validation, schema checking, error reporting
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Run Analysis   │  → User clicks "Run Analysis" button (explicit action)
└────────┬────────┘
         │
         ├─→ Reconstruct P&L (gross margin, EBITDA, margins)
         ├─→ Run Diagnostics (margin bridges, outliers, trends)
         ├─→ Generate Initiatives (LLM proposes hypotheses)
         ├─→ Size Initiatives (deterministic calculations)
         └─→ Rank Initiatives (score = impact × confidence / (risk × time))
         │
         ▼
┌─────────────────┐
│  View Results   │  → Ranked table, detailed views, download reports
└─────────────────┘
```

### Detailed Process

#### 1. Data Ingestion
- **Required**: `gl_pnl_monthly.csv` with columns: `month`, `revenue`, `cogs`, `opex_sales_marketing`, `opex_rnd`, `opex_gna`, `opex_other`
- **Optional**: 
  - `payroll_summary.csv` - Enables headcount optimization initiatives
  - `vendor_spend.csv` - Enables vendor consolidation initiatives
  - `revenue_by_segment.csv` - Enables segment-specific analysis
- Data is validated, normalized, and stored in PostgreSQL

#### 2. P&L Reconstruction
- Builds canonical monthly P&L from GL data
- Calculates derived metrics:
  - `gross_margin = revenue - cogs`
  - `gross_margin_pct = (gross_margin / revenue) × 100`
  - `total_opex = sum of all opex categories`
  - `ebitda = gross_margin - total_opex`
  - `ebitda_margin_pct = (ebitda / revenue) × 100`
- Handles division by zero gracefully

#### 3. Diagnostics
- **Margin Bridge**: Month-over-month EBITDA changes decomposed into revenue, COGS, and opex impacts
- **Outliers**: Detects vendor spend spikes, opex spikes, revenue declines (using Z-scores)
- **Trends**: Calculates linear trends for revenue, EBITDA, margins (using numpy-only regression)
- **Fixed vs Variable Costs**: Estimates cost structure using heuristics + correlation (no full regression)
- **Data Completeness**: Assesses missing data, calculates completeness score, generates data gaps list

#### 4. Initiative Generation (LLM)
- LLM receives diagnostics summary and P&L summary
- Generates initiative hypotheses:
  - Title, description, category
  - Owner suggestions
  - No financial calculations (LLM doesn't do math)
- If LLM fails, pipeline continues with empty initiatives list

#### 5. Initiative Sizing (Deterministic)
- Each initiative is sized based on available data:
  - **Impact Range**: Low and high annual impact estimates
  - **Implementation Cost**: Estimated one-time cost
  - **Time to Value**: Weeks to realize impact
  - **Risk Level**: Low, Med, or High
  - **Confidence**: 0.2 to 0.9 based on data quality
- **Missing Data Handling**:
  - If required data missing → uses heuristics, reduces confidence, widens ranges
  - Marks `needs_data = true` flag
  - Never blocks execution

#### 6. Ranking
- Formula: `score = (impact_mid × confidence) / (risk_multiplier × time_multiplier)`
- Where:
  - `impact_mid = (impact_low + impact_high) / 2`
  - `risk_multiplier`: Low=1.0, Med=1.2, High=1.5
  - `time_multiplier = base + (weeks × per_week)`
- Configurable via `ranking_config.json`

#### 7. Report Generation
- **Executive Memo** (Markdown):
  - Executive summary
  - P&L trends and diagnostics
  - Top 5 initiatives table
  - Data gaps / what would improve confidence
- **PowerPoint Deck** (PPTX):
  - Executive summary slide
  - P&L & EBITDA trend charts
  - Cost structure charts
  - Top initiative deep dive
  - Roadmap or data gaps slide
- Reports always generate, even with no initiatives

## Architecture

The system follows a clean separation of concerns:

```
backend/
  app/
    api/              # FastAPI routers
    core/             # Settings, configuration
    ingestion/        # CSV schemas, validators, loaders
    analytics/        # Deterministic diagnostics + P&L reconstruction
    initiatives/      # Initiative definitions, sizing, ranking
    ai/               # LLM integration (OpenAI/Anthropic)
    reports/          # Memo + slide generation
    storage/          # SQLAlchemy models + database layer
frontend/
  src/
    pages/           # Upload, Results
    components/      # Reusable UI components
    api/             # API client
    types/           # TypeScript types
```

### Key Principles

- **Deterministic-first**: All calculations and sizing are deterministic and reproducible
- **AI-assisted, not AI-driven**: LLMs only propose hypotheses and generate narrative text
- **Auditable**: All recommendations are traceable to source data
- **Extensible**: Clean architecture for future platform expansion

## Tech Stack

### Backend
- Python 3.11
- FastAPI
- PostgreSQL + SQLAlchemy + Alembic
- Pandas + NumPy (no SciPy)
- OpenAI API (or Anthropic)
- python-pptx (PowerPoint generation)
- matplotlib (charts)

### Frontend
- React 18
- TypeScript
- Vite
- Material-UI (MUI)
- Recharts

### Infrastructure
- Docker + docker-compose
- PostgreSQL 15

## Installation & Setup

### Prerequisites

- **Docker** (version 20.10+) and **Docker Compose** (version 2.0+)
- **OpenAI API key** (or Anthropic API key)
  - Get one at: https://platform.openai.com/api-keys
  - Or: https://console.anthropic.com/ (for Anthropic)

### Quick Start (Docker - Recommended)

1. **Clone the repository**

```bash
git clone <repository-url>
cd consulting-engine
```

2. **Create environment file**

Create a `.env` file in the root directory:

```bash
# Copy example if it exists, or create new
touch .env
```

Add the following to `.env`:

```env
# Required: OpenAI API Key
OPENAI_API_KEY=sk-your-api-key-here

# Optional: LLM Configuration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview

# Optional: Anthropic (if using instead of OpenAI)
# ANTHROPIC_API_KEY=your-anthropic-key
# LLM_PROVIDER=anthropic
```

3. **Start all services**

```bash
docker-compose up --build
```

This command will:
- Build Docker images for backend and frontend
- Start PostgreSQL database (port 5432)
- Start Backend API server (port 8000)
- Start Frontend development server (port 5173)
- Initialize database schema automatically

**First run may take 2-3 minutes** to download images and install dependencies.

4. **Verify services are running**

```bash
docker-compose ps
```

You should see three services: `db`, `backend`, `frontend` all in "Up" state.

5. **Access the application**

- **Frontend UI**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health

6. **Stop services**

```bash
docker-compose down
```

To also remove volumes (deletes database data):
```bash
docker-compose down -v
```

### Manual Setup (Development)

For development, you can run services manually instead of Docker:

#### Step 1: Start Database

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

**Option B: Local PostgreSQL**
```bash
# Install PostgreSQL 15, then:
createdb ai_consultant_db
# Or use psql to create database
```

#### Step 2: Setup Backend

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate
# On macOS/Linux: source venv/bin/activate

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

#### Step 3: Setup Frontend

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

#### Step 4: Verify Installation

1. Check backend: http://localhost:8000/docs (should show Swagger UI)
2. Check frontend: http://localhost:5173 (should show upload page)
3. Check database connection: Backend logs should show no connection errors

## Usage Guide

### Step-by-Step Workflow

#### Step 1: Provide Company Context (Optional but Recommended)

1. Navigate to **Company Context** page (http://localhost:5173/context)
2. Fill in information about your company:
   - Company name, industry, size
   - Revenue range, employee count
   - Business model, growth stage
   - Key challenges and strategic priorities
3. Click **"Save Company Context"**

**Why it matters**: Company context helps the AI generate more relevant and tailored improvement initiatives. For example:
- A SaaS company might get recommendations about subscription optimization
- A growth-stage company might get scaling efficiency suggestions
- Industry-specific challenges inform initiative prioritization

#### Step 2: Upload Data

1. Navigate to **Upload Data** page (http://localhost:5173)
2. Click **"Select Files"** and choose your CSV files
3. Click **"Upload"** to validate and store data

**Required File:**
- **gl_pnl_monthly.csv** - Must be uploaded for pipeline to run

**Optional Files** (improve analysis quality):
- **payroll_summary.csv** - Enables headcount optimization initiatives
- **vendor_spend.csv** - Enables vendor consolidation initiatives  
- **revenue_by_segment.csv** - Enables segment-specific analysis

**Important Notes:**
- Only `gl_pnl_monthly.csv` is required
- Pipeline will run even if optional files are missing
- Missing optional data reduces confidence scores and widens impact ranges
- Upload validation shows errors immediately

**Sample Data:**
- Example CSV files are in `sample_data/` directory
- Use these as templates for your data format

#### CSV Format Requirements

**gl_pnl_monthly.csv**
```csv
month,revenue,cogs,opex_sales_marketing,opex_rnd,opex_gna,opex_other
2023-01,2500000,750000,400000,600000,300000,200000
```

**payroll_summary.csv**
```csv
month,function,headcount,fully_loaded_cost
2023-01,Sales,25,187500
2023-01,R&D,40,360000
```

**vendor_spend.csv**
```csv
month,vendor,category,amount
2023-01,AWS,Cloud Infrastructure,85000
2023-01,Salesforce,CRM Software,45000
```

**revenue_by_segment.csv**
```csv
month,segment,revenue
2023-01,Enterprise,1500000
2023-01,Mid-Market,750000
```

### 3. Run Analysis

Navigate to the Results page and click **"Run Analysis"** to execute the full pipeline:

1. Reconstructs P&L from uploaded data (requires `gl_pnl_monthly.csv`)
2. Runs diagnostics (margin bridges, outliers, data completeness)
3. Uses LLM to generate initiative proposals
4. Deterministically sizes each initiative (impact range, cost, time, confidence)
5. Ranks initiatives using formula: `score = impact_mid * confidence / (risk_multiplier * time_multiplier)`

**Important**: The pipeline will always run and produce outputs (memo + PPTX) even with only `gl_pnl_monthly.csv`. Missing optional data will:
- Reduce confidence scores
- Widen impact ranges
- Disable certain initiative types (marked with `needs_data = true`)
- Include data gaps section in reports

### 4. View Results & Download Reports

On the Results page, you can:
- View ranked initiatives in a table
- Click any initiative to see detailed information
- Download **Executive Memo** (Markdown) with data gaps section
- Download **PowerPoint Deck** (PPTX) with charts and analysis

Reports always generate, even if no initiatives are recommended (will show "No new initiatives recommended this quarter").

## API Endpoints

### Ingestion
- `POST /ingest/upload` - Upload CSV files

### Analysis
- `POST /analyze/pnl` - Reconstruct P&L
- `POST /analyze/diagnostics` - Run diagnostics

### Initiatives
- `POST /initiatives/generate` - Generate initiatives (LLM)
- `POST /initiatives/score` - Size initiatives (deterministic)
- `POST /initiatives/rank` - Rank initiatives

### Reports
- `GET /reports/memo` - Download executive memo (Markdown)
- `GET /reports/deck` - Download PowerPoint deck

### Pipeline
- `POST /run/full` - Run full pipeline (ingestion → analysis → initiatives → ranking)

### Company Context
- `GET /context` - Get current company context
- `POST /context` - Save or update company context
- `DELETE /context` - Delete company context

See http://localhost:8000/docs for interactive API documentation.

## Configuration

### Ranking Multipliers

Edit `backend/app/initiatives/ranking_config.json` to adjust initiative ranking multipliers:

```json
{
  "risk_multiplier_low": 1.0,
  "risk_multiplier_med": 1.2,
  "risk_multiplier_high": 1.5,
  "time_multiplier_base": 1.0,
  "time_multiplier_per_week": 0.01
}
```

The ranking formula is: `score = impact_mid * confidence / (risk_multiplier * time_multiplier)`

### LLM Provider

Set `LLM_PROVIDER` in `.env`:
- `openai` (default) - Uses OpenAI API
- `anthropic` - Uses Anthropic API (requires implementation)

## Data Model

The system stores data in PostgreSQL:

- **data_uploads**: Upload metadata and validation status
- **gl_pnl_monthly**: Normalized GL/P&L data
- **payroll_summary**: Normalized payroll data
- **vendor_spend**: Normalized vendor spend data
- **revenue_by_segment**: Normalized revenue data
- **company_context**: Company context information (name, industry, size, challenges, etc.)
- **analysis_runs**: Analysis run metadata and results
- **initiatives**: Generated initiatives with sizing and ranking

## Architecture Decisions

### Deterministic Analytics

All financial calculations, diagnostics, and initiative sizing are deterministic Python code using pandas + numpy only (no SciPy). This ensures:
- Reproducible results
- Testable logic
- CFO-credible outputs
- Minimal dependencies

### LLM Usage Boundaries

LLMs are used ONLY for:
- Generating initiative hypotheses (titles, descriptions, categories)
- Narrative text generation

LLMs are NOT used for:
- Financial calculations
- Initiative sizing
- Ranking/scoring
- Data validation

### Single-Tenant MVP

The current implementation is single-tenant (no multi-tenancy, auth, or billing). This keeps the MVP focused and extensible for future platform features.

## Testing

Run analytics tests:

```bash
cd backend
python -m pytest app/tests/
```

## Extension Path

The system is designed to extend into a platform:

1. **Multi-tenancy**: Add company/user management
2. **Decision Memory**: Track accepted/rejected initiatives and outcomes
3. **Custom Benchmarks**: Replace mock benchmarks with real peer data
4. **Advanced Analytics**: Add more diagnostic metrics
5. **Workflow Automation**: Schedule analyses, alerts, etc.
6. **Integration APIs**: Connect to accounting systems, spend management tools

## Troubleshooting

### Database Connection Issues

Ensure PostgreSQL is running and accessible:
```bash
docker-compose ps
docker-compose logs db
```

### LLM API Errors

Check your API key is set correctly:
```bash
echo $OPENAI_API_KEY
```

Verify the API key works:
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Frontend Not Loading

Check CORS settings in `backend/app/core/config.py`. Ensure frontend URL is in `cors_origins`.

### Missing Data

The system is designed to work with only `gl_pnl_monthly.csv`. If optional files are missing:
- The pipeline will still run
- Confidence scores will be reduced
- Some initiative types may be disabled
- Reports will include a "Data Gaps" section

If the pipeline fails, ensure `gl_pnl_monthly.csv` is uploaded and passes validation.

## License

[Add your license here]

## Contributing

[Add contribution guidelines if applicable]
