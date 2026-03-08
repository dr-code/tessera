"""Tests for the file scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from tessera.graph.scanner import (
    FileInfo,
    _classify_role,
    _content_hash,
    _extract_keywords,
    _extract_summary,
    scan_file,
    walk_project,
)


SAMPLE_PROJECT = Path(__file__).parent / "fixtures" / "sample_project"


def test_content_hash_consistent():
    data = b"hello world"
    assert _content_hash(data) == _content_hash(data)
    assert len(_content_hash(data)) == 8


def test_content_hash_differs():
    assert _content_hash(b"abc") != _content_hash(b"xyz")


def test_extract_summary_python():
    content = '"""This is the docstring."""\n\ndef foo(): pass\n'
    p = Path("src/main.py")
    summary = _extract_summary(content, p)
    assert "docstring" in summary


def test_extract_summary_markdown():
    content = "# My Module\n\nSome text\n"
    summary = _extract_summary(content, Path("README.md"))
    assert "My Module" in summary


def test_extract_keywords_python():
    content = "def my_function(): pass\nclass MyClass: pass\n"
    kw = _extract_keywords(content, Path("src/x.py"))
    assert "my_function" in kw
    assert "MyClass" in kw


def test_classify_role_docs():
    role = _classify_role(Path("README.md"), "")
    assert role == "docs"


def test_classify_role_test():
    role = _classify_role(Path("tests/test_foo.py"), "")
    assert role == "test"


def test_classify_role_code():
    role = _classify_role(Path("src/main.py"), "")
    assert role in ("code", "logic", "shared_ui")


def test_scan_file_python(tmp_path):
    f = tmp_path / "hello.py"
    f.write_text('"""A module."""\n\ndef hello(): pass\n', encoding="utf-8")
    info = scan_file(f, tmp_path)
    assert info is not None
    assert info.extension == ".py"
    assert info.language == "python"
    assert "hello" in info.keywords
    assert info.content_hash


def test_scan_file_missing_returns_none(tmp_path):
    result = scan_file(tmp_path / "nonexistent.py", tmp_path)
    assert result is None


def test_walk_project_finds_files():
    infos = list(walk_project(str(SAMPLE_PROJECT)))
    paths = [i.path for i in infos]
    assert any("main.py" in p for p in paths)
    assert any("utils.py" in p for p in paths)


def test_walk_project_skips_unsupported(tmp_path):
    (tmp_path / "binary.exe").write_bytes(b"\x00\x01")
    (tmp_path / "main.py").write_text("print('hi')", encoding="utf-8")
    infos = list(walk_project(str(tmp_path)))
    assert all(i.extension != ".exe" for i in infos)


def test_walk_project_skips_pycache(tmp_path):
    cache_dir = tmp_path / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "foo.pyc").write_bytes(b"")
    (tmp_path / "main.py").write_text("print('hi')", encoding="utf-8")
    infos = list(walk_project(str(tmp_path)))
    assert all("__pycache__" not in i.path for i in infos)
