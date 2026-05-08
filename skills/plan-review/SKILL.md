---
name: plan-review
description: Send execution plans to GPT for structured review via Codex CLI. Use when you have a written plan and want independent validation before implementation.
---

# /plan-review — Independent Plan Review via Codex

## Usage
`/plan-review path/to/plan.md`
`/plan-review` — reads plan from current conversation context or asks user to provide it

## Description
Send an implementation plan to GPT via Codex CLI for structured review before implementation begins. Claude synthesizes GPT's feedback, agrees or disagrees with each point, and issues a go/no-go verdict.

## Instructions

### Phase 0: Load Plan + Tessera Context

**If tessera MCP is configured in this session:**
```
1. graph_continue (mandatory first call)
2. graph_action_summary — surface locked decisions that may constrain the plan
3. graph_retrieve with the plan's key feature terms — find relevant existing code
```

- If a file path was provided: read the plan file
- If no path: ask the user to paste the plan or specify where it is
- Include the retrieved context and any locked decisions in the GPT review prompt so it can flag contradictions with existing patterns

### Phase 1: Send to GPT
Construct the review prompt with the full plan text and any codebase context:

```bash
codex exec "You are reviewing an implementation plan before execution begins. Plan: <PLAN_TEXT>. Codebase context: <CONTEXT>. Review for: (1) architecture violations or inconsistency with existing patterns, (2) missing edge cases or error handling, (3) wrong ordering of steps or missing dependencies between steps, (4) security concerns, (5) over-engineering or unnecessary complexity. For each issue: ISSUE: <description> | SUGGEST: <specific fix> | SEVERITY: HIGH/MED/LOW. End with VERDICT: approved OR needs_revision"
```

### Phase 2: Claude Synthesizes
For each GPT issue, Claude responds:
- **AGREE** — the plan needs to change here; note what revision is required
- **DISAGREE** — explain why the plan already handles it or why GPT's concern is inapplicable
- **PARTIAL** — the concern is valid but the suggested fix is wrong; propose a better fix

### Phase 3: Output

**Plan Status:** APPROVED / NEEDS REVISION

**GPT Issues + Claude Response:**

| Issue | Severity | Claude's Verdict | Required Change |
|---|---|---|---|
| <issue> | HIGH/MED/LOW | AGREE/DISAGREE/PARTIAL | <change or "none"> |

**Required Changes Before Implementation:**
[Specific revisions needed — these block implementation]

**Optional Improvements:**
[Suggestions worth considering but not blocking]

If APPROVED:
- If tessera MCP is active: call `plan_save` with `project_name`, `subtask_name`, `task`, and `plan_markdown=<full plan text>` to register the reviewed plan for compliance tracking
- Confirm the user is ready to proceed to implementation

If NEEDS REVISION: present the revised plan for user confirmation before implementation. Re-run `plan_save` after the revision is confirmed.
