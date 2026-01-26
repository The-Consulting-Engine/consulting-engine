"""
LLM Client for OpenAI integration.
Simple, reliable implementation that works.
"""
import logging
import os
import json
import time
from typing import Dict, Any, Optional, Union
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
        json_mode: bool = False,
        schema_name: Optional[str] = None
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
            return self._openai_generate(prompt, system_prompt, json_mode, schema_name)
        
        else:
            logger.error("Unknown provider: %s. Falling back to mock.", self.provider)
            return self._mock_generate(prompt, json_mode)
    
    def _openai_generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str], 
        json_mode: bool,
        schema_name: Optional[str] = None
    ) -> str:
        """Generate using OpenAI API. Falls back to mock on any error."""
        from openai import OpenAI
        
        # Check API key
        if not self.api_key:
            logger.warning("No API key available. Falling back to mock.")
            return self._mock_generate(prompt, json_mode)
        
        # Get model from env (default gpt-4o; use gpt-4o-mini for faster responses if you hit timeouts)
        model = os.getenv("LLM_MODEL", "gpt-4o").strip()
        
        # Check if model supports Structured Outputs (gpt-4o, gpt-4o-mini, gpt-4o-2024-08-06)
        supports_structured_outputs = any(
            model.startswith(prefix) 
            for prefix in ["gpt-4o", "gpt-4o-mini", "gpt-4o-2024"]
        )
        
        # Log immediately and force flush so user sees output before blocking call
        import sys
        # gpt-4-turbo-preview often needs 90–120s for core/sandbox JSON; gpt-4o-mini is faster
        timeout_s = 120
        print("[OPENAI] Calling API (model=%s, timeout=%ds)..." % (model, timeout_s), file=sys.stderr, flush=True)
        logger.info("🚀 Calling OpenAI API (model=%s, timeout=%ds)", model, timeout_s)
        logger.info("  Prompt length: %d chars", len(prompt))
        logger.info("  System prompt: %s, JSON mode: %s, Schema: %s", 
                   "yes" if system_prompt else "no", json_mode, schema_name or "none")
        
        start_time = time.time()
        
        try:
            # Create httpx client explicitly to avoid compatibility issues
            import httpx
            http_client = httpx.Client(
                timeout=httpx.Timeout(timeout_s, connect=5.0),
                follow_redirects=True,
            )
            
            # Create OpenAI client with explicit http_client
            client = OpenAI(
                api_key=self.api_key,
                http_client=http_client,
                timeout=float(timeout_s),
                max_retries=0,
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
            
            # Use Structured Outputs for gpt-4o models when schema is provided
            if json_mode and schema_name and supports_structured_outputs:
                from app.llm.json_guard import load_schema
                schema = load_schema(schema_name)
                
                # OpenAI Structured Outputs requires:
                # 1. Root to be an object (not array)
                # 2. ALL nested objects must have additionalProperties: false
                def fix_schema_for_openai(s: Any) -> Any:
                    """Recursively fix schema for OpenAI Structured Outputs:
                    - Add additionalProperties: false to all objects
                    - Add items property to arrays that are missing it
                    """
                    if isinstance(s, dict):
                        result = {}
                        for key, value in s.items():
                            if key == "items":
                                # Recursively fix nested items
                                result[key] = fix_schema_for_openai(value)
                            elif key == "properties":
                                # Recursively fix all properties
                                result[key] = {k: fix_schema_for_openai(v) for k, v in value.items()}
                            else:
                                result[key] = fix_schema_for_openai(value) if isinstance(value, (dict, list)) else value
                        
                        # If this is an array type, ensure it has an items property
                        if s.get("type") == "array" and "items" not in result:
                            # Default to string array if items is missing
                            result["items"] = {"type": "string"}
                            logger.warning("  Added missing 'items' property to array (defaulting to string)")
                        
                        # If this is an object type, ensure additionalProperties is False
                        if s.get("type") == "object" and "additionalProperties" not in result:
                            result["additionalProperties"] = False
                        
                        return result
                    elif isinstance(s, list):
                        return [fix_schema_for_openai(item) for item in s]
                    else:
                        return s
                
                schema = fix_schema_for_openai(schema)
                
                # If schema is an array, wrap it in an object
                if schema.get("type") == "array":
                    wrapped_schema = {
                        "type": "object",
                        "properties": {
                            "items": schema
                        },
                        "required": ["items"],
                        "additionalProperties": False
                    }
                    schema = wrapped_schema
                    logger.info("  Wrapped array schema in object for Structured Outputs")
                
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "strict": True,
                        "schema": schema
                    }
                }
                logger.info("  Using Structured Outputs with schema: %s", schema_name)
            elif json_mode:
                # Fallback to json_object for older models
                kwargs["response_format"] = {"type": "json_object"}
                if supports_structured_outputs:
                    logger.warning("  ⚠️  Model supports Structured Outputs but no schema provided. Using json_object mode (may have issues with arrays).")
            
            # Make API call
            print("[OPENAI] Sending request (timeout %ds)..." % timeout_s, file=sys.stderr, flush=True)
            logger.info("📡 Sending request to OpenAI (timeout %ds)...", timeout_s)
            try:
                response = client.chat.completions.create(**kwargs)
            except Exception as api_call_err:
                elapsed = time.time() - start_time
                err_str = str(api_call_err)
                print("[OPENAI] ERROR after %.1fs: %s" % (elapsed, err_str), file=sys.stderr, flush=True)
                logger.error("❌ OPENAI API CALL FAILED after %.1fs: %s", elapsed, err_str)
                raise
            
            elapsed = time.time() - start_time
            content = response.choices[0].message.content
            
            if not content:
                raise ValueError("OpenAI returned empty response")
            
            # If we used Structured Outputs with a wrapped array schema, unwrap it
            if json_mode and schema_name and supports_structured_outputs:
                try:
                    import json
                    parsed = json.loads(content)
                    # If response is wrapped in {"items": [...]}, extract the array
                    if isinstance(parsed, dict) and "items" in parsed and isinstance(parsed["items"], list):
                        content = json.dumps(parsed["items"])
                        logger.info("  Unwrapped array from Structured Outputs response")
                except (json.JSONDecodeError, KeyError, TypeError):
                    # If unwrapping fails, return content as-is (validation will catch it)
                    pass
            
            logger.info("✅ OpenAI API SUCCESS")
            logger.info("  Response time: %.2f seconds", elapsed)
            logger.info("  Response length: %d characters", len(content))
            logger.info("  First 100 chars: %s", content[:100])
            
            # Close http_client
            http_client.close()
            
            return content
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Log full error details at ERROR level (not debug)
            import traceback
            full_traceback = traceback.format_exc()
            
            # Print to stderr immediately so user sees error even if logs buffer
            print("\n[OPENAI] ERROR after %.1fs: %s" % (elapsed, error_msg), file=sys.stderr, flush=True)
            print("[OPENAI] Falling back to MOCK data", file=sys.stderr, flush=True)
            
            logger.error("\n" + "=" * 80)
            logger.error("❌ OPENAI API ERROR")
            logger.error("=" * 80)
            logger.error("ERROR TYPE: %s", error_type)
            logger.error("ERROR MESSAGE: %s", error_msg)
            logger.error("TIME ELAPSED: %.2f seconds", elapsed)
            logger.error("MODEL: %s", model)
            logger.error("API KEY PRESENT: %s", bool(self.api_key))
            if self.api_key:
                logger.error("API KEY PREFIX: %s...", self.api_key[:15])
            logger.error("PROMPT LENGTH: %d characters", len(prompt))
            logger.error("JSON MODE: %s", json_mode)
            logger.error("")
            logger.error("FULL TRACEBACK:")
            logger.error(full_traceback)
            logger.error("=" * 80)
            
            # Categorize error for better visibility
            error_lower = error_msg.lower()
            if "timeout" in error_lower or "timed out" in error_lower or error_type == "APITimeoutError":
                logger.error("🔴 ERROR CATEGORY: TIMEOUT")
                logger.error("   OpenAI request exceeded timeout (check backend timeout setting)")
                logger.error("   Possible causes:")
                logger.error("     - Network connectivity issues")
                logger.error("     - OpenAI API is slow or overloaded")
                logger.error("     - Prompt is too large/complex")
                logger.error("     - Model is taking longer than expected")
            elif "connection" in error_lower or "connect" in error_lower or "network" in error_lower:
                logger.error("🔴 ERROR CATEGORY: CONNECTION")
                logger.error("   Cannot establish connection to OpenAI API")
                logger.error("   Possible causes:")
                logger.error("     - Network/DNS issues (check docker DNS settings)")
                logger.error("     - Firewall blocking api.openai.com")
                logger.error("     - OpenAI API is down")
                logger.error("     - Docker container cannot reach external APIs")
            elif "api key" in error_lower or "authentication" in error_lower or "401" in error_lower or "unauthorized" in error_lower:
                logger.error("🔴 ERROR CATEGORY: AUTHENTICATION")
                logger.error("   Invalid or missing OpenAI API key")
                logger.error("   Check:")
                logger.error("     - OPENAI_API_KEY in .env file")
                logger.error("     - LLM_API_KEY in .env file")
                logger.error("     - API key is correctly loaded in docker-compose.yml")
                logger.error("     - API key is valid and not expired")
            elif "rate limit" in error_lower or "429" in error_lower:
                logger.error("🔴 ERROR CATEGORY: RATE LIMIT")
                logger.error("   Too many requests to OpenAI API")
                logger.error("   Solution: Wait a few minutes and try again")
            elif "quota" in error_lower or "billing" in error_lower:
                logger.error("🔴 ERROR CATEGORY: QUOTA/BILLING")
                logger.error("   OpenAI account has exceeded quota or billing issue")
                logger.error("   Check your OpenAI account billing and usage limits")
            else:
                logger.error("🔴 ERROR CATEGORY: UNKNOWN")
                logger.error("   Unexpected error occurred")
                logger.error("   Error details: %s", error_msg)
            
            logger.error("")
            logger.error("⚠️  FALLING BACK TO MOCK DATA")
            logger.error("   Generation will continue with placeholder responses")
            logger.error("   Check logs above for the actual OpenAI error")
            logger.error("=" * 80 + "\n")
            
            # Force flush logs to ensure they're visible immediately
            import sys
            sys.stderr.flush()
            sys.stdout.flush()
            
            # Close http_client if it was created
            try:
                if 'http_client' in locals():
                    http_client.close()
            except Exception:
                pass
            
            # Always fall back to mock - don't break the app
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
