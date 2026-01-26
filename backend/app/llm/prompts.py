from __future__ import annotations

import json
from typing import Dict, Any, List, Optional, Tuple


# -------------------------------------------------------------------
# Questionnaire loading + ordered rendering (boutique-consultant style)
# -------------------------------------------------------------------

def _load_questionnaire(vertical_id: str) -> Dict[str, Any]:
    from app.questionnaire.loader import load_questionnaire
    return load_questionnaire(vertical_id)


def _question_index(vertical_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Returns:
      - ordered_questions: list of question dicts in questionnaire order
      - by_id: q_id -> question dict
    """
    q = _load_questionnaire(vertical_id)
    ordered: List[Dict[str, Any]] = []
    by_id: Dict[str, Dict[str, Any]] = {}
    for sec in q.get("sections", []):
        for qn in sec.get("questions", []):
            if qn.get("id"):
                ordered.append(qn)
                by_id[qn["id"]] = qn
    return ordered, by_id


def _multi_select_schema(vertical_id: str) -> Dict[str, List[str]]:
    """Return q_id -> options for multi_select questions."""
    ordered, by_id = _question_index(vertical_id)
    out: Dict[str, List[str]] = {}
    for qn in ordered:
        if qn.get("type") == "multi_select" and qn.get("options"):
            out[qn["id"]] = list(qn["options"])
    return out


def _format_answer(qn: Dict[str, Any], value: Any, multi_opts: Dict[str, List[str]]) -> str:
    q_id = qn.get("id", "")
    q_type = qn.get("type", "")
    options = multi_opts.get(q_id)

    # Multi-select handling
    if q_type == "multi_select" and options is not None:
        selected = value if isinstance(value, list) else ([value] if value is not None else [])
        selected = [str(s).strip() for s in selected if s is not None and str(s).strip()]
        not_selected = [o for o in options if o not in selected]

        # Marketing channels: show both selected and not selected (as you requested)
        if q_id == "E1_channels_used":
            sel_str = ", ".join(selected) if selected else "(none)"
            not_str = ", ".join(not_selected) if not_selected else "(none)"
            return f"selected: {sel_str}; not selected: {not_str}"

        # All other multi-selects: only show selected
        sel_str = ", ".join(selected) if selected else "(none)"
        return sel_str

    # Ranking: expect list[str] in ranked order
    if q_type == "ranking":
        if isinstance(value, list) and value:
            ranked = [str(v).strip() for v in value if v is not None and str(v).strip()]
            return " > ".join(ranked) if ranked else "(none)"
        return "(none)"

    # Likert: keep raw numeric 1-5; it’s not “financial math”
    if q_type == "likert_1_5":
        return str(value) if value is not None else "(none)"

    # Text fields
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value) if value is not None else "(none)"


def format_responses_for_prompt(
    responses: Dict[str, Any],
    vertical_id: Optional[str] = None,
) -> str:
    """
    Boutique-consultant formatting:
    - Preserves questionnaire order (not dict iteration order)
    - Includes labels for readability
    - Multi-select rules:
        * E1_channels_used shows selected + not selected
        * all other multi_select shows only selected
    """
    if not vertical_id:
        # fallback: stable-ish formatting if vertical unknown
        lines = []
        for q_id in sorted(responses.keys()):
            val = responses[q_id]
            if isinstance(val, list):
                val_str = ", ".join(str(v) for v in val)
            else:
                val_str = str(val)
            lines.append(f"{q_id}: {val_str}")
        return "\n".join(lines)

    ordered_questions, by_id = _question_index(vertical_id)
    multi_opts = _multi_select_schema(vertical_id)

    lines: List[str] = []
    # Render in questionnaire order for narrative coherence
    for qn in ordered_questions:
        q_id = qn["id"]
        if q_id not in responses:
            continue
        label = qn.get("label", q_id).strip()
        ans = _format_answer(qn, responses.get(q_id), multi_opts)
        lines.append(f"{q_id} ({label}): {ans}")

    # Also include any unexpected response keys (defensive)
    extras = [k for k in responses.keys() if k not in by_id]
    for k in sorted(extras):
        v = responses.get(k)
        if isinstance(v, list):
            v_str = ", ".join(str(x) for x in v)
        else:
            v_str = str(v)
        lines.append(f"{k} (unknown question): {v_str}")

    return "\n".join(lines)


# ---------------------------------------------------------
# Deterministic "Consultant Brief" (no analytics required)
# ---------------------------------------------------------

def _pick_first_ranked(responses: Dict[str, Any], q_id: str) -> Optional[str]:
    v = responses.get(q_id)
    if isinstance(v, list) and v:
        s = str(v[0]).strip()
        return s or None
    if isinstance(v, str):
        return v.strip() or None
    return None


def build_consultant_brief(
    questionnaire_responses: Dict[str, Any],
    derived_signals: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Deterministic brief to help the LLM write like a boutique consultant:
    - No financial analytics
    - Just structures what the user already provided
    """
    flags = derived_signals.get("flags", []) or []
    scores = derived_signals.get("scores", {}) or {}

    constraints = [f for f in flags if f.startswith("constraint_")]
    pains = [f for f in flags if f.startswith("pain_")]
    other_signals = [f for f in flags if f.startswith("signal_") or f.startswith("profile_")]

    brief = {
        "business_profile": {
            "role": questionnaire_responses.get("A1_role"),
            "locations_scope": questionnaire_responses.get("A3_locations_scope"),
            "concept_type": questionnaire_responses.get("A0_1_concept_type") or questionnaire_responses.get("A0_concept_type"),
            "primary_order_channel": _pick_first_ranked(questionnaire_responses, "A0_2_order_channels_ranked"),
            "primary_dayparts": questionnaire_responses.get("A0_3_primary_dayparts"),
            "employee_count_per_location": questionnaire_responses.get("A0_4_employee_count_per_location"),
        },
        "constraints": constraints,
        "top_pains": pains,
        "signals": other_signals,
        "perception_scores": {k: float(v) for k, v in scores.items()},
        "operator_voice": {
            "fix_in_90_days": questionnaire_responses.get("G1_fix_one_thing_90"),
            "avoid_recommending": questionnaire_responses.get("G2_do_not_recommend"),
        },
    }
    return brief


# -----------------------------
# Boutique consultant styleguide
# -----------------------------

CONSULTANT_VOICE_GUIDE = """
CONSULTANT VOICE REQUIREMENTS (follow strictly):
- Write like an elite boutique ops consultant: crisp, practical, non-generic, no fluff.
- Use "you / your team" language. Assume the reader is a busy owner/operator.
- Avoid vague verbs like "optimize" or "improve." Use concrete actions: "set a rule", "assign an owner", "run a pre-shift huddle", "print a one-page checklist".
- Anchor each rationale to specifics (at least one of: daypart, order channel, staffing state, execution cadence, marketing ownership, or explicit constraints).
- Respect constraints. If pricing control is constrained, frame pricing as validation/communication, not changes.
- Prefer "first 48 hours" moves: what they can do immediately this week.
- Measurements must be manual-friendly: checklists, tallies, simple counts, manager confidence 1–5, guest complaint notes. NO financial math.
"""

MANUAL_MEASUREMENT_RULES = """
MEASUREMENT RULES:
- Use leading indicators (process adherence) and lagging indicators (ops/guest outcomes).
- Examples: "Was the schedule template used?", "Did the pre-shift huddle happen?", "refire/remake tally", "rush complaints noted", "comp approvals logged".
- Do NOT use currency, percentages, ROI, margins, or "week-over-week rate" language.
"""


# -------------------------------------------------------------------
# Prompt builders (category scoring, core initiatives, sandbox)
# -------------------------------------------------------------------

def build_category_scoring_prompt(
    questionnaire_responses: Dict[str, Any],
    derived_signals: Dict[str, Any],
    categories: List[Dict[str, str]],
    vertical_id: str = "restaurant_v0_1",
) -> str:
    """Build prompt for scoring the 10 categories."""
    categories_text = "\n".join([
        f"- {cat['id']}: {cat['label']} — {cat['description']}"
        for cat in categories
    ])

    flags_text = ", ".join(derived_signals.get("flags", []))
    scores_text = ", ".join([f"{k}: {v:.2f}" for k, v in derived_signals.get("scores", {}).items()])

    brief = build_consultant_brief(questionnaire_responses, derived_signals)

    return f"""You are scoring 10 fixed restaurant improvement categories based on intake.

CATEGORIES (you may ONLY score from this list):
{categories_text}

CONSULTANT BRIEF (structured from intake; treat as context, not analytics):
{json.dumps(brief, indent=2)}

QUESTIONNAIRE RESPONSES (ordered; includes question labels):
{format_responses_for_prompt(questionnaire_responses, vertical_id)}

DERIVED SIGNALS:
Flags: {flags_text}
Scores: {scores_text}

SCORING RUBRIC (use this rubric explicitly in your thinking):
- Relevance to stated pains (B1/B2 and pain_* flags)
- Feasibility given constraints (constraint_* flags)
- Speed to impact within ~30 days
- Ease of manual measurement

TASK:
Score each of the 10 categories from 0–100 based on how relevant they are to this restaurant's situation.
Provide a confidence score (0–1) and a rationale that cites specific question IDs and/or derived flags.

RULES:
- You may NOT invent categories
- No financial math, no currency symbols, no percent symbols
- No numeric claims in rationale (only cite question IDs and derived flags; question IDs are allowed)
- Return a JSON array with exactly 10 entries matching this schema:
  - category_id (must be from the list above)
  - score (0-100, integer)
  - confidence (0-1, number)
  - rationale (string, do not include numbers except question IDs like "B1_drags")

CRITICAL: Output ONLY a valid JSON array starting with [ and ending with ]. No markdown, no code blocks.
"""


def build_core_initiative_expansion_prompt(
    questionnaire_responses: Dict[str, Any],
    derived_signals: Dict[str, Any],
    selected_category_ids: List[str],
    categories: List[Dict[str, str]],
    vertical_id: str = "restaurant_v0_1",
) -> str:
    """Build prompt for expanding top categories into core initiatives."""
    selected_categories = [c for c in categories if c["id"] in selected_category_ids]
    categories_text = "\n".join([
        f"- {cat['id']}: {cat['label']} — {cat['description']}"
        for cat in selected_categories
    ])

    flags = derived_signals.get("flags", [])
    flags_text = ", ".join(flags)
    constraints = [f for f in flags if f.startswith("constraint_")]
    constraints_text = ", ".join(constraints) if constraints else "None"

    brief = build_consultant_brief(questionnaire_responses, derived_signals)

    return f"""You are an elite boutique restaurant ops consultant. Expand selected categories into operator-friendly initiatives.

SELECTED CATEGORIES (create exactly 1 initiative per category):
{categories_text}

{CONSULTANT_VOICE_GUIDE}
{MANUAL_MEASUREMENT_RULES}

CONSULTANT BRIEF:
{json.dumps(brief, indent=2)}

QUESTIONNAIRE RESPONSES (ordered; includes question labels):
{format_responses_for_prompt(questionnaire_responses, vertical_id)}

DERIVED SIGNALS:
Flags: {flags_text}
Constraints: {constraints_text}

TASK:
Create exactly {len(selected_categories)} core initiatives, one per selected category.

Each initiative MUST include:
- category_id (from selected categories)
- title (clear, action-oriented; sounds like an operator would say it)
- why_now (1–3 sentences; cite question IDs + one real-world anchor like daypart/channel/ownership/constraint)
- steps (3–7 concrete steps; include a "first 48 hours" move; no generic verbs)
- how_to_measure (2–5 manual measures; include leading + lagging indicators; no financial metrics)
- assumptions (0–4)
- confidence_label (LOW, MEDIUM, or HIGH)

RULES:
- 1 initiative per category
- NO currency, NO percentages, NO ROI, NO "week-over-week rate"
- If constraint_no_pricing_control exists, avoid pricing-change initiatives; frame as validation/communication only
- Return a JSON array with exactly {len(selected_categories)} objects.

CRITICAL: Output ONLY a valid JSON array starting with [ and ending with ]. No markdown, no code blocks.
"""


def build_sandbox_prompt(
    questionnaire_responses: Dict[str, Any],
    derived_signals: Dict[str, Any],
    selected_category_ids: List[str],
    vertical_id: str = "restaurant_v0_1",
) -> str:
    """Build prompt for generating exactly 3 sandbox experiments."""
    flags_text = ", ".join(derived_signals.get("flags", []))
    brief = build_consultant_brief(questionnaire_responses, derived_signals)

    return f"""You are an elite boutique restaurant ops consultant. Generate sandbox experiments.

{CONSULTANT_VOICE_GUIDE}
{MANUAL_MEASUREMENT_RULES}

DEFINITION:
Sandbox initiatives are speculative, reversible tests that explore a hypothesis NOT already covered by core initiatives.
They must be low-lift and realistically runnable within ~30 days.

CONSULTANT BRIEF:
{json.dumps(brief, indent=2)}

QUESTIONNAIRE RESPONSES (ordered; includes question labels):
{format_responses_for_prompt(questionnaire_responses, vertical_id)}

DERIVED SIGNALS:
Flags: {flags_text}

SELECTED CORE CATEGORIES (avoid redundancy):
{', '.join(selected_category_ids)}

TASK:
Generate exactly 3 sandbox experiments. Each must:
- be clearly speculative
- be reversible within ~30 days
- include stop conditions
- be anchored to intake (cite question IDs and/or the operator's open-ended responses)

Each sandbox MUST include:
- title
- why_this_came_up (cite question IDs; optionally reference G1_fix_one_thing_90 phrasing)
- why_speculative (explain what’s unknown)
- test_plan (3–6 concrete steps; include a "first 48 hours" move)
- stop_conditions (1–3)
- how_to_measure (2–5 manual measures; leading + lagging)
- confidence_label (must be LOW)

RULES:
- Exactly 3 sandbox initiatives
- Avoid redundancy with selected core categories (do not repackage the same initiative)
- NO currency, NO percentages, NO ROI, NO numeric claims (question IDs are allowed)
- Return a JSON array with exactly 3 objects.

CRITICAL: Output ONLY a valid JSON array starting with [ and ending with ]. No markdown, no code blocks.
"""