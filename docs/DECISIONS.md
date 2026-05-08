# Architectural Decisions

> Record WHY you chose X over Y. Future-you (and future-Claude) will thank you.

---

## Decision Template

When adding a new decision, copy this template:

```markdown
## ADR-XXX: [Title]

**Date:** YYYY-MM-DD
**Status:** Accepted | Superseded by ADR-XXX | Deprecated

### Context
What is the issue or situation that motivated this decision?

### Decision
What is the change we're making?

### Alternatives Considered
| Option | Pros | Cons |
|--------|------|------|
| Option A | ... | ... |
| Option B | ... | ... |

### Consequences
What are the positive and negative results of this decision?
```

---

## ADR-003: Bundle Superpowers Methodology + Plannotator Visual Review

**Date:** 2026-05-08
**Status:** Accepted

### Context
Tessera provides codebase memory (graph, plans, decisions) but had no structured development methodology and no visual plan-review workflow. Two upstream projects address these gaps: `obra/superpowers` (14 agentic methodology skills) and `backnotprop/plannotator` (visual plan approval via ExitPlanMode hooks). Rather than requiring users to install and wire three separate plugins, we integrate them into Tessera's Claude Code plugin.

### Decision
Bundle adapted Superpowers skills in `skills/` (14 files) and Plannotator hooks in `hooks/hooks.json`. Skills are adapted to inject Tessera graph tool calls (`graph_retrieve`, `graph_read`, `graph_impact`, `plan_save`) at the appropriate workflow phases. The `plan_save` MCP tool bridges the two: the `writing-plans` skill calls it to register approved plans into Tessera's DB, enabling `tessera-verify` compliance checking after implementation.

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Bundle as-is, no adaptation | Simple, low effort | Tessera graph context not used in planning |
| Document only, no bundling | No collision risk | Not integrated, requires manual config |
| Full absorption (port UIs) | Self-contained | Maintains forks of two active projects |

### Consequences

**Positive:**
- Installing Tessera gives a complete brainstorm → plan → review → execute → verify workflow
- Plans registered via `plan_save` are tracked by `tessera-verify` compliance checker
- `graph_retrieve` context in `brainstorming` and `writing-plans` produces codebase-aware designs and plans

**Negative:**
- Plannotator hooks require a separate binary install (`curl | bash`)
- Users who install standalone Plannotator plugin AND Tessera will have duplicate hooks (documented mitigation: install one or the other)
- Upstream skill changes require a manual sync to `skills/`

---

## ADR-001: TypeScript Over JavaScript

**Date:** (today)
**Status:** Accepted

### Context
AI-assisted development needs explicit type information to avoid guessing. JavaScript provides no type contracts, leading to runtime errors that are hard to trace.

### Decision
All new code MUST be TypeScript with strict mode. When editing existing JavaScript files, convert to TypeScript first.

### Alternatives Considered
| Option | Pros | Cons |
|--------|------|------|
| JavaScript + JSDoc | Less setup | AI still guesses, JSDoc can be wrong |
| TypeScript (strict) | Explicit contracts, better AI accuracy | Slightly more verbose |

### Consequences
- Claude can reason about types without guessing
- Refactoring is safer with compile-time checks
- New team members learn the codebase from type signatures

---

## ADR-002: StrictDB for All Database Access

**Date:** (today)
**Status:** Accepted

### Context
Without centralized database access, each file creates its own connection, leading to pool exhaustion. This starter kit originally shipped a custom database adapter that evolved into StrictDB — a standalone npm package and unified driver supporting MongoDB, PostgreSQL, MySQL, MSSQL, SQLite, and Elasticsearch through a single API.

### Decision
All database access uses StrictDB directly. Install `strictdb` + your database driver, create a single `StrictDB` instance at app startup, and share it across the application. NEVER import native database drivers (`mongodb`, `pg`, etc.) directly.

### Consequences
- Single connection pool prevents exhaustion
- One place to add logging, metrics, retries
- Easy to mock for testing
- One API for all backends — switching databases requires only changing STRICTDB_URI
- Built-in sanitization, guardrails, and AI-first discovery (describe, validate, explain)
- StrictDB-MCP server gives AI agents direct database access with all guardrails enforced
