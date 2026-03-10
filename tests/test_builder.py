"""Tests for the graph builder."""

from __future__ import annotations

from pathlib import Path

import pytest

from tessera.core.database import Database
from tessera.graph.builder import build_graph


SAMPLE_PROJECT = Path(__file__).parent / "fixtures" / "sample_project"


@pytest.fixture
def db(tmp_path):
    return Database(str(tmp_path))


def test_build_graph_populates_files(db):
    stats = build_graph(str(SAMPLE_PROJECT), db)
    assert stats["files_scanned"] >= 2
    all_files = db.get_all_files()
    assert len(all_files) >= 2


def test_build_graph_populates_symbols(db):
    build_graph(str(SAMPLE_PROJECT), db)
    all_files = db.get_all_files()
    total_syms = 0
    for f in all_files:
        total_syms += len(db.get_symbols_for_file(f["id"]))
    assert total_syms > 0


def test_build_graph_incremental_skips_unchanged(db):
    # Full build
    stats1 = build_graph(str(SAMPLE_PROJECT), db)
    # Incremental: nothing changed
    stats2 = build_graph(str(SAMPLE_PROJECT), db, incremental=True)
    assert stats2["files_skipped"] == stats1["files_scanned"]
    assert stats2["files_scanned"] == 0


def test_build_graph_full_rescans_all(db):
    build_graph(str(SAMPLE_PROJECT), db)
    stats = build_graph(str(SAMPLE_PROJECT), db, incremental=False)
    assert stats["files_scanned"] >= 2
    assert stats["files_skipped"] == 0


def test_build_graph_empty_project(tmp_path, db):
    stats = build_graph(str(tmp_path), db)
    assert stats["files_scanned"] == 0


def test_build_graph_edges_extracted(db):
    build_graph(str(SAMPLE_PROJECT), db)
    # utils.py imports from main.py
    utils_row = db.get_file_by_path("utils.py")
    assert utils_row is not None, "utils.py should be indexed after build_graph"
    edges = db.get_edges_from(utils_row["id"])
    assert isinstance(edges, list), "get_edges_from should return a list"
    assert len(edges) >= 1, "utils.py should have at least one import edge"


def test_build_graph_with_modified_file(db, tmp_path):
    # Create a project with one file
    f = tmp_path / "hello.py"
    f.write_text("def original(): pass\n", encoding="utf-8")
    build_graph(str(tmp_path), db, incremental=False)

    # Modify the file
    f.write_text("def modified(): pass\n", encoding="utf-8")
    stats = build_graph(str(tmp_path), db, incremental=True)
    # File should be rescanned (hash changed)
    assert stats["files_scanned"] == 1
