---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
---

# Systematic Debugging

<!-- Adapted from obra/superpowers — Tessera graph_impact added to Phase 1 -->

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## Tessera: Map Blast Radius First

**Before starting Phase 1 — if tessera MCP is configured in this session:**

```
1. graph_continue (mandatory first call)
2. graph_impact(changed_files=["<file where bug was reported>"])
```

`graph_impact` shows which other files depend on the broken code. This tells you:
- How far a fix might ripple
- Which tests are likely affected
- Whether this is a leaf-level bug or a core abstraction issue

Surface this impact map before investigating root cause.

## The Four Phases

You MUST complete each phase before proceeding to the next.

### Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

1. **Read error messages carefully** — stack traces, line numbers, error codes
2. **Reproduce consistently** — can you trigger it reliably every time?
3. **Check recent changes** — git diff, recent commits, new dependencies
4. **Gather evidence in multi-component systems**
   - Add diagnostic logging at each component boundary
   - Run once to gather evidence showing WHERE it breaks
   - Then analyze to identify the failing component
5. **Trace data flow** — where does the bad value originate? Trace backward through the call stack

### Phase 2: Pattern Analysis

1. **Find working examples** — similar working code in the same codebase (use `graph_retrieve` if tessera MCP configured)
2. **Compare against references** — read the reference implementation completely
3. **Identify differences** — list every difference, however small
4. **Understand dependencies** — what settings, config, environment does this need?

### Phase 3: Hypothesis and Testing

1. **Form single hypothesis** — "I think X is the root cause because Y"
2. **Test minimally** — smallest possible change to test hypothesis
3. **Verify before continuing** — did it work? If not, form NEW hypothesis. Don't stack fixes.
4. **When you don't know** — say so; don't pretend

### Phase 4: Implementation

1. **Create failing test case** — use `test-driven-development` skill
2. **Implement single fix** — address root cause, ONE change at a time
3. **Verify fix** — test passes, no regressions, issue actually resolved
4. **If fix doesn't work** — return to Phase 1 with new information
5. **If 3+ fixes failed** — STOP. Question the architecture. Discuss with user.

## Red Flags — STOP and Follow Process

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- Proposing solutions before tracing data flow
- "One more fix attempt" when already tried 2+
- Each fix reveals a new problem in a different place

**All of these mean: Return to Phase 1.**

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare | Identify differences |
| **3. Hypothesis** | Form theory, test minimally | Confirmed or new hypothesis |
| **4. Implementation** | Create test, fix, verify | Bug resolved, tests pass |

## Related Skills

- `test-driven-development` — for creating failing test case (Phase 4, Step 1)
- `verification-before-completion` — verify fix worked before claiming success
