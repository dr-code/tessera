---
description: "Get an independent GPT review via Codex CLI — staged changes, last N commits, or specific files."
scope: project
argument-hint: "[HEAD~N | file ...]"
allowed-tools: Read, Grep, Glob, Bash
---

# /codex-review — Independent GPT Code Review

**Scope:** $ARGUMENTS

Get an independent GPT code review via Codex CLI. Claude evaluates each GPT finding (confirm, correct, or dismiss), adds severity, and presents a structured actionable review.

## Phase 0: Determine Scope

- No args → `git diff --staged`. If nothing staged → `git diff HEAD~1`
- `HEAD~N` pattern → `git diff HEAD~N`
- File args → read the specified files directly
- Nothing found → ask the user what to review

## Phase 1: Get Context

If tessera MCP is active:
1. Call `graph_continue` with the names of modified files as the query
2. Call `graph_impact(changed_files=[...])` to show the blast radius — which parts of the codebase depend on what's being changed
3. Include the impact summary in the review prompt

## Phase 2: Send to GPT

For diffs up to ~200 lines, send in one call. For larger diffs, send one file at a time.

```bash
codex exec "Independent code review. Context: $ARGUMENTS. Code/diff to review: <CODE_OR_DIFF>. Review for: (1) bugs and logic errors, (2) security vulnerabilities (injection, auth bypass, data exposure), (3) performance issues, (4) missing error handling, (5) readability and naming. Format each finding as: [BUG|SECURITY|PERF|STYLE|MISSING]: file:line — issue — suggested fix. End with VERDICT: approved | approved-with-notes | needs_revision"
```

## Phase 3: Claude Evaluates

For each GPT finding:
- Confirm the finding is real (not a false positive)
- Assign severity: CRITICAL / HIGH / MED / LOW
- Note if the issue is already handled elsewhere (check via `graph_retrieve` if tessera is active)
- Add any findings GPT missed

## Phase 4: Present Review

**Verdict:** approved | approved-with-notes | needs_revision

**CRITICAL / HIGH — Must Fix:**
[list with file:line and fix]

**MED — Should Fix:**
[list]

**LOW / Style — Consider:**
[list]

**Blast Radius:** [if tessera active — what this change affects downstream]

Ask: fix critical/high issues now?
