"""graph_continue — mandatory first call each turn.

Routes to memory-first or retrieve-then-read path.  Returns recommended
files, confidence level, and session context.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from ...core.database import Database
from ...core.config import PROJECT_ROOT
from ...graph.scorer import score_files, classify_intent
from .state import TurnState


_SMALL_PROJECT_THRESHOLD = 10  # Skip graph for projects with <10 files


def run(
    db: Database,
    state: TurnState,
    session_id: str,
    query: str,
    top_files: int = 5,
    project_root: str = "",
) -> dict:
    """Execute graph_continue logic and reset turn state."""
    state.reset()

    # Check if graph has been built
    stats = db.get_stats()
    total_files = stats["files"]

    if total_files == 0:
        return {
            "ok": False,
            "needs_scan": True,
            "message": "Graph not built. Run graph_scan first.",
            "turn": state.turn_number,
        }

    # Small-project bypass
    if total_files < _SMALL_PROJECT_THRESHOLD:
        return {
            "ok": True,
            "skip": True,
            "reason": f"Project has only {total_files} files — graph routing not needed.",
            "turn": state.turn_number,
        }

    # Check retrieval cache first
    cached = db.get_cached_retrieval(query)
    cache_hit = cached is not None

    if cached:
        top = cached[:top_files]
    else:
        scored = score_files(db, query, top_n=top_files)
        top = [
            {
                "path": s.path,
                "score": round(s.score, 2),
                "summary": s.summary,
                "role": s.role,
                "symbols": s.symbols,
            }
            for s in scored
        ]
        # Build file_hashes for cache
        file_hashes: dict[str, str] = {}
        for item in top:
            row = db.get_file_by_path(item["path"])
            if row:
                file_hashes[item["path"]] = row["content_hash"]
        if top:
            db.cache_retrieval(query, top, file_hashes)

    # Determine confidence
    if top and top[0].get("score", 0) >= 8:
        confidence = "high"
        max_supplementary_greps = 0
        max_supplementary_files = 0
    elif top and top[0].get("score", 0) >= 4:
        confidence = "medium"
        max_supplementary_greps = 2
        max_supplementary_files = 2
    else:
        confidence = "low"
        max_supplementary_greps = 3
        max_supplementary_files = 3

    # Record action
    db.record_action(
        session_id=session_id,
        action_type="graph_continue",
        query=query,
        query_terms=query.split(),
        metadata={"confidence": confidence, "cache_hit": cache_hit},
    )

    # Recent decisions for context
    decisions = db.get_decisions(session_id=session_id, limit=5)
    recent_decisions = [
        {"summary": d["summary"], "scope": d["scope"]} for d in decisions
    ]

    # Active plan checklist — gives Claude item IDs to pass to graph_register_edit
    active_checklist: list[dict] = []
    active_plan = db.get_active_plan()
    if active_plan:
        rows = db.get_plan_checklist(active_plan["id"])
        active_checklist = [
            {
                "id": row["id"],
                "description": row["description"],
                "status": row["status"],
            }
            for row in rows
        ]

    return {
        "ok": True,
        "turn": state.turn_number,
        "query": query,
        "intent": classify_intent(query),
        "confidence": confidence,
        "max_supplementary_greps": max_supplementary_greps,
        "max_supplementary_files": max_supplementary_files,
        "recommended_files": top,
        "cache_hit": cache_hit,
        "graph_stats": stats,
        "recent_decisions": recent_decisions,
        "active_checklist": active_checklist,
    }
