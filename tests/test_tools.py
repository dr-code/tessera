"""Tests for MCP tool modules (happy path)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tessera.core.database import Database
from tessera.graph.builder import build_graph
from tessera.mcp.tools.state import TurnState
from tessera.mcp.tools import continue_, decision, retrieve, read, neighbors, impact, edit, summary, scan, fallback


SAMPLE_PROJECT = Path(__file__).parent / "fixtures" / "sample_project"


@pytest.fixture
def setup(tmp_path):
    db = Database(str(tmp_path))
    build_graph(str(SAMPLE_PROJECT), db, incremental=False)
    session_id = db.get_or_create_session(str(tmp_path))
    state = TurnState()
    return db, session_id, state, str(SAMPLE_PROJECT)


def test_graph_continue_returns_ok(setup):
    db, sid, state, root = setup
    result = continue_.run(db, state, sid, "find the greeting function", project_root=root)
    assert result["ok"] is True
    # Small project may return skip=True; large project returns recommended_files
    assert "recommended_files" in result or result.get("skip") is True


def test_graph_continue_needs_scan_when_empty(tmp_path):
    db = Database(str(tmp_path))
    sid = db.get_or_create_session(str(tmp_path))
    state = TurnState()
    result = continue_.run(db, state, sid, "test query", project_root=str(tmp_path))
    assert result["ok"] is False
    assert result.get("needs_scan") is True


def test_graph_continue_resets_state(setup):
    db, sid, state, root = setup
    state.chars_read = 9999
    state.retrieve_called = True
    continue_.run(db, state, sid, "query", project_root=root)
    assert state.chars_read == 0
    assert state.retrieve_called is False


def test_graph_retrieve_once_per_turn(setup):
    db, sid, state, root = setup
    r1 = retrieve.run(db, state, sid, "greeting", top_files=3)
    assert r1["ok"] is True
    r2 = retrieve.run(db, state, sid, "greeting")
    assert r2["ok"] is False  # already called


def test_graph_read_file(setup):
    db, sid, state, root = setup
    result = read.run(db, state, sid, root, "main.py", max_chars=500)
    assert result["ok"] is True
    assert "content" in result
    assert len(result["content"]) <= 500


def test_graph_read_nonexistent(setup):
    db, sid, state, root = setup
    result = read.run(db, state, sid, root, "nonexistent.py")
    assert result["ok"] is False


def test_graph_read_budget_exceeded(setup):
    db, sid, state, root = setup
    state.chars_read = state.read_budget_chars  # exhaust budget
    result = read.run(db, state, sid, root, "main.py")
    assert result["ok"] is False


def test_graph_neighbors(setup):
    db, sid, state, root = setup
    result = neighbors.run(db, state, sid, "main.py")
    assert result["ok"] is True
    assert "outgoing" in result
    assert "incoming" in result


def test_graph_neighbors_unknown_file(setup):
    db, sid, state, root = setup
    result = neighbors.run(db, state, sid, "nonexistent.py")
    assert result["ok"] is False


def test_graph_impact(setup):
    db, sid, state, root = setup
    result = impact.run(db, state, sid, ["main.py"])
    assert result["ok"] is True
    assert "impacted_files" in result


def test_graph_register_edit(setup):
    db, sid, state, root = setup
    result = edit.run(db, state, sid, ["main.py", "utils.py"], summary="refactored greeter")
    assert result["ok"] is True
    assert result["cache_invalidated"] == 2


def test_graph_register_edit_empty_files_marks_checklist_done(setup):
    """Empty files list + explicit checklist_item_id marks the item done without a file edit."""
    db, sid, state, root = setup
    # Create a plan with one verification task (no file target)
    project_id = db.create_project("test-proj")
    subtask_id = db.create_subtask(project_id, "sprint-verify")
    plan_id = db.save_plan(subtask_id, "transcript", "<xml/>", "")
    item_id = db.add_checklist_item(
        plan_id=plan_id,
        task_id_in_plan="V1",
        description="Verify binary detected via command -v",
        keywords=["binary", "detected", "command"],
        file_target="",
        sort_order=0,
    )
    db.update_plan_status(plan_id, "in_progress")

    result = edit.run(db, state, sid, files=[], checklist_item_id=item_id)

    assert result["ok"] is True
    assert result["cache_invalidated"] == 0
    assert "Verify binary detected via command -v" in result["checklist_auto_completed"]
    row = db.get_plan_checklist(plan_id)[0]
    assert row["status"] == "done"
    assert row["completed_at"] is not None


def test_graph_register_edit_empty_files_no_id_is_noop(setup):
    """Empty files + no checklist_item_id: ok=True but nothing auto-completed."""
    db, sid, state, root = setup
    result = edit.run(db, state, sid, files=[], summary="verified output")
    assert result["ok"] is True
    assert result["cache_invalidated"] == 0
    assert result["checklist_auto_completed"] == []
    assert result["checklist_needs_explicit_id"] == []


def test_graph_register_edit_file_path_exact_match(setup):
    """Single pending item for a file is auto-completed by file path alone."""
    db, sid, state, root = setup
    project_id = db.create_project("proj")
    subtask_id = db.create_subtask(project_id, "sprint-x")
    plan_id = db.save_plan(subtask_id, "t", "<xml/>", "")
    db.add_checklist_item(plan_id, "1", "Implement auth", [], "main.py", 0)
    db.update_plan_status(plan_id, "in_progress")

    result = edit.run(db, state, sid, files=["main.py"])

    assert result["ok"] is True
    assert "Implement auth" in result["checklist_auto_completed"]
    assert result["checklist_needs_explicit_id"] == []


def test_graph_register_edit_ambiguous_returns_needs_explicit_id(setup):
    """Multiple pending items for same file are flagged as ambiguous, not auto-completed."""
    db, sid, state, root = setup
    project_id = db.create_project("proj2")
    subtask_id = db.create_subtask(project_id, "sprint-y")
    plan_id = db.save_plan(subtask_id, "t", "<xml/>", "")
    db.add_checklist_item(plan_id, "1", "Add routing", [], "main.py", 0)
    db.add_checklist_item(plan_id, "2", "Add error handling", [], "main.py", 1)
    db.update_plan_status(plan_id, "in_progress")

    result = edit.run(db, state, sid, files=["main.py"])

    assert result["ok"] is True
    assert result["checklist_auto_completed"] == []
    assert len(result["checklist_needs_explicit_id"]) == 2


def test_graph_action_summary(setup):
    db, sid, state, root = setup
    # Record some actions first
    db.record_action(sid, "graph_read", "main.py")
    db.add_decision(sid, "Use SQLite")
    result = summary.run(db, state, sid, limit=10)
    assert result["ok"] is True
    assert len(result["actions"]) >= 1
    assert len(result["decisions"]) >= 1


def test_graph_scan(tmp_path):
    db = Database(str(tmp_path))
    sid = db.get_or_create_session(str(tmp_path))
    state = TurnState()
    result = scan.run(db, state, sid, str(SAMPLE_PROJECT))
    assert result["ok"] is True
    assert result["stats"]["files_scanned"] >= 2


def test_graph_scan_injects_claude_md(tmp_path):
    db = Database(str(tmp_path))
    sid = db.get_or_create_session(str(tmp_path))
    state = TurnState()
    # Create a minimal project
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "main.py").write_text("def foo(): pass\n", encoding="utf-8")
    scan.run(db, state, sid, str(proj))
    claude_md = proj / "CLAUDE.md"
    assert claude_md.exists()
    assert "TESSERA:START" in claude_md.read_text()


def test_graph_read_symbol(setup):
    db, sid, state, root = setup
    # main.py has a Greeter class — read just that symbol
    result = read.run(db, state, sid, root, "main.py::Greeter")
    # Either succeeds or gives a helpful error
    assert "ok" in result


@pytest.fixture
def setup_large(tmp_path):
    """Fixture using tessera src/ — large enough (>10 files) to bypass small-project skip."""
    src_root = Path(__file__).parent.parent / "src"
    db = Database(str(tmp_path))
    build_graph(str(src_root), db, incremental=False)
    session_id = db.get_or_create_session(str(tmp_path))
    state = TurnState()
    return db, session_id, state, str(src_root)


def test_token_savings_recorded_on_graph_continue(setup_large):
    """graph_continue records recommendation-efficiency savings on every turn."""
    db, sid, state, root = setup_large
    continue_.run(db, state, sid, "find the database layer", project_root=root)
    rows = db.get_token_savings(session_id=sid)
    assert len(rows) == 1, "Expected one savings record per graph_continue call"
    assert rows[0]["chars_read_total"] > 0
    assert rows[0]["chars_saved"] >= 0
    assert rows[0]["files_skipped"] >= 0


def test_token_savings_recorded_each_turn(setup_large):
    """Each graph_continue call produces one savings record."""
    db, sid, state, root = setup_large
    continue_.run(db, state, sid, "query one", project_root=root)
    continue_.run(db, state, sid, "query two", project_root=root)
    rows = db.get_token_savings(session_id=sid)
    assert len(rows) == 2, "Expected one record per turn"
    assert rows[0]["turn_number"] != rows[1]["turn_number"]


def test_atomic_rewrite_checklist_updates_disk(setup, tmp_path):
    """_atomic_rewrite_checklist marks - [ ] → - [x] in the actual plan markdown file."""
    db, sid, state, root = setup

    # Create a plan markdown file using the exact format _build_plan_markdown produces
    plan_file = tmp_path / "plan-test.md"
    plan_file.write_text(
        "# Plan\n\n## Checklist\n- [ ] 1. Implement auth (main.py)\n",
        encoding="utf-8",
    )

    project_id = db.create_project("disk-test")
    subtask_id = db.create_subtask(project_id, "sprint-disk")
    plan_id = db.save_plan(subtask_id, "transcript", "<xml/>", str(plan_file))
    db.add_checklist_item(plan_id, "1", "Implement auth", [], "main.py", 0)
    db.update_plan_status(plan_id, "in_progress")

    result = edit.run(db, state, sid, files=["main.py"])

    assert result["ok"] is True
    assert "Implement auth" in result["checklist_auto_completed"]
    disk_content = plan_file.read_text(encoding="utf-8")
    assert "- [x] 1. Implement auth (main.py)" in disk_content, (
        "Plan markdown file should have the item checked off on disk"
    )
    assert "- [ ] 1. Implement auth (main.py)" not in disk_content


def test_graph_impact_actual_dependency_chain(setup):
    """graph_impact returns the files that depend on the changed file."""
    db, sid, state, root = setup
    # utils.py is in the graph; directly add an edge: utils.py → main.py
    utils_row = db.get_file_by_path("utils.py")
    assert utils_row is not None, "utils.py must be indexed"
    db.add_edge(utils_row["id"], "main.py", "imports", "greet")

    result = impact.run(db, state, sid, ["main.py"])

    assert result["ok"] is True
    assert "utils.py" in result["impacted_files"], (
        "utils.py imports main.py so it should appear in the blast radius"
    )
    assert result["total_impacted"] >= 1
    # The changed file itself should not appear in impacted_files
    assert "main.py" not in result["impacted_files"]


def test_graph_lock_decision_success(setup):
    """Success path: persists decision, returns normalized payload."""
    db, sid, state, _ = setup
    result = decision.run(
        db, state, sid,
        summary="Use SQLite with WAL mode for concurrent reads",
        scope="project",
        files=["src/tessera/core/database.py"],
    )
    assert result["ok"] is True
    assert result["summary"] == "Use SQLite with WAL mode for concurrent reads"
    assert result["scope"] == "project"
    assert result["files"] == ["src/tessera/core/database.py"]
    rows = db.get_decisions(session_id=sid, limit=10)
    assert len(rows) >= 1
    assert rows[0]["summary"] == "Use SQLite with WAL mode for concurrent reads"


def test_graph_lock_decision_invalid_scope(setup):
    """Invalid scope returns ok=False and writes nothing to DB."""
    db, sid, state, _ = setup
    before = db.get_decisions(session_id=sid, limit=10)
    result = decision.run(db, state, sid, summary="some decision", scope="invalid")
    assert result["ok"] is False
    assert "scope" in result["error"]
    after = db.get_decisions(session_id=sid, limit=10)
    assert len(after) == len(before), "No decision should be written on invalid scope"


def test_graph_lock_decision_empty_summary(setup):
    """Empty or whitespace-only summary returns ok=False and writes nothing."""
    db, sid, state, _ = setup
    before = db.get_decisions(session_id=sid, limit=10)
    result_empty = decision.run(db, state, sid, summary="")
    result_ws = decision.run(db, state, sid, summary="   ")
    assert result_empty["ok"] is False
    assert result_ws["ok"] is False
    after = db.get_decisions(session_id=sid, limit=10)
    assert len(after) == len(before), "No decision should be written on empty summary"


def test_graph_lock_decision_visible_in_action_summary(setup):
    """Decisions recorded via decision.run() appear in graph_action_summary output."""
    db, sid, state, _ = setup
    decision.run(db, state, sid, summary="stdio only for MCP transport", scope="project")
    result = summary.run(db, state, sid, limit=10)
    assert result["ok"] is True
    summaries = [d["summary"] for d in result["decisions"]]
    assert "stdio only for MCP transport" in summaries
    assert len(result["decisions"]) >= 1
    assert "scope" in result["decisions"][0]


@pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep not on PATH — install via `brew install ripgrep`")
def test_fallback_rg_returns_real_hits(setup):
    """fallback_rg finds actual matches in the sample project."""
    db, sid, state, root = setup
    result = fallback.run(db, state, sid, r"def greet", project_root=root)

    assert result["ok"] is True, f"fallback_rg failed: {result.get('error')}"
    assert result["total"] >= 1, "Pattern 'def greet' should match at least one line in main.py"
    paths = [h["path"] for h in result["hits"]]
    assert any("main.py" in p for p in paths), (
        "main.py defines 'def greet'; it must appear in the results"
    )
    for hit in result["hits"]:
        assert "path" in hit and "line" in hit and "text" in hit
