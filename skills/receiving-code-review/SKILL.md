---
name: receiving-code-review
description: Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical rigor and verification, not performative agreement or blind implementation
---

# Code Review Reception

<!-- Adapted from obra/superpowers — Tessera graph context and edit registration added -->

## Tessera Context Load

**Before evaluating any feedback — if tessera MCP is configured:**
```
1. graph_continue (mandatory first call)
2. graph_action_summary — surface locked decisions; flag if feedback would violate them
```

## Overview

Code review requires technical evaluation, not emotional performance.

**Core principle:** Verify before implementing. Ask before assuming. Technical correctness over social comfort.

## The Response Pattern

```
1. READ: Complete feedback without reacting
2. UNDERSTAND: Restate requirement in own words (or ask)
3. VERIFY: Check against codebase reality
4. EVALUATE: Technically sound for THIS codebase?
5. RESPOND: Technical acknowledgment or reasoned pushback
6. IMPLEMENT: One item at a time, test each
```

## Forbidden Responses

**NEVER:**
- "You're absolutely right!" (performative)
- "Great point!" (performative)
- "Let me implement that now" (before verification)

**INSTEAD:**
- Restate the technical requirement
- Ask clarifying questions
- Push back with technical reasoning if wrong
- Just start working (actions > words)

## Handling Unclear Feedback

If any item is unclear: STOP. Ask for clarification on ALL unclear items before implementing any of them.

Items may be related. Partial understanding = wrong implementation.

## Source-Specific Handling

**From project owner:**
- Trusted — implement after understanding
- Still ask if scope unclear
- No performative agreement

**From external reviewers:**
1. Check: Technically correct for THIS codebase?
2. Check: Breaks existing functionality?
3. Check: Reason for current implementation?
4. Check: Works on all platforms/versions?

If conflicts with prior architectural decisions (check `graph_action_summary` if tessera MCP configured): STOP and discuss with project owner.

## YAGNI Check for "Professional" Features

If reviewer suggests "implementing properly": grep codebase for actual usage.
- If unused: "This isn't called. Remove it (YAGNI)?"
- If used: Then implement properly.

## When To Push Back

Push back when:
- Suggestion breaks existing functionality
- Reviewer lacks full context
- Violates YAGNI (unused feature)
- Technically incorrect for this stack
- Conflicts with locked architectural decisions

## Acknowledging Correct Feedback

```
✅ "Fixed. [Brief description of what changed]"
✅ "Good catch — [specific issue]. Fixed in [location]."
✅ [Just fix it and show in the code]

❌ "You're absolutely right!"
❌ "Great point!"
❌ Any gratitude expression
```

Actions speak. Just fix it.

## After Implementing Fixes

**If tessera MCP is configured:** after each fix, call `graph_register_edit`:
```
graph_register_edit(
  files   = ["path/to/fixed/file::symbol"],
  summary = "<what was fixed and why>",
  checklist_item_id = <id from active_checklist if this fix maps to a plan item>
)
```

This keeps the graph cache current and marks plan checklist items done if the review fixes were plan-tracked.
