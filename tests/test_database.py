"""Tests for Database, migrations, and all query methods."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from tessera.core.database import Database
from tessera.core.migrations import run_migrations, MIGRATIONS


@pytest.fixture
def db(tmp_path):
    return Database(str(tmp_path))


# ── Migration tests ─────────────────────────────────────────────────────────

def test_migration_fresh_db(tmp_path):
    db = Database(str(tmp_path))
    import sqlite3
    conn = sqlite3.connect(str(tmp_path / ".tessera" / "tessera.db"))
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == len(MIGRATIONS)
    conn.close()


def test_migration_idempotent(tmp_path):
    Database(str(tmp_path))
    # Second open should not re-run migrations
    db2 = Database(str(tmp_path))
    assert db2.get_stats()["files"] == 0


def test_all_tables_created(db):
    tables = {
        r[0] for r in db._execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    expected = {
        "files", "symbols", "edges", "sessions", "actions",
        "decisions", "decisions_archive", "retrieval_cache",
        "projects", "subtasks", "plans", "plan_checklist", "token_savings",
    }
    assert expected.issubset(tables)


# ── Session tests ─────────────────────────────────────────────────────────────

def test_get_or_create_session_creates(db, tmp_path):
    sid = db.get_or_create_session(str(tmp_path))
    assert sid
    # Second call returns same session
    sid2 = db.get_or_create_session(str(tmp_path))
    assert sid == sid2


def test_create_new_session_is_unique(db, tmp_path):
    sid1 = db.get_or_create_session(str(tmp_path))
    sid2 = db.create_new_session(str(tmp_path))
    assert sid1 != sid2


# ── File tests ──────────────────────────────────────────────────────────────

def test_upsert_file_and_retrieve(db):
    fid = db.upsert_file("src/main.py", ".py", "python", 100, "abc123", "entry point", ["main", "run"], "code")
    assert fid > 0
    row = db.get_file_by_path("src/main.py")
    assert row is not None
    assert row["extension"] == ".py"
    assert row["content_hash"] == "abc123"


def test_upsert_file_updates_on_conflict(db):
    db.upsert_file("src/main.py", ".py", "python", 100, "aaa", "old summary", [], "code")
    db.upsert_file("src/main.py", ".py", "python", 200, "bbb", "new summary", [], "code")
    row = db.get_file_by_path("src/main.py")
    assert row["content_hash"] == "bbb"
    assert row["summary"] == "new summary"


def test_get_all_files(db):
    db.upsert_file("a.py", ".py", "python", 10, "h1", "", [], "code")
    db.upsert_file("b.py", ".py", "python", 10, "h2", "", [], "code")
    files = db.get_all_files()
    assert len(files) == 2


def test_delete_file(db):
    db.upsert_file("del.py", ".py", "python", 10, "h", "", [], "code")
    db.delete_file("del.py")
    assert db.get_file_by_path("del.py") is None


# ── Symbol tests ─────────────────────────────────────────────────────────────

def test_upsert_and_get_symbols(db):
    fid = db.upsert_file("f.py", ".py", "python", 10, "h", "", [], "code")
    db.upsert_symbol(fid, "foo", "function", 1, 5, "hash1", "def foo()", True, "high")
    syms = db.get_symbols_for_file(fid)
    assert len(syms) == 1
    assert syms[0]["name"] == "foo"


def test_delete_symbols_for_file(db):
    fid = db.upsert_file("f.py", ".py", "python", 10, "h", "", [], "code")
    db.upsert_symbol(fid, "foo", "function", 1, 5, "hash1")
    db.delete_symbols_for_file(fid)
    assert db.get_symbols_for_file(fid) == []


# ── Edge tests ──────────────────────────────────────────────────────────────

def test_add_and_get_edges(db):
    fid = db.upsert_file("a.py", ".py", "python", 10, "h", "", [], "code")
    db.add_edge(fid, "b.py", "imports", "utils")
    edges = db.get_edges_from(fid)
    assert len(edges) == 1
    assert edges[0]["to_path"] == "b.py"


def test_edges_to(db):
    fid = db.upsert_file("a.py", ".py", "python", 10, "h", "", [], "code")
    db.upsert_file("b.py", ".py", "python", 10, "h2", "", [], "code")
    db.add_edge(fid, "b.py", "imports", "b")
    incoming = db.get_edges_to("b.py")
    assert len(incoming) == 1
    assert incoming[0]["from_path"] == "a.py"


# ── Action tests ─────────────────────────────────────────────────────────────

def test_record_and_get_actions(db, tmp_path):
    sid = db.get_or_create_session(str(tmp_path))
    db.record_action(sid, "graph_read", "src/main.py", query="what does this do")
    actions = db.get_session_actions(sid)
    assert len(actions) == 1
    assert actions[0]["action_type"] == "graph_read"


def test_search_action_history(db, tmp_path):
    sid = db.get_or_create_session(str(tmp_path))
    db.record_action(sid, "graph_read", "src/auth.py", query="authentication flow")
    db.record_action(sid, "graph_read", "src/main.py", query="entry point")
    results = db.search_action_history(sid, ["auth"])
    assert len(results) >= 1


def test_clear_action_graph(db, tmp_path):
    sid = db.get_or_create_session(str(tmp_path))
    db.record_action(sid, "graph_read", "src/main.py")
    db.add_decision(sid, "Use JWT for auth")
    db.clear_action_graph(sid)
    assert db.get_session_actions(sid) == []
    assert db.get_decisions(session_id=sid) == []


# ── Decision tests ────────────────────────────────────────────────────────────

def test_add_and_get_decisions(db, tmp_path):
    sid = db.get_or_create_session(str(tmp_path))
    db.add_decision(sid, "Use SQLite", ["db.py"], "project")
    decisions = db.get_decisions(session_id=sid)
    assert len(decisions) == 1
    assert decisions[0]["summary"] == "Use SQLite"


def test_decisions_rolling_window(db, tmp_path):
    sid = db.get_or_create_session(str(tmp_path))
    from tessera.core.config import MAX_DECISIONS
    for i in range(MAX_DECISIONS + 5):
        db.add_decision(sid, f"Decision {i}")
    decisions = db.get_decisions(session_id=sid, limit=1000)
    assert len(decisions) <= MAX_DECISIONS


# ── Retrieval cache tests ─────────────────────────────────────────────────────

def test_cache_and_retrieve(db, tmp_path):
    fid = db.upsert_file("src/a.py", ".py", "python", 100, "hash1", "", [], "code")
    results = [{"path": "src/a.py", "score": 5.0}]
    db.cache_retrieval("what is auth", results, {"src/a.py": "hash1"})
    cached = db.get_cached_retrieval("what is auth")
    assert cached is not None
    assert cached[0]["path"] == "src/a.py"


def test_cache_invalidated_on_hash_change(db, tmp_path):
    db.upsert_file("src/a.py", ".py", "python", 100, "hash1", "", [], "code")
    results = [{"path": "src/a.py", "score": 5.0}]
    db.cache_retrieval("query", results, {"src/a.py": "hash1"})
    # Update hash
    db.upsert_file("src/a.py", ".py", "python", 100, "hash2", "", [], "code")
    cached = db.get_cached_retrieval("query")
    assert cached is None


def test_cache_invalidate_for_files(db, tmp_path):
    db.upsert_file("src/a.py", ".py", "python", 100, "h1", "", [], "code")
    db.cache_retrieval("q", [{"path": "src/a.py"}], {"src/a.py": "h1"})
    db.invalidate_cache_for_files(["src/a.py"])
    # Cache entry deleted (even though hash matches — we force-delete)
    rows = db._execute("SELECT COUNT(*) FROM retrieval_cache").fetchone()[0]
    assert rows == 0


def test_cache_ttl_expiry(db, tmp_path):
    db.upsert_file("f.py", ".py", "python", 10, "h", "", [], "code")
    db.cache_retrieval("q", [{"path": "f.py"}], {"f.py": "h"})
    # TTL of 0 should always expire
    cached = db.get_cached_retrieval("q", ttl=0)
    assert cached is None


# ── Plan archive tests ────────────────────────────────────────────────────────

def test_create_project_and_subtask(db):
    pid = db.create_project("myproject")
    assert pid > 0
    sid = db.create_subtask(pid, "auth-feature")
    assert sid > 0
    projects = db.list_projects()
    assert any(p["name"] == "myproject" for p in projects)


def test_save_and_get_plan(db):
    pid = db.create_project("proj")
    sid = db.create_subtask(pid, "sub")
    plan_id = db.save_plan(sid, '{"transcript": "text"}', "<plan/>", "/path/plan.md")
    plan = db.get_plan(plan_id)
    assert plan is not None
    assert plan["status"] == "pending"


def test_checklist_items(db):
    pid = db.create_project("proj")
    sid = db.create_subtask(pid, "sub")
    plan_id = db.save_plan(sid, "", "<plan/>", "/path/plan.md")
    db.add_checklist_item(plan_id, "1", "Create auth middleware", ["jwt", "middleware"], "src/auth.py", 0)
    items = db.get_plan_checklist(plan_id)
    assert len(items) == 1
    assert items[0]["status"] == "pending"


def test_auto_check_by_file_and_keywords(db):
    pid = db.create_project("p")
    sid = db.create_subtask(pid, "s")
    plan_id = db.save_plan(sid, "", "<plan/>", "/tmp/plan.md")
    db.add_checklist_item(plan_id, "1", "Add JWT middleware", ["jwt", "middleware"], "src/auth.py", 0)

    # Match: correct file AND keyword
    matched = db.auto_check_by_file_and_keywords(plan_id, "src/auth.py", ["jwt"])
    assert len(matched) == 1

    # No match: correct file but wrong keywords
    matched2 = db.auto_check_by_file_and_keywords(plan_id, "src/auth.py", ["unrelated"])
    assert len(matched2) == 0

    # No match: wrong file
    matched3 = db.auto_check_by_file_and_keywords(plan_id, "src/other.py", ["jwt"])
    assert len(matched3) == 0


# ── Token savings tests ────────────────────────────────────────────────────────

def test_record_token_savings(db, tmp_path):
    sid = db.get_or_create_session(str(tmp_path))
    db.record_token_savings(sid, 1, files_skipped=3, chars_saved=1000, chars_read_total=500)
    rows = db.get_token_savings(sid)
    assert len(rows) == 1
    assert rows[0]["chars_saved"] == 1000


# ── Stats ────────────────────────────────────────────────────────────────────

def test_get_stats(db, tmp_path):
    db.upsert_file("f.py", ".py", "python", 10, "h", "", [], "code")
    db.get_or_create_session(str(tmp_path))
    stats = db.get_stats()
    assert stats["files"] >= 1
    assert stats["sessions"] >= 1
