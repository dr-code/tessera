---
description: "MDD workflow — Document → Audit → Fix → Verify. Build features or audit existing code using Manual-First Development."
scope: project
argument-hint: "<feature-description> or audit [section]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion
---

# MDD — Manual-First Development Workflow

**$ARGUMENTS**

MDD is the core development workflow. Every feature starts with documentation, every fix starts with an audit. No exceptions.

## Step 0 — Detect Mode

Parse `$ARGUMENTS` to determine the mode:

- If arguments start with `audit` → **Audit Mode** (jump to Phase A)
- If arguments start with `status` → **Status Mode** (jump to Phase S)
- If arguments are empty → ask the user what they want to do
- Otherwise → **Build Mode** (the default — jump to Phase 1)

---

## BUILD MODE — New Feature Development

### Phase 1 — Understand the Feature

Read the user's description: **$ARGUMENTS**

Before writing anything, gather context:

1. **Read `CLAUDE.md`** — understand project rules
2. **Read `docs/PROJECT_CONTEXT.md` if present** — use as primary feature map and quick reference
3. **Read `docs/ARCHITECTURE_SUMMARY.md` if present** — architecture brief
4. **Read only the specific feature doc(s) relevant to this request** — do not scan all docs by default
5. **Read `docs/ARCHITECTURE.md` only if the task changes or crosses architectural boundaries**
6. **Read subtree `CLAUDE.md` files for the areas being touched** (e.g., `server/CLAUDE.md`, `client/CLAUDE.md`) if present
7. **Scan `src/`** — only the relevant area for the requested feature

Then ask the user targeted questions using AskUserQuestion. Ask ALL relevant questions upfront in a single interaction — don't spread them across multiple turns:

**Always ask:**
- "Does this feature need database storage? If so, what data does it store?"
- "Does this feature have API endpoints? What operations (create, read, update, delete)?"
- "Does this feature depend on any existing features?" (list the relevant ones from `docs/PROJECT_CONTEXT.md` or `docs/*.md`)
- "Are there any edge cases or error scenarios you already know about?"

**Ask if relevant:**
- "Does this need authentication/authorization?"
- "Does this need real-time updates (WebSocket)?"
- "Does this need background processing (queues, cron)?"
- "Does this integrate with any external services?"

Wait for all answers before proceeding.

### Phase 2 — Write the MDD Documentation

Create the feature documentation file at `docs/<feature-name>.md`.

The doc MUST follow this exact structure:

```markdown
---
id: <feature-name>
title: <Feature Title>
edition: <project name or "Both">
depends_on: [<list of documentation IDs this feature depends on>]
source_files:
  - <files that will be created>
routes:
  - <API routes if applicable>
models:
  - <database collections if applicable>
test_files:
  - <test files that will be created>
known_issues: []
---

# <Feature Title>

## Purpose

<2-3 sentences explaining what this feature does and why it exists>

## Architecture

<How this feature fits into the system. Include a simple diagram if helpful.>

## Data Model

<Collection/table schema if applicable. Field names, types, constraints, indexes.>

## API Endpoints

<For each endpoint: method, path, auth required, request body, response shape, error cases.>

## Business Rules

<Validation rules, state machines, invariants, edge cases.>

## Dependencies

<What this feature requires from other features. List by documentation ID.>

## Known Issues

<Empty for new features. Will be populated by future audits.>
```

**CRITICAL:** This documentation is the source of truth. Everything that follows is generated FROM this doc. Take time to make it complete and accurate.

Show the completed doc to the user and ask: **"Does this accurately describe what you want to build? Anything to add or change?"**

Wait for confirmation before proceeding.

### Phase 3 — Generate Test Skeletons

Read the documentation file created in Phase 2. From the endpoints, business rules, and edge cases documented, generate test skeletons.

