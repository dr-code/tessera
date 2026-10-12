<!-- overlay: before "## Setup" -->
## Tessera Coordinator Discipline

If the tessera MCP is configured, at the start of each dispatch round, before you dispatch any subagent:

1. `graph_continue` (the mandatory first call for the coordinator too)
2. `graph_retrieve` with the current task's key terms

This keeps your routing accurate as files change during execution.

<!-- overlay: after-section "### 1. Dispatch the implementer" -->
### Tessera policy for implementers

If the tessera MCP is configured, hand the policy over as a file, like everything else: once per plan, write the block below to `<workspace>/tessera-policy.md`, and add one line to every implementer dispatch: "Follow the tessera graph policy in <that path>." Do not paste the block into each dispatch.

```
Tessera graph policy:
1. Call graph_continue as your FIRST tool call.
2. Call graph_retrieve with this task's key terms and read the recommended files with graph_read before exploring.
3. After each file edit, call graph_register_edit(files=["file::symbol"], summary="..."). If graph_continue returned an active_checklist, pass the checklist_item_id of the task you just completed.
4. Lock architectural decisions with graph_lock_decision(summary, scope, files).
```

<!-- overlay: before "## Finish" -->
## Tessera Compliance Check

If the tessera MCP is configured and the plan was registered with `plan_save`, run `tessera verify .` (or the `tessera-verify` skill, if it is installed) to confirm plan compliance before you finish. Every checklist item must be done.
