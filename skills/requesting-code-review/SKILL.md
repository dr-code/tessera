---
name: requesting-code-review
description: Use when completing tasks, implementing major features, or before merging to verify work meets requirements
---

# Requesting Code Review

<!-- Adapted from obra/superpowers — Tessera code-review skill is the primary entry point -->

Dispatch a code reviewer to catch issues before they cascade.

**Core principle:** Review early, review often.

## When to Request Review

**Mandatory:**
- After each task in subagent-driven development
- After completing major feature
- Before merge to main

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## How to Request

### Option A: Tessera code-review skill (primary)

If Tessera is installed, invoke the `code-review` skill. It runs a multi-model review (Claude + GPT via Codex CLI) with structured feedback:

```
/code-review
```

The skill handles git diff extraction, context loading, and the review synthesis.

### Option B: Subagent dispatch (when Tessera code-review unavailable)

**1. Get git SHAs:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

**2. Dispatch code reviewer subagent:**

Use Task tool with `general-purpose` type.

**Provide:**
- Brief description of what you built
- What it should do (plan or requirements)
- `BASE_SHA` and `HEAD_SHA`
- Ask for: security vulnerabilities, missing error handling, spec compliance, test adequacy, type safety

**3. Act on feedback:**
- Fix CRITICAL issues immediately
- Fix IMPORTANT issues before proceeding
- Note MINOR issues for later
- Push back if reviewer is wrong (with reasoning)

## Integration with Workflows

**Subagent-Driven Development:**
- Review after EACH task
- Catch issues before they compound
- Fix before moving to next task

**Executing Plans:**
- Review after each task or at natural checkpoints

## Red Flags

**Never:**
- Skip review because "it's simple"
- Ignore CRITICAL issues
- Proceed with unfixed IMPORTANT issues

**If reviewer wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
