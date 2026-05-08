---
name: writing-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---

# Writing Skills

<!-- From obra/superpowers — no Tessera-specific adaptation needed -->

## Overview

Writing skills IS Test-Driven Development applied to process documentation.

Write test cases (pressure scenarios), watch them fail (baseline behavior), write the skill, watch tests pass, refactor (close loopholes).

**Core principle:** If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.

**REQUIRED BACKGROUND:** Understand `test-driven-development` before using this skill.

## What is a Skill?

A skill is a reference guide for proven techniques, patterns, or tools.

**Skills are:** Reusable techniques, patterns, tools, reference guides

**Skills are NOT:** Narratives about how you solved a problem once

## SKILL.md Structure

**Frontmatter (YAML):**
- Two required fields only: `name` and `description`
- `name`: letters, numbers, hyphens only
- `description`: starts with "Use when...", describes triggering conditions, NOT the skill's workflow

```markdown
---
name: skill-name
description: Use when [specific triggering conditions]
---

# Skill Name

## Overview
Core principle in 1-2 sentences.

## When to Use
Bullet list with symptoms and use cases

## Core Pattern
Before/after comparison or process steps

## Common Mistakes
What goes wrong + fixes
```

## Claude Search Optimization

**Description = When to Use, NOT What the Skill Does**

The description answers: "Should I read this skill right now?" It must NOT summarize the workflow.

```yaml
# BAD: Summarizes workflow — Claude follows this instead of reading the skill
description: Use when executing plans - dispatches subagent per task with review between tasks

# GOOD: Triggering conditions only
description: Use when executing implementation plans with independent tasks in the current session
```

## TDD Mapping for Skills

| TDD Concept | Skill Creation |
|-------------|----------------|
| Test case | Pressure scenario with subagent |
| Production code | Skill document (SKILL.md) |
| RED | Agent violates rule without skill (baseline) |
| GREEN | Agent complies with skill present |
| REFACTOR | Close loopholes while maintaining compliance |

## The Iron Law

```
NO SKILL WITHOUT A FAILING TEST FIRST
```

This applies to new skills AND edits to existing skills.

## Skills Live In

Tessera-integrated skills: `skills/<name>/SKILL.md` in the project root.

Personal skills: `~/.claude/skills/<name>/SKILL.md` for Claude Code.

## Skill Creation Checklist

**RED Phase:**
- [ ] Run pressure scenario WITHOUT skill — document baseline failures verbatim

**GREEN Phase:**
- [ ] Frontmatter: `name` and `description` only
- [ ] Description starts with "Use when..." — no workflow summary
- [ ] Clear overview with core principle
- [ ] Address specific baseline failures
- [ ] Run scenario WITH skill — agent complies

**REFACTOR Phase:**
- [ ] Identify new rationalizations
- [ ] Add explicit counters
- [ ] Re-test until bulletproof

## Common Mistakes

**Skipping baseline test:** You don't know what the skill needs to teach.

**Workflow summary in description:** Claude reads the description and skips the skill body.

**Over-documenting:** Target <300 words for frequently-loaded skills.
