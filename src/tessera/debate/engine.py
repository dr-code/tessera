"""Debate engine orchestration.

Flow:
  1. Capability check
  2. GPT Plans (Codex CLI)
  3. Claude Critiques (round 1)
  4. GPT Responds (round 2)
  5. Claude Synthesizes (round 3)
  6. Archive (handled by caller / CLI)
  7. Execute (handled by caller / CLI)
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field

from ..core.config import DEBATE_CLAUDE_MODEL, DEBATE_MAX_ROUNDS
from .codex import CodexError, run as codex_run
from .claude import ClaudeError, run as claude_run
from .sanitizer import sanitize_text


_GPT_PLAN_PROMPT = """\
You are a senior software architect. Given the following task, produce a detailed
implementation plan in XML format. Use this exact schema:

<plan>
  <metadata>
    <task>{task}</task>
    <created></created>
    <rounds>0</rounds>
    <verdict>draft</verdict>
  </metadata>
  <targets>
    <file action="create|modify|delete">path/to/file</file>
  </targets>
  <tasks order="sequential">
    <task id="1" file="path/to/file" keywords="comma,separated,keywords">
      Description of what to implement
    </task>
  </tasks>
  <validation>
    <criterion>Testable acceptance criterion</criterion>
  </validation>
</plan>

Task: {task}

Respond with ONLY the XML. No prose before or after.
"""

_CLAUDE_CRITIQUE_PROMPT = """\
You are reviewing an implementation plan proposed by GPT. Your role is to:
1. Identify any gaps, risks, or missing steps
2. Flag any security concerns
3. Suggest improvements or alternatives

Task: {task}

GPT's plan:
{plan_text}

Provide a structured critique. Be specific and actionable.
"""

_GPT_RESPOND_PROMPT = """\
You previously proposed an implementation plan. A reviewer has critiqued it.
Incorporate the valid criticisms and produce an improved plan.

Original task: {task}

Your original plan:
{plan_text}

Reviewer critique:
{critique}

Produce an improved XML plan using the same schema. Respond with ONLY the XML.
"""

_CLAUDE_SYNTHESIZE_PROMPT = """\
You are producing the final implementation plan after a debate. Given the
original plan, the critique, and the revised plan, synthesize the best
possible final plan.

Task: {task}

Round 1 plan (GPT):
{plan_r1}

Critique (Claude):
{critique}

Round 2 plan (GPT revised):
{plan_r2}

Produce the final XML plan with verdict="approved". Respond with ONLY the XML.
"""


@dataclass
class DebateTranscript:
    task: str
    rounds_completed: int
    gpt_plan_r1: str = ""
    claude_critique: str = ""
    gpt_plan_r2: str = ""
    claude_final: str = ""
    final_xml: str = ""
    errors: list[str] = field(default_factory=list)


def check_capabilities(require_claude_cli: bool = True) -> dict[str, bool]:
    """Return availability of each required capability."""
    from .codex import is_available as codex_ok
    from .claude import is_available as claude_ok

    claude_cli = shutil.which("claude") is not None

    return {
        "codex_cli": codex_ok(),
        "claude_api": claude_ok(),
        "claude_cli": claude_cli,
    }


def run_debate(
    task: str,
    max_rounds: int = DEBATE_MAX_ROUNDS,
    project_root: str = "",
) -> DebateTranscript:
    """Run the full debate and return a DebateTranscript.

    Sanitizes all external content before processing.
    """
    transcript = DebateTranscript(task=task, rounds_completed=0)

    # Round 1: GPT plans
    gpt_prompt_1 = _GPT_PLAN_PROMPT.format(task=task)
    try:
        gpt_r1 = codex_run(gpt_prompt_1)
        raw_r1 = gpt_r1.text
        sanitized_r1, _ = sanitize_text(raw_r1, project_root=project_root)
        transcript.gpt_plan_r1 = sanitized_r1
        transcript.rounds_completed = 1
    except CodexError as exc:
        transcript.errors.append(f"Round 1 (GPT plan): {exc}")
        return transcript

    # Round 2: Claude critiques (optional — skipped when Claude API unavailable)
    critique_prompt = _CLAUDE_CRITIQUE_PROMPT.format(
        task=task, plan_text=transcript.gpt_plan_r1
    )
    try:
        claude_r1 = claude_run(critique_prompt, model=DEBATE_CLAUDE_MODEL)
        transcript.claude_critique = claude_r1.text
        transcript.rounds_completed = 2
    except ClaudeError as exc:
        transcript.errors.append(f"Round 2 (Claude critique): {exc} — using Codex plan directly")
        transcript.final_xml = transcript.gpt_plan_r1
        return transcript

    if max_rounds < 3:
        # Abbreviated path: GPT round-1 plan used directly; critique is captured
        # in transcript.claude_critique but not incorporated into a revised plan.
        transcript.final_xml = transcript.gpt_plan_r1
        return transcript

    # Round 3: GPT responds
    gpt_prompt_2 = _GPT_RESPOND_PROMPT.format(
        task=task,
        plan_text=transcript.gpt_plan_r1,
        critique=transcript.claude_critique,
    )
    try:
        gpt_r2 = codex_run(gpt_prompt_2)
        raw_r2 = gpt_r2.text
        sanitized_r2, _ = sanitize_text(raw_r2, project_root=project_root)
        transcript.gpt_plan_r2 = sanitized_r2
        transcript.rounds_completed = 3
    except CodexError as exc:
        transcript.errors.append(f"Round 3 (GPT respond): {exc}")
        # Fall back to round 1 plan
        transcript.final_xml = transcript.gpt_plan_r1
        return transcript

    # Round 4 (counted as part of round 3 in spec): Claude synthesizes
    synth_prompt = _CLAUDE_SYNTHESIZE_PROMPT.format(
        task=task,
        plan_r1=transcript.gpt_plan_r1,
        critique=transcript.claude_critique,
        plan_r2=transcript.gpt_plan_r2,
    )
    try:
        claude_final = claude_run(synth_prompt, model=DEBATE_CLAUDE_MODEL)
        transcript.claude_final = claude_final.text
        transcript.final_xml = claude_final.text
    except ClaudeError as exc:
        transcript.errors.append(f"Round 4 (Claude synthesis): {exc}")
        transcript.final_xml = transcript.gpt_plan_r2

    return transcript


def execute_plan(plan_file_path: str, task: str) -> dict:
    """Hand off to the claude CLI for execution.

    Returns {"ok": True} if successful, {"ok": False, "message": ...} otherwise.
    """
    if not shutil.which("claude"):
        return {
            "ok": False,
            "plan_only": True,
            "message": (
                f"Claude CLI not found. Plan saved to: {plan_file_path}\n"
                "Paste the plan into your next Claude Code session to execute."
            ),
        }
    import subprocess
    try:
        result = subprocess.run(
            ["claude", "--print", f"Execute the plan at {plan_file_path}: {task}"],
            capture_output=False,
            timeout=300,
        )
        return {"ok": result.returncode == 0}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}
