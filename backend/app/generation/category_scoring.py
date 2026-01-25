from typing import Dict, Any, List
from app.llm.client import LLMClient
from app.llm.prompts import build_category_scoring_prompt
from app.llm.json_guard import validate_and_parse_json
from app.questionnaire.loader import load_categories


def score_categories(
    questionnaire_responses: Dict[str, Any],
    derived_signals: Dict[str, Any],
    vertical_id: str = "restaurant_v0_1"
) -> List[Dict[str, Any]]:
    """Score the 10 categories using LLM."""
    categories_data = load_categories("v0_1")
    categories = categories_data["categories"]
    
    prompt = build_category_scoring_prompt(
        questionnaire_responses,
        derived_signals,
        categories,
        vertical_id=vertical_id,
    )
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info("📊 Step 1: Calling LLM for category scoring...")
    client = LLMClient()
    response = client.generate(prompt, json_mode=True)
    
    # Check if response looks like mock (placeholder) vs real LLM
    is_mock = "placeholder" in response.lower() or response.strip() == "{}"
    if is_mock:
        logger.warning("⚠️  Category scoring used MOCK data (not real LLM)")
    else:
        logger.info("✅ Category scoring used REAL LLM response (length: %d chars)", len(response) if response else 0)
    
    # Clean response if it's wrapped in markdown code blocks
    if response.strip().startswith('```'):
        lines = response.strip().split('\n')
        response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response
    
    # Validate and parse
    scores = validate_and_parse_json(response, "category_scores")
    
    # Safety check: ensure we have exactly 10 categories
    if len(scores) != 10:
        raise ValueError(f"Expected 10 category scores, got {len(scores)}")
    
    return scores


def select_top_4_categories(scores: List[Dict[str, Any]]) -> List[str]:
    """Select top 4 categories by score."""
    sorted_scores = sorted(scores, key=lambda x: x["score"], reverse=True)
    return [s["category_id"] for s in sorted_scores[:4]]
