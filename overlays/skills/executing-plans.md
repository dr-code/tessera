<!-- overlay: before "## Setup" -->
## Tessera Context Load

If the tessera MCP is configured in this session, before you start the first task:

1. `graph_continue` (the mandatory first call)
2. `graph_retrieve` with the plan's key feature terms
3. `graph_read` the recommended files

This gives you current codebase context before execution begins.

<!-- overlay: after-section "### 2. Work the steps" -->
### Tessera: register edits and decisions

If the tessera MCP is configured, after each file edit call `graph_register_edit` with `file::symbol` notation and a one-line summary. If `graph_continue` returned an `active_checklist`, pass the `checklist_item_id` of the task you just completed so it is marked done without keyword matching.

When you make an architectural choice that later tasks depend on, record it with `graph_lock_decision(summary, scope, files)`.

<!-- overlay: before "## Finish" -->
## Tessera Compliance Check

If the tessera MCP is configured and the plan was registered with `plan_save`, run `tessera verify .` (or the `tessera-verify` skill, if it is installed) before you finish, and resolve anything it reports as missing or out of scope.
