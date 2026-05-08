---
description: "MDD workflow — Document → Audit → Fix → Verify. Build features or audit existing code using Manual-First Development."
scope: project
argument-hint: "<feature-description> | audit [section] | status"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion
---

# MDD — Manual-First Development Workflow

**$ARGUMENTS**

MDD is the core development workflow. Every feature starts with documentation, every fix starts with an audit. No exceptions.

## Step 0 — Detect Mode

Parse `$ARGUMENTS` to determine the mode:

- Starts with `audit` → **Audit Mode** (jump to Phase A)
- Starts with `status` → **Status Mode** (jump to Phase S)
- Empty → ask the user what they want to do
- Otherwise → **Build Mode** (default — jump to Phase 1)

---

## BUILD MODE — New Feature Development

### Phase 1 — Understand the Feature

Read the user's description: **$ARGUMENTS**

Before writing anything, gather context:

1. Read `CLAUDE.md` — understand project rules
2. Read `docs/PROJECT_CONTEXT.md` if present — use as primary feature map
3. Read `docs/ARCHITECTURE_SUMMARY.md` if present — architecture brief
4. If tessera MCP is active: call `graph_continue` with key terms from `$ARGUMENTS`, then `graph_retrieve` to surface relevant existing code; read all `recommended_files`
5. Read the specific feature doc(s) relevant to this request — do not scan all docs
6. Read `docs/ARCHITECTURE.md` only if the task crosses architectural boundaries
7. Read subtree `CLAUDE.md` files for the areas being touched if present

Then ask targeted questions using AskUserQuestion — ask ALL relevant questions upfront:

**Always ask:**
- Does this feature need database storage? If so, what data does it store?
- Does this feature have API endpoints? What operations (create, read, update, delete)?
- Does this feature depend on any existing features?
- Are there any edge cases or error scenarios you already know about?

**Ask if relevant:**
- Does this need authentication/authorization?
- Does this need real-time updates?
- Does this need background processing?
- Does this integrate with any external services?

Wait for all answers before proceeding.

### Phase 2 — Write the MDD Documentation

Create the feature documentation file at `docs/<feature-name>.md`.

The doc MUST follow this exact structure:

```markdown
---
id: <feature-name>
title: <Feature Title>
depends_on: [<list of documentation IDs this feature depends on>]
source_files:
  - <files that will be created>
routes:
  - <API routes if applicable>
models:
  - <database tables/collections if applicable>
test_files:
  - <test files that will be created>
known_issues: []
---

# <Feature Title>

## Purpose

<2-3 sentences explaining what this feature does and why it exists>

## Architecture

<How this feature fits into the system. Include a simple ASCII diagram if helpful.>

## Data Model

<Schema if applicable. Field names, types, constraints, indexes.>

## API Endpoints

<For each endpoint: method, path, auth required, request body, response shape, error cases.>

## Business Rules

<Validation rules, state machines, invariants, edge cases.>

## Dependencies

<What this feature requires from other features. List by documentation ID.>

## Known Issues

<Empty for new features. Will be populated by future audits.>
```

**This documentation is the source of truth.** Everything that follows is generated FROM this doc.

Show the completed doc to the user and ask: **"Does this accurately describe what you want to build? Anything to add or change?"**

Wait for confirmation before proceeding.

### Phase 3 — Generate Test Skeletons

Read the documentation file. From the endpoints, business rules, and edge cases documented, generate test skeletons.

Detect the project's test framework from `CLAUDE.md`, `pyproject.toml`, or `package.json`:
- Python/pytest → `tests/<feature-name>_test.py`
- TypeScript/Vitest → `tests/unit/<feature-name>.test.ts`
- TypeScript/Jest → `tests/<feature-name>.test.ts`
- Go → `<package>/<feature>_test.go`

**Python (pytest) skeleton:**
```python
"""Tests for <feature-name>."""
import pytest

class Test<FeatureName>:
    def test_<expected_behavior>(self):
        # Arrange
        # Act
        # Assert
        pytest.fail("Not implemented — MDD skeleton")

    def test_returns_error_when_<edge_case>(self):
        pytest.fail("Not implemented — MDD skeleton")
```

**TypeScript (Vitest) skeleton:**
```typescript
import { describe, it, expect } from 'vitest';

describe('<Feature Name>', () => {
  describe('<operation>', () => {
    it('should <expected behavior from docs>', async () => {
      // Arrange / Act / Assert — minimum 3 assertions
      expect.fail('Not implemented — MDD skeleton');
    });

    it('should return <error> when <edge case from docs>', async () => {
      expect.fail('Not implemented — MDD skeleton');
    });
  });
});
```

Rules for skeleton generation:
- One describe/class block per endpoint or business rule
- One it/test block per documented behavior (happy path + each error case)
- Every test has a failing placeholder
- NO implementation yet — just the structure from the docs

Report to user: Test skeletons created: `<path>` (<N> test cases). These tests will FAIL until implementation is complete.

### Phase 4 — Present the Build Plan

Before writing any implementation code, present a clear plan:

