"""graph_scan — rebuild info graph and inject CLAUDE.md policy block."""

from __future__ import annotations

from pathlib import Path

from ...core.database import Database
from ...graph.builder import build_graph
from .state import TurnState


_POLICY_MARKER_START = "<!-- TESSERA:START"
_POLICY_MARKER_END = "<!-- TESSERA:END -->"

_POLICY_TEMPLATE = """\
<!-- TESSERA:START v2 -->
## Tessera Graph Policy

**MANDATORY**: Call `graph_continue` as your FIRST tool call every turn.

- If `needs_scan=true`: run `graph_scan` with the project root path
- If `skip=true`: project too small, proceed normally
- If error: proceed normally without graph routing for this turn
- Read all `recommended_files` via `graph_read` before other exploration
- Obey confidence caps:
  - high: no supplementary greps or reads
  - medium: up to max_supplementary_greps greps + max_supplementary_files reads
  - low: up to max_supplementary_greps greps + max_supplementary_files reads
- After edits: call `graph_register_edit` with file::symbol notation and summary
  - If `graph_continue` returned `active_checklist`, pass `checklist_item_id` for the item you just completed — this marks it done without keyword matching
  - If no active checklist or the edit doesn't map to a specific item, omit `checklist_item_id` (keyword fallback applies)
- When you identify an architectural decision: call `graph_lock_decision` with a one-sentence summary, scope (`"file"` | `"module"` | `"project"`), and the files it applies to
- Max 1 `graph_retrieve` per turn
- No raw grep/rg/bash file reads before `graph_continue`
<!-- TESSERA:END -->"""


def _inject_policy(claude_md_path: Path) -> None:
    """Insert or replace the Tessera policy block in CLAUDE.md."""
    if claude_md_path.exists():
        content = claude_md_path.read_text(encoding="utf-8")
    else:
        content = "# CLAUDE.md\n\n"

    # Remove existing block
    if _POLICY_MARKER_START in content and _POLICY_MARKER_END in content:
        start_idx = content.index(_POLICY_MARKER_START)
        end_idx = content.index(_POLICY_MARKER_END) + len(_POLICY_MARKER_END)
        content = content[:start_idx].rstrip() + "\n" + content[end_idx:].lstrip()

    content = content.rstrip() + "\n\n" + _POLICY_TEMPLATE + "\n"
    tmp = claude_md_path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, claude_md_path)


def run(
    db: Database,
    state: TurnState,  # noqa: ARG001 — kept for uniform tool signature
    session_id: str,
    project_root: str,
    incremental: bool = True,
) -> dict:
    root = Path(project_root).resolve()
    if not root.exists():
        return {"ok": False, "error": f"Project root not found: {project_root}"}

    stats = build_graph(str(root), db, incremental=incremental)

    # Inject CLAUDE.md policy
    claude_md = root / "CLAUDE.md"
    policy_injected = False
    try:
        _inject_policy(claude_md)
        policy_injected = True
    except OSError:
        pass  # Non-fatal

    db.record_action(
        session_id=session_id,
        action_type="graph_scan",
        metadata={"project_root": str(root), "stats": stats},
    )

    return {
        "ok": True,
        "project_root": str(root),
        "stats": stats,
        "policy_injected": policy_injected,
        "incremental": incremental,
    }
