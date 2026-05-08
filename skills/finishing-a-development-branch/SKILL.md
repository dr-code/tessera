---
name: finishing-a-development-branch
description: Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup
---

# Finishing a Development Branch

<!-- Adapted from obra/superpowers — tessera-verify compliance gate added before Step 1 -->

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## Phase 0: Tessera Compliance Gate

**If tessera MCP is configured AND a plan was registered with `plan_save`:**

Run the `tessera-verify` skill BEFORE verifying tests:

```
1. Run tessera-verify
2. Review compliance report
   - All checklist items done?
   - All target files in git diff?
3. If gaps: complete missing implementation before proceeding
```

Only after tessera-verify is clean: proceed to Step 1.

## Step 1: Verify Tests

```bash
# Python: uv run pytest
# Node: npm test
# Go: go test ./...
```

**If tests fail:**
```
Tests failing (<N> failures). Must fix before completing.
```
Stop. Don't proceed to options.

## Step 2: Detect Environment

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
```

- Normal repo or named-branch worktree: show 4 options
- Detached HEAD worktree: show 3 options (no merge)

## Step 3: Determine Base Branch

```bash
git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
```

## Step 4: Present Options

**Normal repo / named-branch worktree:**
```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

**Detached HEAD:**
```
1. Push as new branch and create a Pull Request
2. Keep as-is (I'll handle it later)
3. Discard this work
```

## Step 5: Execute Choice

**Option 1 — Merge locally:**
```bash
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
cd "$MAIN_ROOT"
git checkout <base-branch> && git pull && git merge <feature-branch>
```
Run tests on merged result. Only on success: cleanup worktree, delete branch.

**Option 2 — Push and create PR:**
```bash
git push -u origin <feature-branch>
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
<2-3 bullets>

## Test Plan
- [ ] <verification steps>
EOF
)"
```
Do NOT clean up worktree — user needs it for PR feedback.

**Option 3 — Keep as-is:**
Report: "Keeping branch <name>."

**Option 4 — Discard:**
Require typed "discard" confirmation before deleting anything.

## Step 6: Cleanup Worktree (Options 1 and 4 only)

Only clean up worktrees created by this skill (under `.worktrees/`, `worktrees/`, or `~/.config/superpowers/worktrees/`). Never remove harness-owned workspaces.

```bash
cd "$MAIN_ROOT"
git worktree remove "$WORKTREE_PATH"
git worktree prune
```

## Red Flags

**Never:**
- Proceed with failing tests
- Proceed with failing tessera-verify
- Delete work without typed confirmation
- Force-push without explicit request
- Clean up worktrees you didn't create
