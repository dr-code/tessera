---
name: codex-review
description: Get an independent GPT review via Codex CLI. Use when you want a second opinion on code, plans, or architecture from a different AI model.
---

# /codex-review — Independent GPT Code Review

## Usage
`/codex-review` — reviews staged changes (`git diff --staged`)
`/codex-review HEAD~N` — reviews last N commits
`/codex-review [file ...]` — reviews specific files

## Description
Get an independent GPT code review via Codex CLI. Claude evaluates each GPT finding (agree, correct, or dismiss), adds severity levels, and presents a structured actionable review.

## Instructions

### Phase 0: Determine Scope
- No args: run `git diff --staged`. If nothing staged, run `git diff HEAD~1` for the last commit.
- `HEAD~N` pattern: run `git diff HEAD~N`
- File args: read the specified files directly
- If nothing found: ask the user what to review

### Phase 1: Get Context (if tessera available)
If tessera MCP is active, call `graph_retrieve` with the names of modified files to get blast radius context — which other parts of the codebase depend on what's being changed.

### Phase 2: Send to GPT
For diffs up to ~200 lines, send in one call. For larger diffs, send one file at a time.

```bash
codex exec "Independent code review. Context: <TASK_OR_DESCRIPTION>. Code/diff to review: <CODE_OR_DIFF>. Review for: (1) bugs and logic errors, (2) security vulnerabilities (injection, auth bypass, data exposure), (3) performance issues, (4) missing error handling, (5) readability and naming. Format each finding as: [BUG|SECURITY|PERF|STYLE|MISSING]: file:line — issue — suggested fix. End with VERDICT: approved | approved-with-notes | needs_revision"
```

### Phase 3: Claude Evaluates
For each GPT finding, Claude:
- Confirms the finding is real (not a false positive)
- Assigns severity: CRITICAL / HIGH / MED / LOW
- Notes if the issue is already handled elsewhere in the codebase
- Adds any findings GPT missed

### Phase 4: Present Review

**Verdict:** approved | approved-with-notes | needs_revision

**CRITICAL / HIGH — Must Fix:**
[list with file:line and fix]

**MED — Should Fix:**
[list]

**LOW / Style — Consider:**
[list]

**Blast Radius:** [if tessera context available — what this change affects]

Ask: fix critical/high issues now?
