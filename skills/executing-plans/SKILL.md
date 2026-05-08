---
name: executing-plans
description: Use when you have a written implementation plan to execute in a separate session with review checkpoints
---

# Executing Plans

<!-- Adapted from obra/superpowers — Tessera graph discipline added to execution loop -->

Load plan, review critically, execute all tasks, report when complete.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

**Note:** If subagents are available, use `subagent-driven-development` instead — quality is significantly higher.

## Phase 0: Tessera Context Load

**If tessera MCP is configured in this session:**

```
1. graph_continue (mandatory first call)
2. graph_retrieve with the plan's key feature terms
3. Read recommended_files via graph_read
```

This ensures you have current codebase context before executing the first task.

## Step 1: Load and Review Plan

1. Read plan file (or use plan from current conversation)
2. Review critically — identify any questions or concerns
3. If concerns: raise with user before starting
4. If no concerns: create task list and proceed

## Step 2: Execute Tasks

For each task:

1. Mark as in_progress
2. Follow each step exactly (plan has bite-sized steps)
3. Run verifications as specified
4. **If tessera MCP is configured:** after each file edit, call `graph_register_edit`
   - Include `checklist_item_id` if `graph_continue` returned an active checklist
5. When a significant architectural choice is made (pattern selected, dependency added, boundary drawn):
   ```
   graph_lock_decision(
     summary = "<one sentence>",
     scope   = "file" | "module" | "project",
     files   = ["affected/file"]
   )
   ```
6. Mark as completed

## Step 3: Complete Development

After all tasks complete and verified:

**If tessera MCP is configured:** run the `tessera-verify` skill first to confirm compliance.

Then invoke `finishing-a-development-branch` skill.

## When to Stop and Ask for Help

**STOP immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- Verification fails repeatedly

Ask for clarification rather than guessing.

## Remember

- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Stop when blocked, don't guess
- Never start implementation on main/master without explicit user consent
