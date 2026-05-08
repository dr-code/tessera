---
name: test-driven-development
description: Use when implementing any feature or bugfix, before writing implementation code
---

# Test-Driven Development (TDD)

<!-- Adapted from obra/superpowers — Tessera graph_read for test pattern discovery added -->

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

**Violating the letter of the rules is violating the spirit of the rules.**

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Delete means delete

## Tessera: Discover Existing Test Patterns First

**Before writing any test — if tessera MCP is configured in this session:**

```
1. graph_continue (mandatory first call)
2. graph_retrieve with "<feature> test" as query
3. graph_read the nearest existing test file for the module you're testing
```

This ensures your new test follows the project's established patterns — fixture style, assertion format, naming conventions — instead of inventing something inconsistent.

Also check:
- Are there shared test fixtures in `conftest.py` or similar?
- Does the project use real DB instances or mocks for this layer?
- What is the expected assertion style (bare `assert`, `pytest.raises`, custom matchers)?

## Red-Green-Refactor

### RED — Write Failing Test

Write one minimal test showing what should happen.

```
Test: exactly one specific behavior
Assert: expected output or state change
Run: verify it FAILS with the right error
```

**If it passes before you write the implementation:** the test is wrong. Delete it, re-examine the behavior, rewrite.

**If it fails with the wrong error:** the test is testing the wrong thing. Fix the test first.

### GREEN — Write Minimal Code

Write the minimum code to make the test pass. Nothing more.

**"Minimum" means:**
- No extra error handling
- No extra features
- No optimizations
- Just enough to pass the test

Run all tests. Verify only the intended tests pass. No regressions.

### REFACTOR — Clean Up

Improve without changing behavior. Tests must stay green throughout.

Clean up:
- Remove duplication
- Improve naming
- Simplify logic

**Run tests after every change.** If they go red, revert.

## Common TDD Violations

| Violation | Why it fails |
|-----------|-------------|
| Writing tests after the code | Tests become "does it do what the code does" instead of "does it do what it should" |
| Multiple test cases at once | Can't isolate what's broken |
| Skipping the failure run | Might be testing wrong thing |
| "I'll just add one quick feature" | YAGNI. Write a test first. |
| "Tests are passing, good enough" | No refactor phase = accumulating debt |

## Red Flags — STOP

- Writing production code before a failing test exists
- "I'll write tests after to verify"
- "It's too simple to need a test"
- "I already manually tested it"
- Tests passing immediately without seeing them fail first

**All of these mean: Delete the code. Start over with a failing test.**

## After Implementation

If tessera MCP is configured, call `graph_register_edit` for each modified file with `file::symbol` notation and a summary. This updates the compliance tracker.
