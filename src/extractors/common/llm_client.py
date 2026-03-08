"""Thin LLM client wrapper — supports OpenAI and Anthropic.

Reads LLM_PROVIDER and LLM_MODEL from environment. Callers must ensure
environment is populated (e.g., via python-dotenv in the entry point).
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when an LLM call fails in a non-recoverable way."""


class LLMContentRefused(LLMError):
    """Raised when the LLM refuses to process the content (content filter)."""


class LLMParsingError(LLMError):
    """Raised when the LLM response cannot be parsed as JSON."""


def _get_provider() -> str:
    return os.getenv("LLM_PROVIDER", "openai")


def _get_model() -> str:
    return os.getenv("LLM_MODEL", "gpt-4o")


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.0,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Call LLM and parse JSON response with retry logic.

    Raises:
        LLMContentRefused: If the LLM refuses to process the content.
        LLMParsingError: If the response is not valid JSON after retries.
        LLMError: For other non-recoverable failures (auth, config).
    """
    model = model or _get_model()
    provider = _get_provider()

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            if provider == "anthropic":
                return _call_anthropic(system_prompt, user_prompt, model, temperature)
            return _call_openai(system_prompt, user_prompt, model, temperature)
        except (LLMContentRefused, LLMError):
            raise  # Don't retry on content refusal or config errors
        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(
                "LLM JSON parse failed (attempt %d/%d): %s",
                attempt, max_retries, str(e)[:200],
            )
        except Exception as e:
            # Rate limits and transient errors — retry with backoff
            last_error = e
            error_name = type(e).__name__
            logger.warning(
                "LLM call failed (attempt %d/%d): %s: %s",
                attempt, max_retries, error_name, str(e)[:200],
            )

        if attempt < max_retries:
            wait = 2 ** attempt  # 2s, 4s, 8s
            logger.info("Retrying in %ds...", wait)
            time.sleep(wait)

    raise LLMParsingError(
        f"Failed after {max_retries} attempts. Last error: {type(last_error).__name__}: {str(last_error)[:200]}"
    )


def _call_openai(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
) -> dict[str, Any]:
    from openai import AuthenticationError, OpenAI

    try:
        client = OpenAI()
    except AuthenticationError as e:
        raise LLMError(f"OpenAI auth failed — check OPENAI_API_KEY: {e}") from e

    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    if not response.choices:
        raise LLMError("OpenAI returned empty choices array")

    choice = response.choices[0]
    if choice.finish_reason == "content_filter":
        raise LLMContentRefused("OpenAI content filter refused this input")

    text = choice.message.content
    if not text:
        raise LLMContentRefused(
            f"OpenAI returned no content (finish_reason={choice.finish_reason})"
        )

    return json.loads(text)


def _call_anthropic(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
) -> dict[str, Any]:
    import anthropic

    try:
        client = anthropic.Anthropic()
    except Exception as e:
        raise LLMError(f"Anthropic client init failed — check ANTHROPIC_API_KEY: {e}") from e

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    if not response.content:
        raise LLMContentRefused("Anthropic returned empty content")

    # Find the first text block
    text = None
    for block in response.content:
        if hasattr(block, "text"):
            text = block.text
            break

    if not text:
        raise LLMContentRefused("Anthropic response has no text blocks")

    # Extract JSON from potential markdown code blocks
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if json_match:
        text = json_match.group(1)

    return json.loads(text)
