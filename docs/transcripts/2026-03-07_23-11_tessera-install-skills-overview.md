# Session Transcript — 2026-03-07 23:11
**Project:** Tessera
**Directory:** /Users/rutvikshah/Projects/tessera

---

## Session Summary

### Completed
- Diagnosed that tessera was not installed (not in pip, not in pipx, CLI not on PATH)
- Installed pipx via brew (was also missing)
- Installed tessera in editable mode via `pipx install --editable "/Users/rutvikshah/Projects/tessera[all]"`
- Added `~/.local/bin` to PATH via `pipx ensurepath`
- Confirmed `tessera --help` works and all CLI commands are available
- Clarified that all 5 tessera skills (build, cleanup, codex-review, debate, plan-review) are already installed at `~/.claude/skills/`
- Explained difference between `/codex-review` (post-implementation code audit) and `/plan-review` (pre-implementation plan validation)
- Explained that skills work without the MCP server; MCP adds optional graph context enrichment

### In Progress
- Setting up tessera MCP server for onshift project — not yet done
- No `.tessera/` directory exists in any project yet

### Decisions Made
- **pipx for installation**: macOS PEP 668 blocks system pip installs; pipx is the correct approach for Python CLI tools
- **Per-project opt-in**: Tessera graph memory requires `tessera scan <path>` per project; skills work globally without it
- **Incremental adoption**: Skills can be used immediately; MCP setup is a separate step

### Files Modified
- None (installation only, no source files changed)

### Blockers / Open Questions
- Need to open a new terminal for `~/.local/bin` to be on PATH automatically (pipx ensurepath wrote to shell config but current shell not yet reloaded)
- MCP server not yet configured for onshift or any other project
- Tessera not yet published to PyPI — install.sh's `pip install tessera` would fail; editable local install is the current path

---

## Key Decisions

| Decision | Rationale |
|---|---|
| Install via pipx | macOS Homebrew Python enforces PEP 668, blocking system-wide pip installs |
| Editable install (`-e`) | Source is local at `/Users/rutvikshah/Projects/tessera`; editable mode means changes to source are reflected immediately |
| Skills vs MCP are independent | Skills are subprocess-based (Codex CLI + Claude), no graph needed; MCP server provides graph context as an enhancement |
