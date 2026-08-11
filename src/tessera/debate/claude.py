"""Claude wrapper for debate engine.

Prefers the `claude --print` CLI (Claude Code subscription, no API key needed).
Falls back to the Anthropic Python SDK if ANTHROPIC_API_KEY is set.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import NamedTuple


class ClaudeError(Exception):
    pass


class ClaudeResponse(NamedTuple):
    text: str
    model: str
    input_tokens: int
    output_tokens: int


def _cli_available() -> bool:
    return shutil.which("claude") is not None


def _api_available() -> bool:
    import os
    try:
        import anthropic  # noqa: F401
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    except ImportError:
        return False


def is_available() -> bool:
    """True if either the claude CLI or Anthropic SDK+key are present."""
    return _cli_available() or _api_available()


def run(
    prompt: str,
    system: str = "",
    model: str = "claude-opus-4-6",
    max_tokens: int = 4096,
    timeout: int = 120,
) -> ClaudeResponse:
    """Send *prompt* to Claude.

    Tries in order:
      1. `claude --print` CLI (Claude Code subscription, no API key required)
      2. Anthropic Python SDK (requires ANTHROPIC_API_KEY)

    Raises ClaudeError if neither is available or the call fails.
    """
    if _cli_available():
        return _run_via_cli(prompt, system=system, timeout=timeout)
    if _api_available():
        return _run_via_api(prompt, system=system, model=model,
                            max_tokens=max_tokens, timeout=timeout)
    raise ClaudeError(
        "Claude unavailable: install Claude Code CLI or set ANTHROPIC_API_KEY."
    )


def _run_via_cli(
    prompt: str,
    system: str = "",
    timeout: int = 120,
) -> ClaudeResponse:
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    try:
        result = subprocess.run(
            ["claude", "--print", "--", full_prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise ClaudeError(f"claude CLI timed out after {timeout}s")
    except Exception as exc:
        raise ClaudeError(f"claude CLI error: {exc}")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise ClaudeError(f"claude CLI exited {result.returncode}: {stderr}")

    text = result.stdout.strip()
    if not text:
        raise ClaudeError("claude CLI returned empty response")

    return ClaudeResponse(text=text, model="claude-cli", input_tokens=0, output_tokens=0)


def _run_via_api(
    prompt: str,
    system: str = "",
    model: str = "claude-opus-4-6",
    max_tokens: int = 4096,
    timeout: int = 120,
) -> ClaudeResponse:
    import os
    try:
        import anthropic
    except ImportError:
        raise ClaudeError(
            "anthropic package not installed. Run: pip install tessera[debate]"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ClaudeError("ANTHROPIC_API_KEY not set.")

    client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
    messages = [{"role": "user", "content": prompt}]
    kwargs: dict = dict(model=model, max_tokens=max_tokens, messages=messages)
    if system:
        kwargs["system"] = system

    try:
        response = client.messages.create(**kwargs)
    except anthropic.APIConnectionError as exc:
        raise ClaudeError(f"Connection error: {exc}")
    except anthropic.RateLimitError as exc:
        raise ClaudeError(f"Rate limit: {exc}")
    except anthropic.APIStatusError as exc:
        raise ClaudeError(f"API error {exc.status_code}: {exc.message}")
    except Exception as exc:
        raise ClaudeError(f"Unexpected error: {exc}")

    text = "".join(
        block.text for block in response.content if hasattr(block, "text")
    )
    return ClaudeResponse(
        text=text,
        model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
