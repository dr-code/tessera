"""Tessera MCP server — stdio transport, all 10 tools.

Each inbound JSON-RPC request is dispatched to the appropriate tool module.
Turn state is reset on every graph_continue call.
"""

from __future__ import annotations

import os
from pathlib import Path

import mcp.server.stdio as stdio_server
from mcp.server import Server
from mcp.types import (
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
    Tool,
)

from ..core.config import PROJECT_ROOT
from ..core.database import Database
from .tools.state import TurnState
from .tools import (
    continue_,
    decision,
    edit,
    fallback,
    impact,
    neighbors,
    plan_save,
    read,
    retrieve,
    scan,
    summary,
)

import json


def _resolve_project_root() -> str:
    root = PROJECT_ROOT or os.environ.get("TESSERA_PROJECT_ROOT", "") or os.getcwd()
    return str(Path(root).resolve())


def _tool_result(data: dict) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(data, indent=2))]
    )


def _resolve_read_path(args: dict) -> str:
    """Extract a single file path from graph_read arguments.

    Accepts any of:
    - ``path`` as a plain string  (standard)
    - ``paths`` as a list          (Claude sometimes sends an array)
    - ``paths`` as a JSON-encoded string like '["a.py","b.py"]'
    Returns the first path found, or ``""`` if none.
    """
    raw = args.get("path") or args.get("paths", "")
    if isinstance(raw, list):
        return raw[0] if raw else ""
    if isinstance(raw, str) and raw.startswith("["):
        try:
            decoded = json.loads(raw)
            return decoded[0] if decoded else ""
        except (json.JSONDecodeError, IndexError):
            pass
    return raw


def _error_result(message: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps({"ok": False, "error": message}))]
    )


