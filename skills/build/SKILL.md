---
name: build
description: Autonomous build loop — GPT plans, Claude+GPT debate, user approval gates implementation and verification.
---

# /build — Autonomous Build Loop

## Usage
`/build <task description>`

## Description
Full pipeline: load context → GPT initial plan → Claude+GPT debate → user approval gate → implement → test → GPT code review → finalize. Uses tessera graph context when available.

## Instructions

### Phase 0: Load Context
1. Read CLAUDE.md in the project root (skip silently if missing)
2. Read docs/PROJECT_CONTEXT.md (skip silently if missing)
3. If tessera MCP is active: call `graph_continue`; if `needs_scan=true`, run `graph_scan` first
4. Record the user's exact task as acceptance criteria

### Phase 1: GPT Plans
Send the task and project context to Codex for an initial plan:

```bash
codex exec "You are a senior engineer. Create a detailed implementation plan for: <TASK>. Project context: <CONTEXT>. Output: (1) files to create or modify with rationale, (2) implementation approach per file, (3) correct ordering of steps, (4) edge cases to handle, (5) risks. Be specific — name actual files and functions."
```

Read and internalize GPT's plan. If tessera is active, use `graph_retrieve` with key terms from the plan to surface relevant existing code.

### Phase 2: Claude Debates GPT's Plan
Claude critiques the plan: architecture fit, project conventions, edge cases, ordering problems. Then send critique to Codex:

```bash
codex exec "Plan revision for: <TASK>. Your original plan: <GPT_PLAN>. Claude critique: <CRITIQUE>. Output a revised plan that addresses each critique point. Keep what was correct, fix what was wrong."
```

Produce a final agreed plan from the debate output.

### Phase 3: User Approval Gate
Present the final plan to the user via AskUserQuestion. Include:
- Task summary and acceptance criteria
- Files to create or modify
- Implementation approach
- Resolved debate points
- Open risks

**Do NOT write any code until the user explicitly approves.**

If tessera MCP is active and the user approves:
```
plan_save(
  project_name = "<short project id>",
  subtask_name = "<feature name>",
  task         = "<one sentence from acceptance criteria>",
  plan_markdown = "<full plan from Phase 2>"
)
```
This registers the plan for `tessera-verify` compliance tracking.

### Phase 4: Implement
Write code following the approved plan. Do not deviate from the plan without noting it.

When an architectural decision is made during implementation (choosing a pattern, adding a dependency, splitting a module):
```
graph_lock_decision(
  summary = "<one sentence decision>",
  scope   = "file" | "module" | "project",
  files   = ["path/to/affected/file"]
)
```

### Phase 5: Verify
1. Run tests using the project's test command (check CLAUDE.md, package.json, or pyproject.toml for the right command)
2. If tessera is active: call `graph_register_edit` for each modified file using `file::symbol` notation with a summary of changes
3. Fix any failing tests before proceeding

### Phase 6: GPT Code Review
If tessera MCP is active, call `graph_impact(changed_files=[...])` to determine blast radius before sending the diff. Include the impact map in the review prompt so GPT can flag cascading risks.

Get Codex's independent review of the diff:

```bash
git diff HEAD | codex exec - << 'EOF'
You are doing a code review. Task: <TASK>. Review the diff above for: bugs and logic errors, security vulnerabilities, missing error handling, edge cases not addressed. Format each issue as: [BUG|SECURITY|PERF|STYLE]: file:line — issue — suggested fix. End with VERDICT: approved OR needs_revision.
EOF
```

If the diff is large (>200 lines), send one file at a time. Fix any BUG or SECURITY issues found. Use judgment on PERF/STYLE.

### Phase 7: Finalize
Present a summary:
- Requirements checklist: each acceptance criterion marked pass/fail
- Test results
- GPT review verdict and issues fixed
- Files modified