```
MDD Build Plan for: <Feature Name>

Documentation: docs/<feature-name>.md — done
Test skeletons: <N> tests across <N> files — done

Implementation steps:
  Step 1 (<name>): <what will be created> — est. <time>
  Step 2 (<name>): <what will be created> — est. <time>
  ...

Total files to create: <N>
Tests to satisfy: <N>

Ready to build? (yes / modify plan / stop here)
```

**Step naming is MANDATORY** — every step has a unique name.

If tessera MCP is active, call `plan_save` with `project_name`, `subtask_name=<feature-name>`, `task=$ARGUMENTS`, and `plan_markdown=<build plan>` to register the plan for compliance tracking.

Wait for user confirmation.

### Phase 5 — Implement (Test-Driven)

For each step in the plan:

1. Read the MDD doc — refresh context on what this step needs
2. Read the test skeleton for the relevant tests
3. If tessera MCP is active: call `graph_continue`, read recommended files
4. Implement the code that makes the tests pass
5. Run tests after each step using the project's test command:
   - Python: `uv run pytest tests/<feature>_test.py -v` or `python -m pytest`
   - Node: `pnpm test:unit -- --grep "<feature>"` or `npm test`
   - Go: `go test ./... -run <Feature>`
6. Report progress: `Step N (<name>): done — <N>/<N> tests passing`
7. If tessera MCP is active: after each file edit, call `graph_register_edit` with `file::symbol` notation

**If a test fails, fix the implementation — NOT the test.** The tests were generated from the documentation. If the test seems wrong, re-read the doc. If the doc is wrong, ask the user.

After all steps complete, run full test suite and typecheck/lint.

### Phase 6 — Verify + Report

1. Run full test suite
2. Run typecheck / lint clean
3. Update `docs/PROJECT_CONTEXT.md` — add or refresh the feature entry
4. Update `docs/ARCHITECTURE_SUMMARY.md` only if the feature changes a service boundary, data flow, or global invariant
5. Update `docs/<feature>.md` — add any `known_issues` discovered
6. Update `CLAUDE.md` if new project-wide patterns were established
7. If tessera MCP is active: run `tessera-verify` to confirm plan compliance

Present the final report:

```
MDD Complete: <Feature Name>

Documentation: docs/<feature-name>.md
Files created: <list>
Tests: <N>/<N> passing
Lint/typecheck: clean

New patterns established: <any new rules worth adding to CLAUDE.md>

Branch: feat/<feature-name>
Ready for review.
```

### When to Suggest Subtree CLAUDE.md Files

When a domain grows complex enough to warrant area-specific rules, suggest creating:
- `server/CLAUDE.md` — backend patterns, database conventions
- `client/CLAUDE.md` — state management, routing, UI patterns
- `src/<feature>/CLAUDE.md` — feature-specific invariants

Only suggest when the area has meaningful complexity. Never pre-create empty subtree CLAUDE.md files.

---

## AUDIT MODE — `/mdd audit [section]`

Triggered when arguments start with `audit`.

### Phase A1 — Scope

If a section is specified (e.g., `/mdd audit database`), audit only that feature.
If no section, audit the entire project.

1. Read `docs/PROJECT_CONTEXT.md` — use as the primary feature map
2. Fall back to scanning `docs/*.md` only if `PROJECT_CONTEXT.md` is absent
3. If tessera MCP is active: call `graph_continue` for each feature area to surface relevant files
4. If no `docs/` directory exists: create it and ask the user how to proceed

### Phase A2 — Read + Notes

For each feature:

1. Read ALL source files listed in the documentation's `source_files` frontmatter
2. Write notes to `.mdd/audits/notes-<date>.md` every 2 features — do not accumulate in memory

Note format per feature:
```markdown
### [<feature-id>] <Feature Name>
**Files read:** <list>
**Findings:**
- <severity> <finding description>
**Test coverage:** <existing test count> / <endpoint count>
**Doc accuracy:** <any discrepancies between docs and code>
```

### Phase A3 — Analyze

Read only the notes file (not source code again). Produce findings report at `.mdd/audits/report-<date>.md`:

1. Executive summary
2. Feature completeness matrix
3. Findings by severity (CRITICAL / HIGH / MEDIUM / LOW)
4. Test coverage summary
5. Fix plan with effort estimates

### Phase A4 — Present Findings

Show the user:
```
MDD Audit Complete

Findings: <N> total (<N> Critical, <N> High, <N> Medium, <N> Low)
Report: .mdd/audits/report-<date>.md

Top issues:
  1. <most critical finding>
  2. <second most critical>
  3. <third most critical>

Fix all now? (yes / review report first / fix only critical+high)
```

If user confirms:

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

1. Scan `docs/` — count feature docs
2. Scan `.mdd/audits/` — find latest audit report
3. Count tests
4. Count known issues — grep `known_issues` across all docs

Present:
```
MDD Status

Feature docs:     <N> files in docs/
Last audit:       <date> (<N> findings, <N> fixed, <N> open)
Tests:            <N> unit tests
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

If on `main` or `master`:
- Build mode: `git checkout -b feat/<feature-name>`
- Audit mode: `git checkout -b fix/mdd-audit-<date>`

If already on a feature branch: proceed.

---

## CLAUDE.md Update Trigger

After ANY MDD operation that changes code, check if new patterns were established that should be added to CLAUDE.md. If so, suggest the addition and ask the user before writing.
