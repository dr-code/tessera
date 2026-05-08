---
name: brainstorming
description: "You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation."
---

# Brainstorming Ideas Into Designs

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design and get user approval.

<!-- Adapted from obra/superpowers — Tessera codebase-context injection added -->

<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>

## Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A todo list, a single-function utility, a config change — all of them. "Simple" projects are where unexamined assumptions cause the most wasted work. The design can be short (a few sentences for truly simple projects), but you MUST present it and get approval.

## Checklist

You MUST create a task for each of these items and complete them in order:

1. **Explore project context** — call `graph_continue` (if tessera MCP is configured), then `graph_retrieve` with the topic's key terms; also read `CLAUDE.md` and `docs/PROJECT_CONTEXT.md`
2. **Offer visual companion** (if topic will involve visual questions) — this is its own message, not combined with a clarifying question. See the Visual Companion section below.
3. **Ask clarifying questions** — one at a time, understand purpose/constraints/success criteria
4. **Propose 2-3 approaches** — with trade-offs and your recommendation
5. **Present design** — in sections scaled to their complexity, get user approval after each section
6. **Write design doc** — save to `docs/specs/YYYY-MM-DD-<topic>-design.md` and commit
7. **Spec self-review** — quick inline check for placeholders, contradictions, ambiguity, scope (see below)
8. **User reviews written spec** — ask user to review the spec file before proceeding
9. **Transition to implementation** — invoke writing-plans skill to create implementation plan

## Tessera Context Integration

**Step 1 expanded — if tessera MCP is configured in this session:**

```
1. graph_continue (mandatory first call every turn)
2. graph_retrieve with 2-3 key terms from the request
   → read all recommended_files at high confidence
   → up to max_supplementary_files at medium/low confidence
3. graph_read any architecturally significant files surfaced
```

This surfaces relevant existing code, dependencies, and prior decisions before asking a single clarifying question — preventing designs that contradict established patterns.

**Also check for locked decisions:**
- Call `graph_action_summary` to see recent architectural decisions that constrain this design
- If a prior `graph_lock_decision` applies to the area being designed, surface it explicitly to the user before proposing approaches

## Process Flow

The checklist drives the process. Key decision points:

- If topic will involve visual questions → offer Visual Companion in a standalone message before clarifying questions
- After each design section → get user approval or revise
- After writing spec → run Spec Self-Review, then User Review Gate
- Terminal state → invoke writing-plans skill (the ONLY skill after brainstorming)

**The terminal state is invoking writing-plans.** Do NOT invoke any other implementation skill.

## The Process

**Understanding the idea:**

- Check out the current project state first (graph_retrieve, CLAUDE.md, docs, recent commits)
- Before asking detailed questions, assess scope: if the request describes multiple independent subsystems, flag this immediately and help decompose into sub-projects
- For appropriately-scoped projects, ask questions one at a time to refine the idea
- Prefer multiple choice questions when possible
- Only one question per message

**Exploring approaches:**

- Propose 2-3 different approaches with trade-offs
- Lead with your recommended option and explain why

**Presenting the design:**

- Present design in sections, ask after each section whether it looks right
- Cover: architecture, components, data flow, error handling, testing

**Design for isolation and clarity:**

- Break the system into smaller units with one clear purpose each
- Smaller, well-bounded units are easier to reason about and edit reliably

**Working in existing codebases:**

- Explore the current structure (via graph_retrieve) before proposing changes
- Follow existing patterns
- Where existing code has problems that affect the work, include targeted improvements as part of the design

## After the Design

**Documentation:**

- Write the validated design (spec) to `docs/specs/YYYY-MM-DD-<topic>-design.md`
- Commit the design document to git

**Spec Self-Review:**
After writing the spec, look at it with fresh eyes:

1. **Placeholder scan:** Any "TBD", "TODO", incomplete sections? Fix them.
2. **Internal consistency:** Do any sections contradict each other?
3. **Scope check:** Is this focused enough for a single implementation plan?
4. **Ambiguity check:** Could any requirement be interpreted two ways? Pick one and make it explicit.

**User Review Gate:**
After the spec review loop passes, ask the user to review the written spec before proceeding.

**Implementation:**

- Invoke the writing-plans skill to create a detailed implementation plan
- Do NOT invoke any other skill. writing-plans is the next step.

## Key Principles

- **One question at a time** — Don't overwhelm with multiple questions
- **Multiple choice preferred** — Easier to answer than open-ended when possible
- **YAGNI ruthlessly** — Remove unnecessary features from all designs
- **Explore alternatives** — Always propose 2-3 approaches before settling
- **Incremental validation** — Present design, get approval before moving on
- **Be flexible** — Go back and clarify when something doesn't make sense

## Visual Companion

When you anticipate that upcoming questions will involve visual content (mockups, layouts, diagrams), offer it once for consent:

> "Some of what we're working on might be easier to explain if I can show it to you in a web browser. I can put together mockups, diagrams, comparisons, and other visuals as we go. Want to try it? (Requires opening a local URL)"

**This offer MUST be its own message.** Do not combine it with clarifying questions. Wait for the user's response before continuing.

**Per-question decision:** Even after the user accepts, use the browser only for content that IS visual — mockups, wireframes, layout comparisons, architecture diagrams. Use text for conceptual questions and tradeoff discussions.
