"""XML payload schema parser and generator for debate plans."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Matches & not already part of a valid XML entity reference.
_UNESCAPED_AMP = re.compile(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)")


@dataclass
class PlanTask:
    task_id: str
    description: str
    file: str
    keywords: list[str] = field(default_factory=list)
    depends: str = ""


@dataclass
class PlanPayload:
    task: str
    created: str
    rounds: int
    verdict: str
    targets: list[dict]    # [{"path": ..., "action": ...}]
    tasks: list[PlanTask]
    validation: list[str]  # criterion strings
    raw_xml: str = ""


def parse_xml(xml_text: str) -> PlanPayload | None:
    """Parse a debate plan XML string into a PlanPayload."""
    # Strip any prose the LLM may have added before/after the XML block.
    start = xml_text.find("<plan")
    end = xml_text.rfind("</plan>")
    if start != -1 and end != -1:
        xml_text = xml_text[start : end + len("</plan>")]
    xml_text = xml_text.strip()
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        # LLMs sometimes emit unescaped & in text nodes. Repair and retry once.
        repaired = _UNESCAPED_AMP.sub("&amp;", xml_text)
        try:
            root = ET.fromstring(repaired)
        except ET.ParseError:
            return None

    meta = root.find("metadata")
    task = meta.findtext("task", "") if meta is not None else ""
    created = meta.findtext("created", "") if meta is not None else ""
    rounds = int(meta.findtext("rounds", "0") or 0) if meta is not None else 0
    verdict = meta.findtext("verdict", "pending") if meta is not None else "pending"

    targets: list[dict] = []
    targets_el = root.find("targets")
    if targets_el is not None:
        for f in targets_el.findall("file"):
            targets.append({"path": f.text or "", "action": f.get("action", "modify")})

    tasks: list[PlanTask] = []
    tasks_el = root.find("tasks")
    if tasks_el is not None:
        for t in tasks_el.findall("task"):
            keywords_raw = t.get("keywords", "")
            keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
            tasks.append(
                PlanTask(
                    task_id=t.get("id", ""),
                    description=(t.text or "").strip(),
                    file=t.get("file", ""),
                    keywords=keywords,
                    depends=t.get("depends", ""),
                )
            )

    validation: list[str] = []
    val_el = root.find("validation")
    if val_el is not None:
        for c in val_el.findall("criterion"):
            if c.text:
                validation.append(c.text.strip())

    return PlanPayload(
        task=task,
        created=created,
        rounds=rounds,
        verdict=verdict,
        targets=targets,
        tasks=tasks,
        validation=validation,
        raw_xml=xml_text,
    )


def build_xml(
    task: str,
    targets: list[dict],
    tasks: list[PlanTask],
    validation: list[str],
    rounds: int,
    verdict: str = "approved",
) -> str:
    """Produce a canonical plan XML string."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    e = saxutils.escape
    targets_xml = "\n".join(
        f'    <file action="{e(t["action"])}">{e(t["path"])}</file>' for t in targets
    )
    tasks_xml = "\n".join(
        f'    <task id="{t.task_id}" file="{e(t.file)}" '
        f'keywords="{e(",".join(t.keywords))}"'
        + (f' depends="{e(t.depends)}"' if t.depends else "")
        + f">\n      {e(t.description)}\n    </task>"
        for t in tasks
    )
    val_xml = "\n".join(f"    <criterion>{e(c)}</criterion>" for c in validation)

    return f"""<plan>
  <metadata>
    <task>{e(task)}</task>
    <created>{now}</created>
    <rounds>{rounds}</rounds>
    <verdict>{verdict}</verdict>
  </metadata>
  <targets>
{targets_xml}
  </targets>
  <tasks order="sequential">
{tasks_xml}
  </tasks>
  <validation>
{val_xml}
  </validation>
</plan>"""
