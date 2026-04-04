"""Codex CLI subprocess wrapper.

Sends a prompt to the `codex` CLI and returns the text response.
Handles missing CLI, timeouts, and non-zero exits gracefully.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import NamedTuple


class CodexError(Exception):
    pass


class CodexResponse(NamedTuple):
    text: str
    exit_code: int


def is_available() -> bool:
    """Check whether `codex` CLI is on PATH."""
    return shutil.which("codex") is not None


def run(prompt: str, timeout: int = 1200) -> CodexResponse:
    """Send *prompt* to the Codex CLI and return its response.

    Raises CodexError if codex is not found, times out, or exits non-zero.
    """
    if not is_available():
        raise CodexError(
            "Codex CLI not found. Install with: npm install -g @openai/codex\n"
            "Or run 'tessera debate --no-exec' to generate a plan without execution."
        )
    try:
        result = subprocess.run(
            ["codex", "exec", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise CodexError(f"Codex CLI timed out after {timeout}s.")
    except Exception as exc:
        raise CodexError(f"Codex CLI subprocess error: {exc}")

    if result.returncode != 0:
        raise CodexError(
            f"Codex CLI exited with code {result.returncode}.\n"
            f"stderr: {result.stderr[:500]}"
        )

    return CodexResponse(text=result.stdout.strip(), exit_code=result.returncode)
