<!-- overlay: before "## The Iron Law" -->
## Tessera: Discover Existing Test Patterns First

If the tessera MCP is configured, before you write any test:

1. `graph_continue` (the mandatory first call)
2. `graph_retrieve` with "<feature> test" as the query
3. `graph_read` the nearest existing test file for the module you are testing

Follow the conventions you find (names, fixtures, helpers) instead of inventing new ones.

<!-- overlay: before "## Verification Checklist" -->
## Tessera: register the edits

If the tessera MCP is configured, call `graph_register_edit` for each modified file with `file::symbol` notation and a summary. This updates the compliance tracker.
