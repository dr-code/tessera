"""Regression tests for `tessera scan` .mcp.json generation.

Verifies that:
- Generated .mcp.json uses `tessera` command directly (not uvx, which pulls the
  wrong PyPI package due to a name collision)
- Args are exactly ["mcp"]
- TESSERA_PROJECT_ROOT is set to the scanned path
- No-overwrite semantics: existing .mcp.json is left untouched
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from tessera.cli import main, _build_mcp_config


# ── _build_mcp_config unit tests ─────────────────────────────────────────────

def test_build_mcp_config_command_is_tessera():
    cfg = _build_mcp_config("/tmp/proj")
    server = cfg["mcpServers"]["tessera"]
    assert server["command"] == "tessera", (
        "command must be 'tessera' — uvx pulls the wrong PyPI package"
    )


def test_build_mcp_config_args_exact():
    cfg = _build_mcp_config("/tmp/proj")
    server = cfg["mcpServers"]["tessera"]
    assert server["args"] == ["mcp"]


def test_build_mcp_config_project_root_env():
    cfg = _build_mcp_config("/my/project")
    server = cfg["mcpServers"]["tessera"]
    assert server["env"]["TESSERA_PROJECT_ROOT"] == "/my/project"


def test_build_mcp_config_has_mcp_servers_key():
    cfg = _build_mcp_config("/tmp/proj")
    assert "mcpServers" in cfg
    assert "tessera" in cfg["mcpServers"]


# ── tessera scan CLI integration tests ───────────────────────────────────────

@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """A minimal project with one Python file."""
    (tmp_path / "main.py").write_text("def hello(): pass\n", encoding="utf-8")
    return tmp_path


def test_scan_writes_tessera_mcp_json(sample_project: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(sample_project)])
    assert result.exit_code == 0, f"scan failed: {result.output}"

    mcp_json = sample_project / ".mcp.json"
    assert mcp_json.exists(), ".mcp.json should be created by tessera scan"

    data = json.loads(mcp_json.read_text(encoding="utf-8"))
    server = data["mcpServers"]["tessera"]
    assert server["command"] == "tessera"
    assert server["args"] == ["mcp"]
    assert "TESSERA_PROJECT_ROOT" in server["env"]


def test_scan_mcp_json_project_root_is_absolute(sample_project: Path) -> None:
    runner = CliRunner()
    runner.invoke(main, ["scan", str(sample_project)])

    mcp_json = sample_project / ".mcp.json"
    data = json.loads(mcp_json.read_text(encoding="utf-8"))
    root = data["mcpServers"]["tessera"]["env"]["TESSERA_PROJECT_ROOT"]
    assert Path(root).is_absolute(), "TESSERA_PROJECT_ROOT must be an absolute path"


def test_scan_does_not_overwrite_existing_mcp_json(sample_project: Path) -> None:
    sentinel = '{"sentinel": true}'
    mcp_json = sample_project / ".mcp.json"
    mcp_json.write_text(sentinel, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(sample_project)])
    assert result.exit_code == 0

    # File content must not have changed
    assert mcp_json.read_text(encoding="utf-8") == sentinel
    assert "not overwritten" in result.output
