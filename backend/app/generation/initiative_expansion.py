from typing import Dict, Any, List
from app.llm.client import LLMClient
from app.llm.prompts import build_core_initiative_expansion_prompt, build_sandbox_prompt
from app.llm.json_guard import validate_and_parse_json
from app.questionnaire.loader import load_categories


def expand_core_initiatives(
    questionnaire_responses: Dict[str, Any],
    derived_signals: Dict[str, Any],
    selected_category_ids: List[str],
    vertical_id: str = "restaurant_v0_1"
) -> List[Dict[str, Any]]:
    """Expand top 4 categories into core initiatives."""
    categories_data = load_categories("v0_1")
    categories = categories_data["categories"]
    
    import logging
    logger = logging.getLogger(__name__)
    
    prompt = build_core_initiative_expansion_prompt(
        questionnaire_responses,
        derived_signals,
        selected_category_ids,
        categories,
        vertical_id=vertical_id,
    )
    
    logger.info("📝 Step 3: Calling LLM for core initiative expansion...")
    client = LLMClient()
    response = client.generate(prompt, json_mode=True)
    
    # Check if response looks like mock (placeholder) vs real LLM
    is_mock = "placeholder" in response.lower() or response.strip() == "{}"
    if is_mock:
        logger.warning("⚠️  Core initiatives used MOCK data (not real LLM)")
    else:
        logger.info("✅ Core initiatives used REAL LLM response (length: %d chars)", len(response) if response else 0)
    
    # Clean response if it's wrapped in markdown code blocks
    if response.strip().startswith('```'):
        lines = response.strip().split('\n')
        response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response
    
    # Validate and parse
    initiatives = validate_and_parse_json(response, "core_initiatives")
    
    # Safety check: ensure we have exactly 4 core initiatives
    if len(initiatives) != 4:
        raise ValueError(f"Expected 4 core initiatives, got {len(initiatives)}")
    
    return initiatives


def generate_sandbox_initiatives(
    questionnaire_responses: Dict[str, Any],
    derived_signals: Dict[str, Any],
    selected_category_ids: List[str],
    vertical_id: str = "restaurant_v0_1",
) -> List[Dict[str, Any]]:
    """Generate exactly 3 sandbox experiments."""
    import logging
    logger = logging.getLogger(__name__)
    
    prompt = build_sandbox_prompt(
        questionnaire_responses,
        derived_signals,
        selected_category_ids,
        vertical_id=vertical_id,
    )
    
    logger.info("🧪 Step 4: Calling LLM for sandbox initiative generation...")
    client = LLMClient()
    response = client.generate(prompt, json_mode=True)
    
    # Check if response looks like mock (placeholder) vs real LLM
    is_mock = "placeholder" in response.lower() or response.strip() == "{}"
    if is_mock:
        logger.warning("⚠️  Sandbox initiatives used MOCK data (not real LLM)")
    else:
        logger.info("✅ Sandbox initiatives used REAL LLM response (length: %d chars)", len(response) if response else 0)
    
    # Clean response if it's wrapped in markdown code blocks
    if response.strip().startswith('```'):
        lines = response.strip().split('\n')
        response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response
    
    # Validate and parse
    sandbox = validate_and_parse_json(response, "sandbox_initiatives")
    
    # Safety check: ensure we have exactly 3 sandbox initiatives
    if len(sandbox) != 3:
        raise ValueError(f"Expected 3 sandbox initiatives, got {len(sandbox)}")
    
    return sandbox