**Create test file at:** `tests/unit/<feature-name>.test.ts`

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('<Feature Name>', () => {
  // For each endpoint documented:
  describe('<operation>', () => {
    it('should <expected behavior from docs>', async () => {
      // Arrange
      // Act
      // Assert — minimum 3 assertions based on documented response shape
      expect.fail('Not implemented — MDD skeleton');
    });

    it('should return <error> when <edge case from docs>', async () => {
      expect.fail('Not implemented — MDD skeleton');
    });
  });
});
```

**Rules for skeleton generation:**
- One `describe` block per endpoint or business rule
- One `it` block per documented behavior (happy path + each error case)
- Every `it` block has `expect.fail('Not implemented — MDD skeleton')` as placeholder
- NO implementation yet — just the structure from the docs
- Include the exact response shapes and status codes from the documentation

**If E2E tests are needed** (the feature has UI): also create `tests/e2e/<feature-name>.spec.ts` with Playwright skeletons following the same pattern.

Tell the user:
```
📋 Test skeletons created:
   - tests/unit/<feature-name>.test.ts (<N> test cases)
   - tests/e2e/<feature-name>.spec.ts (<N> test cases) [if applicable]

These tests will FAIL until implementation is complete.
That's the point — they're the finish line.
```

### Phase 4 — Present the Build Plan

Before writing any implementation code, present a clear plan:

```
🔨 MDD Build Plan for: <Feature Name>

Documentation: docs/<feature-name>.md ✅
Test skeletons: <N> tests across <N> files ✅

Implementation steps:
  Step 1 (<name>): <what will be created> — est. <time>
  Step 2 (<name>): <what will be created> — est. <time>
  Step 3 (<name>): <what will be created> — est. <time>
  ...

Total files to create: <N>
Total estimated time: <N> minutes
Tests to satisfy: <N>

Ready to build? (yes / modify plan / stop here)
```

**Step naming is MANDATORY** — every step has a unique name so the user can reference it.

**Estimation rules:**
- Types file: ~2 min
- Handler with 5 CRUD ops: ~5 min
- Route file (thin): ~3 min
- Wiring into server: ~1 min
- Test implementation: ~5 min per 10 tests
- Complex business logic: ~10 min per function

Wait for user confirmation.

### Phase 5 — Implement (Test-Driven)

For each step in the plan:

1. **Read the MDD doc** — refresh context on what this step needs
2. **Read the test skeleton** for the relevant tests
3. **Implement the code** that makes the tests pass
4. **Run tests** after each step: `pnpm test:unit -- --grep "<feature>"`
5. **Report progress:**
   ```
   Step 1 (Types): ✅ — src/types/<feature>.ts created
   Step 2 (Handler): ✅ — 4/5 tests passing, fixing edge case...
   Step 2 (Handler): ✅ — 5/5 tests passing
   Step 3 (Routes): 🔄 in progress...
   ```

**CRITICAL:** If a test fails, fix the implementation — NOT the test. The tests were generated from the documentation. If the test seems wrong, re-read the doc. If the doc is wrong, ask the user.

After all steps complete:

```bash
pnpm typecheck     # Must pass
pnpm test:unit     # All tests must pass (including pre-existing)
```

### Phase 6 — Verify + Report

After implementation is complete:

1. **Run full test suite:** `pnpm test:unit`
2. **Run typecheck:** `pnpm typecheck`
3. **Update `docs/PROJECT_CONTEXT.md`** — add or refresh the feature entry in the lookup table
4. **Update `docs/ARCHITECTURE_SUMMARY.md`** only if the feature changes a service boundary, data flow, shared abstraction, or global invariant. Skip for feature-only changes.
5. **Update `docs/<feature>.md`** — add any `known_issues` discovered during implementation
6. **Update `CLAUDE.md`** if new project-wide patterns were established

Present the final report:

```
✅ MDD Complete: <Feature Name>

Documentation: docs/<feature-name>.md
Files created: <list>
Tests: <N>/<N> passing
Typecheck: Clean

New patterns established: <any new rules worth adding to CLAUDE.md>

