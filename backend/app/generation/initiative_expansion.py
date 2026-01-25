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
    """Expand top 5 categories into core initiatives."""
    categories_data = load_categories("v0_1")
    categories = categories_data["categories"]
    
    prompt = build_core_initiative_expansion_prompt(
        questionnaire_responses,
        derived_signals,
        selected_category_ids,
        categories
    )
    
    client = LLMClient()
    response = client.generate(prompt, json_mode=True)
    
    # Clean response if it's wrapped in markdown code blocks
    if response.strip().startswith('```'):
        lines = response.strip().split('\n')
        response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response
    
    # Validate and parse
    initiatives = validate_and_parse_json(response, "core_initiatives")
    
    # Safety check: ensure we have exactly 5 core initiatives
    if len(initiatives) != 5:
        raise ValueError(f"Expected 5 core initiatives, got {len(initiatives)}")
    
    return initiatives


def generate_sandbox_initiatives(
    questionnaire_responses: Dict[str, Any],
    derived_signals: Dict[str, Any],
    selected_category_ids: List[str]
) -> List[Dict[str, Any]]:
    """Generate exactly 2 sandbox experiments."""
    prompt = build_sandbox_prompt(
        questionnaire_responses,
        derived_signals,
        selected_category_ids
    )
    
    client = LLMClient()
    response = client.generate(prompt, json_mode=True)
    
    # Clean response if it's wrapped in markdown code blocks
    if response.strip().startswith('```'):
        lines = response.strip().split('\n')
        response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response
    
    # Validate and parse
    sandbox = validate_and_parse_json(response, "sandbox_initiatives")
    
    # Safety check: ensure we have exactly 2 sandbox initiatives
    if len(sandbox) != 2:
        raise ValueError(f"Expected 2 sandbox initiatives, got {len(sandbox)}")
    
    return sandbox
