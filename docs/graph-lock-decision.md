---
id: graph-lock-decision
title: graph_lock_decision MCP Tool
edition: tessera
depends_on: [database, mcp-server]
source_files:
  - src/tessera/mcp/tools/decision.py
  - src/tessera/mcp/server.py
  - src/tessera/mcp/tools/scan.py
  - CLAUDE.md
routes: []
models:
  - decisions (existing SQLite table via db.add_decision)
test_files:
  - tests/test_tools.py
known_issues: []
---

# graph_lock_decision MCP Tool

## Purpose

`graph_lock_decision` is an MCP tool that allows Claude to explicitly record
architectural decisions into the tessera SQLite database during a session. The
`decisions` table and `db.add_decision()` method have existed since the initial
schema but were never wired to any call site, making the "Locked Decisions"
section of the dashboard perpetually empty. This tool closes that gap.

## Architecture

```
Claude (during a session)
  └─ calls graph_lock_decision(summary, scope, files)
       └─ decision.run() → db.add_decision()
            └─ writes to decisions table in .tessera/tessera.db

Dashboard GET /api/decisions
  └─ db.get_decisions() ← already implemented, now has data

graph_continue response
  └─ recent_decisions[] ← already populated from same table
```

The tool is intentionally simple — no new DB schema, no migrations, no new
tables. It is a thin call-site wrapper over existing infrastructure.

## Data Model

Uses the existing `decisions` table (no migration needed):

| Column     | Type    | Notes                                      |
|------------|---------|--------------------------------------------|
| id         | INTEGER | PK autoincrement                           |
| session_id | TEXT    | FK to sessions                             |
| summary    | TEXT    | One-sentence description of the decision   |
| files      | TEXT    | JSON array of affected file paths          |
| scope      | TEXT    | "file" \| "module" \| "project"            |
| created_at | INTEGER | Unix timestamp (set by DB default)         |

## API Endpoints

None — MCP tool only, not a dashboard HTTP endpoint.

## Business Rules

- `summary` is required and must be non-empty.
- `scope` defaults to `"project"` if omitted.
- `files` defaults to `[]` if omitted.
- Scope must be one of: `"file"`, `"module"`, `"project"`. Invalid values are
  rejected with `{ok: false, error: ...}`.
- The rolling-window enforcement (MAX_DECISIONS per session) is handled by
  `db.add_decision()` — the tool does not need to re-implement it.
- Duplicate detection is NOT performed — Claude is trusted to call this
  intentionally.

## Policy Template Update

`scan.py` `_POLICY_TEMPLATE` is bumped from `v1` to `v2` and gains one bullet:

```
- When you identify an architectural decision: call `graph_lock_decision`
  with a one-sentence summary, scope ("file" | "module" | "project"),
  and the files it applies to.
```

The already-injected block in this project's `CLAUDE.md` is updated in-place
to match.

## Dependencies

- `src/tessera/core/database.py` — `add_decision()` (already implemented)
- `src/tessera/mcp/server.py` — tool registration and dispatch
- `src/tessera/mcp/tools/scan.py` — `_POLICY_TEMPLATE` v2

## Known Issues

<!-- empty — will be populated by future audits -->
