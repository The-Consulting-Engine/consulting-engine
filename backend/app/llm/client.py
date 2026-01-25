import logging
import os
import json
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", settings.llm_provider)
        self.api_key = os.getenv("LLM_API_KEY", settings.llm_api_key)
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> str:
        """Generate text using the configured LLM provider."""
        if self.provider == "mock":
            return self._mock_generate(prompt, json_mode)
        elif self.provider == "openai":
            return self._openai_generate(prompt, system_prompt, json_mode)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")
    
    def _mock_generate(self, prompt: str, json_mode: bool) -> str:
        """Return deterministic mock responses for local dev."""
        # Simple heuristic: if prompt mentions categories, return category scores
        if "category" in prompt.lower() and "score" in prompt.lower():
            return json.dumps([
                {"category_id": "labor_scheduling", "score": 85, "confidence": 0.9, "rationale": "B1_drags includes Labor too high and Staffing chaotic"},
                {"category_id": "service_speed", "score": 75, "confidence": 0.8, "rationale": "C3_ops_stressors includes Service is slow during rush"},
                {"category_id": "manager_cadence", "score": 80, "confidence": 0.85, "rationale": "B1_drags includes Managers not executing consistently"},
                {"category_id": "training_consistency", "score": 70, "confidence": 0.75, "rationale": "C3_ops_stressors includes Training is inconsistent"},
                {"category_id": "menu_simplicity", "score": 60, "confidence": 0.7, "rationale": "D1_menu_size indicates menu complexity"},
                {"category_id": "discounting_discipline", "score": 90, "confidence": 0.95, "rationale": "B1_drags includes Too much discounting/comps"},
                {"category_id": "upsell_attachment", "score": 65, "confidence": 0.7, "rationale": "D3_upselling indicates weak upselling"},
                {"category_id": "marketing_ownership", "score": 75, "confidence": 0.8, "rationale": "E3_marketing_owner indicates missing ownership"},
                {"category_id": "local_search", "score": 60, "confidence": 0.65, "rationale": "E1_channels_used includes Google Business Profile"},
                {"category_id": "delivery_ops", "score": 55, "confidence": 0.6, "rationale": "General delivery operations opportunity"}
            ])
        
        # If prompt mentions core initiatives
        if "core initiative" in prompt.lower() or "top 5" in prompt.lower():
            return json.dumps([
                {
                    "category_id": "labor_scheduling",
                    "title": "Tighten labor schedules to match demand",
                    "why_now": "B1_drags includes Labor too high and Staffing chaotic. C2_schedule_confidence is low.",
                    "steps": [
                        "Review last four weeks of sales by day and hour",
                        "Build a baseline schedule template",
                        "Set rules for when to add or cut shifts",
                        "Train managers on schedule adjustments"
                    ],
                    "how_to_measure": [
                        "Track scheduled hours vs actual sales",
                        "Monitor callouts and coverage gaps",
                        "Review labor cost weekly"
                    ],
                    "assumptions": [
                        "Managers can access sales data",
                        "Staffing levels can be adjusted week-to-week"
                    ],
                    "confidence_label": "HIGH"
                },
                {
                    "category_id": "discounting_discipline",
                    "title": "Bring structure to comps and voids",
                    "why_now": "B1_drags includes Too much discounting/comps. B2_suspected_leak points to Discounting / promos.",
                    "steps": [
                        "Document current comp and void process",
                        "Set clear rules for when comps are allowed",
                        "Require manager approval for all comps",
                        "Track comps by reason and manager"
                    ],
                    "how_to_measure": [
                        "Weekly comp and void report",
                        "Compare comp rate week-over-week",
                        "Review comp reasons with team"
                    ],
                    "assumptions": [
                        "POS system can track comps and voids",
                        "Managers will follow new process"
                    ],
                    "confidence_label": "MEDIUM"
                },
                {
                    "category_id": "manager_cadence",
                    "title": "Establish weekly execution rhythm",
                    "why_now": "B1_drags includes Managers not executing consistently. F1_review_frequency is Ad hoc or Rarely.",
                    "steps": [
                        "Set a fixed weekly review meeting time",
                        "Create a simple weekly scorecard",
                        "Review top three priorities each week",
                        "Follow up on previous week commitments"
                    ],
                    "how_to_measure": [
                        "Track meeting attendance and consistency",
                        "Review action items completion rate",
                        "Monitor team feedback on process"
                    ],
                    "assumptions": [
                        "Managers can commit to weekly meetings",
                        "Scorecard data is available"
                    ],
                    "confidence_label": "HIGH"
                },
                {
                    "category_id": "service_speed",
                    "title": "Reduce bottlenecks during peak periods",
                    "why_now": "C3_ops_stressors includes Service is slow during rush and Kitchen bottlenecks.",
                    "steps": [
                        "Identify peak hours and days",
                        "Map current service flow",
                        "Test prep work before peak",
                        "Adjust station assignments during rush"
                    ],
                    "how_to_measure": [
                        "Track average ticket time during peak",
                        "Monitor customer wait times",
                        "Review kitchen ticket times"
                    ],
                    "assumptions": [
                        "Staff can be cross-trained",
                        "Peak patterns are predictable"
                    ],
                    "confidence_label": "MEDIUM"
                },
                {
                    "category_id": "marketing_ownership",
                    "title": "Clarify marketing ownership and weekly plan",
                    "why_now": "E3_marketing_owner is No one/ad hoc. E4_marketing_roi_confidence is low.",
                    "steps": [
                        "Assign one person to own marketing",
                        "Create a simple weekly marketing checklist",
                        "Set up basic tracking for each channel",
                        "Review marketing results weekly"
                    ],
                    "how_to_measure": [
                        "Track marketing task completion",
                        "Monitor channel engagement",
                        "Review customer feedback on marketing"
                    ],
                    "assumptions": [
                        "Someone can take ownership",
                        "Basic marketing tools are available"
                    ],
                    "confidence_label": "MEDIUM"
                }
            ])
        
        # If prompt mentions sandbox
        if "sandbox" in prompt.lower() or "experimental" in prompt.lower():
            return json.dumps([
                {
                    "title": "Test simplified menu during off-peak hours",
                    "why_this_came_up": "D1_menu_size indicates menu complexity. This could reduce kitchen errors and speed.",
                    "why_speculative": "Menu changes can impact customer satisfaction. Need to test carefully.",
                    "test_plan": [
                        "Select three slowest days of the week",
                        "Create a simplified menu for those days",
                        "Train staff on new menu",
                        "Run test for four weeks",
                        "Collect customer feedback",
                        "Compare ticket times and errors"
                    ],
                    "stop_conditions": [
                        "Customer complaints increase significantly",
                        "Sales drop more than expected",
                        "Staff cannot execute consistently"
                    ],
                    "how_to_measure": [
                        "Track ticket times",
                        "Monitor order errors",
                        "Collect customer feedback",
                        "Compare sales to baseline"
                    ],
                    "confidence_label": "LOW"
                },
                {
                    "title": "Experiment with local partnership program",
                    "why_this_came_up": "E2_channels_drive includes Local partnerships/events. This could drive new customers.",
                    "why_speculative": "Partnerships require time and may not yield immediate results.",
                    "test_plan": [
                        "Identify three potential local partners",
                        "Reach out with partnership proposal",
                        "Set up one partnership test",
                        "Track customer referrals",
                        "Measure partnership ROI",
                        "Decide whether to expand"
                    ],
                    "stop_conditions": [
                        "No partners respond positively",
                        "Partnership does not drive customers",
                        "Time investment exceeds value"
                    ],
                    "how_to_measure": [
                        "Track referral customers",
                        "Monitor partnership engagement",
                        "Review customer feedback",
                        "Compare sales from partnership"
                    ],
                    "confidence_label": "LOW"
                }
            ])
        
        # Default fallback when no heuristic matches
        return "{}"
    
    def _openai_generate(self, prompt: str, system_prompt: Optional[str], json_mode: bool) -> str:
        """Generate using OpenAI API."""
        import httpx
        from openai import OpenAI

        # Use custom httpx client (no proxies) to avoid OpenAI client passing
        # 'proxies' to incompatible underlying client (e.g. httpx 0.28+).
        http_client = httpx.Client()
        try:
            client = OpenAI(api_key=self.api_key, http_client=http_client)

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            kwargs = {
                "model": "gpt-4-turbo-preview",
                "messages": messages,
                "temperature": 0.7,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if content is None:
                raise RuntimeError("OpenAI returned empty response")
            return content
        except Exception as e:
            err = str(e).lower()
            if "connection" in err or "connect" in err or "timeout" in err or "connection refused" in err:
                # Fall back to mock so demo works when OpenAI is unreachable (Docker, firewall, etc.)
                logger.warning(
                    "OpenAI unreachable (%s). Falling back to mock. Set LLM_PROVIDER=mock to avoid this.",
                    e,
                )
                return self._mock_generate(prompt, json_mode)
            raise RuntimeError(f"OpenAI API error: {str(e)}") from e
        finally:
            http_client.close()
