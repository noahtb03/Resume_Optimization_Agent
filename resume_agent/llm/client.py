"""The ONLY module that imports the Anthropic SDK.

BYOK + stateless: the key is held only on a request-scoped instance, a fresh
SDK client is constructed per call, and the key is never written to env, disk,
logs, or any module-level state. Tests inject a fake LLMClient instead.
"""
from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    def complete(self, *, system: str, user: str, max_tokens: int = 1500) -> str: ...


class AnthropicClient:
    """Request-scoped. Construct with the user's key, use, discard. No caching."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        if not api_key:
            raise ValueError("BYOK: an Anthropic API key is required")
        self._api_key = api_key            # request-scoped only; never persisted
        self.model = model

    def complete(self, *, system: str, user: str, max_tokens: int = 1500) -> str:
        import anthropic  # lazy import so the package works without the SDK in tests
        client = anthropic.Anthropic(api_key=self._api_key)  # fresh per call
        msg = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
