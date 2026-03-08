"""Tests for compliance verifier."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from tessera.core.database import Database
from tessera.debate.payload import parse_xml
from tessera.compliance.verifier import verify, format_report
from tessera.plans.archive import save_plan


SAMPLE_XML = (Path(__file__).parent / "fixtures" / "sample_plan.xml").read_text()


@pytest.fixture
def db_with_plan(tmp_path):
    db = Database(str(tmp_path))
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
    return db, plan_id, str(tmp_path)


def test_verify_all_matched(db_with_plan):
    db, plan_id, root = db_with_plan
    changed = [
        "src/middleware/auth.py",
        "src/routes/user.py",
        "src/config.py",
    ]
    with patch("tessera.compliance.verifier._git_diff_files", return_value=changed):
        report = verify(db, root, plan_id=plan_id)
    assert len(report.matched) == 3
    assert len(report.missing) == 0
    assert len(report.extra) == 0


def test_verify_missing_file(db_with_plan):
    db, plan_id, root = db_with_plan
    # Only changed 2 of 3 declared files
    changed = ["src/middleware/auth.py", "src/routes/user.py"]
    with patch("tessera.compliance.verifier._git_diff_files", return_value=changed):
        report = verify(db, root, plan_id=plan_id)
    assert len(report.matched) == 2
    assert len(report.missing) == 1
    assert report.missing[0]["path"] == "src/config.py"


def test_verify_extra_files(db_with_plan):
    db, plan_id, root = db_with_plan
    changed = [
        "src/middleware/auth.py",
        "src/routes/user.py",
        "src/config.py",
        "package.json",  # not in plan
    ]
    with patch("tessera.compliance.verifier._git_diff_files", return_value=changed):
        report = verify(db, root, plan_id=plan_id)
    assert len(report.extra) == 1
    assert "package.json" in report.extra


def test_format_report_contains_symbols(db_with_plan):
    db, plan_id, root = db_with_plan
    with patch("tessera.compliance.verifier._git_diff_files",
               return_value=["src/middleware/auth.py"]):
        report = verify(db, root, plan_id=plan_id)
    text = format_report(report)
    assert "✓" in text or "matched" in text.lower()
    assert "✗" in text or "missing" in text.lower()


def test_verify_no_plan_raises(tmp_path):
    db = Database(str(tmp_path))
    with pytest.raises(ValueError, match="No active plan"):
        verify(db, str(tmp_path))


def test_verify_all_matched_completes_plan(db_with_plan):
    db, plan_id, root = db_with_plan
    # Mark plan as in_progress
    db.update_plan_status(plan_id, "in_progress")
    changed = ["src/middleware/auth.py", "src/routes/user.py", "src/config.py"]
    with patch("tessera.compliance.verifier._git_diff_files", return_value=changed):
        verify(db, root, plan_id=plan_id)
    plan = db.get_plan(plan_id)
    assert plan["status"] == "completed"
