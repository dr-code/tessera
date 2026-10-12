---
name: using-superpowers
description: Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before ANY response including clarifying questions
---

<!-- TESSERA:OVERLAY begin provenance -->
<!-- Generated from obra/superpowers v7.0.0 (bb92a77) + overlays/skills/using-superpowers.md. Do not edit by hand: edit the overlay and run scripts/build_skills.py. -->
<!-- TESSERA:OVERLAY end provenance -->

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

<!-- TESSERA:OVERLAY begin using-superpowers-1 -->
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
<!-- TESSERA:OVERLAY end using-superpowers-1 -->

## The Rule

**Invoke relevant or requested skills BEFORE any response or action** — including clarifying questions, exploring the codebase, or checking files. If it turns out wrong for the situation, you don't have to use it.

**Before entering plan mode:** if you haven't already brainstormed, invoke the brainstorming skill first.

Then announce "Using [skill] to [purpose]" and follow the skill exactly. If it has a checklist, create a todo per item.

## Skill Priority

When multiple skills apply, process skills come first — they set the approach, then implementation skills (frontend-design, etc.) carry it out. Brainstorming and systematic-debugging are Superpowers' most common process skills, but the rule holds for any of them.

- "Let's build X" → tessera:brainstorming first, then implementation skills.
- "Fix this bug" → tessera:systematic-debugging first, then domain skills.

## Red Flags

These thoughts mean STOP—you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |

## Platform Adaptation

If your harness appears here, read its reference file for special instructions:

- Claude Code: `references/claude-code-tools.md`
- Codex: `references/codex-tools.md`
- Pi: `references/pi-tools.md`
- Antigravity: `references/antigravity-tools.md`
- Hermes Agent: `references/hermes-tools.md`
- Muse: `references/muse-tools.md`

## User Instructions

User instructions (CLAUDE.md, AGENTS.md, GEMINI.md, etc, direct requests) take precedence over skills, which in turn override default behavior. Only skip skill workflows or instructions when your human partner has explicitly told you to.
