"""graph_neighbors — edge traversal for a given file."""

from __future__ import annotations

from ...core.database import Database
from .state import TurnState


def run(
    db: Database,
    state: TurnState,
    session_id: str,
    file_path: str,
    limit: int = 30,
) -> dict:
    file_row = db.get_file_by_path(file_path)
    if not file_row:
        return {"ok": False, "error": f"File not in graph: {file_path}"}

    outgoing = db.get_edges_from(file_row["id"])
    incoming = db.get_edges_to(file_path)

    out_list = [
        {"to": e["to_path"], "rel": e["rel"], "import_name": e["import_name"]}
        for e in outgoing[:limit]
    ]
    in_list = [
        {"from": e["from_path"], "rel": e["rel"]}
        for e in incoming[:limit]
    ]

    db.record_action(
        session_id=session_id,
        action_type="graph_neighbors",
        file_path=file_path,
        metadata={"outgoing": len(out_list), "incoming": len(in_list)},
    )

    return {
        "ok": True,
        "file": file_path,
        "outgoing": out_list,
        "incoming": in_list,
    }
