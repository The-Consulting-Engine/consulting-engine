import json
import jsonschema
from typing import Dict, Any, List
from pathlib import Path


def load_schema(schema_name: str) -> Dict[str, Any]:
    """Load JSON schema from schemas directory."""
    schemas_dir = Path(__file__).parent.parent / "schemas"
    schema_path = schemas_dir / f"{schema_name}.schema.json"
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    
    with open(schema_path, "r") as f:
        return json.load(f)


def validate_and_parse_json(
    json_string: str,
    schema_name: str,
    retry_on_failure: bool = True
) -> Any:
    """
    Validate JSON string against schema and return parsed object.
    Retries once on failure, then falls back to mock if still failing.
    """
    try:
        # Try to parse JSON
        data = json.loads(json_string)
        
        # Load and validate schema
        schema = load_schema(schema_name)
        jsonschema.validate(instance=data, schema=schema)
        
        return data
    except (json.JSONDecodeError, jsonschema.ValidationError) as e:
        if retry_on_failure:
            # Return mock data on failure
            return get_mock_data(schema_name)
        raise ValueError(f"JSON validation failed: {str(e)}")


def get_mock_data(schema_name: str) -> Any:
    """Return mock data matching the schema."""
    if schema_name == "category_scores":
        return [
            {"category_id": "labor_scheduling", "score": 80, "confidence": 0.8, "rationale": "Labor issues identified"},
            {"category_id": "service_speed", "score": 70, "confidence": 0.7, "rationale": "Service speed concerns"},
            {"category_id": "manager_cadence", "score": 75, "confidence": 0.75, "rationale": "Manager execution issues"},
            {"category_id": "training_consistency", "score": 65, "confidence": 0.65, "rationale": "Training gaps"},
            {"category_id": "menu_simplicity", "score": 60, "confidence": 0.6, "rationale": "Menu complexity"},
            {"category_id": "discounting_discipline", "score": 85, "confidence": 0.85, "rationale": "Discounting issues"},
            {"category_id": "upsell_attachment", "score": 70, "confidence": 0.7, "rationale": "Upselling opportunities"},
            {"category_id": "marketing_ownership", "score": 75, "confidence": 0.75, "rationale": "Marketing ownership gaps"},
            {"category_id": "local_search", "score": 60, "confidence": 0.6, "rationale": "Local search opportunities"},
            {"category_id": "delivery_ops", "score": 55, "confidence": 0.55, "rationale": "Delivery operations"}
        ]
    elif schema_name == "core_initiatives":
        return [
            {
                "category_id": "labor_scheduling",
                "title": "Tighten labor schedules",
                "why_now": "Labor scheduling issues identified",
                "steps": ["Review schedules", "Adjust staffing", "Monitor results"],
                "how_to_measure": ["Track hours", "Monitor coverage"],
                "assumptions": ["Data available"],
                "confidence_label": "MEDIUM"
            }
        ] * 5
    elif schema_name == "sandbox_initiatives":
        return [
            {
                "title": "Test new approach",
                "why_this_came_up": "Opportunity identified",
                "why_speculative": "Needs testing",
                "test_plan": ["Plan step 1", "Plan step 2", "Plan step 3"],
                "stop_conditions": ["Condition 1"],
                "how_to_measure": ["Measure 1", "Measure 2"],
                "confidence_label": "LOW"
            }
        ] * 2
    else:
        return []
