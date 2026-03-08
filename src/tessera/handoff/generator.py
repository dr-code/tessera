"""Enhanced handoff generator — pulls from action graph, plan status, decisions."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from ..core.database import Database


def _recent_commits(project_root: str, n: int = 5) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"-{n}"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip().splitlines()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return []


def generate(
    db: Database,
    project_root: str,
    session_id: str | None = None,
    as_json: bool = False,
) -> str:
    if not session_id:
        session_id = db.get_or_create_session(project_root)

    actions = db.get_session_actions(session_id, limit=50)
    decisions = db.get_decisions(session_id=session_id, limit=10)
    active_plan = db.get_active_plan()
    stats = db.get_stats()

    # Aggregate token savings
    savings = db.get_token_savings(session_id)
    total_saved = sum(s["chars_saved"] for s in savings)
    total_read = sum(s["chars_read_total"] for s in savings)

    # Files touched this session
    files_touched: list[str] = sorted(
        {a["file_path"] for a in actions if a["file_path"]}
    )

    # Files edited
    files_edited: list[str] = sorted(
        {
            a["file_path"]
            for a in actions
            if a["action_type"] == "graph_register_edit" and a["file_path"]
        }
    )
    # Actually parse edit metadata for files list
    edit_files: set[str] = set()
    for a in actions:
        if a["action_type"] == "graph_register_edit":
            try:
                meta = json.loads(a["metadata"] or "{}")
                edit_files.update(meta.get("files", []))
            except Exception:
                pass
    files_edited = sorted(edit_files)

    # Plan info
    plan_info = ""
    next_step = ""
    if active_plan:
        checklist = db.get_plan_checklist(active_plan["id"])
        done = sum(1 for i in checklist if i["status"] == "done")
        total = len(checklist)
        pending_items = [i for i in checklist if i["status"] == "pending"]
        if pending_items:
            next_step = f"{pending_items[0]['description']} ({pending_items[0]['file_target']})"
        plan_id = active_plan["id"]
        plan_info = f"Plan #{plan_id} — {done}/{total} checklist items complete"

    # Recent commits
    commits = _recent_commits(project_root)

    # Decisions
    decision_list = [d["summary"] for d in decisions]

    project_name = Path(project_root).name
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if as_json:
        data = {
            "project": project_name,
            "directory": project_root,
            "timestamp": now,
            "graph_stats": stats,
            "files_touched": files_touched,
            "files_edited": files_edited,
            "decisions": decision_list,
            "active_plan": plan_info,
            "next_step": next_step,
            "token_savings": {
                "chars_saved": total_saved,
                "chars_read_total": total_read,
            },
            "recent_commits": commits,
        }
        return json.dumps(data, indent=2)

    lines = [
        f"Project: {project_name}",
        f"Directory: {project_root}",
        f"Time: {now}",
        "",
        "Graph context (from tessera):",
        f"  Graph: {stats['files']} files, {stats['symbols']} symbols, {stats['edges']} edges",
    ]
    if files_touched:
        lines.append(f"  Files touched: {', '.join(files_touched[:10])}")
    if decision_list:
        lines.append("  Decisions locked:")
        for d in decision_list[:5]:
            lines.append(f"    - {d}")
    if total_saved:
        lines.append(f"  Token savings: {total_saved:,} chars saved ({total_read:,} read)")
    if plan_info:
        lines.append(f"  Active plan: {plan_info}")
    if files_edited:
        lines.append("")
        lines.append("Completed this session:")
        for f in files_edited[:10]:
            lines.append(f"  - {f}")
    if commits:
        lines.append("")
        lines.append("Recent commits:")
        for c in commits[:3]:
            lines.append(f"  {c}")
    if next_step:
        lines.append("")
        lines.append(f"Next step: {next_step}")

    return "\n".join(lines)
