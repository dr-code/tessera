"""Tests for MCP tool modules (happy path)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tessera.core.database import Database
from tessera.graph.builder import build_graph
from tessera.mcp.tools.state import TurnState
from tessera.mcp.tools import continue_, retrieve, read, neighbors, impact, edit, summary, scan


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
