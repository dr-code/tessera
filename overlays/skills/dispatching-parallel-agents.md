<!-- overlay: before "## The Pattern" -->
## Tessera Context Load (coordinator)

If the tessera MCP is configured, before you dispatch any agent:

1. `graph_continue` (the mandatory first call for the coordinator)
2. `graph_retrieve` with the names of the failing components

<!-- overlay: after-section "## Agent Prompt Structure" -->
## Tessera Discipline for Each Agent

If the tessera MCP is configured, add this to each agent prompt:

```
Tessera graph policy:
- Call graph_continue as your FIRST tool call
- Call graph_retrieve with this task's key terms
- Read recommended_files via graph_read before exploring
- After each file edit: graph_register_edit(files=["file::symbol"], summary="...")
- Lock architectural choices: graph_lock_decision(summary, scope, files)
```
