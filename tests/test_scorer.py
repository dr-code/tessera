"""Tests for the retrieval scorer."""

from __future__ import annotations

import pytest

from tessera.core.database import Database
from tessera.graph.scorer import classify_intent, score_files


@pytest.fixture
def db_with_files(tmp_path):
    db = Database(str(tmp_path))
    db.upsert_file("src/auth.py", ".py", "python", 200, "h1", "JWT authentication middleware", ["jwt", "auth", "token"], "logic")
    db.upsert_file("src/main.py", ".py", "python", 100, "h2", "Entry point", ["main", "run", "app"], "code")
    db.upsert_file("README.md", ".md", "markdown", 500, "h3", "Project documentation", ["overview", "install"], "docs")
    db.upsert_file("tests/test_auth.py", ".py", "python", 150, "h4", "Auth test suite", ["test", "auth", "jwt"], "test")
    return db


def test_classify_intent_debug():
    assert classify_intent("fix the bug in auth") == "debug"


def test_classify_intent_test():
    assert classify_intent("write tests for the API") == "test"


def test_classify_intent_feature():
    assert classify_intent("add JWT authentication") == "feature"


def test_classify_intent_general():
    assert classify_intent("some random thing") == "general"


def test_score_files_returns_top_n(db_with_files):
    scored = score_files(db_with_files, "JWT authentication", top_n=2)
    assert len(scored) <= 2


def test_score_files_auth_query_returns_auth_file(db_with_files):
    scored = score_files(db_with_files, "JWT authentication middleware", top_n=5)
    assert len(scored) > 0
    # auth.py should be near the top
    top_paths = [s.path for s in scored[:3]]
    assert any("auth" in p for p in top_paths)


def test_score_files_docs_penalized_for_debug(db_with_files):
    scored = score_files(db_with_files, "fix crash in authentication", top_n=5)
    readme = next((s for s in scored if "README" in s.path), None)
    auth = next((s for s in scored if "auth.py" in s.path), None)
    if readme and auth:
        assert auth.score >= readme.score


def test_score_files_empty_db(tmp_path):
    db = Database(str(tmp_path))
    scored = score_files(db, "anything", top_n=5)
    assert scored == []


def test_score_files_symbol_boost(tmp_path):
    db = Database(str(tmp_path))
    fid = db.upsert_file("src/auth.py", ".py", "python", 100, "h", "auth module", ["auth"], "logic")
    db.upsert_symbol(fid, "verify_jwt", "function", 1, 10, "hashA", exported=True, confidence="high")
    scored = score_files(db, "verify_jwt", top_n=3)
    assert len(scored) > 0
    assert scored[0].path == "src/auth.py"
