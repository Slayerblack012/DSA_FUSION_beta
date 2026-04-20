import logging
import asyncio
import time
import json
import re
from typing import Any, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

try:
    # New SDK: google-genai (pip install google-genai)
    import google.genai as genai
    from google.genai import types
    _USING_NEW_SDK = True
except ImportError:
    # Fallback: legacy google-generativeai (pip install google-generativeai)
    import google.generativeai as genai  # type: ignore
    types = None  # type: ignore
    _USING_NEW_SDK = False

from app.core.models import AIResponse

logger = logging.getLogger("dsa.ai.gemini")

# Thread pool for blocking SDK calls
_GEMINI_EXECUTOR = ThreadPoolExecutor(max_workers=20)

class GeminiProvider:
    """
    Highly optimized Google Gemini AI provider.
    Supports both legacy and modern SDKs with automatic JSON repair and safety bypass.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self._api_key = api_key
        self._model_name = model_name
        self._client = None
        
        if _USING_NEW_SDK:
            try:
                self._client = genai.Client(api_key=self._api_key)
                logger.info("Gemini provider: Using NEW google-genai SDK (Model: %s)", self._model_name)
            except Exception as e:
                logger.error("Failed to init new Gemini SDK client: %s", e)
        else:
            try:
                genai.configure(api_key=self._api_key)  # type: ignore
                logger.info("Gemini provider: Using LEGACY google-generativeai SDK (Model: %s)", self._model_name)
            except Exception as e:
                logger.error("Failed to configure legacy Gemini SDK: %s", e)

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """
        Execute generation with standard completion and safety bypass.
        """
        start_time = time.time()
        temperature = kwargs.get("temperature", 0.1)
        max_tokens = kwargs.get("max_tokens", 8192)
        response_mime_type = kwargs.get("response_mime_type")
        response_schema = kwargs.get("response_schema")

        try:
            loop = asyncio.get_running_loop()

            if _USING_NEW_SDK:
                # Optimized path for New SDK
                safety_settings = [
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                ]
                
                config_dict = {
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                    "safety_settings": safety_settings,
                }
                if response_mime_type:
                    config_dict["response_mime_type"] = response_mime_type
                if response_schema:
                    config_dict["response_schema"] = response_schema

                def _call_new():
                    return self._client.models.generate_content(
                        model=self._model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(**config_dict)
                    )
                
                response = await loop.run_in_executor(_GEMINI_EXECUTOR, _call_new)
                content = response.text if response and response.text else ""
                
            else:
                # Optimized path for Legacy SDK
                def _call_legacy():
                    model = genai.GenerativeModel(self._model_name)  # type: ignore
                    safety_config = [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                    ]
                    gen_config = genai.types.GenerationConfig(  # type: ignore
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                        response_mime_type=response_mime_type
                    )
                    return model.generate_content(
                        prompt, 
                        generation_config=gen_config,
                        safety_settings=safety_config
                    )
                
                response = await loop.run_in_executor(_GEMINI_EXECUTOR, _call_legacy)
                content = response.text if response and response.text else ""

            latency_ms = (time.time() - start_time) * 1000
            
            if not content:
                # Check for blocking
                reason = "BLOCKED_OR_EMPTY"
                try: 
                    if hasattr(response, 'candidates') and response.candidates:
                        reason = f"FinishReason: {response.candidates[0].finish_reason}"
                except: pass
                
                return AIResponse(
                    content="", model=self._model_name, usage={},
                    latency_ms=latency_ms, success=False, error_message=reason
                )

            return AIResponse(
                content=content,
                model=self._model_name,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                latency_ms=latency_ms,
                success=True
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("Gemini generation failed: %s", e)
            return AIResponse(
                content="", model=self._model_name, usage={},
                latency_ms=latency_ms, success=False, error_message=str(e)
            )

    async def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate structured JSON response with robust surgical repair logic.
        """
        kwargs.setdefault("temperature", 0)
        response_schema = kwargs.pop("response_schema", None)
        
        response = await self.generate(
            prompt,
            response_mime_type="application/json",
            response_schema=response_schema,
            **kwargs,
        )

        if not response.success:
            return {"error": response.error_message}

        content = response.content.strip()
        
        try:
            return json.loads(content, strict=False)
        except Exception as e:
            logger.warning("JSON parse failed, attempting surgical repair for error: %s", e)
            
            # Reparing truncation (missing closing brackets)
            open_braces = content.count("{")
            close_braces = content.count("}")
            open_brackets = content.count("[")
            close_brackets = content.count("]")
            
            # Unclosed string fix
            if content.count('"') % 2 != 0:
                content += '"'
            
            # Close arrays and objects in reverse order
            if open_brackets > close_brackets:
                content += "]" * (open_brackets - close_brackets)
            if open_braces > close_braces:
                content += "}" * (open_braces - close_braces)
                
            try:
                # Flatten lines to remove literal newlines inside strings
                lines = content.splitlines()
                content = " ".join([l.strip() for l in lines if l.strip()])
                
                # Polish: fix trailing commas and single-quoted property names
                content = re.sub(r',\s*([\]}])', r'\1', content)
                content = re.sub(r"([{,]\s*)'([^']+)'(\s*:)", r'\1"\2"\3', content)
                
                return json.loads(content, strict=False)
            except Exception as e2:
                logger.error("JSON repair failed: %s. Lead chars: %s", e2, content[:100])
                return {"error": "Invalid JSON response (Truncated)", "raw": response.content}

    async def health_check(self) -> bool:
        """
        Lightweight model availability check.
        """
        try:
            loop = asyncio.get_running_loop()
            if _USING_NEW_SDK and self._client:
                # We just check if client exists and a simple call works
                await loop.run_in_executor(_GEMINI_EXECUTOR, lambda: list(self._client.models.list(config={'page_size': 1})))
            else:
                # Legacy check
                await loop.run_in_executor(_GEMINI_EXECUTOR, lambda: next(genai.list_models())) # type: ignore
            return True
        except Exception as e:
            logger.error("Gemini health check failed: %s", e)
            return False
