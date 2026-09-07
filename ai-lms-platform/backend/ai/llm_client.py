import json
import logging
import os
from typing import Any, Dict, Optional, Tuple
import httpx

logger = logging.getLogger("lms.ai.client")


class LLMError(Exception):
    """Base exception for LLM provider errors."""
    pass


class LLMKeyMissingError(LLMError):
    """Raised when no LLM API key is configured."""
    pass


class LLMResponseError(LLMError):
    """Raised when an LLM returns an invalid HTTP response or malformed payload."""
    pass


def get_gemini_config() -> Tuple[Optional[str], str]:
    """Reads the Gemini API key and model name from environment variables."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    return api_key, model


def call_gemini_json(
    prompt: str,
    system_instruction: Optional[str] = None,
    timeout_seconds: float = 60.0,
) -> Dict[str, Any]:
    """
    Invokes the Google Gemini REST API with structured JSON output enforcement.

    Args:
        prompt: User prompt containing content chunks and instructions.
        system_instruction: Optional system instruction for instructional design guidelines.
        timeout_seconds: HTTP request timeout.

    Returns:
        Parsed JSON dictionary returned by the model.
    """
    api_key, model = get_gemini_config()
    if not api_key:
        raise LLMKeyMissingError("GEMINI_API_KEY / GOOGLE_API_KEY is not configured in environment.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload: Dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(url, json=payload)
    except Exception as exc:
        logger.error("HTTP network failure connecting to Gemini: %s", exc)
        raise LLMResponseError(f"Network error calling Gemini: {exc}") from exc

    if response.status_code != 200:
        logger.error("Gemini API error (HTTP %d): %s", response.status_code, response.text)
        raise LLMResponseError(
            f"Gemini API returned error code {response.status_code}. Details: {response.text[:200]}"
        )

    try:
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise LLMResponseError("Gemini response contained no candidates.")

        candidate = candidates[0]
        content_parts = candidate.get("content", {}).get("parts", [])
        if not content_parts:
            raise LLMResponseError("Gemini candidate contained no content parts.")

        text_response = content_parts[0].get("text", "")
        parsed_json = json.loads(text_response)
        return parsed_json
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini output as JSON: %s", exc)
        raise LLMResponseError("Gemini response was not valid JSON.") from exc
    except Exception as exc:
        logger.error("Unexpected error parsing Gemini response: %s", exc)
        raise LLMResponseError(f"Failed to process Gemini response: {exc}") from exc
