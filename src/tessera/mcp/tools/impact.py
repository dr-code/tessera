"""graph_impact — bidirectional change propagation (blast radius)."""

from __future__ import annotations

from ...core.database import Database
from .state import TurnState


def _collect_impacted(db: Database, file_path: str, visited: set[str], depth: int) -> None:
    if depth <= 0 or file_path in visited:
        return
    visited.add(file_path)
    # Files that import this file (incoming edges)
    incoming = db.get_edges_to(file_path)
    for edge in incoming:
        _collect_impacted(db, edge["from_path"], visited, depth - 1)


_MAX_DEPTH_CAP = 10


def run(
    db: Database,
    state: TurnState,
    session_id: str,
    changed_files: list[str],
    max_depth: int = 3,
) -> dict:
    max_depth = min(max_depth, _MAX_DEPTH_CAP)
    impacted: set[str] = set()
    for f in changed_files:
        _collect_impacted(db, f, impacted, max_depth)

    # Remove the changed files themselves from the blast radius
    blast_radius = sorted(impacted - set(changed_files))

    db.record_action(
        session_id=session_id,
        action_type="graph_impact",
        metadata={
            "changed": changed_files,
            "impacted_count": len(blast_radius),
        },
    )

    return {
        "ok": True,
        "changed_files": changed_files,
        "impacted_files": blast_radius,
        "total_impacted": len(blast_radius),
    }
