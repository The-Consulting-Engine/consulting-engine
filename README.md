# Consulting Engine MVP v2

**A vertical-configured, AI-assisted decision diagnostic system for operating businesses.**

---

## Overview

The Consulting Engine is a founder-operated diagnostic system designed to analyze business operations and recommend actionable initiatives. Built with a **generic core** and **vertical-specific configurations**, the system is currently configured for **restaurant operations** as the first pilot but can be extended to other operating businesses such as:

- Fast food chains
- Franchise operators (e.g., Urban Air)
- Education franchises (e.g., Goddard Schools)
- Other service-based operating businesses

### Key Principles

1. **One decision engine** - Generic pipeline with plug-in vertical configurations
2. **Deterministic analytics first** - LLMs used only for explanation and advisory
3. **Works with messy data** - Handles partial, misaligned, or incomplete data gracefully
4. **Always produces output** - Even in "Directional Mode" with limited data
5. **Explicit confidence** - All assumptions and data quality clearly stated

---

## Architecture

### Vertical Configuration Model

The system uses a **vertical configuration layer** to adapt to different business types without changing core logic:

```
Core Pipeline (Generic)
  ↓
Vertical Config (JSON)
  • Data pack definitions
  • Canonical fields + synonyms
  • Signals to compute
  • Initiative playbook
  • Eligibility rules
  • Sizing heuristics
  ↓
Business-Specific Analysis
```

**Current Configurations:**
- `restaurant_v1.json` - Restaurant operations (7 initiatives)
- `general_v1.json` - Fallback for generic operating businesses (3 initiatives)

---

## System Workflow

### 1. Run Creation
Create a diagnostic run and select a vertical configuration.

### 2. Data Ingestion
Upload CSV files for any combination of:
- **P&L** - Monthly profit & loss statement
- **Revenue** - Transaction-level revenue data (POS, invoices, etc.)
- **Labor** - Payroll and labor data

### 3. Column Mapping
- System profiles uploaded columns (type, null %, samples)
- LLM suggests mappings to canonical fields
- User confirms mappings via UI

### 4. Normalization
Generic normalization engine transforms data to monthly panels:
- Date parsing and month inference
- Cross-month allocation (for payroll periods)
- Handles missing data gracefully
- Returns completeness score and warnings

### 5. Analytics
Deterministic analytics compute:
- Basic metrics (averages, totals)
- Trends (linear regression)
- Volatility (coefficient of variation)
- Outliers (standard deviation based)
- Vertical-specific signals (labor %, COGS %, etc.)

**Operating Modes:**
- **PNL_MODE** - Complete P&L with 3+ months (confidence 0.6+)
- **OPS_MODE** - Operational data with 2+ months (confidence 0.7+)
- **DIRECTIONAL_MODE** - Limited data, directional insights only

### 6. Initiative Selection
Playbook-driven approach:
1. Deterministic eligibility filtering (data requirements, minimum months)
2. Initiative count limited by operating mode
3. LLM selects initiatives and writes explanations
4. Deterministic sizing based on vertical rules
5. Ranking by priority score

**Restaurant Initiatives:**
- Pricing discipline
- Labor scheduling optimization
- Discount control
- Table turnover improvement
- Overhead reduction
- Waste minimization
- Dynamic pricing

### 7. Report Generation
Produces:
- **Markdown Executive Memo** - Owner-friendly narrative with evidence keys
- **PowerPoint Deck** - 5-7 slides with metrics and initiatives

LLM writes narrative using ONLY computed analytics facts (evidence keys). Falls back to deterministic templates if LLM fails.

---

## Tech Stack

### Backend
- **Python 3.11**
- **FastAPI** - API framework
- **SQLAlchemy 2.0** - ORM
- **PostgreSQL 15** - Database
- **Pandas + NumPy** - Data processing
- **OpenAI API** - LLM provider (single provider, no frameworks)
- **python-pptx** - PowerPoint generation
- **matplotlib** - Charts

### Frontend
- **React 18**
- **TypeScript**
- **Vite** - Build tool
- **Material-UI (MUI)** - Component library
- **Axios** - HTTP client

### Infrastructure
- **Docker + docker-compose** - Containerization

---

## Setup & Installation

### Prerequisites
- Docker and Docker Compose
- OpenAI API key

### Quick Start

1. **Clone the repository**
   ```bash
   cd consulting-engine
   ```

2. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Start the system**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Sample Data

Sample restaurant data is included in `sample_data/`:
- `restaurant_pnl_monthly.csv` - 12 months of P&L data
- `restaurant_revenue_pos.csv` - POS transaction samples
- `restaurant_labor_payroll.csv` - Payroll data with pay periods

---

## Usage Guide

### Creating Your First Diagnostic

1. **Create a Run**
   - Navigate to http://localhost:3000
   - Click "New Diagnostic Run"
   - Select vertical (restaurant_v1 for demo)
   - Enter company name
   - Click "Create & Start"

2. **Upload Data**
   - Select pack type (PNL, REVENUE, or LABOR)
   - Choose CSV file
   - Click "Upload File"
   - Repeat for additional data packs

3. **Map Columns**
   - Click "Map Columns" for each upload
   - Review LLM-suggested mappings
   - Adjust confidence if needed
   - Click "Confirm Mappings"

4. **Run Analysis**
   - Once all mappings confirmed, click "Start Analysis"
   - System will compute analytics and select initiatives
   - Takes 30-60 seconds depending on data size

5. **View Results**
   - Review operating mode and confidence
   - Examine key metrics and evidence
   - Review ranked initiatives with impact estimates
   - Generate reports (Memo and/or Deck)

---

## Extending to New Verticals

The system is designed to be extended to new business verticals. Here's how:

### 1. Create a New Vertical Configuration

Create `backend/app/initiatives/playbooks/your_vertical_v1.json`:

```json
{
  "vertical_id": "your_vertical_v1",
  "vertical_name": "Your Vertical Name",
  "data_packs": [
    {
      "pack_type": "PNL",
      "fields": [
        {
          "name": "month",
          "required": true,
          "synonyms": ["period", "date"],
          "field_type": "date",
          "description": "Month identifier"
        },
        // ... more fields
      ]
    }
  ],
  "signals": [
    {
      "signal_id": "your_signal",
      "label": "Your Signal Label",
      "requires": ["field1", "field2"],
      "formula": "field1 / field2 * 100"
    }
  ],
  "initiatives": [
    {
      "id": "your_init_001",
      "title": "Your Initiative",
      "category": "Category",
      "description": "Description",
      "eligibility_rules": {
        "min_months": 3,
        "requires_data": ["PNL"]
      },
      "sizing_method": "percentage_of_revenue",
      "sizing_params": {
        "low": 0.02,
        "mid": 0.05,
        "high": 0.08
      },
      "priority_weight": 1.0
    }
  ],
  "default_assumptions": {
    "min_confidence_for_ops_mode": 0.7,
    "min_confidence_for_pnl_mode": 0.6,
    "max_initiatives_directional": 3,
    "max_initiatives_ops": 5,
    "max_initiatives_pnl": 7
  }
}
```

### 2. Key Configuration Elements

**Data Packs**: Define canonical fields for each pack type (PNL, REVENUE, LABOR)
- Use generic field names when possible
- Include synonyms for flexible mapping
- Mark required vs. optional fields

**Signals**: Computed metrics specific to the vertical
- Simple ratio formulas supported
- Can reference other signals for complex calculations

**Initiatives**: Fixed playbook of recommendations
- Eligibility rules (data requirements, minimum months)
- Sizing methods:
  - `percentage_of_revenue`
  - `percentage_of_labor`
  - `percentage_of_cogs`
  - `fixed_value`
- Priority weights for ranking

### 3. Design Guidelines

- **Keep the core generic** - Don't hardcode vertical-specific logic in core modules
- **Use canonical field names** - Even if different from source data
- **Be explicit about requirements** - Clearly state what data is needed
- **Size conservatively** - Use ranges and acknowledge uncertainty
- **Document assumptions** - Make it clear what the system assumes

---

## Data Handling Philosophy

### Messy Data is Expected

The system is designed to work with real-world data:
- **Partial coverage**: Missing months or incomplete data packs
- **Misaligned data**: Revenue from Q1, labor from Q2
- **Poor quality**: High null percentages, inconsistent formats
- **Multiple formats**: Different POS systems, accounting software exports

### Graceful Degradation

1. **PNL_MODE** → Full P&L with 3+ months → Comprehensive analysis
2. **OPS_MODE** → Revenue or Labor data → Operational insights
3. **DIRECTIONAL_MODE** → Limited data → High-level recommendations only

