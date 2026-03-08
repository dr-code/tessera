---
name: debate
description: Real Claude vs GPT multi-round debate. Use when you need a second opinion, want to debate architecture decisions, or evaluate competing approaches with multi-model collaboration.
---

# /debate — Multi-Round Claude vs GPT Debate

## Usage
`/debate "<topic or question>"`

## Description
Structured 3-round debate between Claude (native) and GPT (via Codex CLI). Claude and GPT take positions, critique each other, then Claude synthesizes a verdict. Tessera graph context is used when available.

## Instructions

### Phase 0: Context
1. If tessera MCP is configured in this session, call `graph_continue` then `graph_retrieve` with the debate topic keywords to pull relevant codebase context.
2. Note any architectural patterns, constraints, or decisions relevant to the topic.

### Phase 1: Claude's Initial Position
Formulate a clear stance on the topic with 3 supporting reasons. Include any codebase context found. State what would change your mind.

### Phase 2: GPT's Position (Round 1)
Send the topic and context to Codex:

```bash
codex exec "You are a senior software architect in a structured debate. Topic: <TOPIC>. Codebase context (if any): <CONTEXT>. Give: (1) your clear stance, (2) top 3 reasons, (3) biggest risk of your approach, (4) what evidence would change your mind. Be direct and specific. No hedging."
```

Record GPT's full position.

### Phase 3: Claude's Critique + GPT's Response (Round 2)
Claude critiques GPT's position: identify flawed assumptions, missing edge cases, or contradictions with project constraints. Then send:

```bash
codex exec "Debate round 2. Topic: <TOPIC>. Your position: <GPT_POSITION>. Claude's critique: <CLAUDE_CRITIQUE>. Respond: either defend your stance with new evidence OR concede specific points. If you concede, state what you now believe. Be precise."
```

### Phase 4: Synthesis
Claude produces the final verdict:
- Summarize both positions
- Note where agreement was reached
- Note where genuine disagreement remains
- Issue a clear recommendation with confidence level (high / medium / low)

### Phase 5: Record Decision (if tessera available)
If tessera MCP is active, call `graph_action_summary` with the debate topic, verdict, and rationale as the summary string.

### Output Format

```
Topic: <topic>

GPT Position: <1-2 sentence summary>

Claude Critique: <key objections raised>

GPT Response: <concessions or defenses>

Verdict: <clear recommendation>
Confidence: high / medium / low
Open disagreements (if any): <what remains unresolved>
```