Branch: feat/<feature-name>
Ready for review — run `git diff main...HEAD` to see all changes.
```

### When to Suggest Subtree CLAUDE.md Files

Claude Code loads subtree `CLAUDE.md` files only when working in that directory — the real mechanism for runtime-selective context loading (not `@path` imports in root CLAUDE.md).

When a domain grows complex enough to warrant area-specific rules, suggest creating:
- `server/CLAUDE.md` — backend auth chain, route patterns, database conventions, test expectations
- `client/CLAUDE.md` — state management, routing, form conventions, API client usage
- `client/src/features/<feature>/CLAUDE.md` — feature-specific invariants and edge cases

**Rules:**
- Only suggest creating subtree CLAUDE.md when the area has meaningful, area-specific complexity
- Never pre-create empty subtree CLAUDE.md files
- Subtree CLAUDE.md is preferred over `@path` imports in root CLAUDE.md for domain-specific rules

---

## AUDIT MODE — `/mdd audit [section]`

Triggered when arguments start with `audit`.

### Phase A1 — Scope

If a section is specified (e.g., `/mdd audit database`), audit only that feature.
If no section, audit the entire project.

1. **Read `docs/PROJECT_CONTEXT.md` if present** — use it as the primary feature map
2. Only fall back to **scanning `docs/*.md`** if `PROJECT_CONTEXT.md` is absent or incomplete
3. **If no `docs/` directory exists:** Create it. Also ensure `.mdd/audits/` exists for audit reports. Then tell the user: "No MDD documentation found. Run `/mdd` for each feature to create docs first, or I can scan the codebase and create them now. Which do you prefer?"
   - If "scan": read all source files and generate documentation files (Phase 0)
   - If "manual": exit and let the user create docs per feature

### Phase A2 — Read + Notes

For each feature (or the specified section):

1. Read ALL source files listed in the documentation's `source_files` frontmatter
2. Write notes to `.mdd/audits/notes-<date>.md`
3. **CRITICAL: Write every 2 features** — do not accumulate in memory

Note format per feature:
```markdown
### [<feature-id>] <Feature Name>
**Files read:** <list>
**Findings:**
- <severity emoji> <finding description>
**Test coverage:** <existing test count> / <endpoint count>
**Doc accuracy:** <any discrepancies between docs and code>
```

### Phase A3 — Analyze

Read ONLY the notes file (NOT source code again). Produce findings report at `.mdd/audits/report-<date>.md`:

1. Executive summary
2. Feature completeness matrix
3. Findings by severity (CRITICAL / HIGH / MEDIUM / LOW)
4. Test coverage summary
5. Fix plan with effort estimates

### Phase A4 — Present Findings

Show the user:
```
🔍 MDD Audit Complete

Findings: <N> total (<N> Critical, <N> High, <N> Medium, <N> Low)
Report: .mdd/audits/report-<date>.md

Top issues:
  1. <most critical finding>
  2. <second most critical>
  3. <third most critical>

Estimated fix time: <N> hours (traditional) → <N> minutes (MDD)

Fix all now? (yes / review report first / fix only critical+high)
```

If user says yes (or selects a subset):

### Phase A5 — Fix

Read the findings report. For each finding to fix:
1. Read the specific source files
2. Apply the fix
3. Write or update tests
4. Run tests after each fix group

Report progress per finding. Update documentation `known_issues` to remove fixed items.

---

## STATUS MODE — `/mdd status`

Quick overview of MDD state for the project:

1. **Scan `docs/`** — count feature docs
2. **Scan `.mdd/audits/`** — find latest audit report
3. **Count tests** — `pnpm test:unit --reporter=json 2>/dev/null | jq '.numTotalTests'`
4. **Count known issues** — grep `known_issues` across all docs

Present:
```
📊 MDD Status

Feature docs:     <N> files in documentation/
Last audit:       <date> (<N> findings, <N> fixed, <N> open)
Test coverage:    <N> unit tests, <N> E2E tests
Known issues:     <N> tracked across <N> features
Quality gates:    <N> files over 300 lines

Run `/mdd audit` to refresh or `/mdd <feature>` to build something new.
```

---

## Auto-Branch (All Modes)

Before creating or modifying any files, check the current branch:

```bash
git branch --show-current
```

**Default behavior** (`auto_branch = true` in `claude-mastery-project.conf`):
- If on `main` or `master`:
  - Build mode: `git checkout -b feat/<feature-name>`
  - Audit mode: `git checkout -b fix/mdd-audit-<date>`
- If already on a feature branch: proceed

---

## CLAUDE.md Update Trigger

After ANY MDD operation that changes code, check if new patterns were established that should be added to CLAUDE.md. If so, suggest the addition:

```
💡 New pattern detected: <description>
Add to CLAUDE.md? (yes / no)
```

This is the MDD feedback loop — every project interaction improves future interactions.
