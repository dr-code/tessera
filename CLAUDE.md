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

---

## Critical Rules

### 0. NEVER Publish Sensitive Data
- NEVER commit passwords, API keys, tokens, or secrets to git
- NEVER commit `.env` files — ALWAYS verify `.env` is in `.gitignore`
- Before ANY commit: verify no secrets are included
- NEVER output secrets in suggestions, logs, or responses

### 3. Testing
- Minimum 3 assertions per test
- Explicit success criteria only — "it works" is not a criterion

### 4. Quality Gates
- No file > 300 lines, no function > 50 lines
- All tests must pass before committing
- No linter warnings

### 5. Git Workflow
- NEVER work on main
- Branch naming: `feat/`, `fix/`, `docs/`, `refactor/`, `chore/`, `test/`

### 6. Plan Mode
- For any non-trivial task, start in plan mode
- Named steps only; when modifying a plan, replace the step instead of appending

### 7. Merge Gate — MDD
- `docs/` updated to reflect what was actually built
- Code matches the documented spec
- Tests pass, no secrets committed

### 8. Renames
- Never do project-wide renames without a checklist and a fresh follow-up session

### 9. CLAUDE.md Is Team Memory
- When Claude makes a project-specific mistake, add the rule here

---

## Project Docs

- `docs/PROJECT_CONTEXT.md` — feature map, quick reference, common gotchas
- `docs/ARCHITECTURE_SUMMARY.md` — 1-page architecture brief
- `docs/ARCHITECTURE.md` — full system architecture
- `docs/INFRASTRUCTURE.md` — deployment and environment details
- `docs/DECISIONS.md` — architectural decisions
- `.env.example` — required environment variables

---

## Python Coding Standards

- Use `pyproject.toml` for all project metadata and tool config (ruff, pytest, mypy)
- Type-annotate all function signatures; use `from __future__ import annotations` for forward refs
- Use `pytest` for all tests; fixtures in `conftest.py`; no bare `assert` without a message in non-test code
- Prefer `pathlib.Path` over `os.path`
- All write operations should be atomic — use temp file + `os.replace()` (already a project rule)
- Never use `except Exception` without logging; always re-raise or handle explicitly
- Run `ruff check .` and `mypy src/` clean before committing

---

## Workflow Preferences

- Quality over speed — if unsure, ask before executing
- Plan first, code second — use plan mode for non-trivial tasks
- One task, one chat — `/clear` between unrelated tasks
- When testing: queue observations, fix in batch
