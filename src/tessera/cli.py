"""Tessera CLI — built with Click.

All subcommands are defined here. Heavy imports (debate, dashboard) are
done inside the command functions to avoid ImportError when optional deps
are not installed.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import click

from .core.config import (
    ENABLE_COMPLIANCE,
    ENABLE_DASHBOARD,
    ENABLE_DEBATE,
    PROJECT_ROOT,
)
from .core.database import Database


def _get_db(project_root: str | None = None) -> tuple[Database, str]:
    root = project_root or PROJECT_ROOT or os.getcwd()
    root = str(Path(root).resolve())
    return Database(root), root


def _build_mcp_config(project_root: str) -> dict:
    """Return the MCP server config dict for a given project root.

    Uses ``uvx --from tessera tessera mcp`` so the server starts without
    requiring tessera to be pre-installed in the active Python environment.
    Consistent with ``.claude-plugin/.mcp.json``.
    """
    return {
        "mcpServers": {
            "tessera": {
                "command": "uvx",
                "args": ["--from", "tessera", "tessera", "mcp"],
                "env": {"TESSERA_PROJECT_ROOT": project_root},
            }
        }
    }


# ─────────────────────────────────────────────────────────────────────────────

@click.group()
@click.version_option()
def main() -> None:
    """Tessera — persistent codebase memory for Claude Code."""


# ── tessera scan ────────────────────────────────────────────────────────────

@main.command()
@click.argument("path", default=".")
@click.option("--full", is_flag=True, help="Force full rebuild (skip incremental).")
def scan(path: str, full: bool) -> None:
    """Build or rebuild the info graph for PATH (default: current directory)."""
    from .graph.builder import build_graph

    root = str(Path(path).resolve())
    db, _ = _get_db(root)
    db.get_or_create_session(root)

    click.echo(f"Scanning {root} ({'full' if full else 'incremental'})...")
    stats = build_graph(root, db, incremental=not full)
    click.echo(
        f"Done. {stats['files_scanned']} files scanned, "
        f"{stats['files_skipped']} skipped, "
        f"{stats['symbols_found']} symbols, "
        f"{stats['edges_found']} edges."
    )

    # Inject CLAUDE.md policy
    from .mcp.tools.scan import _inject_policy
    claude_md = Path(root) / "CLAUDE.md"
    try:
        _inject_policy(claude_md)
        click.echo(f"CLAUDE.md policy injected → {claude_md}")
    except OSError as exc:
        click.echo(f"Warning: could not update CLAUDE.md: {exc}", err=True)

    # Write .mcp.json
    mcp_json = Path(root) / ".mcp.json"
    mcp_config = _build_mcp_config(root)
    if not mcp_json.exists():
        mcp_json.write_text(json.dumps(mcp_config, indent=2), encoding="utf-8")
        click.echo(f".mcp.json written → {mcp_json}")
    else:
        click.echo(f".mcp.json already exists → {mcp_json} (not overwritten)")


# ── tessera mcp ─────────────────────────────────────────────────────────────

@main.command("mcp")
def mcp_serve() -> None:
    """Start the MCP server (stdio transport)."""
    from .mcp.server import serve
    asyncio.run(serve())


# ── tessera status ──────────────────────────────────────────────────────────

@main.command()
@click.argument("path", default=".")
def status(path: str) -> None:
    """Show graph stats for PATH."""
    root = str(Path(path).resolve())
    db, _ = _get_db(root)
    stats = db.get_stats()
    click.echo(f"Project: {root}")
    for k, v in stats.items():
        click.echo(f"  {k}: {v}")


# ── tessera decisions ────────────────────────────────────────────────────────

@main.command()
@click.argument("path", default=".")
def decisions(path: str) -> None:
    """List locked decisions for the current session."""
    root = str(Path(path).resolve())
    db, _ = _get_db(root)
    session_id = db.get_or_create_session(root)
    rows = db.get_decisions(session_id=session_id)
    if not rows:
        click.echo("No decisions recorded this session.")
        return
    for d in rows:
        click.echo(f"  [{d['scope']}] {d['summary']}")


# ── tessera reset ────────────────────────────────────────────────────────────

@main.command()
@click.argument("path", default=".")
@click.option("--yes", is_flag=True, help="Skip confirmation.")
def reset(path: str, yes: bool) -> None:
    """Clear the action graph (actions + decisions) for current session."""
    root = str(Path(path).resolve())
    db, _ = _get_db(root)
    session_id = db.get_or_create_session(root)
    if not yes:
        click.confirm("Clear action graph for this session?", abort=True)
    db.clear_action_graph(session_id)
    click.echo("Action graph cleared.")


# ── tessera plans ────────────────────────────────────────────────────────────

@main.command("plans")
@click.argument("project", default="")
@click.argument("subtask", default="")
@click.argument("path", default=".")
def plans_cmd(project: str, subtask: str, path: str) -> None:
    """List plans. Optionally filter by PROJECT and SUBTASK."""
    root = str(Path(path).resolve())
    db, _ = _get_db(root)

    all_projects = db.list_projects()
    if not all_projects:
        click.echo("No plans found.")
        return

    for p in all_projects:
        if project and p["name"] != project:
            continue
        click.echo(f"\nProject: {p['name']}")
        for s in db.list_subtasks(p["id"]):
            if subtask and s["name"] != subtask:
                continue
            plan = db._execute(
                "SELECT * FROM plans WHERE subtask_id=? ORDER BY created_at DESC LIMIT 1",
                (s["id"],),
            ).fetchone()
            status_str = plan["status"] if plan else "no plan"
            click.echo(f"  {s['name']}  [{status_str}]")
            if plan and subtask:
                checklist = db.get_plan_checklist(plan["id"])
                for item in checklist:
                    mark = "x" if item["status"] == "done" else " "
                    click.echo(f"    [{mark}] {item['description']}")


# ── tessera verify ───────────────────────────────────────────────────────────

@main.command()
@click.option("--plan-id", type=int, default=None)
@click.option("--base-ref", default="HEAD~1")
@click.argument("path", default=".")
def verify(plan_id: int | None, base_ref: str, path: str) -> None:
    """Compliance check: plan targets vs git diff."""
    if not ENABLE_COMPLIANCE:
        click.echo("Compliance is disabled (TESSERA_ENABLE_COMPLIANCE=0).", err=True)
        sys.exit(1)
    from .compliance.verifier import format_report, verify as do_verify

    root = str(Path(path).resolve())
    db, _ = _get_db(root)
    try:
        report = do_verify(db, root, plan_id=plan_id, base_ref=base_ref)
        click.echo(format_report(report))
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)


# ── tessera handoff ──────────────────────────────────────────────────────────

@main.command()
@click.argument("path", default=".")
@click.option("--json", "as_json", is_flag=True)
def handoff(path: str, as_json: bool) -> None:
    """Generate a clipboard-ready handoff summary."""
    from .handoff.generator import generate

    root = str(Path(path).resolve())
    db, _ = _get_db(root)
    session_id = db.get_or_create_session(root)
    output = generate(db, root, session_id=session_id, as_json=as_json)
    click.echo(output)


# ── tessera dashboard ────────────────────────────────────────────────────────

@main.command()
@click.argument("path", default=".")
def dashboard(path: str) -> None:
    """Start the dashboard at localhost:5050."""
    if not ENABLE_DASHBOARD:
        click.echo("Dashboard is disabled (TESSERA_ENABLE_DASHBOARD=0).", err=True)
        sys.exit(1)
    from .dashboard.server import run_dashboard

    root = str(Path(path).resolve())
    run_dashboard(project_root=root)


# ── tessera debate ───────────────────────────────────────────────────────────

@main.command()
@click.argument("task")
@click.option("--project", default="", help="Project name (skips prompt).")
@click.option("--subtask", default="", help="Subtask name (skips prompt).")
@click.option("--yes", is_flag=True, help="Skip confirmation, auto-execute.")
@click.option("--no-exec", is_flag=True, help="Archive plan but don't execute.")
@click.option("--max-rounds", type=int, default=3)
@click.option("--codex-timeout", type=int, default=1200, help="Seconds before a Codex CLI call times out (default 1200).")
@click.argument("path", default=".")
def debate(
    task: str,
    project: str,
    subtask: str,
    yes: bool,
    no_exec: bool,
    max_rounds: int,
    codex_timeout: int,
    path: str,
) -> None:
    """Run a multi-round Claude vs GPT debate and archive the resulting plan."""
    if not ENABLE_DEBATE:
        click.echo("Debate is disabled (TESSERA_ENABLE_DEBATE=0).", err=True)
        sys.exit(1)

    from .debate.engine import check_capabilities, run_debate, execute_plan
    from .debate.payload import parse_xml
    from .plans.archive import save_plan

    # Capability check
    caps = check_capabilities()
    if not caps["codex_cli"]:
        click.echo(
            "Error: Codex CLI not found.\n"
            "Install with: npm install -g @openai/codex\n"
            "Or run with --no-exec to generate a plan without execution.",
            err=True,
        )
        sys.exit(1)
    if not caps["claude_api"]:
        click.echo(
            "Warning: Claude API unavailable (ANTHROPIC_API_KEY not set or anthropic not installed).\n"
            "Debate will run in Codex-only mode — Claude critique rounds will be skipped.\n"
            "Set ANTHROPIC_API_KEY for full multi-model debate.",
            err=True,
        )

    root = str(Path(path).resolve())
    db, _ = _get_db(root)

    click.echo(f"Starting debate: {task!r} ({max_rounds} rounds)...")
    transcript = run_debate(task, max_rounds=max_rounds, project_root=root, codex_timeout=codex_timeout)

    if transcript.errors:
        click.echo("Debate errors:", err=True)
        for e in transcript.errors:
            click.echo(f"  {e}", err=True)

    final_xml = transcript.final_xml
    payload = parse_xml(final_xml)
    if not payload:
        click.echo("Error: could not parse final plan XML.", err=True)
        click.echo(final_xml)
        sys.exit(1)

    # Project / subtask selection
    if not project:
        existing = [p["name"] for p in db.list_projects()]
        if existing:
            click.echo("Existing projects: " + ", ".join(existing))
        project = click.prompt("Project name", default="default")
    if not subtask:
        subtask = click.prompt("Subtask name", default=task[:40])

    # Build transcript text
    transcript_text = json.dumps(
        {
            "task": task,
            "rounds": transcript.rounds_completed,
            "gpt_r1": transcript.gpt_plan_r1[:2000],
            "claude_critique": transcript.claude_critique[:2000],
            "gpt_r2": transcript.gpt_plan_r2[:2000],
            "claude_final": transcript.claude_final[:2000],
        }
    )
    debate_summary = transcript.claude_critique[:300] if transcript.claude_critique else ""

    plan_id, plan_file = save_plan(
        db=db,
        project_root=root,
        project_name=project,
        subtask_name=subtask,
        task=task,
        debate_transcript_text=transcript_text,
        payload=payload,
        debate_summary=debate_summary,
    )
    click.echo(f"Plan #{plan_id} saved → {plan_file}")

    if no_exec:
        click.echo("--no-exec: skipping execution.")
        return

    if not yes:
        click.confirm("Execute this plan with Claude?", abort=True)

    result = execute_plan(plan_file, task)
    if result.get("plan_only"):
        click.echo(result["message"])
    elif result.get("ok"):
        click.echo("Execution complete.")
    else:
        click.echo(f"Execution error: {result.get('message', 'unknown')}", err=True)
        sys.exit(1)


# ── tessera plan-add ─────────────────────────────────────────────────────────

@main.command("plan-add")
@click.argument("path", default=".")
@click.option("--project", default="", help="Project name.")
@click.option("--subtask", default="", help="Subtask / feature name.")
@click.option("--description", default="", help="Plan description or summary.")
@click.option("--task", "tasks", multiple=True, help="Checklist item (repeatable).")
@click.option("--status", default="in_progress",
              type=click.Choice(["pending", "in_progress", "done"]),
              help="Initial plan status.")
def plan_add(
    path: str,
    project: str,
    subtask: str,
    description: str,
    tasks: tuple[str, ...],
    status: str,
) -> None:
    """Save a plan to the tessera DB without running a full debate.

    Useful when the build skill uses its inline fallback and you still want
    the plan visible in the dashboard.

    Example:
        tessera plan-add --project my-app --subtask "add filters" \\
            --description "Add date/status filters to the table." \\
            --task "Create FilterBar component" \\
            --task "Wire filters to API query params" \\
            --task "Write unit tests"
    """
    from datetime import datetime

    root = str(Path(path).resolve())
    db, _ = _get_db(root)

    if not project:
        existing = [p["name"] for p in db.list_projects()]
        if existing:
            click.echo("Existing projects: " + ", ".join(existing))
        project = click.prompt("Project name", default="default")
    if not subtask:
        subtask = click.prompt("Subtask name")

    project_id = db.create_project(project)
    subtask_id = db.create_subtask(project_id, subtask)

    # Write a minimal markdown plan file so the record has a valid path
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    plan_dir = Path(root) / ".tessera" / "plans" / project / subtask
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_file = plan_dir / f"plan-{timestamp}.md"

    checklist_md = "\n".join(f"- [ ] {t}" for t in tasks) if tasks else "_No checklist items._"
    plan_file.write_text(
        f"# Plan: {project} / {subtask}\n\nCreated: {timestamp}\nStatus: {status}\n\n"
        f"## Description\n{description or '(no description provided)'}\n\n"
        f"## Checklist\n{checklist_md}\n",
        encoding="utf-8",
    )

    plan_id = db.save_plan(
        subtask_id=subtask_id,
        debate_transcript=description,
        final_plan_xml="",
        plan_file_path=str(plan_file),
    )
    db.update_plan_status(plan_id, status)

    _STOP_WORDS = {
        "a", "an", "the", "and", "or", "to", "in", "of", "for", "with",
        "add", "new", "update", "create", "write", "make", "implement", "fix",
    }

    for i, task_text in enumerate(tasks):
        # Extract meaningful keywords from the task description for auto-checking
        raw_words = task_text.lower().replace("-", " ").split()
        keywords = [w for w in raw_words if len(w) > 3 and w not in _STOP_WORDS]
        db.add_checklist_item(
            plan_id=plan_id,
            task_id_in_plan=str(i + 1),
            description=task_text,
            keywords=keywords,
            file_target="",
            sort_order=i,
        )

    click.echo(f"Plan #{plan_id} saved → {plan_file}")
    click.echo(f"  Project: {project} / {subtask}")
    click.echo(f"  Status:  {status}")
    click.echo(f"  Tasks:   {len(tasks)}")


# ── tessera plan-check ────────────────────────────────────────────────────────

@main.command("plan-check")
@click.argument("path", default=".")
@click.option("--plan-id", type=int, default=0, help="Plan ID (default: active in_progress plan).")
@click.option("--item-id", type=int, default=0, help="Mark a specific checklist item done.")
@click.option("--all-pending", is_flag=True, help="Mark all pending items done.")
def plan_check(path: str, plan_id: int, item_id: int, all_pending: bool) -> None:
    """Show or manually complete checklist items for a plan.

    With no flags: shows current checklist status for the active plan.
    With --item-id: marks that item done.
    With --all-pending: marks every pending item done (use after confirming implementation).

    Examples:
        tessera plan-check .
        tessera plan-check --item-id 3 .
        tessera plan-check --plan-id 2 --all-pending .
    """
    import time as _time

    root = str(Path(path).resolve())
    db, _ = _get_db(root)

    if plan_id:
        plan = db.get_plan(plan_id)
    else:
        plan = db.get_active_plan()

    if not plan:
        click.echo("No active in_progress plan found. Use --plan-id to specify one.", err=True)
        return

    pid = plan["id"]
    checklist = db.get_plan_checklist(pid)

    if not checklist:
        click.echo(f"Plan #{pid} has no checklist items.")
        return

    if item_id:
        target = next((i for i in checklist if i["id"] == item_id), None)
        if not target:
            click.echo(f"Item {item_id} not found in plan #{pid}.", err=True)
            return
        db.update_checklist_item(item_id, "done", _time.time())
        if plan["plan_file_path"]:
            from .mcp.tools.edit import _atomic_rewrite_checklist
            _atomic_rewrite_checklist(plan["plan_file_path"], target["description"])
        click.echo(f"Marked done: {target['description']}")
    elif all_pending:
        pending = [i for i in checklist if i["status"] != "done"]
        for item in pending:
            db.update_checklist_item(item["id"], "done", _time.time())
            if plan["plan_file_path"]:
                from .mcp.tools.edit import _atomic_rewrite_checklist
                _atomic_rewrite_checklist(plan["plan_file_path"], item["description"])
            click.echo(f"Marked done: {item['description']}")
        if not pending:
            click.echo("All items already done.")
        remaining = db.get_plan_checklist(pid)
        if all(i["status"] == "done" for i in remaining):
            db.update_plan_status(pid, "completed")
            click.echo(f"Plan #{pid} marked completed.")
    else:
        # Status display
        done = sum(1 for i in checklist if i["status"] == "done")
        click.echo(f"\nPlan #{pid} — {done}/{len(checklist)} complete\n")
        for item in checklist:
            tick = "x" if item["status"] == "done" else " "
            click.echo(f"  [{tick}] (id={item['id']}) {item['description']}")
        click.echo()


if __name__ == "__main__":
    main()
