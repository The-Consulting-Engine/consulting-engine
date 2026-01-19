# Architecture Document

## System Design Philosophy

The Consulting Engine is built on three core architectural principles:

### 1. Vertical-Agnostic Core
All business logic is generic and reusable. Vertical-specific knowledge lives in JSON configuration files, not code.

### 2. Deterministic First, LLM Second
- Analytics are purely deterministic (math, statistics)
- LLMs only write explanations citing pre-computed evidence
- System never depends on LLM output for decisions

### 3. Graceful Degradation
System always produces output, clearly stating confidence and limitations. Never fails silently.

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (React)                     │
│  • Run creation & management                                 │
│  • File upload with drag-drop                                │
│  • Mapping confirmation UI                                   │
│  • Results visualization                                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓ REST API
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                         │
├─────────────────────────────────────────────────────────────┤
│  API Layer (routes)                                          │
│    • Runs, Uploads, Mappings, Analytics, Reports             │
├─────────────────────────────────────────────────────────────┤
│  Core Services                                               │
│    ┌──────────────────────────────────────────────┐         │
│    │  Vertical Configuration Manager               │         │
│    │  • Loads JSON configs                         │         │
│    │  • Provides canonical schemas                 │         │
│    │  • Returns initiative playbooks               │         │
│    └──────────────────────────────────────────────┘         │
│                                                               │
│    ┌──────────────────────────────────────────────┐         │
│    │  Ingestion Pipeline                           │         │
│    │  1. Column Profiler                           │         │
│    │     • Infer types (numeric, date, text)       │         │
│    │     • Calculate null percentages              │         │
│    │     • Extract sample values                   │         │
│    │  2. LLM Mapper                                │         │
│    │     • Suggests canonical mappings             │         │
│    │     • Assigns confidence scores               │         │
│    │     • Fallback to heuristic matching          │         │
│    └──────────────────────────────────────────────┘         │
│                                                               │
│    ┌──────────────────────────────────────────────┐         │
│    │  Normalization Engine                         │         │
│    │  • Generic transforms (parse_date, to_number) │         │
│    │  • Pack-specific aggregation                  │         │
│    │    - P&L: validate monthly format             │         │
│    │    - Revenue: aggregate transactions          │         │
│    │    - Labor: prorate across months             │         │
│    │  • Returns completeness score + warnings      │         │
│    └──────────────────────────────────────────────┘         │
│                                                               │
│    ┌──────────────────────────────────────────────┐         │
│    │  Analytics Engine                             │         │
│    │  1. Build monthly panel (join all packs)      │         │
│    │  2. Detect operating mode                     │         │
│    │     • PNL_MODE (3+ months, P&L data)          │         │
│    │     • OPS_MODE (2+ months, ops data)          │         │
│    │     • DIRECTIONAL_MODE (limited data)         │         │
│    │  3. Compute metrics                           │         │
│    │     • Averages, totals                        │         │
│    │     • Linear trends                           │         │
│    │     • Volatility (CV)                         │         │
│    │     • Outlier detection                       │         │
│    │     • Vertical signals (labor %, COGS %)      │         │
│    │  4. Generate evidence keys                    │         │
│    └──────────────────────────────────────────────┘         │
│                                                               │
│    ┌──────────────────────────────────────────────┐         │
│    │  Initiative Selector                          │         │
│    │  1. Filter by eligibility (deterministic)     │         │
│    │  2. Limit by mode                             │         │
│    │  3. LLM selection + explanations              │         │
│    │  4. Deterministic sizing                      │         │
│    │     • Percentage of revenue                   │         │
│    │     • Percentage of labor                     │         │
│    │     • Fixed value ranges                      │         │
│    │  5. Ranking by priority score                 │         │
│    └──────────────────────────────────────────────┘         │
│                                                               │
│    ┌──────────────────────────────────────────────┐         │
│    │  Report Generator                             │         │
│    │  • Markdown Memo (LLM-written narrative)      │         │
│    │  • PowerPoint Deck (python-pptx)              │         │
│    │  • Fallback to templates if LLM fails         │         │
│    └──────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                       │
│  • Runs, Uploads, Mappings                                   │
│  • Analytics Facts (evidence-keyed)                          │
│  • Initiatives (with explanations)                           │
│  • Reports (file paths)                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Upload Phase

