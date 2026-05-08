---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists via native tools or git worktree fallback
---

# Using Git Worktrees

<!-- Adapted from obra/superpowers — tessera scan step added after setup -->

## Overview

Ensure work happens in an isolated workspace. Prefer your platform's native worktree tools. Fall back to manual git worktrees only when no native tool is available.

**Announce at start:** "I'm using the using-git-worktrees skill to set up an isolated workspace."

## Step 0: Detect Existing Isolation

Before creating anything, check if you are already in an isolated workspace:

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
```

Submodule guard: verify you are not in a submodule before concluding "already in a worktree":
```bash
git rev-parse --show-superproject-working-tree 2>/dev/null
```

- If `GIT_DIR != GIT_COMMON` (and not a submodule): already in a linked worktree. Skip to Step 3.
- If `GIT_DIR == GIT_COMMON`: normal repo. Ask for consent before creating a worktree.

## Step 1: Create Isolated Workspace

Try in order:

**1a. Native worktree tool (preferred):** If a tool like `EnterWorktree`, `WorktreeCreate`, or `/worktree` command is available, use it and skip to Step 3. Never fight the harness.

**1b. Git worktree fallback (only if no native tool):**

Directory priority:
1. Declared user preference in instructions
2. Existing `.worktrees/` or `worktrees/` at project root
3. Existing `~/.config/superpowers/worktrees/<project>/`
4. Default: `.worktrees/` at project root

Safety check for project-local directories:
```bash
git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
```
If NOT ignored: add to `.gitignore`, commit, then proceed.

```bash
git worktree add "$path" -b "$BRANCH_NAME"
cd "$path"
```

## Step 2: Project Setup

```bash
if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
if [ -f pyproject.toml ]; then uv sync; fi
if [ -f package.json ]; then npm install; fi
```

## Step 3: Tessera Context Rebuild

**If tessera MCP is configured in this session:** run `tessera scan .` after setup.

```bash
tessera scan .
```

This registers the new worktree's files in Tessera's graph so `graph_continue` can route reads correctly in the new workspace.

## Step 4: Verify Clean Baseline

```bash
# Python: uv run pytest
# Node: npm test
# Go: go test ./...
```

If tests fail: report failures, ask whether to proceed or investigate.

**Report:**
```
Worktree ready at <full-path>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Quick Reference

| Situation | Action |
|-----------|--------|
| Already in linked worktree | Skip creation (Step 0) |
| Native worktree tool available | Use it (Step 1a) |
| No native tool | Git worktree fallback (Step 1b) |
| Directory not ignored | Add to .gitignore + commit |
| Tests fail during baseline | Report failures + ask |

## Red Flags

**Never:**
- Create a worktree when Step 0 detects existing isolation
- Use `git worktree add` when a native worktree tool is available
- Skip baseline test verification
- Skip `tessera scan` when tessera is active (graph becomes stale)
