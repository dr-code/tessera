<!-- overlay: before "## Scope Check" -->
## Tessera Context Load

If the tessera MCP is configured in this session, ground the file-structure analysis in the real codebase before you write a single task:

1. `graph_continue` (the mandatory first call)
2. `graph_retrieve` with the feature's key terms
3. `graph_read` each recommended file (at high confidence read all of them; at medium or low, up to `max_supplementary_files`)
4. `graph_action_summary` to surface locked decisions that constrain this plan

In an existing codebase, follow the patterns that retrieval shows.

<!-- overlay: before "## Execution Handoff" -->
## Codex Plan Review (complex plans)

After self-review and before you save the plan, decide whether a second model should review it.

It **auto-runs** if ANY of these hold: the plan has more than 3 tasks; it modifies more than 5 files; it touches auth, payments, security, database schema, API contracts, or migrations; or your human partner says "debate" or "codex review" or passes `--debate`. It **skips** small plans (3 tasks or fewer and 5 files or fewer), doc-only, and UI-only plans. `--no-debate` forces it off.

```bash
codex exec "Review this implementation plan. Plan: <PLAN_MARKDOWN>. Identify: missing steps, sequencing errors, security holes, integration risks, untested edge cases. Per issue: [CRITICAL|HIGH|MED|LOW]: <issue> — <suggested fix>. End with VERDICT: approved | needs_revision."
```

Fix every CRITICAL and HIGH issue in the plan, apply judgment to MED and LOW, and add a "Codex Review Summary" at the end of the plan: the verdict, the issues fixed, and the issues deferred with the reason.

## Archive with Tessera

After the plan is written and self-reviewed, if the tessera MCP is configured, call the `plan_save` MCP tool so the plan is registered:

```
plan_save(
  project_name = "<short project identifier>",
  subtask_name = "<feature or subtask name>",
  task         = "<one sentence describing what the plan builds>",
  plan_markdown = "<full plan markdown content>"
)
```

This stores the plan in tessera's archive, parses the `- [ ]` checklist items, and lets `tessera-verify` check compliance after implementation. Keep the returned `plan_id`: it appears in `graph_continue` output as `active_checklist`, and `graph_register_edit` uses it to mark tasks complete.

If you are in plan mode, `ExitPlanMode` opens the Plannotator visual review. Wait for the approval before handing off for execution.
