---
name: cleanup
description: Bidirectional AI slop scanner — Claude + GPT independently analyze, then debate disagreements.
---

# /cleanup — Bidirectional AI Slop Scanner

## Usage
`/cleanup [file or directory]`
`/cleanup` — uses tessera graph to find recently modified files, or prompts for target

## Description
Claude and GPT independently analyze code for quality issues and AI slop patterns, then reconcile disagreements. Produces a unified report with agreed issues (high confidence) and model-specific findings (lower confidence).

## Instructions

### Phase 0: Identify Target

**If tessera MCP is configured:**
```
1. graph_continue (mandatory first call)
2. graph_retrieve("recently modified files") — find candidates
3. graph_read each target file before analysis begins
```

- If user specified files or a directory: use those (still call `graph_read` for each)
- If tessera not active: ask user which files to analyze

Read all target files before starting analysis.

### Phase 1: Claude's Independent Analysis
Analyze the files independently. Look for:
- Unnecessary complexity or indirection
- Dead code, unused variables, unreachable branches
- Poor naming: vague, misleading, or verbose AI-generated names
- Missing error handling at system boundaries (user input, external APIs, file I/O)
- Premature abstractions: helpers used once, over-generalized interfaces, unnecessary wrapper functions
- AI-generated patterns: comments that restate what the code does, defensive checks for impossible cases, empty catch blocks
- Security issues at input boundaries

Format each issue as: `[HIGH|MED|LOW] [TYPE] file:line — description`

**Do not share your findings yet.**

### Phase 2: GPT's Independent Analysis
Send the same files to Codex without revealing Claude's findings:

```bash
codex exec "Analyze this code for quality issues. Look for: unnecessary complexity, dead code, poor naming, missing error handling at boundaries, premature abstractions, AI-generated patterns (verbose comments restating code, unnecessary wrappers, impossible-case guards). File contents: <FILE_CONTENTS>. Format each issue as: [HIGH|MED|LOW] [TYPE] file:line — description. Do not suggest rewrites, only identify issues."
```

### Phase 3: Reconcile
Compare the two sets of findings:
- **Agreed**: both found the same issue — high confidence, list first
- **Claude-only**: Claude found it, GPT missed it — present with reasoning
- **GPT-only**: Claude evaluates each one. For significant disagreements, run a quick debate:

```bash
codex exec "Quick verdict needed. Issue: <ISSUE>. Claude disagrees because: <CLAUDE_REASONING>. Is Claude correct? Give a one-sentence verdict: agree with Claude OR stand by original finding with one supporting reason."
```

### Phase 4: Report
Present the unified report:

**Agreed Issues (fix these):**
[list with severity and file:line]

**Claude-Only Findings:**
[list — lower confidence, Claude's assessment]

**GPT-Only Findings (Claude evaluated):**
[list with Claude's verdict on each: confirmed / dismissed with reason]

**Resolved Disagreements:**
[what was debated, what was concluded]

Ask: which issues to fix now? All HIGH? Specific items? Leave as reference?
