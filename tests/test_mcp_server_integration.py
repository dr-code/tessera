"""In-process integration tests against the real registered MCP handlers.

Unlike the tool-module unit tests (test_tools.py), these go through
create_server() and mcp.types.Server.request_handlers directly — the same
dispatch path a real MCP client uses — so they catch handler-shape breaks
across `mcp` package upgrades and verify security fixes at the boundary
where untrusted tool-call arguments actually enter the system.

No pytest-asyncio dependency: handlers are driven with asyncio.run() from
plain synchronous test functions.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from mcp import types

from tessera.mcp.server import create_server


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_PROJECT_ROOT", str(tmp_path))
    return create_server(), str(tmp_path.resolve())


async def _call_tool(app, name: str, arguments: dict) -> dict:
    handler = app.request_handlers[types.CallToolRequest]
    request = types.CallToolRequest(
        params=types.CallToolRequestParams(name=name, arguments=arguments)
    )
    server_result = await handler(request)
    result: types.CallToolResult = server_result.root
    assert result.isError is not True, f"tool call errored: {result.content}"
    return json.loads(result.content[0].text)


def test_list_tools_handler_returns_graph_scan(server):
    app, _root = server
    handler = app.request_handlers[types.ListToolsRequest]
    server_result = asyncio.run(handler(None))
    tool_names = [t.name for t in server_result.root.tools]
    assert "graph_scan" in tool_names
    assert "graph_continue" in tool_names
    assert len(tool_names) >= 8


def test_graph_scan_ignores_malicious_project_root(server, tmp_path):
    """A graph_scan call carrying a different project_root must still scan
    (and report) the server's own root — not the caller-supplied path."""
    app, real_root = server
    outside = tmp_path.parent / "some-other-victim-project"
    outside.mkdir(exist_ok=True)

    data = asyncio.run(
        _call_tool(app, "graph_scan", {"project_root": str(outside), "incremental": False})
    )

    assert data["ok"] is True
    assert data["project_root"] == real_root
    assert data["project_root"] != str(outside.resolve())


def test_graph_continue_round_trip(server):
    app, _root = server
    data = asyncio.run(_call_tool(app, "graph_continue", {"query": "test"}))
    assert "ok" in data or "needs_scan" in data or "skip" in data
