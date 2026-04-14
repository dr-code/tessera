"""Plan Archive — save, load, and manage debate plans.

Plans are stored in both SQLite (for querying) and on-disk markdown files
(for human readability and atomic edits).
"""

from __future__ import annotations

import gzip
from datetime import datetime
from pathlib import Path

from ..core.database import Database
from ..core.config import MAX_DEBATE_TRANSCRIPT_BYTES
from ..debate.payload import PlanPayload


def _compress_transcript(text: str) -> str:
    """Compress a debate transcript if it exceeds the size limit."""
    encoded = text.encode("utf-8")
    if len(encoded) <= MAX_DEBATE_TRANSCRIPT_BYTES:
        return text
    # Gzip + base64 for storage
    import base64
    compressed = gzip.compress(encoded)
    return "gz:" + base64.b64encode(compressed).decode("ascii")


def _decompress_transcript(text: str) -> str:
    if not text.startswith("gz:"):
        return text
    import base64
    compressed = base64.b64decode(text[3:])
    decompressed = gzip.decompress(compressed)
    if len(decompressed) > MAX_DEBATE_TRANSCRIPT_BYTES * 10:
        raise ValueError("Transcript decompressed size exceeds safety limit")
    return decompressed.decode("utf-8")


def _build_plan_markdown(
    project_name: str,
    subtask_name: str,
    task: str,
    payload: PlanPayload,
    debate_summary: str,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    targets = "\n".join(
        f"- {t['path']} [{t['action']}]" for t in payload.targets
    )
    checklist = "\n".join(
        f"- [ ] {t.task_id}. {t.description} ({t.file})"
        for t in payload.tasks
    )
    validation = "\n".join(f"- {c}" for c in payload.validation)

    return f"""# Plan: {project_name} / {subtask_name}

Created: {now}
Debate rounds: {payload.rounds}
Status: pending

## Task
{task}

## Debate Summary
{debate_summary}

## File Targets
{targets}

## Checklist
{checklist}

## Validation Criteria
{validation}
"""


def save_plan(
    db: Database,
    project_root: str,
    project_name: str,
    subtask_name: str,
    task: str,
    debate_transcript_text: str,
    payload: PlanPayload,
    debate_summary: str = "",
) -> tuple[int, str]:
    """Save a plan to the DB and disk.

    Returns (plan_id, plan_file_path).
    """
    # DB: upsert project + subtask
    project_id = db.create_project(project_name)
    subtask_id = db.create_subtask(project_id, subtask_name)

    # Compress transcript if needed
    stored_transcript = _compress_transcript(debate_transcript_text)

    # Disk: write plan markdown
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    plans_base = (Path(project_root) / ".tessera" / "plans").resolve()
    plan_dir = (plans_base / project_name / subtask_name).resolve()
    if not str(plan_dir).startswith(str(plans_base)):
        raise ValueError(
            f"Invalid project/subtask name: path escapes .tessera/plans/ "
            f"({project_name!r}, {subtask_name!r})"
        )
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_file = plan_dir / f"plan-{timestamp}.md"

    # DB: save plan before writing disk so an orphaned file is never created
    plan_id = db.save_plan(
        subtask_id=subtask_id,
        debate_transcript=stored_transcript,
        final_plan_xml=payload.raw_xml,
        plan_file_path=str(plan_file),
    )

    md_content = _build_plan_markdown(
        project_name, subtask_name, task, payload, debate_summary
    )
    plan_file.write_text(md_content, encoding="utf-8")

    # DB: insert checklist items
    for i, t in enumerate(payload.tasks):
        db.add_checklist_item(
            plan_id=plan_id,
            task_id_in_plan=t.task_id,
            description=t.description,
            keywords=t.keywords,
            file_target=t.file,
            sort_order=i,
        )

    # Mark plan as in_progress (ready for execution)
    db.update_plan_status(plan_id, "in_progress")

    return plan_id, str(plan_file)


def list_plans(db: Database) -> list[dict]:
    """List all projects, subtasks, and their plans."""
    result = []
    for project in db.list_projects():
        subtasks = db.list_subtasks(project["id"])
        for sub in subtasks:
            result.append(
                {
                    "project": project["name"],
                    "subtask": sub["name"],
                    "status": sub["status"],
                }
            )
    return result


def get_plan_summary(db: Database, plan_id: int) -> dict | None:
    plan = db.get_plan(plan_id)
    if not plan:
        return None
    checklist = db.get_plan_checklist(plan_id)
    done = sum(1 for i in checklist if i["status"] == "done")
    return {
        "plan_id": plan_id,
        "status": plan["status"],
        "plan_file_path": plan["plan_file_path"],
        "checklist_done": done,
        "checklist_total": len(checklist),
        "items": [
            {
                "id": i["id"],
                "description": i["description"],
                "file": i["file_target"],
                "status": i["status"],
            }
            for i in checklist
        ],
    }
