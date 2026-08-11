"""Failure-mode tests — missing files, corrupt DB, malformed input, API errors."""

from __future__ import annotations

import shutil

import pytest

from pathlib import Path

from tessera.core.database import Database
from tessera.mcp.tools.state import TurnState
from tessera.mcp.tools import continue_, retrieve, read, edit, fallback
from tessera.mcp.tools.fallback import _contained_paths


@pytest.fixture
def empty_db(tmp_path):
    db = Database(str(tmp_path))
    session_id = db.get_or_create_session(str(tmp_path))
    return db, session_id, TurnState(), str(tmp_path)


def test_continue_empty_graph_returns_needs_scan(empty_db):
    db, sid, state, root = empty_db
    result = continue_.run(db, state, sid, "test", project_root=root)
    assert result.get("needs_scan") is True or result.get("skip") is True


def test_read_nonexistent_file_returns_error(empty_db):
    db, sid, state, root = empty_db
    result = read.run(db, state, sid, root, "does_not_exist.py")
    assert result["ok"] is False
    assert "error" in result


def test_read_budget_enforced(empty_db):
    db, sid, state, root = empty_db
    # Create a file
    from pathlib import Path
    f = Path(root) / "big.py"
    f.write_text("x = 1\n" * 1000, encoding="utf-8")
    db.upsert_file("big.py", ".py", "python", 6000, "hbig", "", [], "code")
    state.chars_read = state.read_budget_chars
    result = read.run(db, state, sid, root, "big.py")
    assert result["ok"] is False


def test_retrieve_second_call_blocked(empty_db):
    db, sid, state, root = empty_db
    state.retrieve_called = True
    result = retrieve.run(db, state, sid, "query")
    assert result["ok"] is False


def test_fallback_rg_capped(empty_db):
    db, sid, state, root = empty_db
    # Force already-called state
    state.grep_calls = 1
    result = fallback.run(db, state, sid, "pattern", project_root=root)
    assert result["ok"] is False


def test_fallback_rg_rejects_paths_outside_project_root(empty_db):
    db, sid, state, root = empty_db
    result = fallback.run(
        db, state, sid, "pattern", paths=["/etc", "/"], project_root=root
    )
    assert result["ok"] is False
    assert "outside project_root" in result["error"]
    assert state.grep_calls == 1


def test_contained_paths_keeps_relative_paths_inside_root(tmp_path):
    (tmp_path / "sub").mkdir()
    kept = _contained_paths(["sub"], str(tmp_path))
    assert kept == [str((tmp_path / "sub").resolve())]


def test_contained_paths_keeps_absolute_paths_inside_root(tmp_path):
    inside = tmp_path / "sub"
    inside.mkdir()
    kept = _contained_paths([str(inside)], str(tmp_path))
    assert kept == [str(inside.resolve())]


def test_contained_paths_drops_absolute_paths_outside_root(tmp_path):
    kept = _contained_paths(["/etc", "/"], str(tmp_path))
    assert kept == []


def test_contained_paths_drops_relative_escape(tmp_path):
    kept = _contained_paths(["../../etc"], str(tmp_path))
    assert kept == []


def test_contained_paths_mixed_keeps_only_valid_ones(tmp_path):
    (tmp_path / "sub").mkdir()
    kept = _contained_paths(["sub", "/etc"], str(tmp_path))
    assert kept == [str((tmp_path / "sub").resolve())]


@pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep not on PATH — install via `brew install ripgrep`")
def test_fallback_rg_keeps_paths_inside_project_root(empty_db):
    db, sid, state, root = empty_db
    (Path(root) / "sub").mkdir()
    (Path(root) / "sub" / "f.py").write_text("def greet(): pass\n", encoding="utf-8")
    result = fallback.run(
        db, state, sid, "def greet", paths=["sub"], project_root=root
    )
    assert result["ok"] is True
    assert result["total"] == 1
    assert "f.py" in result["hits"][0]["path"]


def test_edit_with_empty_files(empty_db):
    db, sid, state, root = empty_db
    result = edit.run(db, state, sid, [], summary="nothing")
    assert result["ok"] is True
    assert result["files_registered"] == []


def test_read_symbol_not_in_index(empty_db, tmp_path):
    db, sid, state, root = empty_db
    # Create real file
    f = tmp_path / "mod.py"
    f.write_text("def existing(): pass\n", encoding="utf-8")
    db.upsert_file("mod.py", ".py", "python", 100, "h", "", [], "code")
    result = read.run(db, state, sid, root, "mod.py::NonExistentSymbol")
    assert "ok" in result
    # Either ok (line-search fallback) or ok:false with error
    if result["ok"]:
        assert "warning" in result or "content" in result
    else:
        assert "error" in result
