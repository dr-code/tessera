"""Regression tests for the Claude Code plugin manifest.

`claude plugin validate` found two defects that made the plugin load neither
its MCP server nor its Plannotator hooks:
- mcpServers pointed at a file that does not exist
- hooks pointed at a directory instead of a .json file

These tests keep the manifest consistent with `tessera scan` and with the
hooks file that ships in the repo.
"""

from __future__ import annotations

import json
from pathlib import Path

from tessera.cli import _build_mcp_config

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_JSON = ROOT / ".claude-plugin" / "plugin.json"


def _manifest() -> dict:
    return json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))


def test_mcp_server_is_inline_and_matches_scan_config():
    server = _manifest()["mcpServers"]["tessera"]
    scan_server = _build_mcp_config("/tmp/proj")["mcpServers"]["tessera"]
    assert server["command"] == scan_server["command"] == "tessera"
    assert server["args"] == scan_server["args"] == ["mcp"]


def test_mcp_server_does_not_use_uvx_or_absolute_paths():
    server = _manifest()["mcpServers"]["tessera"]
    assert server["command"] != "uvx", "uvx pulls the wrong PyPI package"
    assert "env" not in server, "plugin config must not embed a project path"


def test_hooks_path_is_an_existing_json_file():
    hooks = _manifest()["hooks"]
    assert hooks.endswith(".json")
    assert (PLUGIN_JSON.parent.parent / hooks).is_file()


def test_hooks_file_wires_plannotator_for_plan_mode():
    hooks_file = ROOT / _manifest()["hooks"]
    data = json.loads(hooks_file.read_text(encoding="utf-8"))["hooks"]
    pre = data["PreToolUse"][0]
    perm = data["PermissionRequest"][0]
    assert pre["matcher"] == "EnterPlanMode"
    assert perm["matcher"] == "ExitPlanMode"
    assert perm["hooks"][0]["command"] == "plannotator"