The system ALWAYS produces output, clearly stating confidence and limitations.

### Evidence-Based Narrative

LLMs only cite **evidence keys** from deterministic analytics:
- `revenue_avg_monthly`
- `labor_pct`
- `revenue_trend`
- `labor_volatility`

This ensures all recommendations are grounded in actual data, not hallucinated.

---

## API Reference

### Runs
- `POST /api/runs/` - Create new run
- `GET /api/runs/` - List all runs
- `GET /api/runs/{run_id}` - Get run details
- `GET /api/runs/verticals/list` - List available verticals

### Uploads
- `POST /api/uploads/{run_id}/upload` - Upload CSV file
- `GET /api/uploads/{run_id}/uploads` - List uploads
- `POST /api/uploads/{run_id}/uploads/{upload_id}/suggest-mappings` - Get LLM mapping suggestions

### Mappings
- `POST /api/mappings/{run_id}/confirm` - Confirm column mappings
- `GET /api/mappings/{run_id}/mappings` - Get confirmed mappings

### Analytics
- `POST /api/analytics/{run_id}/analyze` - Run full analysis
- `GET /api/analytics/{run_id}/results` - Get analysis results

### Reports
- `POST /api/reports/{run_id}/generate-memo` - Generate Markdown memo
- `POST /api/reports/{run_id}/generate-deck` - Generate PowerPoint deck
- `GET /api/reports/{run_id}/reports` - List generated reports
- `GET /api/reports/download/{report_id}` - Download report file

---

## Development

### Running Tests
```bash
cd backend
pytest app/tests/
```

### Project Structure
```
consulting-engine/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routes
│   │   ├── core/             # Configuration & vertical config
│   │   ├── db/               # Database models
│   │   ├── ingestion/        # CSV profiling & mapping
│   │   ├── normalization/    # Generic normalization engine
│   │   ├── analytics/        # Deterministic analytics
│   │   ├── initiatives/      # Initiative selection & playbooks
│   │   ├── llm/              # OpenAI client
│   │   ├── reports/          # Report generation
│   │   └── tests/            # Test suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/              # API client
│   │   ├── pages/            # React pages
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
├── sample_data/              # Sample CSV files
├── docker-compose.yml
└── README.md
```

---

## Why This Scales Beyond Restaurants

The architecture is **truly vertical-agnostic**:

### Generic Core Components
1. **Ingestion** - Profile any CSV, map to canonical fields
2. **Normalization** - Transform to monthly panels regardless of source format
3. **Analytics** - Compute metrics from unified panel structure
4. **Initiative Selection** - Playbook-driven with configurable rules
5. **Reporting** - Template-based with evidence key citation

### Vertical-Specific Configurations
- JSON files define business-specific logic
- No code changes required for new verticals
- Initiatives and sizing rules are declarative

### Example Verticals

**Urban Air (Franchise):**
- Data packs: PNL, Bookings, Staff
- Signals: Utilization %, labor efficiency, booking conversion
- Initiatives: Peak capacity optimization, upsell programs, staff training

**Goddard Schools (Education):**
- Data packs: PNL, Enrollment, Staffing
- Signals: Enrollment trends, teacher-to-student ratio, retention rate
- Initiatives: Enrollment campaigns, curriculum enhancements, capacity planning

**General Operating Business:**
- Minimal data requirements
- Conservative initiative set
- Focus on operational efficiency and cost control

---

## Limitations & Future Work

### Current Limitations
- Single LLM provider (OpenAI)
- No real-time data integration
- No multi-tenancy or user authentication
- Limited to monthly aggregation (no weekly/daily)
- No predictive forecasting

### Potential Enhancements
- Add more vertical configurations
- Weekly/daily analysis granularity
- Benchmarking against industry standards
- Multi-year trend analysis
- Custom playbook builder UI
- A/B testing framework for initiatives

---

## Contributing

This is a founder-operated system, not yet a SaaS platform. Contributions should focus on:
- New vertical configurations
- Improved normalization heuristics
- Additional sizing methods
- Enhanced report templates
- Test coverage

---

## License

Proprietary - Internal use only

---

## Support

For questions or issues:
1. Check API documentation at http://localhost:8000/docs
2. Review sample data for expected format
3. Examine vertical configuration files for customization options

---

**Built with clarity, determinism, and extensibility in mind.**
