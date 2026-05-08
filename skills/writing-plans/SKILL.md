---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

<!-- Adapted from obra/superpowers — Tessera graph context + plan_save integration added -->

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for the codebase and questionable taste. Document everything they need: which files to touch, code, testing, docs, how to verify. Bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md`

## Phase 0: Tessera Context Load

**If tessera MCP is configured in this session:**

```
1. graph_continue (mandatory first call)
2. graph_retrieve with the feature's key terms
3. graph_read each recommended file (at high confidence: read all; medium/low: up to max_supplementary_files)
4. graph_action_summary — surface any locked decisions that constrain this plan
```

This grounds the file structure analysis in actual codebase reality before writing a single task.

## Scope Check

If the spec covers multiple independent subsystems, suggest breaking into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified:

- Design units with clear boundaries and well-defined interfaces
- Prefer smaller, focused files over large ones
- Files that change together should live together
- In existing codebases (informed by graph_retrieve above), follow established patterns

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1:** Write the failing test

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2:** Run test to verify it fails

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3:** Write minimal implementation

- [ ] **Step 4:** Run test to verify it passes

- [ ] **Step 5:** Commit
````

## No Placeholders

Every step must contain the actual content an engineer needs. Never write:
- "TBD", "TODO", "implement later"
- "Add appropriate error handling" (without showing the code)
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code — engineer may be reading tasks out of order)

## Self-Review

After writing the complete plan, check against the spec:

1. **Spec coverage:** Can you point to a task that implements each requirement?
2. **Placeholder scan:** Any red flags from the list above?
3. **Type consistency:** Do method signatures match across tasks?

Fix inline. No need to re-review.

## Archive with Tessera

**After the plan is written and self-reviewed — if tessera MCP is configured:**

Call the `plan_save` MCP tool:

```
plan_save(
  project_name = "<short project identifier>",
  subtask_name = "<feature or subtask name>",
  task         = "<one sentence describing what the plan builds>",
  plan_markdown = "<full plan markdown content>"
)
```

This registers the plan in Tessera's SQLite archive, parses the `- [ ]` checklist items, and enables `tessera-verify` to track compliance after implementation.

**Save the returned `plan_id`** — it appears in `graph_continue` output as `active_checklist` and is used by `graph_register_edit` to auto-mark tasks complete.

## Execution Handoff

After saving the plan, offer execution choice:

**"Plan complete and saved to `docs/plans/<filename>.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — Fresh subagent per task, two-stage review

**2. Inline Execution** — Execute tasks in this session with batch checkpoints

**Which approach?"**

- Subagent-Driven: invoke `subagent-driven-development` skill
- Inline Execution: invoke `executing-plans` skill
