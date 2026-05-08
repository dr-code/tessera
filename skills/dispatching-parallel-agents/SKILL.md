---
name: dispatching-parallel-agents
description: Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
---

# Dispatching Parallel Agents

<!-- From obra/superpowers — no Tessera-specific adaptation needed -->

## Overview

When you have multiple unrelated failures (different test files, different subsystems, different bugs), investigate them concurrently.

**Core principle:** Dispatch one agent per independent problem domain. Let them work concurrently.

## When to Use

- 3+ test files failing with different root causes
- Multiple subsystems broken independently
- Each problem can be understood without context from others
- No shared state between investigations

**Don't use when:**
- Failures are related (fix one might fix others)
- Agents would interfere with each other (same files, same resources)

## Tessera Context Load

**Before dispatching any agents — if tessera MCP is configured:**
```
1. graph_continue (mandatory first call for the coordinator)
2. graph_retrieve with the failing component names as query
```
This routes the coordinator to the most relevant files for understanding the problem space before splitting work into agents.

## The Pattern

### 1. Identify Independent Domains

Group failures by what's broken:
- File A tests: one component
- File B tests: different component
- File C tests: yet another component

Each domain is independent.

### 2. Create Focused Agent Tasks

Each agent gets:
- **Specific scope:** One test file or subsystem
- **Clear goal:** Make these tests pass
- **Constraints:** Don't change other code
- **Expected output:** Summary of what you found and fixed

Include the Tessera graph discipline in each agent prompt (if tessera MCP is configured):
```
- Call graph_continue as your FIRST tool call
- Call graph_retrieve with this task's key terms
- Read recommended_files via graph_read before exploring
- After each file edit: graph_register_edit(files=["file::symbol"], summary="...")
- Lock architectural choices: graph_lock_decision(summary, scope, files)
```

### 3. Dispatch in Parallel

Use Task tool — all dispatches in a single message so they run concurrently.

### 4. Review and Integrate

- Read each summary
- Verify fixes don't conflict
- Run full test suite
- Integrate all changes

## Agent Prompt Structure

```markdown
Fix the failing tests in <file>:

1. "<test name>" - expects <X>
2. "<test name>" - expects <Y>

Your task:
1. Read the test file
2. Identify root cause
3. Fix — do NOT just adjust expectations
4. Return: what you found and what you fixed

Do NOT change code outside this file.
```

## Common Mistakes

- **Too broad:** "Fix all the tests" — agent gets lost
- **No context:** Paste the error messages and test names
- **No constraints:** Agent might refactor everything
- **Vague output:** Specify what you need back

## Verification

After agents return:
1. Review each summary — understand what changed
2. Check for conflicts — did agents edit the same code?
3. Run full suite — verify all fixes work together
