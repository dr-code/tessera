"""plan_save — archive a markdown plan and its checklist to the session DB."""

from __future__ import annotations

import re

from ...core.database import Database
from ...plans.archive import save_raw_plan
from .state import TurnState

# Matches: - [ ] optional **Step N:** description
_TASK_RE = re.compile(
    r"^\s*-\s*\[\s*\]\s*(?:\*\*Step\s+\d+:\s*\*\*)?\s*(.+)$",
    re.MULTILINE,
)

# Matches lines like "- Create: path/to/file.py" or "- Modify: ..." or "- Test: ..."
_FILE_REF_RE = re.compile(
    r"^\s*-\s*(?:Create|Modify|Test):\s*`?([^\s`]+)`?",
    re.MULTILINE,
)


def _parse_checklist(markdown: str) -> list[tuple[str, str, list[str], str]]:
    """Extract checklist items from a Superpowers-format markdown plan.

    Returns list of (task_id, description, keywords, file_target).
    Each task_id is its sequential index as a string.
    file_target is the nearest file reference preceding the checkbox, or "".
    """
    file_refs: dict[int, str] = {m.start(): m.group(1) for m in _FILE_REF_RE.finditer(markdown)}
    sorted_ref_positions = sorted(file_refs.keys(), reverse=True)

    items: list[tuple[str, str, list[str], str]] = []
    for idx, m in enumerate(_TASK_RE.finditer(markdown)):
        description = m.group(1).strip()
        task_pos = m.start()

        file_target = ""
        for ref_pos in sorted_ref_positions:
            if ref_pos < task_pos:
                file_target = file_refs[ref_pos]
                break

        words = re.findall(r"[a-zA-Z_][\w]*", description)
        keywords = [w.lower() for w in words[:3] if len(w) > 2]

        items.append((str(idx), description, keywords, file_target))

    return items


def run(
    db: Database,
    state: TurnState,  # noqa: ARG001 — kept for uniform tool signature
    session_id: str,
    project_root: str,
    project_name: str = "",
    subtask_name: str = "",
    task: str = "",
    plan_markdown: str = "",
) -> dict:
    if not project_name or not project_name.strip():
        return {"ok": False, "error": "project_name is required"}
    if not subtask_name or not subtask_name.strip():
        return {"ok": False, "error": "subtask_name is required"}
    if not task or not task.strip():
        return {"ok": False, "error": "task is required"}
    if not plan_markdown or not plan_markdown.strip():
        return {"ok": False, "error": "plan_markdown is required"}

    checklist_items = _parse_checklist(plan_markdown)

    try:
        plan_id, plan_file = save_raw_plan(
            db=db,
            project_root=project_root,
            project_name=project_name.strip(),
            subtask_name=subtask_name.strip(),
            plan_markdown=plan_markdown,
            checklist_items=checklist_items,
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    db.record_action(
        session_id=session_id,
        action_type="plan_save",
        metadata={
            "project": project_name.strip(),
            "subtask": subtask_name.strip(),
            "task": task.strip(),
            "plan_id": plan_id,
            "checklist_count": len(checklist_items),
        },
    )

    return {
        "ok": True,
        "plan_id": plan_id,
        "plan_file": plan_file,
        "checklist_count": len(checklist_items),
    }
