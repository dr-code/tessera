---
description: "Autonomous build loop — GPT plans, Claude+GPT debate, user approval gate, implement, test, GPT code review."
scope: project
argument-hint: "<task description>"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion
---

# /build — Autonomous Build Loop

**Task:** $ARGUMENTS

Full pipeline: load context → GPT initial plan → Claude+GPT debate → user approval gate → implement → test → GPT code review → finalize.

## Phase 0: Load Context

1. Read `CLAUDE.md` in the project root (skip silently if missing)
2. Read `docs/PROJECT_CONTEXT.md` (skip silently if missing)
3. If tessera MCP is active:
   - Call `graph_continue` with the task as query
   - If `needs_scan=true`, run `graph_scan` first
   - Read all `recommended_files` via `graph_read`
4. Record the user's exact task as acceptance criteria

## Phase 1: GPT Plans

Send the task and project context to Codex for an initial plan:

```bash
codex exec "You are a senior engineer. Create a detailed implementation plan for: $ARGUMENTS. Project context: <CONTEXT>. Output: (1) files to create or modify with rationale, (2) implementation approach per file, (3) correct ordering of steps, (4) edge cases to handle, (5) risks. Be specific — name actual files and functions."
```

If tessera is active, call `graph_retrieve` with key terms from the plan to surface relevant existing code.

## Phase 2: Claude Debates GPT's Plan

Claude critiques the plan: architecture fit, project conventions, edge cases, ordering problems. Then send critique to Codex:

```bash
codex exec "Plan revision for: $ARGUMENTS. Your original plan: <GPT_PLAN>. Claude critique: <CRITIQUE>. Output a revised plan that addresses each critique point. Keep what was correct, fix what was wrong."
```

Produce a final agreed plan from the debate output.

## Phase 3: User Approval Gate

Present the final plan via AskUserQuestion. Include:
- Task summary and acceptance criteria
- Files to create or modify
- Implementation approach
- Resolved debate points
- Open risks

**Do NOT write any code until the user explicitly approves.**

If tessera MCP is active, call `plan_save` with `project_name`, `subtask_name`, `task=$ARGUMENTS`, and `plan_markdown=<approved plan>` to register the plan for compliance tracking.

## Phase 4: Implement

Write code following the approved plan. Do not deviate from the plan without noting it.

If tessera MCP is active, call `graph_continue` at the start of each implementation sub-turn. After each file edit, call `graph_register_edit` with `file::symbol` notation and a summary. Pass `checklist_item_id` from `active_checklist` if available to auto-mark plan items done.

## Phase 5: Verify

1. Detect and run the project's test command:
   - Python: `uv run pytest` or `python -m pytest`
   - Node: `pnpm test` / `npm test`
   - Go: `go test ./...`
   - Rust: `cargo test`
   - Check `CLAUDE.md`, `package.json`, or `pyproject.toml` for the correct command
2. Fix any failing tests before proceeding

## Phase 6: GPT Code Review

Get Codex's independent review of the diff:

```bash
git diff HEAD | codex exec - << 'EOF'
You are doing a code review. Task: $ARGUMENTS. Review the diff for: bugs and logic errors, security vulnerabilities, missing error handling, edge cases not addressed. Format each issue as: [BUG|SECURITY|PERF|STYLE]: file:line — issue — suggested fix. End with VERDICT: approved OR needs_revision.
EOF
```

If the diff is large (>200 lines), send one file at a time. Fix any BUG or SECURITY issues. Use judgment on PERF/STYLE.

## Phase 7: Finalize

If tessera MCP is active, run the `tessera-verify` skill to confirm plan compliance before wrapping up.

Present a summary:
- Requirements checklist: each acceptance criterion marked pass/fail
- Test results
- GPT review verdict and issues fixed
- Files modified
