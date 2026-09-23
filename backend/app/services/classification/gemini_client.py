"""
Gemini Client Abstraction for NagarSetu
Encapsulates structured JSON generation using the official Google GenAI SDK.
Strictly isolates credentials, manages timeouts, and provides clear error semantics.
"""

import json
import logging
import re
from typing import Optional, Dict, Any

from app.core.config import settings

logger = logging.getLogger("nagarsetu.gemini_client")


class GeminiError(Exception):
    """Base exception for Gemini client failures."""
    pass


class GeminiNotConfiguredError(GeminiError):
    """Raised when GEMINI_API_KEY is not set or empty."""
    pass


class GeminiTimeoutError(GeminiError):
    """Raised when the Gemini API call exceeds the configured timeout."""
    pass


class GeminiResponseMalformedError(GeminiError):
    """Raised when the Gemini API response cannot be parsed as valid JSON."""
    pass


class GeminiClassificationClient:
    """
    Production client for interacting with Google Gemini API.
    Enforces structured JSON generation, temperature=0.1, and timeout bounds.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: float = 15.0
    ):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model_name = model_name or settings.MODEL_VERSION
        self.timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        """Returns True if an API key is available."""
        return bool(self.api_key and self.api_key.strip())

    def generate_structured_json(
        self,
        system_instruction: str,
        prompt: str
    ) -> Dict[str, Any]:
        """
        Calls Gemini API requesting structured JSON output.
        Returns parsed dictionary or raises a subclass of GeminiError.
        """
        if not self.is_configured():
            raise GeminiNotConfiguredError(
                "GEMINI_API_KEY is not configured. Set GEMINI_API_KEY in the environment or .env file."
            )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            config = types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                system_instruction=system_instruction
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            raw_text = response.text
            if not raw_text:
                raise GeminiResponseMalformedError("Gemini returned an empty response body.")

            # Clean any potential markdown code blocks
            cleaned_text = raw_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            try:
                parsed_json = json.loads(cleaned_text)
                if not isinstance(parsed_json, dict):
                    raise GeminiResponseMalformedError(
                        f"Expected JSON object, got {type(parsed_json).__name__}"
                    )
                return parsed_json
            except json.JSONDecodeError as jde:
                logger.error("Failed to parse Gemini JSON output: %s", raw_text[:200])
                raise GeminiResponseMalformedError(f"Malformed JSON from Gemini: {jde}") from jde

        except GeminiError:
            raise
        except TimeoutError as te:
            logger.warning("Gemini API call timed out: %s", te)
            raise GeminiTimeoutError(f"Gemini API timed out after {self.timeout_seconds}s") from te
        except Exception as exc:
            logger.error("Gemini API invocation error: %s", exc)
            raise GeminiError(f"Gemini API request failed: {exc}") from exc
