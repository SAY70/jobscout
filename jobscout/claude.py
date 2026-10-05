"""Thin wrapper over the Anthropic Messages API.

Two entry points: ``complete`` for plain text generation, and
``complete_with_search`` which gives the model the server-side web search
tool so it can find live job postings.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

DEFAULT_MODEL = "claude-sonnet-4-5"


class ClaudeError(Exception):
    """Raised when the API is unavailable or returns an error."""


def _client():
    try:
        from anthropic import Anthropic
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ClaudeError(
            "The anthropic package is required. Install it with: pip install anthropic"
        ) from exc
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ClaudeError(
            "ANTHROPIC_API_KEY is not set. Create a key at console.anthropic.com "
            "and set it as an environment variable."
        )
    return Anthropic(api_key=key)


def _text_of(message: Any) -> str:
    return "".join(
        block.text for block in message.content if getattr(block, "type", "") == "text"
    ).strip()


def complete(prompt: str, *, model: str = DEFAULT_MODEL, max_tokens: int = 8000) -> str:
    """Return the model's text answer to ``prompt``."""
    client = _client()
    try:
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # noqa: BLE001 - surface the provider's message
        raise ClaudeError(str(exc)) from exc
    return _text_of(message)


def complete_with_search(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 16000,
    max_searches: int = 24,
) -> str:
    """Answer ``prompt`` with the server-side web search tool enabled."""
    client = _client()
    try:
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": max_searches,
                }
            ],
        )
    except Exception as exc:  # noqa: BLE001 - surface the provider's message
        raise ClaudeError(str(exc)) from exc
    return _text_of(message)


def extract_json(text: str) -> Any:
    """Pull the first JSON array or object out of a model reply.

    Models sometimes wrap JSON in prose or a fenced block. This finds the
    outermost balanced structure and parses it.
    """
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fenced:
        text = fenced.group(1)

    start = min(
        (i for i in (text.find("["), text.find("{")) if i != -1),
        default=-1,
    )
    if start == -1:
        raise ClaudeError("No JSON found in the model's reply.")

    opener = text[start]
    closer = "]" if opener == "[" else "}"
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError as exc:
                    raise ClaudeError(f"Model returned malformed JSON: {exc}") from exc
    raise ClaudeError("Model returned truncated JSON.")
