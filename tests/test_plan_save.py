"""Tests for the plan_save MCP tool and save_raw_plan archive helper."""

from __future__ import annotations

from pathlib import Path

import pytest

from tessera.core.database import Database
from tessera.mcp.tools.plan_save import _parse_checklist, run
from tessera.plans.archive import save_raw_plan


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def db(tmp_path):
    return Database(str(tmp_path))


@pytest.fixture
def project_root(tmp_path):
    return str(tmp_path)


_SAMPLE_PLAN = """\
# My Feature Implementation Plan

**Goal:** Build the thing

## Task 1: Setup

**Files:**
- Create: `src/myapp/setup.py`
- Modify: `src/myapp/__init__.py`

- [ ] **Step 1:** Write the failing test
- [ ] **Step 2:** Implement minimal code

## Task 2: Validation

**Files:**
- Create: `src/myapp/validate.py`

- [ ] **Step 3:** Add validation logic
"""

_PLAN_NO_TASKS = """\
# Empty Plan

This plan has no checkboxes yet.
"""


# ── _parse_checklist unit tests ───────────────────────────────────────────────


def test_parse_checklist_extracts_correct_count():
    items = _parse_checklist(_SAMPLE_PLAN)
    assert len(items) == 3, f"expected 3 checklist items, got {len(items)}"


def test_parse_checklist_descriptions_are_correct():
    items = _parse_checklist(_SAMPLE_PLAN)
    descriptions = [item[1] for item in items]
    # The regex strips the **Step N:** bold prefix from descriptions
    assert descriptions[0] == "Write the failing test"
    assert descriptions[1] == "Implement minimal code"
    assert descriptions[2] == "Add validation logic"


def test_parse_checklist_file_targets_from_nearest_preceding_ref():
    items = _parse_checklist(_SAMPLE_PLAN)
    # Steps 1 and 2 are under Task 1; last file ref before them is __init__.py
    assert "myapp" in items[0][3] or items[0][3] == "src/myapp/__init__.py"
    # Step 3 is under Task 2; last file ref before it is validate.py
    assert "validate.py" in items[2][3]


def test_parse_checklist_empty_for_plan_without_tasks():
    items = _parse_checklist(_PLAN_NO_TASKS)
    assert items == [], f"expected empty list, got {items}"


def test_parse_checklist_returns_sequential_task_ids():
    items = _parse_checklist(_SAMPLE_PLAN)
    task_ids = [item[0] for item in items]
    assert task_ids == ["0", "1", "2"]


# ── save_raw_plan integration tests ──────────────────────────────────────────


def test_save_raw_plan_creates_db_record(db, project_root):
    checklist = [("0", "Do thing", ["do", "thing"], "src/foo.py")]
    plan_id, _ = save_raw_plan(
        db=db,
        project_root=project_root,
        project_name="test-project",
        subtask_name="test-subtask",
        plan_markdown=_SAMPLE_PLAN,
        checklist_items=checklist,
    )
    row = db.get_plan(plan_id)
    assert row is not None, "plan row should exist in DB"
    assert row["status"] == "in_progress"
    assert row["plan_file_path"].endswith(".md")


def test_save_raw_plan_writes_disk_file(db, project_root):
    checklist: list = []
    _, plan_file = save_raw_plan(
        db=db,
        project_root=project_root,
        project_name="proj",
        subtask_name="sub",
        plan_markdown=_SAMPLE_PLAN,
        checklist_items=checklist,
    )
    assert Path(plan_file).exists(), f"plan file not found at {plan_file}"
    content = Path(plan_file).read_text()
    assert "My Feature" in content


def test_save_raw_plan_inserts_checklist_items(db, project_root):
    checklist = [
        ("0", "Step one", ["step", "one"], "src/a.py"),
        ("1", "Step two", ["step", "two"], "src/b.py"),
        ("2", "Step three", ["step", "three"], "src/c.py"),
    ]
    plan_id, _ = save_raw_plan(
        db=db,
        project_root=project_root,
        project_name="proj",
        subtask_name="sub",
        plan_markdown=_SAMPLE_PLAN,
        checklist_items=checklist,
    )
    items = db.get_plan_checklist(plan_id)
    assert len(items) == 3, f"expected 3 checklist rows, got {len(items)}"
    assert items[0]["description"] == "Step one"
    assert items[2]["file_target"] == "src/c.py"


def test_save_raw_plan_empty_checklist_still_saves(db, project_root):
    plan_id, _ = save_raw_plan(
        db=db,
        project_root=project_root,
        project_name="proj",
        subtask_name="empty-sub",
        plan_markdown=_PLAN_NO_TASKS,
        checklist_items=[],
    )
    assert plan_id > 0
    items = db.get_plan_checklist(plan_id)
    assert items == []


def test_save_raw_plan_rejects_path_traversal(db, project_root):
    with pytest.raises(ValueError, match="path escapes"):
        save_raw_plan(
            db=db,
            project_root=project_root,
            project_name="../escape",
            subtask_name="sub",
            plan_markdown="content",
            checklist_items=[],
        )


# ── plan_save MCP tool tests ──────────────────────────────────────────────────


def test_plan_save_run_returns_ok(db, project_root):
    from tessera.mcp.tools.state import TurnState
    session_id = db.get_or_create_session(project_root)
    result = run(
        db=db,
        state=TurnState(),
        session_id=session_id,
        project_root=project_root,
        project_name="proj",
        subtask_name="sub",
        task="Build the thing",
        plan_markdown=_SAMPLE_PLAN,
    )
    assert result["ok"] is True
    assert result["plan_id"] > 0
    assert result["checklist_count"] == 3
    assert result["plan_file"].endswith(".md")


def test_plan_save_run_validates_required_fields(db, project_root):
    from tessera.mcp.tools.state import TurnState
    session_id = db.get_or_create_session(project_root)
    result = run(
        db=db,
        state=TurnState(),
        session_id=session_id,
        project_root=project_root,
        project_name="",
        subtask_name="sub",
        task="task",
        plan_markdown="content",
    )
    assert result["ok"] is False
    assert "project_name" in result["error"]


def test_plan_save_run_records_action(db, project_root):
    from tessera.mcp.tools.state import TurnState
    session_id = db.get_or_create_session(project_root)
    run(
        db=db,
        state=TurnState(),
        session_id=session_id,
        project_root=project_root,
        project_name="proj",
        subtask_name="sub",
        task="Do something",
        plan_markdown=_SAMPLE_PLAN,
    )
    actions = db.get_session_actions(session_id)
    plan_save_actions = [a for a in actions if a["action_type"] == "plan_save"]
    assert len(plan_save_actions) == 1, "expected one plan_save action recorded"
