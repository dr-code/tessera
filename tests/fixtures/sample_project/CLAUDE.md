# CLAUDE.md

<!-- TESSERA:START v2 -->
## Tessera Graph Policy

**MANDATORY**: Call `graph_continue` as your FIRST tool call every turn.

- If `needs_scan=true`: run `graph_scan` with the project root path
- If `skip=true`: project too small, proceed normally
- If error: proceed normally without graph routing for this turn
- Read all `recommended_files` via `graph_read` before other exploration
- Obey confidence caps:
  - high: no supplementary greps or reads
  - medium: up to max_supplementary_greps greps + max_supplementary_files reads
  - low: up to max_supplementary_greps greps + max_supplementary_files reads
- After edits: call `graph_register_edit` with file::symbol notation and summary
  - If `graph_continue` returned `active_checklist`, pass `checklist_item_id` for the item you just completed — this marks it done without keyword matching
  - If no active checklist or the edit doesn't map to a specific item, omit `checklist_item_id` (keyword fallback applies)
- When you identify an architectural decision: call `graph_lock_decision` with a one-sentence summary, scope (`"file"` | `"module"` | `"project"`), and the files it applies to
- Max 1 `graph_retrieve` per turn
- No raw grep/rg/bash file reads before `graph_continue`
<!-- TESSERA:END -->
