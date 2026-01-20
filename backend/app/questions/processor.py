"""Question processing and context derivation."""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict


class QuestionProcessor:
    """Process intake questions and derive run context."""
    
    def __init__(self, vertical_id: str = "restaurant_v1"):
        self.vertical_id = vertical_id
        self.questions = self._load_questions()
    
    def _load_questions(self) -> Dict[str, Any]:
        """Load question pack for vertical."""
        questions_file = Path(__file__).parent / f"{self.vertical_id}_questions.json"
        
        if not questions_file.exists():
            # Fallback to empty question pack
            return {"questions": [], "default_responses": {}}
        
        with open(questions_file, 'r') as f:
            return json.load(f)
    
    def get_questions(self) -> List[Dict[str, Any]]:
        """Get all questions for the vertical."""
        return self.questions.get("questions", [])
    
    def get_default_responses(self) -> Dict[str, Any]:
        """Get default responses for auto-fill."""
        return self.questions.get("default_responses", {})
    
    def derive_context(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Derive run context from user responses.
        
        Args:
            responses: List of {question_id, response_value}
        
        Returns:
            {
                constraints: {...},
                operations: {...},
                marketing: {...},
                goals: {...},
                risk: {...},
                derived: {
                    initiative_blacklist: [...],
                    initiative_priority_boost: [...],
                    tags: [...],
                    assumption_overrides: {...},
                    sandbox_enabled: bool
                }
            }
        """
        # Build response lookup
        response_map = {r['question_id']: r['response_value'] for r in responses}
        
        # Initialize context structure
        context = {
            "constraints": {},
            "operations": {},
            "marketing": {},
            "goals": {},
            "risk": {},
            "derived": {
                "initiative_blacklist": [],
                "initiative_priority_boost": [],
                "tags": [],
                "assumption_overrides": {},
                "sandbox_enabled": False
            }
        }
        
        # Process each question
        questions = self.get_questions()
        
        for question in questions:
            question_id = question["question_id"]
            section = question["section"].lower()
            response_value = response_map.get(question_id)
            
            if response_value is None:
                continue
            
            # Store response in appropriate section
            if section in context:
                context[section][question_id] = response_value
            
            # Process effects
            self._process_effects(question, response_value, context["derived"])
        
        # Deduplicate lists in derived
        context["derived"]["initiative_blacklist"] = list(set(context["derived"]["initiative_blacklist"]))
        context["derived"]["initiative_priority_boost"] = list(set(context["derived"]["initiative_priority_boost"]))
        context["derived"]["tags"] = list(set(context["derived"]["tags"]))
        
        return context
    
    def _process_effects(
        self,
        question: Dict[str, Any],
        response_value: Any,
        derived: Dict[str, Any]
    ):
        """Process effects from a question response."""
        question_type = question["type"]
        options = question.get("options", [])
        
        if question_type in ["single_select", "yes_no"]:
            # Find matching option
            for option in options:
                if option["value"] == response_value:
                    self._apply_effects(option.get("effects", {}), derived)
                    break
        
        elif question_type == "multi_select":
            # Response is a list, apply effects from each selected option
            if not isinstance(response_value, list):
                response_value = [response_value]
            
            for option in options:
                if option["value"] in response_value:
                    self._apply_effects(option.get("effects", {}), derived)
            
            # Check question-level effects
            question_effects = question.get("effects", {})
            if question_effects:
                self._apply_conditional_effects(question_effects, response_value, derived)
    
    def _apply_effects(self, effects: Dict[str, Any], derived: Dict[str, Any]):
        """Apply effects from an option."""
        if "initiative_blacklist" in effects:
            derived["initiative_blacklist"].extend(effects["initiative_blacklist"])
        
        if "initiative_priority_boost" in effects:
            derived["initiative_priority_boost"].extend(effects["initiative_priority_boost"])
        
        if "tags" in effects:
            derived["tags"].extend(effects["tags"])
        
        if "assumption_overrides" in effects:
            derived["assumption_overrides"].update(effects["assumption_overrides"])
        
        if "sandbox_enabled" in effects:
            if effects["sandbox_enabled"] is True:
                derived["sandbox_enabled"] = True
    
    def _apply_conditional_effects(
        self,
        effects: Dict[str, Any],
        response_values: List[str],
        derived: Dict[str, Any]
    ):
        """Apply conditional effects based on response values."""
        if "sandbox_enabled" in effects:
            condition = effects["sandbox_enabled"]
            
            # Parse condition like "contains_any:google_maps,social_media,email_sms"
            if isinstance(condition, str) and condition.startswith("contains_any:"):
                required_values = condition.split(":")[1].split(",")
                if any(val in response_values for val in required_values):
                    derived["sandbox_enabled"] = True
    
    def validate_responses(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate that all required questions are answered.
        
        Returns:
            {
                valid: bool,
                missing_required: [question_ids],
                errors: [error messages]
            }
        """
        response_ids = {r['question_id'] for r in responses}
        required_questions = [
            q for q in self.get_questions()
            if q.get("required", False)
        ]
        
        missing = [q["question_id"] for q in required_questions if q["question_id"] not in response_ids]
        
        return {
            "valid": len(missing) == 0,
            "missing_required": missing,
            "errors": [f"Missing required question: {qid}" for qid in missing]
        }
