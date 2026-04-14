"""Task chunking helpers for the debate engine.

When a single Codex call times out, split the task via Claude and merge
the resulting per-chunk XML plans into one coherent plan document.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils

from .claude import ClaudeError, run as claude_run

_SPLIT_PROMPT = """\
Break the following task into 2 to 4 independent, ordered subtasks.
Return ONLY a numbered list, one subtask per line. No prose, no headers.

Task: {task}
"""


def split_task(task: str, model: str) -> list[str]:
    """Ask Claude to decompose *task* into 2–4 ordered subtasks.

    Returns an empty list if Claude is unavailable or returns unparseable output.
    """
    try:
        resp = claude_run(_SPLIT_PROMPT.format(task=task), model=model)
    except ClaudeError:
        return []

    subtasks: list[str] = []
    for line in resp.text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip leading "1. " / "1) " numbering if present
        if line[0].isdigit() and len(line) > 2 and line[1] in ".):":
            line = line[2:].lstrip()
        elif line[:2].rstrip(".):").isdigit() and len(line) > 3:
            line = line[3:].lstrip()
        if line:
            subtasks.append(line)

    return subtasks[:4]


def merge_xml_plans(plans: list[str], original_task: str) -> str:
    """Merge a list of XML plan strings into one combined plan document.

    Concatenates <file>, <task>, and <criterion> nodes across all plans,
    renumbering tasks sequentially. Returns an empty string if no valid
    XML could be extracted from any plan.
    """
    merged_targets: list[tuple[str, str]] = []  # (action, path)
    merged_tasks: list[tuple[str, str, str, str]] = []  # (id, file, keywords, desc)
    merged_criteria: list[str] = []
    task_id = 1

    for plan in plans:
        start = plan.find("<plan")
        end = plan.rfind("</plan>")
        if start == -1 or end == -1:
            continue
        xml_str = plan[start : end + len("</plan>")]
        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError:
            continue

        for f in root.findall("targets/file"):
            merged_targets.append((f.get("action", "modify"), f.text or ""))

        for t in root.findall("tasks/task"):
            merged_tasks.append((
                str(task_id),
                t.get("file", ""),
                t.get("keywords", ""),
                (t.text or "").strip(),
            ))
            task_id += 1

        for c in root.findall("validation/criterion"):
            merged_criteria.append(c.text or "")

    if not merged_tasks:
        return ""

    e = saxutils.escape
    lines = [
        "<plan>",
        "  <metadata>",
        f"    <task>{e(original_task)}</task>",
        "    <created></created>",
        "    <rounds>0</rounds>",
        "    <verdict>draft</verdict>",
        "  </metadata>",
        "  <targets>",
    ]
    for action, path in merged_targets:
        lines.append(f'    <file action="{action}">{e(path)}</file>')
    lines += ["  </targets>", '  <tasks order="sequential">']
    for tid, tfile, tkw, desc in merged_tasks:
        lines.append(f'    <task id="{tid}" file="{e(tfile)}" keywords="{e(tkw)}">')
        lines.append(f"      {e(desc)}")
        lines.append("    </task>")
    lines += ["  </tasks>", "  <validation>"]
    for criterion in merged_criteria:
        lines.append(f"    <criterion>{e(criterion)}</criterion>")
    lines += ["  </validation>", "</plan>"]

    return "\n".join(lines)
