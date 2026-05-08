# Project Context

## Key Commands
| Command | What it does |
|---------|-------------|
| `pip install -e ".[all]"` | Install in editable mode with all optional deps |
| `pytest tests/` | Run all tests |
| `tessera scan .` | Scan tessera itself (dogfood) |
| `tessera mcp` | Start MCP server (stdio) |

## Feature → Doc Lookup

| Working on... | Read first |
|---------------|------------|
| MCP tools (`graph_*`, `plan_save`) | `src/tessera/mcp/server.py`, `src/tessera/mcp/tools/` |
| Plan archive / compliance | `src/tessera/plans/archive.py`, `src/tessera/compliance/` |
| Superpowers skills | `skills/<name>/SKILL.md`, `docs/DECISIONS.md` ADR-003 |
| Plannotator hooks | `hooks/hooks.json`, `docs/DECISIONS.md` ADR-003 |
| Graph scan / scoring | `src/tessera/graph/`, `src/tessera/mcp/tools/scan.py` |
| Dashboard | `src/tessera/dashboard/` |
| Debate engine | `src/tessera/debate/` |

## Skill Families

| Family | Skills |
|--------|--------|
| Design | `brainstorming`, `writing-plans` |
| Execution | `subagent-driven-development`, `executing-plans`, `dispatching-parallel-agents` |
| Quality | `test-driven-development`, `requesting-code-review`, `receiving-code-review` |
| Debugging | `systematic-debugging`, `verification-before-completion` |
| Git workflow | `using-git-worktrees`, `finishing-a-development-branch` |
| Meta | `using-superpowers`, `writing-skills` |

## Common Gotchas

<!-- Add project-specific gotchas here as they are discovered -->

## Reference Docs
- Architecture: `docs/ARCHITECTURE_SUMMARY.md` (brief) · `docs/ARCHITECTURE.md` (full)
- Infrastructure: `docs/INFRASTRUCTURE.md`
- Decisions: `docs/DECISIONS.md`
- Transcripts: `docs/transcripts/`
