from typing import Dict, List, Any
from app.questionnaire.loader import load_signal_map


def evaluate_responses(responses: Dict[str, Any], vertical_id: str = "restaurant_v0_1") -> Dict[str, Any]:
    """
    Evaluate questionnaire responses against signal map rules.
    Returns derived_signals with flags, scores, and notes.
    """
    signal_map = load_signal_map(vertical_id)
    flags: List[str] = []
    scores: Dict[str, float] = {}
    notes: List[str] = []
    
    for rule in signal_map.get("rules", []):
        when_conditions = rule.get("when", [])
        then_action = rule.get("then", {})
        
        if evaluate_conditions(when_conditions, responses):
            # Apply then action
            if "add_flags" in then_action:
                flags.extend(then_action["add_flags"])
            
            if "set_score" in then_action:
                score_config = then_action["set_score"]
                key = score_config.get("key")
                if not key or not when_conditions:
                    continue
                if score_config.get("map_likert_1_5_to_0_1"):
                    q_id = when_conditions[0].get("q")
                    if not q_id:
                        continue
                    value = get_response_value(responses, q_id)
                    if isinstance(value, (int, float)) and 1 <= value <= 5:
                        scores[key] = (value - 1) / 4.0  # Maps 1->0, 5->1
    
    return {
        "flags": list(set(flags)),  # Deduplicate
        "scores": scores,
        "notes": ["Derived from questionnaire only."] if not notes else notes
    }


def evaluate_conditions(conditions: List[Dict], responses: Dict[str, Any]) -> bool:
    """Evaluate a list of AND conditions."""
    for condition in conditions:
        if not evaluate_condition(condition, responses):
            return False
    return True


def evaluate_condition(condition: Dict, responses: Dict[str, Any]) -> bool:
    """Evaluate a single condition."""
    if not responses:
        return False
        
    question_id = condition.get("q")
    if not question_id:
        return False
        
    op = condition.get("op")
    if not op:
        return False
        
    value = condition.get("value")
    
    response_value = get_response_value(responses, question_id)
    
    if op == "exists":
        return response_value is not None
    
    if op == "equals":
        return response_value == value
    
    if op == "contains":
        if isinstance(response_value, list):
            return value in response_value
        if isinstance(response_value, str):
            return value in response_value
        return False
    
    if op == "in":
        if isinstance(value, list):
            return response_value in value
        return False
    
    if op == "lte":
        try:
            return float(response_value) <= float(value)
        except (ValueError, TypeError):
            return False
    
    if op == "gte":
        try:
            return float(response_value) >= float(value)
        except (ValueError, TypeError):
            return False
    
    if op == "regex":
        import re
        pattern = value
        text = str(response_value) if response_value is not None else ""
        return bool(re.search(pattern, text))
    
    if op == "array_first":
        # Check if response is an array and first element equals value
        if isinstance(response_value, list) and len(response_value) > 0:
            return response_value[0] == value
        return False
    
    return False


def get_response_value(responses: Dict[str, Any], question_id: str) -> Any:
    """Get response value for a question ID."""
    if not responses:
        return None
    return responses.get(question_id)
