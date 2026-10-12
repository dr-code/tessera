<!-- overlay: before "## Quick Reference" -->
## Step 4: Tessera Context Rebuild

If the tessera MCP is configured, run `tessera scan .` in the new workspace after setup:

```bash
tessera scan .
```

This registers the worktree's files in tessera's graph so `graph_continue` can route reads correctly there. Do not skip it: the graph goes stale otherwise.
