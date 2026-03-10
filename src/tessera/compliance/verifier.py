"""Compliance verifier — compares plan file targets against actual git diff.

Usage:
  tessera verify [--plan-id N] [--base-ref HEAD~1]
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

from ..core.database import Database
from ..debate.payload import parse_xml


@dataclass
class ComplianceReport:
    plan_id: int
    base_ref: str
    matched: list[dict] = field(default_factory=list)
    missing: list[dict] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)


def _git_diff_files(project_root: str, base_ref: str) -> list[str]:
    """Return list of files changed vs *base_ref*."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref, "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def verify(
    db: Database,
    project_root: str,
    plan_id: int | None = None,
    base_ref: str = "HEAD~1",
) -> ComplianceReport:
    """Run compliance check.

    If *plan_id* is None, uses the most recently active plan.
    """
    if plan_id is not None:
        plan = db.get_plan(plan_id)
    else:
        plan = db.get_active_plan()

    if not plan:
        raise ValueError("No active plan found. Specify --plan-id or activate a plan.")

    pid = plan["id"]
    final_xml = plan["final_plan_xml"] or ""
    payload = parse_xml(final_xml)
    if not payload:
        raise ValueError(f"Could not parse plan XML for plan_id={pid}")

    changed_files = set(_git_diff_files(project_root, base_ref))
    declared_targets = {t["path"]: t["action"] for t in payload.targets}

    report = ComplianceReport(plan_id=pid, base_ref=base_ref)

    for path, action in declared_targets.items():
        if path in changed_files:
            report.matched.append({"path": path, "action": action})
        else:
            report.missing.append({"path": path, "action": action})

    for changed in changed_files:
        if changed not in declared_targets:
            report.extra.append(changed)

    # Auto-complete plan if all matched
    if not report.missing and report.matched:
        db.update_plan_status(pid, "completed")

    return report


def format_report(report: ComplianceReport) -> str:
    total = len(report.matched) + len(report.missing)
    lines = ["Compliance Report", "─" * 40]
    lines.append(f"Matched ({len(report.matched)}/{total}):")
    for item in report.matched:
        lines.append(f"  ✓ {item['path']}  [{item['action']}]")
    if report.missing:
        lines.append(f"\nMissing ({len(report.missing)}/{total}):")
        for item in report.missing:
            lines.append(f"  ✗ {item['path']}  [{item['action']}]  ← declared but not changed")
    if report.extra:
        lines.append(f"\nExtra ({len(report.extra)}):")
        for path in report.extra:
            lines.append(f"  ? {path}  ← changed but not in plan")
    return "\n".join(lines)
