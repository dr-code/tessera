# Tessera — CLAUDE.md

## Project Overview
Tessera is an open-source Python MCP server + CLI giving Claude Code persistent codebase memory via SQLite. No license gating.

## Architecture
- `src/tessera/core/` — SQLite DB, migrations, feature flags
- `src/tessera/graph/` — scanner, symbol parser, builder, scorer
- `src/tessera/mcp/` — MCP server (stdio), 9 tools, turn state
- `src/tessera/debate/` — engine, codex wrapper, claude wrapper, DLP sanitizer, XML payload
- `src/tessera/plans/` — plan archive (DB + disk)
- `src/tessera/compliance/` — git diff vs plan targets
- `src/tessera/handoff/` — session handoff generator
- `src/tessera/dashboard/` — Flask dashboard, localhost:5050
- `src/tessera/cli.py` — Click CLI entry point

## Key Decisions (locked)
- Storage: SQLite with WAL mode, not JSON files
- MCP transport: stdio only (dashboard is a separate HTTP process)
- Debate: GPT (Codex CLI subprocess) → Claude critique → GPT respond → Claude synthesize
- Feature flags: TESSERA_ENABLE_DEBATE, TESSERA_ENABLE_DASHBOARD, TESSERA_ENABLE_COMPLIANCE
- Core install (no debate deps): zero remote calls, no API keys needed

## Development

```bash
# Install in editable mode with all optional deps
pip install -e ".[all]"

# Run tests
pytest tests/

# Run specific test file
pytest tests/test_database.py -v

# Scan tessera itself (dogfood)
tessera scan .
```

## DB Location
`.tessera/tessera.db` in the project root.

## Non-Negotiable Rules
- Never hardcode API keys or secrets
- Never commit .env files
- All write operations go through `_retry_write` for lock resilience
- All file rewrites use atomic `os.replace()` pattern
- DLP sanitizer runs on all content going to external APIs

<!-- TESSERA:START v1 -->
## Tessera Graph Policy

**MANDATORY**: Call `graph_continue` as your FIRST tool call every turn.

- If `needs_scan=true`: run `graph_scan` with the project root path
- If `skip=true`: project too small, proceed normally
- If error: proceed normally without graph routing for this turn
- Read all `recommended_files` via `graph_read` before other exploration
- Obey confidence caps:
  - high: no supplementary greps or reads
  - medium: up to max_supplementary_greps greps + max_supplementary_files reads
  - low: up to max_supplementary_greps greps + max_supplementary_files reads
- After edits: call `graph_register_edit` with file::symbol notation and summary
  - If `graph_continue` returned `active_checklist`, pass `checklist_item_id` for the item you just completed — this marks it done without keyword matching
  - If no active checklist or the edit doesn't map to a specific item, omit `checklist_item_id` (keyword fallback applies)
- Max 1 `graph_retrieve` per turn
- No raw grep/rg/bash file reads before `graph_continue`
<!-- TESSERA:END -->
