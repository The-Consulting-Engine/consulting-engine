# Signals Implementation Verification

## ✅ Signals System Implementation Status

### 1️⃣ What Signals Are
**Status: ✅ IMPLEMENTED**

Signals are structured interpretations of questionnaire responses, stored as:
- **Flags**: Binary yes/no statements (e.g., `pain_labor_high`, `constraint_no_pricing_control`)
- **Scores**: 0-1 normalized values (e.g., `schedule_confidence: 0.25`)
- **Notes**: Metadata about signal derivation

**Location**: `backend/app/questionnaire/evaluator.py`

### 2️⃣ Signal Creation Process
**Status: ✅ IMPLEMENTED**

**Step 1**: User answers questionnaire
- ✅ Handled in `frontend/src/pages/QuestionsPage.tsx`
- ✅ Saved via `POST /api/cycles/{cycle_id}/questionnaire`

**Step 2**: Deterministic rules run
- ✅ Rules loaded from `backend/app/seed/questionnaire_signal_map_v0_1.json`
- ✅ Evaluated in `evaluate_responses()` function
- ✅ Supports operators: `exists`, `equals`, `contains`, `in`, `lte`, `gte`, `regex`

**Step 3**: Scores normalized
- ✅ Likert 1-5 mapped to 0-1: `(value - 1) / 4.0`
- ✅ Example: `C2_schedule_confidence: 2` → `schedule_confidence: 0.25`

**Step 4**: Signals stored once
- ✅ Stored in `questionnaire_responses.derived_signals` (JSONB column)
- ✅ Immutable for the cycle (set once, never modified)
- ✅ Structure:
  ```json
  {
    "flags": ["pain_labor_high", "signal_schedule_low_confidence"],
    "scores": {"schedule_confidence": 0.25},
    "notes": ["Derived from questionnaire only."]
  }
  ```

### 3️⃣ Signal Usage (Three Uses)

#### Use 1: Category Scoring ✅
**Status: ✅ IMPLEMENTED**

- Signals passed to `build_category_scoring_prompt()`
- LLM uses flags and scores to determine category relevance
- Example: `pain_labor_high` + `signal_schedule_low_confidence` → boosts `labor_scheduling` category

**Location**: `backend/app/generation/category_scoring.py`

#### Use 2: Constraint Enforcement ✅
**Status: ✅ IMPLEMENTED**

- Constraints extracted: `[f for f in flags if f.startswith("constraint_")]`
- Explicit rule in prompt: "If constraints include constraint_no_pricing_control, avoid pricing change initiatives or frame as validation only"
- Prevents irresponsible recommendations

**Location**: `backend/app/llm/prompts.py` line 61, 91

#### Use 3: Evidence Citation ✅
**Status: ✅ IMPLEMENTED**

- Prompts instruct LLM to cite question IDs and signals
- `why_now` field must cite questionnaire context
- Example: "B1_drags includes Labor too high" (traceable to signals)

**Location**: `backend/app/llm/prompts.py` lines 32, 37, 80, 125

### 4️⃣ Signal Map Rules
**Status: ✅ IMPLEMENTED**

Rules defined in `backend/app/seed/questionnaire_signal_map_v0_1.json`:
- ✅ Constraint flags (franchise pricing, menu lock, etc.)
- ✅ Pain flags (labor high, staffing chaos, etc.)
- ✅ Signal flags (schedule low confidence, menu complex, etc.)
- ✅ Score mappings (schedule_confidence, marketing_roi_confidence)

### 5️⃣ Data Flow

```
Questionnaire Responses
    ↓
evaluate_responses() [deterministic]
    ↓
derived_signals {flags, scores, notes}
    ↓
Stored in questionnaire_responses.derived_signals
    ↓
Used in:
  1. Category scoring (LLM prompt)
  2. Initiative expansion (with constraint checks)
  3. Memo generation (for evidence)
```

## ✅ All Requirements Met

The signals system is fully implemented according to the specification:
- ✅ Deterministic signal derivation
- ✅ Flags and scores properly structured
- ✅ Signals stored once and immutable
- ✅ Used for category scoring
- ✅ Used for constraint enforcement
- ✅ Used for evidence citation
- ✅ No math, no inference - just structured facts
