<!-- overlay: before "## The Gate Function" -->
## Tessera Compliance Gate

If the tessera MCP is configured AND a plan was registered with `plan_save`, run `tessera verify .` (or the `tessera-verify` skill, if it is installed) before any other verification. Every checklist item must be done, and no file outside the plan may be changed without a reason. Only when it is clean, run the tests and the linter.
