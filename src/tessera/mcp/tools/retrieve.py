"""graph_retrieve — scored file ranking, capped at 1 per turn."""

from __future__ import annotations

from ...core.database import Database
from ...graph.scorer import score_files
from .state import TurnState


def run(
    db: Database,
    state: TurnState,
    session_id: str,
    query: str,
    top_files: int = 5,
    top_edges: int = 12,
) -> dict:
    if state.retrieve_called:
        return {
            "ok": False,
            "error": "graph_retrieve already called this turn. Use graph_read for additional files.",
        }
    state.retrieve_called = True

    # Cache check
    cached = db.get_cached_retrieval(query)
    if cached:
        db.record_action(
            session_id=session_id,
            action_type="graph_retrieve",
            query=query,
            metadata={"cache_hit": True},
        )
        return {"ok": True, "results": cached[:top_files], "cache_hit": True}

    scored = score_files(db, query, top_n=top_files, top_edges=top_edges)
    results = [
        {
            "path": s.path,
            "score": round(s.score, 2),
            "summary": s.summary,
            "role": s.role,
            "language": s.language,
            "edge_count": s.edge_count,
            "symbols": s.symbols,
        }
        for s in scored
    ]

    file_hashes: dict[str, str] = {}
    for item in results:
        row = db.get_file_by_path(item["path"])
        if row:
            file_hashes[item["path"]] = row["content_hash"]

    if results:
        db.cache_retrieval(query, results, file_hashes)

    db.record_action(
        session_id=session_id,
        action_type="graph_retrieve",
        query=query,
        query_terms=query.split(),
        metadata={"cache_hit": False},
    )

    return {"ok": True, "results": results, "cache_hit": False}
