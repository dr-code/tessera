---
name: verification-before-completion
description: Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always
---

# Verification Before Completion

<!-- Adapted from obra/superpowers — Tessera compliance check (tessera-verify) added as final gate -->

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

## Tessera Compliance Gate

**If tessera MCP is configured AND a plan was registered with `plan_save` — run `tessera-verify` before any other verification:**

```
1. Run the tessera-verify skill
2. Review the compliance report:
   - All plan checklist items should be marked done
   - All target files should appear in git diff
3. If items are missing: complete them before proceeding
4. Only after tessera-verify is clean: run unit tests + linter
```

This closes the loop between what was planned and what was built.

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim
```

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Requirements met | Line-by-line checklist | Tests passing |
| Plan complete | tessera-verify: all items done | Checklist looks done visually |

## Red Flags — STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification
- About to commit/push/PR without verification
- Relying on partial verification
- Thinking "just this once"
- **ANY wording implying success without having run verification**

## Key Patterns

**Tests:**
```
Run test command → See: N/N pass → "All tests pass"
NOT: "Should pass now" / "Looks correct"
```

**TDD Regression:**
```
Write → Run (pass) → Revert fix → Run (MUST FAIL) → Restore → Run (pass)
NOT: "I've written a regression test" (without red-green verification)
```

**Plan compliance:**
```
Run tessera-verify → See: all items complete → "Plan requirements met"
NOT: "I implemented all the tasks"
```

## The Bottom Line

**No shortcuts for verification.** Run the command. Read the output. THEN claim the result.
