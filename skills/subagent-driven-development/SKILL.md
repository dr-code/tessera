---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks in the current session
---

# Subagent-Driven Development

<!-- Adapted from obra/superpowers — Tessera graph discipline injected into subagent prompts -->

Execute plan by dispatching fresh subagent per task, with two-stage review after each: spec compliance review first, then code quality review.

**Core principle:** Fresh subagent per task + two-stage review = high quality, fast iteration.

**Continuous execution:** Do not pause between tasks unless BLOCKED, genuinely ambiguous, or all tasks complete.

## When to Use

Use when you have a written implementation plan with independent tasks and want to stay in the current session. For parallel-session execution, use `executing-plans` instead.

## Tessera Coordinator Discipline

**At the start of each dispatch round (before dispatching any subagent) — if tessera MCP is configured:**
```
1. graph_continue (mandatory first call for the coordinator too)
2. graph_retrieve with the current task's key terms
```
This keeps the coordinator's routing accurate as files change during execution.

## Tessera Subagent Discipline

**Every implementer subagent prompt you dispatch MUST include these instructions:**

```
Tessera graph policy (if tessera MCP is configured in this session):
1. Call graph_continue as your FIRST tool call
2. Call graph_retrieve with this task's key terms
3. Read all recommended_files via graph_read before exploring
4. After each file edit, call graph_register_edit with file::symbol notation
   - If graph_continue returned an active_checklist, include the checklist_item_id
     for the task you just completed
5. Call graph_lock_decision when you make an architectural choice
```

This ensures Tessera's compliance tracker stays updated as each subagent works.

## The Process

### Per Task Loop

1. **Dispatch implementer subagent**
   - Craft a focused, self-contained prompt with exactly the context needed
   - Include the Tessera graph policy block above
   - Include the specific task steps, file paths, and expected test outcomes
   - Include: "Do NOT inherit session history. Work only from this prompt."

2. **Implementer questions?**
   - Answer questions, provide context, re-dispatch

3. **Implementer implements, tests, commits, self-reviews**

4. **Dispatch spec reviewer subagent**
   - Provide: the plan's task spec + the actual diff (`git diff HEAD~1`)
   - Ask: Does code match spec? List any gaps.

5. **Spec gaps?**
   - Dispatch implementer to fix gaps

6. **Dispatch code quality reviewer subagent**
   - Provide: the diff + project coding standards from CLAUDE.md
   - Ask: Code quality, security, type safety, test adequacy. Severity: CRITICAL/IMPORTANT/MINOR.

7. **Quality issues?**
   - Fix CRITICAL and IMPORTANT before proceeding

8. **Mark task complete** — if tessera MCP is configured, `graph_register_edit` marks the checklist item done

9. **Next task**

### After All Tasks Complete

**If tessera MCP is configured:** run `tessera-verify` to confirm plan compliance before finishing.

```
All checklist items done? → tessera-verify passes → proceed
Missing items? → complete them first
```

Then invoke `finishing-a-development-branch` skill.

## Subagent Prompt Template

```markdown
## Task: [Task name from plan]

**Goal:** [One sentence]

**Files to modify:**
- Create: `path/to/file`
- Modify: `path/to/existing`

**Steps:**
[Paste exact steps from plan]

**Verification:**
[Exact test commands and expected output]

**Tessera graph policy (if tessera MCP is configured):**
- Call graph_continue as your FIRST tool call
- Read recommended_files via graph_read
- After each edit: graph_register_edit(files=["file::symbol"], summary="...")
- Lock architectural decisions: graph_lock_decision(...)

**Do NOT inherit session history. Work only from this prompt.**
**Return: Summary of what you implemented and what tests pass.**
```

## Red Flags

**Never:**
- Skip the two-stage review (spec then quality)
- Proceed with unfixed CRITICAL issues
- Give subagents your session's full history
- Pause to ask "should I continue?" between tasks unless genuinely blocked
