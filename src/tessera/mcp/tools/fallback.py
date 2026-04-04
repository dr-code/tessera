"""fallback_rg — capped grep, 1 call per turn by default."""

from __future__ import annotations

import json
import subprocess

from ...core.database import Database
from .state import TurnState


_MAX_GREP_CALLS = 1
_MAX_HITS_DEFAULT = 30


def run(
    db: Database,
    state: TurnState,
    session_id: str,
    pattern: str,
    max_hits: int = _MAX_HITS_DEFAULT,
    paths: list[str] | None = None,
    project_root: str = "",
) -> dict:
    if state.grep_calls >= _MAX_GREP_CALLS:
        return {
            "ok": False,
            "error": f"fallback_rg already called {state.grep_calls} time(s) this turn. "
                     "Use graph_retrieve instead of additional greps.",
        }
    state.grep_calls += 1

    cmd = ["rg", "--json", f"--max-count={max_hits}", pattern]
    if paths:
        cmd += paths
    elif project_root:
        cmd.append(project_root)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        # rg not found or timed out — fallback to no results
        return {
            "ok": False,
            "error": f"ripgrep error: {exc}",
        }

    hits: list[dict] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if obj.get("type") == "match":
                data = obj["data"]
                hits.append(
                    {
                        "path": data["path"]["text"],
                        "line": data["line_number"],
                        "text": data["lines"]["text"].rstrip(),
                    }
                )
        except (json.JSONDecodeError, KeyError):
            continue
        if len(hits) >= max_hits:
            break

    db.record_action(
        session_id=session_id,
        action_type="fallback_rg",
        query=pattern,
        metadata={"hits": len(hits)},
    )

    return {
        "ok": True,
        "pattern": pattern,
        "hits": hits,
        "total": len(hits),
    }