def create_server() -> Server:
    project_root = _resolve_project_root()
    db = Database(project_root)
    session_id = db.create_new_session(project_root)
    state = TurnState()

    app = Server("tessera")

    @app.list_tools()
    async def list_tools(request: ListToolsRequest) -> ListToolsResult:
        return ListToolsResult(
            tools=[
                Tool(
                    name="graph_continue",
                    description=(
                        "MANDATORY first call every turn. Resets turn state, routes to "
                        "cached or freshly-scored file recommendations. Returns confidence "
                        "level and recommended_files."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Current task description"},
                            "top_files": {"type": "integer", "default": 5},
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="graph_retrieve",
                    description="Scored file ranking. Max 1 call per turn.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "top_files": {"type": "integer", "default": 5},
                            "top_edges": {"type": "integer", "default": 12},
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="graph_read",
                    description=(
                        "Read ONE file or file::symbol per call. Enforces turn read budget. "
                        "Pass a single path via `path`. If you pass multiple paths via `paths`, "
                        "only the first is read. Supports anchor-based excerpts."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Single file path, or path::Symbol. One file per call.",
                            },
                            "paths": {
                                "description": "Alias accepted for compatibility. Only the first path is read.",
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "array", "items": {"type": "string"}},
                                ],
                            },
                            "max_chars": {"type": "integer", "default": 4000},
                            "query": {"type": "string", "default": ""},
                            "anchor": {"type": "string", "default": ""},
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="graph_neighbors",
                    description="Return incoming and outgoing edges for a file.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "limit": {"type": "integer", "default": 30},
                        },
                        "required": ["file"],
                    },
                ),
                Tool(
                    name="graph_impact",
                    description="Bidirectional blast-radius analysis for changed files.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "changed_files": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "max_depth": {"type": "integer", "default": 3},
                        },
                        "required": ["changed_files"],
                    },
                ),
                Tool(
                    name="graph_register_edit",
                    description=(
                        "Log file edits, invalidate retrieval cache, and mark the "
                        "corresponding plan checklist item done. Pass checklist_item_id "
                        "(from graph_continue active_checklist) to mark it done directly "
                        "without text matching. Falls back to keyword matching when no ID "
                        "is given. Pass an empty files list when completing a verification "
                        "or observation task that does not involve a file edit — the "
                        "checklist item will still be marked done."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "files": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                                "description": (
                                    "Files edited. May be empty for verification-only "
                                    "tasks when checklist_item_id is provided."
                                ),
                            },
                            "summary": {"type": "string", "default": ""},
                            "checklist_item_id": {
                                "anyOf": [{"type": "integer"}, {"type": "string"}],
                                "default": 0,
                                "description": (
                                    "ID of the checklist item completed by this edit. "
                                    "Use the id from graph_continue active_checklist. "
                                    "When set, the item is marked done immediately without "
                                    "keyword matching."
                                ),
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="graph_lock_decision",
                    description=(
                        "Record an architectural decision to the session database. "
                        "Call when you identify a key design choice so it appears in "
                        "the dashboard and future graph_continue context."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "One-sentence description of the decision.",
                            },
                            "scope": {
                                "type": "string",
                                "enum": ["file", "module", "project"],
                                "default": "project",
                            },
                            "files": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                                "description": "File paths the decision applies to.",
                            },
                        },
                        "required": ["summary"],
                    },
                ),
                Tool(
                    name="graph_action_summary",
                    description="Recent actions, locked decisions, and active plan status.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "default": ""},
                            "limit": {"type": "integer", "default": 12},
                        },
                    },
                ),
                Tool(
                    name="graph_scan",
                    description="Rebuild the info graph. Injects CLAUDE.md policy block.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_root": {"type": "string"},
                            "incremental": {"type": "boolean", "default": True},
                        },
                        "required": ["project_root"],
                    },
                ),
                Tool(
                    name="plan_save",
                    description=(
                        "Archive an approved markdown plan to Tessera's DB and disk. "
                        "Parses `- [ ]` checklist items for compliance tracking. "
                        "Call after writing-plans skill produces an approved plan."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Short project identifier, e.g. 'my-app'",
                            },
                            "subtask_name": {
                                "type": "string",
                                "description": "Feature or subtask name, e.g. 'auth-refactor'",
                            },
                            "task": {
                                "type": "string",
                                "description": "One-sentence description of what the plan builds",
                            },
                            "plan_markdown": {
                                "type": "string",
                                "description": "Full markdown content of the implementation plan",
                            },
                        },
                        "required": ["project_name", "subtask_name", "task", "plan_markdown"],
                    },
                ),
                Tool(
                    name="fallback_rg",
                    description="Capped ripgrep search. Max 1 call per turn.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string"},
                            "max_hits": {"type": "integer", "default": 30},
                            "paths": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["pattern"],
                    },
                ),
            ]
        )

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> CallToolResult:
        args = arguments or {}

        try:
            if name == "graph_continue":
                result = continue_.run(
                    db=db,
                    state=state,
                    session_id=session_id,
                    query=args["query"],
                    top_files=int(args.get("top_files", 5)),
                    project_root=project_root,
                )
            elif name == "graph_retrieve":
                result = retrieve.run(
                    db=db,
                    state=state,
                    session_id=session_id,
                    query=args["query"],
                    top_files=int(args.get("top_files", 5)),
                    top_edges=int(args.get("top_edges", 12)),
                )
            elif name == "graph_read":
                raw_path = _resolve_read_path(args)
                if not raw_path:
                    result = {"ok": False, "error": "graph_read requires 'path' (single file path)"}
                else:
                    result = read.run(
                        db=db,
                        state=state,
                        session_id=session_id,
                        project_root=project_root,
                        file_ref=str(raw_path),
                        max_chars=int(args.get("max_chars", 4000)),
                        query=str(args.get("query", "")),
                        anchor=str(args.get("anchor", "")),
                    )
            elif name == "graph_neighbors":
                result = neighbors.run(
                    db=db,
                    state=state,
                    session_id=session_id,
                    file_path=args["file"],
                    limit=int(args.get("limit", 30)),
                )
            elif name == "graph_impact":
                result = impact.run(
                    db=db,
                    state=state,
                    session_id=session_id,
                    changed_files=list(args["changed_files"]),
                    max_depth=int(args.get("max_depth", 3)),
                )
            elif name == "graph_register_edit":
                raw_files = args.get("files", [])
                files_list = raw_files if isinstance(raw_files, list) else [raw_files]
                result = edit.run(
                    db=db,
                    state=state,
                    session_id=session_id,
                    files=[str(f) for f in files_list],
                    summary=str(args.get("summary", "")),
                    checklist_item_id=int(args.get("checklist_item_id", 0)),
                )
            elif name == "graph_lock_decision":
                raw_files = args.get("files", [])
                files_list = raw_files if isinstance(raw_files, list) else []
                result = decision.run(
                    db=db,
                    state=state,
                    session_id=session_id,
                    summary=str(args.get("summary", "")),
                    scope=str(args.get("scope", "project")),
                    files=[str(f) for f in files_list],
                )
            elif name == "graph_action_summary":
                result = summary.run(
                    db=db,
                    state=state,
                    session_id=session_id,
                    query=str(args.get("query", "")),
                    limit=int(args.get("limit", 12)),
                )
            elif name == "graph_scan":
                result = scan.run(
                    db=db,
                    state=state,
                    session_id=session_id,
                    project_root=args["project_root"],
                    incremental=bool(args.get("incremental", True)),
                )
            elif name == "plan_save":
                result = plan_save.run(
                    db=db,
                    state=state,
                    session_id=session_id,
                    project_root=project_root,
                    project_name=str(args.get("project_name", "")),
                    subtask_name=str(args.get("subtask_name", "")),
                    task=str(args.get("task", "")),
                    plan_markdown=str(args.get("plan_markdown", "")),
                )
            elif name == "fallback_rg":
                result = fallback.run(
                    db=db,
                    state=state,
                    session_id=session_id,
                    pattern=args["pattern"],
                    max_hits=int(args.get("max_hits", 30)),
                    paths=list(args.get("paths", [])) or None,
                    project_root=project_root,
                )
            else:
                return _error_result(f"Unknown tool: {name}")
        except KeyError as exc:
            return _error_result(f"Missing required argument: {exc}")
        except Exception as exc:
            return _error_result(f"Tool error: {exc}")

        return _tool_result(result)

    return app


async def serve() -> None:
    app = create_server()
    async with stdio_server.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())
