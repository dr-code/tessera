"""graph_lock_decision — record an architectural decision to the session DB."""

from __future__ import annotations

from ...core.database import Database
from .state import TurnState

_VALID_SCOPES = {"file", "module", "project"}


def run(
    db: Database,
    state: TurnState,  # noqa: ARG001 — kept for uniform tool signature
    session_id: str,
    summary: str,
    scope: str = "project",
    files: list[str] | None = None,
) -> dict:
    if not summary or not summary.strip():
        return {"ok": False, "error": "summary is required and must be non-empty"}

    if scope not in _VALID_SCOPES:
        return {
            "ok": False,
            "error": f"scope must be one of {sorted(_VALID_SCOPES)}, got {scope!r}",
        }

    files_list = [f for f in (files or []) if f]

    db.add_decision(
        session_id=session_id,
        summary=summary.strip(),
        files=files_list,
        scope=scope,
    )

    db.record_action(
        session_id=session_id,
        action_type="graph_lock_decision",
        metadata={"summary": summary.strip(), "scope": scope, "files": files_list},
    )

    return {
        "ok": True,
        "summary": summary.strip(),
        "scope": scope,
        "files": files_list,
    }
