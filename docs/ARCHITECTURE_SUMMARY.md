# Architecture Summary

> Full architecture detail: `docs/ARCHITECTURE.md`

## System Overview

Tessera is a Python MCP server + CLI that gives Claude Code persistent codebase memory via SQLite. It scans a project's files and symbols into a graph, then routes Claude's reads to the most relevant files per-turn. It also archives implementation plans, tracks checklist compliance, records architectural decisions, and provides a local Flask dashboard. Version 0.4.0 adds a bundled Superpowers methodology (14 skills) and Plannotator visual plan review (ExitPlanMode hooks).

## Service Boundaries

| Layer | Responsibility |
|-------|---------------|
| `mcp/` | stdio MCP server — 11 tools, turn state management |
| `graph/` | Scanner, symbol parser, scorer, builder — populates SQLite |
| `plans/` | Plan archive: `save_plan` (debate-driven), `save_raw_plan` (skills-driven) |
| `compliance/` | git diff vs plan_checklist targets |
| `debate/` | GPT↔Claude multi-round debate engine |
| `dashboard/` | Flask HTTP server at localhost:5050 |
| `handoff/` | Session handoff generator |
| `skills/` | 14 Superpowers methodology skills (Tessera-adapted) |
| `hooks/` | Plannotator ExitPlanMode hooks for visual plan review |

## Data Flow

**Typical turn (with Tessera MCP active):**
```
graph_continue → scores files → returns recommended_files + confidence level
  → Claude reads via graph_read (budget-capped)
  → Claude edits code
  → graph_register_edit → updates plan_checklist if active plan
```

**Plan flow (Superpowers integrated):**
```
writing-plans skill → plan_save MCP tool → plans table + plan_checklist rows
  → ExitPlanMode → Plannotator binary → visual approval gate
  → subagent-driven-development → graph_register_edit marks checklist items done
  → tessera-verify → compliance check (diff vs checklist)
```

## Core Invariants

- All writes go through `_retry_write` (WAL + exponential backoff)
- All file rewrites use `os.replace()` (atomic)
- DLP sanitizer runs on all content going to external APIs (debate, codex)
- Path escapes from `.tessera/plans/` are blocked in both `save_plan` and `save_raw_plan`
- MCP server is stdio only; dashboard is a separate HTTP process

## MCP Tools (11)

| Tool | Purpose |
|------|---------|
| `graph_continue` | Start-of-turn: score files, return routing |
| `graph_retrieve` | Semantic search over graph |
| `graph_read` | Budget-capped file read |
| `graph_neighbors` | Adjacent files in dependency graph |
| `graph_impact` | Blast radius for changed files |
| `graph_register_edit` | Record an edit + mark checklist item |
| `graph_lock_decision` | Persist an architectural decision |
| `graph_action_summary` | Recent actions + decisions summary |
| `graph_scan` | Rebuild the graph (incremental or full) |
| `fallback_rg` | Capped ripgrep search |
| `plan_save` | Archive a markdown plan + parse checklist items |

## Key Decisions

- SQLite + WAL over JSON files (concurrent writes, transactions, indexable history)
- stdio MCP transport only (dashboard runs separately, no port conflicts)
- Superpowers skills bundled in `skills/` (adapted with graph context injection)
- Plannotator hooks bundled in `hooks/hooks.json` (requires separate binary install)
- `plan_save` parses `- [ ]` items into plan_checklist without requiring debate workflow
