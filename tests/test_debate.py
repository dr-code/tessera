"""Tests for debate engine, payload parser, and related modules."""

from __future__ import annotations

from pathlib import Path

import pytest

from tessera.debate.payload import parse_xml, build_xml, PlanTask


SAMPLE_XML = (Path(__file__).parent / "fixtures" / "sample_plan.xml").read_text()


def test_parse_xml_valid():
    payload = parse_xml(SAMPLE_XML)
    assert payload is not None
    assert payload.task == "Add JWT authentication"
    assert payload.rounds == 3
    assert payload.verdict == "approved"


def test_parse_xml_targets():
    payload = parse_xml(SAMPLE_XML)
    assert len(payload.targets) == 3
    paths = [t["path"] for t in payload.targets]
    assert "src/middleware/auth.py" in paths


def test_parse_xml_tasks():
    payload = parse_xml(SAMPLE_XML)
    assert len(payload.tasks) == 3
    assert payload.tasks[0].task_id == "1"
    assert "jwt" in payload.tasks[0].keywords


def test_parse_xml_validation():
    payload = parse_xml(SAMPLE_XML)
    assert len(payload.validation) >= 1


def test_parse_xml_invalid_returns_none():
    payload = parse_xml("not xml at all")
    assert payload is None


def test_parse_xml_empty_returns_none():
    payload = parse_xml("")
    assert payload is None


def test_build_xml_roundtrip():
    task = PlanTask("1", "Create middleware", "src/auth.py", ["jwt", "auth"])
    xml = build_xml(
        task="Add JWT",
        targets=[{"path": "src/auth.py", "action": "create"}],
        tasks=[task],
        validation=["Routes return 401"],
        rounds=3,
    )
    payload = parse_xml(xml)
    assert payload is not None
    assert payload.task == "Add JWT"
    assert payload.tasks[0].task_id == "1"


def test_check_capabilities_no_codex(monkeypatch):
    """check_capabilities should detect missing codex gracefully."""
    monkeypatch.setattr("shutil.which", lambda x: None)
    from tessera.debate.engine import check_capabilities
    caps = check_capabilities()
    assert caps["codex_cli"] is False
    assert caps["claude_cli"] is False


def test_codex_unavailable_raises(monkeypatch):
    """codex.run should raise CodexError if codex not on PATH."""
    monkeypatch.setattr("shutil.which", lambda x: None)
    from tessera.debate.codex import run, CodexError
    with pytest.raises(CodexError, match="Codex CLI not found"):
        run("test prompt")


def test_claude_unavailable_without_package():
    """claude.run should raise ClaudeError if anthropic not installed."""
    import sys
    # Simulate missing anthropic
    original = sys.modules.get("anthropic")
    sys.modules["anthropic"] = None  # type: ignore
    try:
        from tessera.debate.claude import run, ClaudeError
        import importlib
        import tessera.debate.claude as cm
        importlib.reload(cm)
        with pytest.raises((cm.ClaudeError, Exception)):
            cm.run("test prompt")
    finally:
        if original is None:
            sys.modules.pop("anthropic", None)
        else:
            sys.modules["anthropic"] = original