```
CSV File → Column Profiler → Profile JSON
                                   ↓
                      Store in DB (Upload record)
                                   ↓
                           UI displays profile
```

### 2. Mapping Phase

```
Upload + Vertical Config → LLM Mapper → Suggested Mappings
                                             ↓
                                    User Confirmation
                                             ↓
                              Store in DB (Mapping records)
```

### 3. Normalization Phase

```
Raw CSV + Mappings → Apply Transforms → Pack-Specific Logic
                                              ↓
                                     Normalized DataFrame
                                              ↓
                                  (not persisted, kept in memory)
```

### 4. Analytics Phase

```
Normalized DataFrames → Join to Panel → Detect Mode
                                            ↓
                                    Compute Metrics
                                            ↓
                            Store as Analytics Facts (evidence-keyed)
```

### 5. Initiative Phase

```
Analytics Facts + Playbook → Filter Eligible → LLM Select
                                                    ↓
                                         Deterministic Sizing
                                                    ↓
                                           Rank by Priority
                                                    ↓
                                    Store as Initiative records
```

### 6. Report Phase

```
Facts + Initiatives → LLM Prompt → Narrative
                                       ↓
                            Generate Markdown/PPTX
                                       ↓
                              Save to filesystem
                                       ↓
                          Store path in Report record
```

---

## Key Design Patterns

### 1. Configuration-Driven

**Problem**: Hard-coded business logic makes system inflexible.

**Solution**: JSON configs define:
- Data schemas (fields, synonyms)
- Computed signals (formulas)
- Initiative playbooks (rules, sizing)
- Default assumptions (thresholds)

**Benefit**: New verticals without code changes.

### 2. Evidence-Based LLM Usage

**Problem**: LLMs hallucinate numbers and recommendations.

**Solution**: 
1. Compute all metrics deterministically
2. Store as evidence-keyed facts
3. LLM can ONLY cite evidence keys
4. Fallback to templates if LLM fails

**Benefit**: All recommendations grounded in data.

### 3. Tiered Confidence

**Problem**: Incomplete data leads to overconfident output.

**Solution**: Operating modes with explicit thresholds:
- PNL_MODE: 0.6+ confidence, comprehensive analysis
- OPS_MODE: 0.7+ confidence, operational insights
- DIRECTIONAL_MODE: <0.6 confidence, limited recommendations

**Benefit**: Never implies certainty where none exists.

### 4. Graceful Normalization

**Problem**: Real-world data is messy (missing values, misaligned periods).

**Solution**:
- All transforms handle nulls gracefully
- Proration for cross-month periods
- Completeness scores for transparency
- Warnings logged but don't fail pipeline

**Benefit**: System works with imperfect data.

### 5. Generic Transform Library

**Problem**: Each vertical needs different data transformations.

**Solution**: Reusable transform functions:
- `parse_date`, `parse_month`
- `to_number`, `sum_columns`, `coalesce_columns`
- Pack-specific aggregation (monthly, proration)

**Benefit**: Normalization logic shared across verticals.

---

## Database Schema

### Core Tables

**runs**
- Diagnostic run metadata
- Vertical selection
- Operating mode and confidence
- Status tracking

**uploads**
- File metadata
- Column profiling results
- Links to run

**mappings**
- Source → canonical field mappings
- Transform specification
- Confidence and confirmation status

**analytics_facts**
- Evidence-keyed metrics
- Value (numeric or text)
- Period, unit, source
- Links to run

