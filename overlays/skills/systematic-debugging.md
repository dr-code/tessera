<!-- overlay: before "## The Four Phases" -->
## Tessera: Map the Blast Radius First

If the tessera MCP is configured, before Phase 1:

1. `graph_continue` (the mandatory first call)
2. `graph_impact(changed_files=["<file where the bug was reported>"])`

`graph_impact` shows which other files depend on the broken code, so you know what else a fix could affect and what else to check.

<!-- overlay: after-section "### Phase 2: Pattern Analysis" -->
### Tessera: find and read the working example

If the tessera MCP is configured, use `graph_retrieve(query="<working component similar to the broken one>")` to find similar code, and `graph_read` to read the working implementation completely.

<!-- overlay: after-section "### Phase 4: Implementation" -->
### Tessera: register the fix

If the tessera MCP is configured, once the fix is in, call `graph_register_edit(files=["file::symbol"], summary="<what was wrong and the fix>")`.
