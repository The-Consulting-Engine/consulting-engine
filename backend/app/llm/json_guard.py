import json
import jsonschema
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


def load_schema(schema_name: str) -> Dict[str, Any]:
    """Load JSON schema from schemas directory."""
    schemas_dir = Path(__file__).parent.parent / "schemas"
    schema_path = schemas_dir / f"{schema_name}.schema.json"
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    
    with open(schema_path, "r") as f:
        return json.load(f)


def _unwrap_single_key_array(data: Any) -> Any:
    """
    GPT-4 with json_object often wraps arrays in an object (e.g. {"initiatives": [...]}).
    If we get a single-key dict whose value is a list, unwrap and return that list.
    """
    if isinstance(data, dict) and len(data) == 1:
        (val,) = data.values()
        if isinstance(val, list):
            return val
    return data


def validate_and_parse_json(
    json_string: str,
    schema_name: str,
    retry_on_failure: bool = True
) -> Any:
    """
    Validate JSON string against schema and return parsed object.
    Retries once on failure, then falls back to mock if still failing.
    Unwraps single-key objects (e.g. {"initiatives": [...]}) so GPT-4 json_object output matches array schemas.
    """
    try:
        data = json.loads(json_string)
        data = _unwrap_single_key_array(data)

        schema = load_schema(schema_name)
        
        # Check if schema expects array but we got a single object
        if schema.get("type") == "array" and isinstance(data, dict) and not isinstance(data, list):
            expected_count = schema.get("minItems", schema.get("maxItems", "multiple"))
            logger.error(
                "❌ GPT returned a SINGLE OBJECT instead of an ARRAY for %s. Expected array with %s items, got 1 object.",
                schema_name,
                expected_count,
            )
            logger.error("   This usually means GPT-4-turbo with json_object mode only generated one item.")
            logger.error("   The prompt should explicitly request an array with multiple items.")
            raise ValueError(
                f"Expected array with {expected_count} items for {schema_name}, but got single object. "
                f"GPT likely only generated one item instead of the required {expected_count}."
            )
        
        jsonschema.validate(instance=data, schema=schema)

        return data
    except (json.JSONDecodeError, jsonschema.ValidationError, ValueError) as e:
        preview = (json_string or "")[:500]
        if len(json_string or "") > 500:
            preview += "... [truncated]"
        logger.warning(
            "⚠️  JSON validation failed for %s: %s. Using placeholder data.",
            schema_name,
            str(e),
        )
        logger.warning("   Raw response preview: %s", preview)
        if retry_on_failure:
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
        # Placeholder initiatives - clearly marked so user knows LLM failed
        placeholder = {
            "category_id": "placeholder",
            "title": "PLACEHOLDER: Core Initiative (LLM generation failed)",
            "why_now": "This is a placeholder. The LLM failed to generate real initiatives. Check backend logs for errors.",
            "steps": [
                "PLACEHOLDER: Real steps will appear when LLM generation succeeds"
            ],
            "how_to_measure": [
                "PLACEHOLDER: Real measurement methods will appear when LLM generation succeeds"
            ],
            "assumptions": [
                "PLACEHOLDER: Real assumptions will appear when LLM generation succeeds"
            ],
            "confidence_label": "LOW"
        }
        return [placeholder] * 4
    elif schema_name == "sandbox_initiatives":
        # Placeholder initiatives - clearly marked so user knows LLM failed
        placeholder = {
            "title": "PLACEHOLDER: Sandbox Experiment (LLM generation failed)",
            "why_this_came_up": "This is a placeholder. The LLM failed to generate real sandbox experiments. Check backend logs for errors.",
            "why_speculative": "PLACEHOLDER: Real speculative reasoning will appear when LLM generation succeeds.",
            "test_plan": [
                "PLACEHOLDER: Real test plan will appear when LLM generation succeeds"
            ],
            "stop_conditions": [
                "PLACEHOLDER: Real stop conditions will appear when LLM generation succeeds"
            ],
            "how_to_measure": [
                "PLACEHOLDER: Real measurement methods will appear when LLM generation succeeds"
            ],
            "confidence_label": "LOW"
        }
        return [placeholder] * 3
    else:
        return []
