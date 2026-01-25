from typing import Dict, Any, List


def build_category_scoring_prompt(
    questionnaire_responses: Dict[str, Any],
    derived_signals: Dict[str, Any],
    categories: List[Dict[str, str]]
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

QUESTIONNAIRE RESPONSES:
{format_responses_for_prompt(questionnaire_responses)}

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
- Return JSON array with exactly 10 entries matching this schema:
  - category_id (must be from the list above)
  - score (0-100)
  - confidence (0-1)
  - rationale (string, no numbers except question IDs)

Return only valid JSON array."""


def build_core_initiative_expansion_prompt(
    questionnaire_responses: Dict[str, Any],
    derived_signals: Dict[str, Any],
    selected_category_ids: List[str],
    categories: List[Dict[str, str]]
) -> str:
    """Build prompt for expanding top 5 categories into core initiatives."""
    selected_categories = [c for c in categories if c["id"] in selected_category_ids]
    categories_text = "\n".join([
        f"- {cat['id']}: {cat['label']} - {cat['description']}"
        for cat in selected_categories
    ])
    
    flags_text = ", ".join(derived_signals.get("flags", []))
    constraints = [f for f in derived_signals.get("flags", []) if f.startswith("constraint_")]
    constraints_text = ", ".join(constraints) if constraints else "None"
    
    return f"""You are expanding the top 5 selected categories into concrete, operator-friendly core initiatives.

SELECTED CATEGORIES (create 1 initiative per category):
{categories_text}

QUESTIONNAIRE RESPONSES:
{format_responses_for_prompt(questionnaire_responses)}

DERIVED SIGNALS:
Flags: {flags_text}
Constraints: {constraints_text}

TASK:
Create exactly 5 core initiatives, one per selected category. Each initiative must include:
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
- Return JSON array with exactly 5 entries

Return only valid JSON array."""


def build_sandbox_prompt(
    questionnaire_responses: Dict[str, Any],
    derived_signals: Dict[str, Any],
    selected_category_ids: List[str]
) -> str:
    """Build prompt for generating exactly 2 sandbox experiments."""
    flags_text = ", ".join(derived_signals.get("flags", []))
    
    return f"""You are generating exactly 2 sandbox/experimental initiatives that may not fit the core categories.

QUESTIONNAIRE RESPONSES:
{format_responses_for_prompt(questionnaire_responses)}

DERIVED SIGNALS:
Flags: {flags_text}

SELECTED CORE CATEGORIES (avoid redundancy):
{', '.join(selected_category_ids)}

TASK:
Generate exactly 2 sandbox experiments that:
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
- Exactly 2 sandbox initiatives
- Must be clearly speculative
- Must be reversible in 30 days
- Must include stop conditions
- NO numbers, money, or percent
- Return JSON array with exactly 2 entries

Return only valid JSON array."""


def format_responses_for_prompt(responses: Dict[str, Any]) -> str:
    """Format questionnaire responses for LLM prompt."""
    lines = []
    for q_id, value in responses.items():
        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value)
        else:
            value_str = str(value)
        lines.append(f"{q_id}: {value_str}")
    return "\n".join(lines)
