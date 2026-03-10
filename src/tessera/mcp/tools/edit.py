"""graph_register_edit — log edits, invalidate cache, auto-check plan checklist."""

from __future__ import annotations

import os
import time
from pathlib import Path

from ...core.database import Database
from .state import TurnState


def _atomic_rewrite_checklist(plan_file_path: str, item_desc: str) -> None:
    """Mark an item done in the plan markdown file using an atomic write.

    Searches line-by-line for any line containing both `- [ ]` and a substring
    of the item description.  This is robust to varying plan formats (with or
    without task IDs and file annotations appended to the checklist line).
    """
    plan_path = Path(plan_file_path)
    if not plan_path.exists():
        return
    content = plan_path.read_text(encoding="utf-8")
    key = item_desc[:50].strip()
    lines = content.splitlines(keepends=True)
    new_lines = []
    replaced = False
    for line in lines:
        if not replaced and "- [ ]" in line and key in line:
            line = line.replace("- [ ]", "- [x]", 1)
            replaced = True
        new_lines.append(line)
    new_content = "".join(new_lines)
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
    needs_explicit_id: list[dict] = []
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
            # Fallback: file-path matching — one item per file, exact match only.
            # If multiple pending items share the same file_target the match is
            # ambiguous; those items are returned in `needs_explicit_id` so the
            # caller can retry with checklist_item_id.
            for file_path in files:
                # Strip ::symbol notation before matching
                bare_path = file_path.split("::")[0]
                matched = db.auto_check_by_file_path(
                    plan_id=active_plan["id"],
                    file_path=bare_path,
                )
                if len(matched) == 1:
                    item = matched[0]
                    db.update_checklist_item(item["id"], "done", time.time())
                    auto_completed.append(item["description"])
                    if active_plan["plan_file_path"]:
                        _atomic_rewrite_checklist(
                            active_plan["plan_file_path"], item["description"]
                        )
                elif len(matched) > 1:
                    needs_explicit_id.extend(
                        {"id": i["id"], "description": i["description"]} for i in matched
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
        "checklist_needs_explicit_id": needs_explicit_id,
    }
