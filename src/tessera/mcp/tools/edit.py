"""graph_register_edit — log edits, invalidate cache, auto-check plan checklist."""

from __future__ import annotations

import os
import time
from pathlib import Path

from ...core.database import Database
from .state import TurnState


def _atomic_rewrite_checklist(plan_file_path: str, item_desc: str) -> None:
    """Mark an item done in the plan markdown file using an atomic write."""
    plan_path = Path(plan_file_path)
    if not plan_path.exists():
        return
    content = plan_path.read_text(encoding="utf-8")
    # Replace `- [ ] ...description...` with `- [x] ...`
    # Match on a substring of the description to avoid exact-match failures
    key = item_desc[:50].strip()
    new_content = content.replace(f"- [ ] {key}", f"- [x] {key}", 1)
    if new_content != content:
        tmp = str(plan_path) + ".tmp"
        Path(tmp).write_text(new_content, encoding="utf-8")
        os.replace(tmp, str(plan_path))


def run(
    db: Database,
    state: TurnState,
    session_id: str,
    files: list[str],
    summary: str = "",
    checklist_item_id: int = 0,
) -> dict:
    # Invalidate retrieval cache for edited files
    db.invalidate_cache_for_files(files)

    # Record action
    db.record_action(
        session_id=session_id,
        action_type="graph_register_edit",
        metadata={"files": files, "summary": summary,
                  "checklist_item_id": checklist_item_id},
    )

    auto_completed: list[str] = []
    active_plan = db.get_active_plan()

    if active_plan:
        if checklist_item_id:
            # Explicit ID path: mark the item done directly, no text matching.
            checklist = db.get_plan_checklist(active_plan["id"])
            target = next(
                (i for i in checklist if i["id"] == checklist_item_id
                 and i["status"] != "done"),
                None,
            )
            if target:
                db.update_checklist_item(target["id"], "done", time.time())
                auto_completed.append(target["description"])
                if active_plan["plan_file_path"]:
                    _atomic_rewrite_checklist(
                        active_plan["plan_file_path"], target["description"]
                    )
        else:
            # Fallback: keyword match across edited files
            summary_keywords = [w.lower() for w in summary.split() if len(w) > 3]
            for file_path in files:
                matched = db.auto_check_by_file_and_keywords(
                    plan_id=active_plan["id"],
                    file_path=file_path,
                    summary_keywords=summary_keywords,
                )
                for item in matched:
                    db.update_checklist_item(item["id"], "done", time.time())
                    auto_completed.append(item["description"])
                    if active_plan["plan_file_path"]:
                        _atomic_rewrite_checklist(
                            active_plan["plan_file_path"], item["description"]
                        )

        # Close plan when every item is done
        checklist = db.get_plan_checklist(active_plan["id"])
        if checklist and all(i["status"] == "done" for i in checklist):
            db.update_plan_status(active_plan["id"], "completed")

    return {
        "ok": True,
        "files_registered": files,
        "summary": summary,
        "cache_invalidated": len(files),
        "checklist_auto_completed": auto_completed,
    }
