<!-- overlay: before "## First: What Do You Actually Know?" -->
## Tessera Context

If the tessera MCP is configured in this session, load what the codebase already tells you before you decide what you know:

1. `graph_continue` (the mandatory first call every turn)
2. `graph_retrieve` with 2-3 key terms from the request, then read the recommended files with `graph_read`
3. `graph_action_summary` to see the locked architectural decisions. If a locked decision (`graph_lock_decision`) covers the area being designed, tell your human partner before you propose anything.

This surfaces existing code, dependencies, and prior decisions before you ask a single question, so the design does not contradict what is already established.

<!-- overlay: after-section "## Size the Work" -->
## Second Opinion from Codex (projects only)

When the size is **a project with a written design**, decide whether a second model should challenge the approach before you write the design down.

It **auto-runs** if ANY of these hold:
- the design covers more than 2 independent components
- it involves auth, payments, security, database-schema changes, API contracts, migrations, or external integrations
- your human partner says "debate", "codex review", or "second opinion", or passes `--debate`

It **auto-skips** for single-file changes, pure UI tweaks, doc-only work, and well-established patterns. `--no-debate` or "skip debate" forces it off.

When it runs, before you write the design, send the approach you have settled on and its trade-offs to Codex:

```bash
codex exec "You are a senior engineer reviewing a design proposal. Proposal: <APPROACH_SUMMARY>. Project context: <BRIEF_CONTEXT>. Identify: (1) technical gaps or omissions, (2) missing edge cases, (3) security concerns, (4) better alternative approaches. Be specific — cite components and files. Output each issue as: [CRITICAL|HIGH|MED|LOW]: <issue> — <suggested fix>."
```

Judge the feedback critically: the other model can be wrong or out of scope for this codebase. Fold the 1-3 most valuable points into the design, and record a "Codex Debate Summary" in the design document: the points you accepted and why, and the points you rejected and why. Do not move on to the builder check until the debate output has been integrated or explicitly rejected.
