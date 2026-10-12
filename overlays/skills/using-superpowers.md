<!-- overlay: before "## The Rule" -->
## Tessera + Superpowers

This copy of the skills ships with the tessera plugin. Tessera adds persistent codebase memory (a graph of files, symbols, and dependencies, locked decisions, and archived plans) to the Superpowers methodology. Skills are named `tessera:<skill>` here. The workflow:

```
brainstorming        (graph context, locked decisions, optional Codex second opinion)
  -> writing-plans   (graph context, optional Codex plan review, plan_save)
    -> Plannotator visual review   (ExitPlanMode hook)
      -> subagent-driven-development or executing-plans   (graph_register_edit per edit)
        -> verification-before-completion   (tessera verify)
          -> finishing-a-development-branch
```

Tessera steps apply only when the tessera MCP is configured in the session; without it, the skills run as upstream wrote them.
