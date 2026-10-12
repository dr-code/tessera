<!-- overlay: before "## The Response Pattern" -->
## Tessera Context Load

If the tessera MCP is configured, before you evaluate any feedback:

1. `graph_continue` (the mandatory first call)
2. `graph_action_summary` to surface locked decisions, and flag any feedback that would violate one. If feedback conflicts with a prior architectural decision, stop and discuss it with your human partner instead of implementing it.

<!-- overlay: after-section "## Implementation Order" -->
## Tessera: register each fix

If the tessera MCP is configured, after each fix call `graph_register_edit(files=["file::symbol"], summary="...")` so the compliance tracker reflects the change.
