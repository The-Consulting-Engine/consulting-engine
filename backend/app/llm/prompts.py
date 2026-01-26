from typing import Dict, Any, List, Optional


def _multi_select_schema(vertical_id: str) -> Dict[str, List[str]]:
    """Load questionnaire and return q_id -> options for multi_select questions."""
    from app.questionnaire.loader import load_questionnaire
    q = load_questionnaire(vertical_id)
    out: Dict[str, List[str]] = {}
    for sec in q.get("sections", []):
        for qn in sec.get("questions", []):
            if qn.get("type") == "multi_select" and qn.get("options"):
                out[qn["id"]] = list(qn["options"])
    return out


def format_responses_for_prompt(
    responses: Dict[str, Any],
    vertical_id: Optional[str] = None,
) -> str:
    """Format questionnaire responses for LLM prompt.
    For multi_select questions, includes both selected and not selected options when
    vertical_id is provided (not selected is often as important, e.g. marketing channels not used).
    """
    multi_opts = _multi_select_schema(vertical_id) if vertical_id else {}
    lines = []
    for q_id, value in responses.items():
        opts = multi_opts.get(q_id)
        if opts is not None:
            selected = value if isinstance(value, list) else ([value] if value is not None else [])
            selected = [str(s).strip() for s in selected if s is not None and str(s).strip()]
            not_selected = [o for o in opts if o not in selected]
            sel_str = ", ".join(selected) if selected else "(none)"
            not_str = ", ".join(not_selected) if not_selected else "(none)"
            lines.append(f"{q_id}: selected: {sel_str}; not selected: {not_str}")
        else:
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
            else:
                value_str = str(value)
            lines.append(f"{q_id}: {value_str}")
    return "\n".join(lines)


def build_category_scoring_prompt(
    questionnaire_responses: Dict[str, Any],
    derived_signals: Dict[str, Any],
    categories: List[Dict[str, str]],
    vertical_id: str = "restaurant_v0_1",
) -> str:
    """Build prompt for scoring the 10 categories."""
    categories_text = "\n".join([
        f"- {cat['id']}: {cat['label']} - {cat['description']}"
        for cat in categories
    ])
    
    flags_text = ", ".join(derived_signals.get("flags", []))
    scores_text = ", ".join([f"{k}: {v:.2f}" for k, v in derived_signals.get("scores", {}).items()])
    
    return f"""You are scoring 10 fixed restaurant improvement categories based on questionnaire responses.

CATEGORIES (you may ONLY score from this list):
{categories_text}

QUESTIONNAIRE RESPONSES (for multi-select, both "selected" and "not selected" are shown; not selected is often as important, e.g. marketing channels they don't use):
{format_responses_for_prompt(questionnaire_responses, vertical_id)}

DERIVED SIGNALS:
Flags: {flags_text}
Scores: {scores_text}

TASK:
Score each of the 10 categories from 0-100 based on how relevant they are to this restaurant's situation.
Provide a confidence score (0-1) and a rationale that cites specific question IDs (e.g., "B1_drags includes Labor too high").

RULES:
- You may NOT invent categories
- No financial math, no dollar or percent symbols
- No numeric claims in rationale (only cite question IDs and signals)
- Return a JSON array with exactly 10 entries matching this schema:
  - category_id (must be from the list above)
  - score (0-100, integer)
  - confidence (0-1, number)
  - rationale (string, no numbers except question IDs)

CRITICAL: You MUST return a JSON array with exactly 10 objects. Each object represents one category score.
Example format:
[
  {{"category_id": "labor_scheduling", "score": 85, "confidence": 0.9, "rationale": "..."}},
  {{"category_id": "service_speed", "score": 70, "confidence": 0.8, "rationale": "..."}},
  ... (8 more entries, one for each of the 10 categories)
]

Output ONLY a valid JSON array starting with [ and ending with ]. Do not wrap in an object. No markdown, no code blocks."""


