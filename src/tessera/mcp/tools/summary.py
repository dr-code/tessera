"""graph_action_summary — recent actions, decisions, and plan status."""

from __future__ import annotations

import json

from ...core.database import Database
from .state import TurnState


def run(
    db: Database,
    state: TurnState,
    session_id: str,
    query: str = "",
    limit: int = 12,
) -> dict:
    if query:
        actions = db.search_action_history(
            session_id=session_id,
            query_terms=query.split(),
            limit=limit,
        )
    else:
        actions = db.get_session_actions(session_id=session_id, limit=limit)

    action_list = [
        {
            "type": a["action_type"],
            "file": a["file_path"],
            "symbol": a["symbol_name"],
            "query": a["query"],
            "ts": a["created_at"],
        }
        for a in actions
    ]

    decisions = db.get_decisions(session_id=session_id, limit=10)
    decision_list = [
        {"summary": d["summary"], "scope": d["scope"], "ts": d["created_at"]}
        for d in decisions
    ]

    active_plan = db.get_active_plan()
    plan_info: dict | None = None
    if active_plan:
        checklist = db.get_plan_checklist(active_plan["id"])
        done = sum(1 for i in checklist if i["status"] == "done")
        plan_info = {
            "plan_id": active_plan["id"],
            "status": active_plan["status"],
            "checklist_done": done,
            "checklist_total": len(checklist),
        }

    return {
        "ok": True,
        "session_id": session_id,
        "actions": action_list,
        "decisions": decision_list,
        "active_plan": plan_info,
    }
