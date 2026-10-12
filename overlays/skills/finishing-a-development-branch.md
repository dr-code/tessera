<!-- overlay: before "## Step 1: Verify Tests" -->
## Step 0: Tessera Compliance Gate

If the tessera MCP is configured AND a plan was registered with `plan_save`, run `tessera verify .` (or the `tessera-verify` skill, if it is installed) BEFORE you verify tests. If it reports missing or out-of-scope work, resolve that first (complete the item, or tell your human partner why it is not needed). Only when it is clean, continue to Step 1. Never proceed past a failing check.