def build_core_initiative_expansion_prompt(
    questionnaire_responses: Dict[str, Any],
    derived_signals: Dict[str, Any],
    selected_category_ids: List[str],
    categories: List[Dict[str, str]],
    vertical_id: str = "restaurant_v0_1",
) -> str:
    """Build prompt for expanding top 4 categories into core initiatives."""
    selected_categories = [c for c in categories if c["id"] in selected_category_ids]
    categories_text = "\n".join([
        f"- {cat['id']}: {cat['label']} - {cat['description']}"
        for cat in selected_categories
    ])
    
    flags_text = ", ".join(derived_signals.get("flags", []))
    constraints = [f for f in derived_signals.get("flags", []) if f.startswith("constraint_")]
    constraints_text = ", ".join(constraints) if constraints else "None"
    
    return f"""You are expanding the top 4 selected categories into concrete, operator-friendly core initiatives.

SELECTED CATEGORIES (create 1 initiative per category):
{categories_text}

QUESTIONNAIRE RESPONSES (for multi-select, both "selected" and "not selected" are shown; not selected is often as important, e.g. marketing channels they don't use):
{format_responses_for_prompt(questionnaire_responses, vertical_id)}

DERIVED SIGNALS:
Flags: {flags_text}
Constraints: {constraints_text}

TASK:
Create exactly 4 core initiatives, one per selected category. Each initiative must include:
- category_id (from selected categories)
- title (clear, action-oriented)
- why_now (cite questionnaire context with question IDs)
- steps (3-7 concrete, operator-friendly steps)
- how_to_measure (2-5 qualitative/manual measurement methods)
- assumptions (0-4 assumptions)
- confidence_label (LOW, MEDIUM, or HIGH)

RULES:
- 1 initiative per category
- Steps must be concrete and restaurant-operator friendly
- Include measurement that can be tracked manually
- NO numbers, NO money, NO percentages
- If constraints include constraint_no_pricing_control, avoid pricing change initiatives or frame as validation only
- Return a JSON array with exactly 4 entries (one per selected category).

CRITICAL: You MUST return a JSON array with exactly 4 objects. Each object represents one core initiative.
Example format:
[
  {{"category_id": "labor_scheduling", "title": "...", "why_now": "...", "steps": [...], "how_to_measure": [...], "assumptions": [...], "confidence_label": "HIGH"}},
  {{"category_id": "discounting_discipline", "title": "...", "why_now": "...", "steps": [...], "how_to_measure": [...], "assumptions": [...], "confidence_label": "MEDIUM"}},
  {{"category_id": "manager_cadence", "title": "...", "why_now": "...", "steps": [...], "how_to_measure": [...], "assumptions": [...], "confidence_label": "HIGH"}},
  {{"category_id": "marketing_ownership", "title": "...", "why_now": "...", "steps": [...], "how_to_measure": [...], "assumptions": [...], "confidence_label": "MEDIUM"}}
]

Output ONLY a valid JSON array starting with [ and ending with ]. Do not wrap in an object. No markdown, no code blocks."""


def build_sandbox_prompt(
    questionnaire_responses: Dict[str, Any],
    derived_signals: Dict[str, Any],
    selected_category_ids: List[str],
    vertical_id: str = "restaurant_v0_1",
) -> str:
    """Build prompt for generating exactly 3 sandbox experiments."""
    flags_text = ", ".join(derived_signals.get("flags", []))
    
    return f"""You are generating exactly 3 sandbox/experimental initiatives that may not fit the core categories.

QUESTIONNAIRE RESPONSES (for multi-select, both "selected" and "not selected" are shown; not selected is often as important, e.g. marketing channels they don't use):
{format_responses_for_prompt(questionnaire_responses, vertical_id)}

DERIVED SIGNALS:
Flags: {flags_text}

SELECTED CORE CATEGORIES (avoid redundancy):
{', '.join(selected_category_ids)}

TASK:
Generate exactly 3 sandbox experiments that:
- May not fit the core categories
- Are clearly speculative
- Are reversible in 30 days
- Include stop conditions

Each sandbox must include:
- title
- why_this_came_up (cite questionnaire context)
- why_speculative (explain why this is experimental)
- test_plan (3-6 steps)
- stop_conditions (1-3 conditions)
- how_to_measure (2-5 measurement methods)
- confidence_label (must be LOW)

RULES:
- Exactly 3 sandbox initiatives
- Must be clearly speculative
- Must be reversible in 30 days
- Must include stop conditions
- NO numbers, money, or percent
- Return a JSON array with exactly 3 entries.

CRITICAL: You MUST return a JSON array with exactly 3 objects. Each object represents one sandbox experiment.
Example format:
[
  {{"title": "...", "why_this_came_up": "...", "why_speculative": "...", "test_plan": [...], "stop_conditions": [...], "how_to_measure": [...], "confidence_label": "LOW"}},
  {{"title": "...", "why_this_came_up": "...", "why_speculative": "...", "test_plan": [...], "stop_conditions": [...], "how_to_measure": [...], "confidence_label": "LOW"}},
  {{"title": "...", "why_this_came_up": "...", "why_speculative": "...", "test_plan": [...], "stop_conditions": [...], "how_to_measure": [...], "confidence_label": "LOW"}}
]

Output ONLY a valid JSON array starting with [ and ending with ]. Do not wrap in an object. No markdown, no code blocks."""
