"""
LLM Client for OpenAI integration.
Simple, reliable implementation that works.
"""
import logging
import os
import json
import time
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for LLM generation. Supports OpenAI and mock modes."""
    
    def __init__(self):
        # Get provider from env (default: mock for safety)
        self.provider = os.getenv("LLM_PROVIDER", "mock").lower().strip()
        
        # Get API key - support both LLM_API_KEY and OPENAI_API_KEY
        self.api_key = (
            os.getenv("LLM_API_KEY") or 
            os.getenv("OPENAI_API_KEY") or 
            settings.llm_api_key or 
            ""
        ).strip()
        
        # Log initialization
        logger.info("=" * 60)
        logger.info("LLMClient initialized")
        logger.info("  Provider: %s", self.provider)
        logger.info("  API key present: %s", bool(self.api_key))
        if self.api_key:
            logger.info("  API key prefix: %s...", self.api_key[:10])
        logger.info("=" * 60)
        
        # Warn if OpenAI is configured but no key
        if self.provider == "openai" and not self.api_key:
            logger.warning(
                "⚠️  WARNING: LLM_PROVIDER=openai but no API key found. "
                "Set OPENAI_API_KEY or LLM_API_KEY in .env file. "
                "Will fall back to mock mode."
            )
    
    def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None, 
        json_mode: bool = False
    ) -> str:
        """
        Generate text using the configured LLM provider.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            json_mode: If True, request JSON response format
            
        Returns:
            Generated text (or mock data if provider is mock or OpenAI fails)
        """
        logger.info("LLM.generate called: provider=%s, json_mode=%s", self.provider, json_mode)
        
        if self.provider == "mock":
            logger.info("Using MOCK mode (provider=mock)")
            return self._mock_generate(prompt, json_mode)
        
        elif self.provider == "openai":
            logger.info("Using OPENAI mode - attempting API call")
            return self._openai_generate(prompt, system_prompt, json_mode)
        
        else:
            logger.error("Unknown provider: %s. Falling back to mock.", self.provider)
            return self._mock_generate(prompt, json_mode)
    
    def _openai_generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str], 
        json_mode: bool
    ) -> str:
        """Generate using OpenAI API. Falls back to mock on any error."""
        from openai import OpenAI
        
        # Check API key
        if not self.api_key:
            logger.warning("No API key available. Falling back to mock.")
            return self._mock_generate(prompt, json_mode)
        
        # Get model from env (default to gpt-4o which is reliable)
        model = os.getenv("LLM_MODEL", "gpt-4o").strip()
        
        logger.info("🚀 Calling OpenAI API")
        logger.info("  Model: %s", model)
        logger.info("  Prompt length: %d chars", len(prompt))
        logger.info("  System prompt: %s", "yes" if system_prompt else "no")
        logger.info("  JSON mode: %s", json_mode)
        
        start_time = time.time()
        
        try:
            # Create OpenAI client - simple, let it handle HTTP
            client = OpenAI(
                api_key=self.api_key,
                timeout=90.0,  # 90 second timeout (generous for complex prompts)
                max_retries=2,  # Retry up to 2 times for transient errors
            )
            
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Build request kwargs
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            # Make API call
            logger.info("📡 Sending request to OpenAI...")
            response = client.chat.completions.create(**kwargs)
            
            elapsed = time.time() - start_time
            content = response.choices[0].message.content
            
            if not content:
                raise ValueError("OpenAI returned empty response")
            
            logger.info("✅ OpenAI API SUCCESS")
            logger.info("  Response time: %.2f seconds", elapsed)
            logger.info("  Response length: %d characters", len(content))
            logger.info("  First 100 chars: %s", content[:100])
            
            return content
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_type = type(e).__name__
            error_msg = str(e)
            
            logger.error("❌ OpenAI API FAILED")
            logger.error("  Error type: %s", error_type)
            logger.error("  Error message: %s", error_msg[:500])
            logger.error("  Time elapsed: %.2f seconds", elapsed)
            
            # Log full traceback for debugging
            import traceback
            logger.debug("Full traceback:\n%s", traceback.format_exc())
            
            # Always fall back to mock - don't break the app
            logger.warning("⚠️  Falling back to MOCK data")
            return self._mock_generate(prompt, json_mode)
    
    def _mock_generate(self, prompt: str, json_mode: bool) -> str:
        """
        Return mock responses for testing/fallback.
        Clearly marked as placeholders so user knows LLM failed.
        """
        prompt_lower = prompt.lower()
        
        # Category scoring response
        if "category" in prompt_lower and "score" in prompt_lower:
            logger.info("Mock: Returning category scores")
            return json.dumps([
                {"category_id": "labor_scheduling", "score": 85, "confidence": 0.9, "rationale": "B1_drags includes Labor too high"},
                {"category_id": "service_speed", "score": 75, "confidence": 0.8, "rationale": "C3_ops_stressors includes Service is slow"},
                {"category_id": "manager_cadence", "score": 80, "confidence": 0.85, "rationale": "B1_drags includes Managers not executing"},
                {"category_id": "training_consistency", "score": 70, "confidence": 0.75, "rationale": "C3_ops_stressors includes Training inconsistent"},
                {"category_id": "menu_simplicity", "score": 60, "confidence": 0.7, "rationale": "D1_menu_size indicates complexity"},
                {"category_id": "discounting_discipline", "score": 90, "confidence": 0.95, "rationale": "B1_drags includes Too much discounting"},
                {"category_id": "upsell_attachment", "score": 65, "confidence": 0.7, "rationale": "D3_upselling indicates weak upselling"},
                {"category_id": "marketing_ownership", "score": 75, "confidence": 0.8, "rationale": "E3_marketing_owner indicates missing ownership"},
                {"category_id": "local_search", "score": 60, "confidence": 0.65, "rationale": "E1_channels_used includes Google Business"},
                {"category_id": "delivery_ops", "score": 55, "confidence": 0.6, "rationale": "General delivery operations opportunity"}
            ])
        
        # Core initiatives response
        if "core initiative" in prompt_lower or "top 4" in prompt_lower:
            logger.info("Mock: Returning core initiatives (4 placeholders)")
            placeholders = []
            for i in range(1, 5):
                placeholders.append({
                    "category_id": f"category_{i}",
                    "title": f"PLACEHOLDER: Core Initiative {i} (LLM generation failed)",
                    "why_now": "This is placeholder data. The LLM failed to generate real initiatives. Check backend logs for OpenAI connection errors.",
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
                })
            return json.dumps(placeholders)
        
        # Sandbox initiatives response
        if "sandbox" in prompt_lower or "experimental" in prompt_lower:
            logger.info("Mock: Returning sandbox initiatives (3 placeholders)")
            placeholders = []
            for i in range(1, 4):
                placeholders.append({
                    "title": f"PLACEHOLDER: Sandbox Experiment {i} (LLM generation failed)",
                    "why_this_came_up": "This is placeholder data. The LLM failed to generate real sandbox experiments. Check backend logs for OpenAI connection errors.",
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
                })
            return json.dumps(placeholders)
        
        # Default fallback
        logger.info("Mock: Returning empty JSON object")
        return "{}"
