import asyncio
import logging
import time
import json
from typing import Any, Dict
from concurrent.futures import ThreadPoolExecutor
import google.genai as genai
from google.genai import types
from app.core.models import AIResponse

logger = logging.getLogger("dsa.ai.gemini")

# Shared thread pool for blocking Gemini SDK calls
_GEMINI_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="gemini")


class GeminiProvider:
    """
    Google Gemini AI provider using the modern google-genai SDK.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self._api_key = api_key
        self._model_name = model_name
        self._client = genai.Client(api_key=self._api_key)
        logger.info("Gemini provider initialized with model: %s", self._model_name)

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """
        Generate text from prompt using Gemini.
        """
        start_time = time.time()

        try:
            # Configure generation parameters
            temperature = kwargs.get("temperature", 0.1)
            max_tokens = kwargs.get("max_tokens", 8192)
            response_mime_type = kwargs.get("response_mime_type")
            
            config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            if response_mime_type:
                config["response_mime_type"] = response_mime_type

            def _sync_generate():
                return self._client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config)
                )

            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(_GEMINI_EXECUTOR, _sync_generate)

            latency_ms = (time.time() - start_time) * 1000

            # Guard against empty/None response
            content = ""
            if response and hasattr(response, 'text') and response.text:
                content = response.text
            elif response and hasattr(response, 'candidates') and response.candidates:
                # Fallback: extract from candidates if .text is None
                try:
                    content = response.candidates[0].content.parts[0].text or ""
                except (IndexError, AttributeError):
                    pass

            if not content:
                logger.warning("Gemini returned empty content for model %s", self._model_name)
                return AIResponse(
                    content="",
                    model=self._model_name,
                    usage={},
                    latency_ms=latency_ms,
                    success=False,
                    error_message="Gemini returned empty response (possible safety filter or quota issue)",
                )

            logger.debug(
                "Gemini %s generated %d chars in %.0fms", self._model_name, len(content), latency_ms
            )

            return AIResponse(
                content=content,
                model=self._model_name,
                usage={
                    "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                    "total_tokens": response.usage_metadata.total_token_count if response.usage_metadata else 0,
                },
                latency_ms=latency_ms,
                success=True,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("Gemini generation failed: %s", e)

            return AIResponse(
                content="",
                model=self._model_name,
                usage={},
                latency_ms=latency_ms,
                success=False,
                error_message=str(e),
            )

    async def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate structured JSON response.
        """
        # Add instruction for JSON output if not already present
        json_prompt = f"""{prompt}

Respond ONLY with valid JSON. No markdown, no explanations, no code fences.
"""
        response = await self.generate(
            json_prompt,
            response_mime_type="application/json",
            **kwargs,
        )

        if not response.success:
            return {"error": response.error_message}

        content = response.content.strip()
        
        # Simple extraction and parsing
        try:
            # Handle possible markdown fences if AI ignores mime_type
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            # Find the actual JSON object
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                content = content[start:end+1]
                
            return json.loads(content, strict=False)
        except Exception as e:
            logger.error("Failed to parse JSON from Gemini response: %s", e)
            return {"error": "Invalid JSON response", "raw": response.content}

    async def health_check(self) -> bool:
        """
        Check if Gemini API is available.
        """
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(_GEMINI_EXECUTOR, lambda: list(self._client.models.list()))
            return True
        except Exception as e:
            logger.error("Gemini health check failed: %s", e)
            return False
