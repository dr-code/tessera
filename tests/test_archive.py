"""Tests for the Plan Archive module."""

from __future__ import annotations

from pathlib import Path

import pytest

from tessera.core.database import Database
from tessera.debate.payload import parse_xml
from tessera.plans.archive import save_plan, save_raw_plan, list_plans, get_plan_summary


SAMPLE_XML = (Path(__file__).parent / "fixtures" / "sample_plan.xml").read_text()


@pytest.fixture
def db(tmp_path):
    return Database(str(tmp_path))


def test_save_plan_creates_db_record(db, tmp_path):
    payload = parse_xml(SAMPLE_XML)
    plan_id, plan_path = save_plan(
        db=db,
        project_root=str(tmp_path),
        project_name="myproject",
        subtask_name="jwt-auth",
        task="Add JWT authentication",
        debate_transcript_text='{"rounds": 3}',
        payload=payload,
    )
    assert plan_id > 0
    plan = db.get_plan(plan_id)
    assert plan is not None
    assert plan["status"] == "in_progress"


def test_save_plan_creates_disk_file(db, tmp_path):
    payload = parse_xml(SAMPLE_XML)
    plan_id, plan_path = save_plan(
        db=db,
        project_root=str(tmp_path),
        project_name="myproject",
        subtask_name="jwt-auth",
        task="Add JWT authentication",
        debate_transcript_text="{}",
        payload=payload,
    )
    assert Path(plan_path).exists()
    content = Path(plan_path).read_text()
    assert "Add JWT authentication" in content
    assert "- [ ]" in content  # Checklist items


def test_save_plan_populates_checklist(db, tmp_path):
    payload = parse_xml(SAMPLE_XML)
    plan_id, _ = save_plan(
        db=db,
        project_root=str(tmp_path),
        project_name="p",
        subtask_name="s",
        task="Add JWT",
        debate_transcript_text="{}",
        payload=payload,
    )
    checklist = db.get_plan_checklist(plan_id)
    assert len(checklist) == 3
    assert all(i["status"] == "pending" for i in checklist)


def test_list_plans_returns_all(db, tmp_path):
    payload = parse_xml(SAMPLE_XML)
    save_plan(db=db, project_root=str(tmp_path), project_name="proj", subtask_name="t1",
              task="T1", debate_transcript_text="{}", payload=payload)
    save_plan(db=db, project_root=str(tmp_path), project_name="proj", subtask_name="t2",
              task="T2", debate_transcript_text="{}", payload=payload)
    plans = list_plans(db)
    assert len(plans) >= 2


def test_get_plan_summary(db, tmp_path):
    payload = parse_xml(SAMPLE_XML)
    plan_id, _ = save_plan(db=db, project_root=str(tmp_path), project_name="p",
                           subtask_name="s", task="T", debate_transcript_text="{}",
                           payload=payload)
    s = get_plan_summary(db, plan_id)
    assert s is not None
    assert s["checklist_total"] == 3
    assert s["checklist_done"] == 0


def test_save_plan_rejects_project_name_that_escapes_plans_dir(db, tmp_path):
    """A crafted project_name sharing a prefix with 'plans' must not be treated as contained.

    e.g. project_name="../plans_evil" resolves to a sibling of .tessera/plans/
    whose name happens to start with the string "plans" — a naive str.startswith
    check on the un-terminated prefix would wrongly accept this as "inside".
    """
    payload = parse_xml(SAMPLE_XML)
    with pytest.raises(ValueError, match="escapes"):
        save_plan(
            db=db,
            project_root=str(tmp_path),
            project_name="../plans_evil",
            subtask_name="x",
            task="T",
            debate_transcript_text="{}",
            payload=payload,
        )
    assert not (tmp_path / ".tessera" / "plans_evil").exists()


def test_save_raw_plan_rejects_project_name_that_escapes_plans_dir(db, tmp_path):
    with pytest.raises(ValueError, match="escapes"):
        save_raw_plan(
            db=db,
            project_root=str(tmp_path),
            project_name="../plans_evil",
            subtask_name="x",
            plan_markdown="# plan",
            checklist_items=[],
        )
    assert not (tmp_path / ".tessera" / "plans_evil").exists()


def test_save_plan_writes_file_before_db_row_exists(db, tmp_path):
    """The plan file must exist on disk by the time save_plan returns —
    verifies the write-before-DB-insert ordering (no orphaned DB rows)."""
    payload = parse_xml(SAMPLE_XML)
    plan_id, plan_path = save_plan(
        db=db,
        project_root=str(tmp_path),
        project_name="p",
        subtask_name="s",
        task="T",
        debate_transcript_text="{}",
        payload=payload,
    )
    plan = db.get_plan(plan_id)
    assert Path(plan["plan_file_path"]).exists()
    assert Path(plan_path).read_text(encoding="utf-8") != ""


def test_transcript_compressed_if_large(db, tmp_path):
    payload = parse_xml(SAMPLE_XML)
    large_transcript = "x" * 60000  # > 50KB
    plan_id, _ = save_plan(db=db, project_root=str(tmp_path), project_name="p",
                           subtask_name="s", task="T",
                           debate_transcript_text=large_transcript, payload=payload)
    plan = db.get_plan(plan_id)
    # Should be stored compressed
    assert plan["debate_transcript"].startswith("gz:")
