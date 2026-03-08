"""Shared JSON utilities for LLM response parsing."""

from __future__ import annotations

from typing import Any


def flatten_nested_json(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested JSON where LLM groups fields by section headers.

    Example:
        {"Evidence Assessment": {"motive_proven": true}} → {"motive_proven": true}

    If both top-level and nested keys exist, nested value wins (LLM's
    section-specific answer is more intentional than a top-level duplicate).
    """
    flat: dict[str, Any] = {}
    nested: dict[str, Any] = {}

    for key, val in raw.items():
        if isinstance(val, dict):
            nested.update(val)
        else:
            flat[key] = val

    # Top-level first, then nested overwrites (nested is more specific)
    flat.update(nested)
    return flat