**initiatives**
- Selected initiative details
- Impact sizing (low/mid/high)
- Rank and priority score
- LLM explanation
- Assumptions and data gaps

**reports**
- Report type (memo, deck)
- File path
- Generation timestamp

---

## Extension Points

### Adding a New Vertical

1. Create `{vertical}_v1.json` in `playbooks/`
2. Define data packs with canonical fields
3. Specify signals to compute
4. Build initiative playbook
5. Set default assumptions

**No code changes required.**

### Adding a New Transform

1. Add method to `NormalizationEngine._apply_transform()`
2. Document in vertical config examples
3. Update tests

### Adding a New Signal

1. Add to vertical config `signals` array
2. Implement formula or special logic in `AnalyticsEngine._compute_signals()`
3. Reference in initiative eligibility rules

### Adding a New Sizing Method

1. Add case in `InitiativeSelector._size_initiatives()`
2. Document parameters in vertical config
3. Use in initiative `sizing_method`

---

## LLM Integration Strategy

### Where LLMs Are Used

1. **Column Mapping Suggestions**
   - Input: Column profiles + canonical schema
   - Output: Mapping suggestions with confidence
   - Fallback: Heuristic name matching

2. **Initiative Selection**
   - Input: Eligible initiatives + analytics facts
   - Output: Selected initiatives with explanations
   - Fallback: Top N by priority weight

3. **Report Narrative**
   - Input: Analytics facts + initiatives
   - Output: Markdown memo text
   - Fallback: Template-based generation

### Where LLMs Are NOT Used

- Computing any metrics (purely deterministic)
- Making decisions (initiative eligibility, sizing, ranking)
- Data transformations
- Validation logic

### LLM Prompt Engineering

**Principles:**
1. **Zero data in prompts** - Only metadata (column names, types, samples)
2. **Strict output format** - Always request JSON
3. **Explicit constraints** - "ONLY cite evidence keys", "ONLY select from playbook"
4. **Temperature control** - 0.0 for mapping, 0.2 for selection, 0.4 for narrative
5. **Fallback always available** - System never depends on LLM success

---

## Testing Strategy

### Unit Tests
- Transform functions
- Metric calculations
- Mode detection
- Initiative filtering

### Integration Tests
- Full pipeline with sample data
- Multiple verticals
- Error handling

### Manual Testing
- Upload various CSV formats
- Verify mapping suggestions
- Check report quality
- Validate calculations

---

## Performance Considerations

### Current Scale
- Single diagnostic run: 30-60 seconds
- Data size: Up to 100K rows per file
- LLM calls: 2-3 per run (mapping, selection, memo)

### Optimization Opportunities
- Cache vertical configs
- Batch LLM requests
- Async report generation
- Database indexing on evidence_key

### Scalability Notes
- Current design: Single-tenant, synchronous
- For multi-tenant: Add user auth, row-level security
- For real-time: WebSocket updates, job queue

---

## Security & Data Privacy

### Current State
- No authentication (founder-operated)
- No encryption at rest
- OpenAI API: Data not used for training (per policy)

### Production Considerations
- Add JWT auth
- Encrypt sensitive fields
- GDPR compliance (data deletion)
- Audit logging

---

## Monitoring & Observability

### Current Logging
- FastAPI request/response logs
- Pipeline stage completion
- LLM failures (fallback triggered)
- Data quality warnings

### Production Additions
- Metrics: Run duration, LLM latency, error rates
- Alerts: Pipeline failures, low confidence runs
- Dashboards: Usage stats, vertical adoption

---

## Why This Architecture Works

1. **Clear separation** between generic core and vertical configs
2. **Deterministic foundation** with LLMs as enhancement
3. **Explicit confidence** prevents overstatement
4. **Fallback at every layer** ensures reliability
5. **Evidence-based** recommendations build trust
6. **Extensible by design** for new verticals

The architecture prioritizes **clarity, correctness, and configurability** over clever abstractions or maximum automation.
