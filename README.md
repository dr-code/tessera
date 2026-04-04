# Tessera

Persistent codebase memory for Claude Code — open source, no license gating.

Tessera gives Claude Code a semantic understanding of your project that persists across turns and sessions, eliminating redundant file re-reads and providing a structured action history.

## How it works

1. `tessera scan .` — builds a SQLite graph of your codebase (files, symbols, imports)
2. Claude calls `graph_continue` every turn — routes to cached, scored file recommendations
3. `graph_register_edit` updates the graph after edits, auto-checks plan checklists
4. Optional: run `tessera debate "task"` for a Claude vs GPT multi-round planning debate

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/dr-code/tessera/main/install.sh | bash
```

When the `claude` CLI is present the script uses the plugin marketplace (registers the MCP server via `uvx` and installs all skills). Without it, it falls back to `pip install tessera` and offers to copy the skills to `~/.claude/skills/`.

Then in any project:

```bash
tessera scan .          # builds graph, writes .mcp.json and CLAUDE.md
```

### Manual alternatives

```bash
# Claude Code plugin (two steps)
claude plugin marketplace add dr-code/tessera
claude plugin install tessera@tessera

# pip only
pip install tessera          # core — no API keys needed
pip install tessera[debate]  # adds debate mode (requires ANTHROPIC_API_KEY + codex CLI)
pip install tessera[dashboard]
pip install tessera[all]
```

## Quick start

```bash
cd my-project
tessera scan .          # builds graph, writes .mcp.json and CLAUDE.md
tessera status          # show graph stats
tessera dashboard       # start dashboard at localhost:5050
```

## MCP registration

After `tessera scan .`, your project will have a `.mcp.json`:

```json
{
  "mcpServers": {
    "tessera": {
      "command": "uvx",
      "args": ["--from", "tessera", "tessera", "mcp"],
      "env": { "TESSERA_PROJECT_ROOT": "/path/to/project" }
    }
  }
}
```

`uvx` fetches and caches tessera from PyPI on first run — no PATH entry needed. Claude Code picks this up automatically.

## CLI reference

```
tessera scan [PATH]              Build/rebuild the graph
tessera mcp                      Start MCP server (stdio)
tessera status [PATH]            Show graph stats
tessera decisions [PATH]         List locked decisions
tessera reset [PATH]             Clear action graph
tessera plans [PROJECT [SUB]]    List archived plans
tessera verify [PATH]            Compliance: plan vs git diff
tessera handoff [PATH]           Generate clipboard handoff summary
tessera debate "task" [flags]    Run Claude vs GPT debate
tessera dashboard [PATH]         Start dashboard at localhost:5050
```

## Debate mode

Requires `pip install tessera[debate]` and the `codex` CLI.

### Connecting to ChatGPT (no API key needed)

If you have a ChatGPT Plus or Pro subscription you can authenticate the `codex` CLI with it — no separate API key or billing setup required:

```bash
npm install -g @openai/codex   # install once
codex auth login               # opens browser — sign in with your ChatGPT account
```

That's it. `tessera debate` and all Claude Code skills (`/debate`, `/build`, `/cleanup`, etc.) will use your subscription automatically.

### Connecting via API key (optional)

Set `OPENAI_API_KEY` if you prefer direct API billing rather than the subscription OAuth path.

```bash
tessera debate "Add JWT authentication" \
  --project myapp \
  --subtask auth-middleware \
  --max-rounds 3
```

## Feature flags

| Flag | Default | Effect |
|---|---|---|
| `TESSERA_ENABLE_DEBATE` | on | Enables `tessera debate` |
| `TESSERA_ENABLE_DASHBOARD` | on | Enables `tessera dashboard` |
| `TESSERA_ENABLE_COMPLIANCE` | on | Enables `tessera verify` |

## Token savings target

| Metric | Target |
|---|---|
| Turn 2+ read reduction | ≥50% chars vs cold-start |
| 10-turn session reduction | ≥40% total chars |
| Cache hit rate (after turn 3) | ≥60% |
| Symbol excerpt savings | ≥70% vs full-file reads |

## Claude Code in-session skills

Tessera ships five Claude Code slash commands that use the tessera graph for context and Codex CLI for GPT's perspective. The plugin marketplace install auto-installs them from the `skills/` directory in this repo. For manual install, run `./install.sh` or copy from `skills/` to `~/.claude/skills/`.

Requires: `codex` CLI (`npm install -g @openai/codex`) authenticated via `codex auth login` (ChatGPT subscription) or `OPENAI_API_KEY`.

| Skill | Usage | Description |
|---|---|---|
| `/debate` | `/debate "REST vs GraphQL"` | Multi-round Claude vs GPT debate on architecture or design decisions |
| `/build` | `/build "add JWT auth"` | Full build loop: GPT plans → debate → user approval → implement → GPT review |
| `/cleanup` | `/cleanup src/` | Bidirectional slop scanner — Claude + GPT independently analyze, then reconcile |
| `/plan-review` | `/plan-review plan.md` | Send an implementation plan to GPT for structured review before coding |
| `/codex-review` | `/codex-review HEAD~2` | Independent GPT code review of staged changes, commits, or files |

All skills degrade gracefully when tessera MCP is not configured — they still run Claude+GPT collaboration, just without graph context.

## License

MIT
