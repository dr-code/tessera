"""Tests for the CLAUDE.md policy block that `tessera scan` injects.

The block must stay in sync with the canonical project template, upgrade older
blocks in place without touching the rest of the file, and be idempotent.
"""

from __future__ import annotations

from pathlib import Path

from tessera.mcp.tools.scan import _POLICY_TEMPLATE, _inject_policy

OLD_V2_BLOCK = """\
<!-- TESSERA:START v2 -->
## Tessera Graph Policy

**MANDATORY**: Call `graph_continue` as your FIRST tool call every turn.
<!-- TESSERA:END -->"""


def test_template_is_v3_and_marked() -> None:
    assert _POLICY_TEMPLATE.startswith("<!-- TESSERA:START v3 -->")
    assert _POLICY_TEMPLATE.rstrip().endswith("<!-- TESSERA:END -->")


def test_template_covers_every_tool_the_workflow_relies_on() -> None:
    for tool in (
        "graph_continue",
        "graph_scan",
        "graph_read",
        "graph_register_edit",
        "graph_lock_decision",
        "graph_retrieve",
        "plan_save",
        "checklist_item_id",
    ):
        assert f"`{tool}`" in _POLICY_TEMPLATE or tool in _POLICY_TEMPLATE, tool


def test_plan_save_bullet_names_its_arguments() -> None:
    line = next(ln for ln in _POLICY_TEMPLATE.splitlines() if "plan_save" in ln)
    for arg in ("project_name", "subtask_name", "task", "plan_markdown"):
        assert arg in line


def test_inject_creates_claude_md_with_one_block(tmp_path: Path) -> None:
    claude_md = tmp_path / "CLAUDE.md"
    _inject_policy(claude_md)
    text = claude_md.read_text(encoding="utf-8")
    assert text.count("<!-- TESSERA:START") == 1
    assert text.count("<!-- TESSERA:END -->") == 1
    assert "plan_save" in text


def test_inject_upgrades_an_old_block_in_place_and_keeps_other_content(tmp_path: Path) -> None:
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text(
        f"# My project\n\nKeep this.\n\n{OLD_V2_BLOCK}\n\n## After\n\nAnd this.\n",
        encoding="utf-8",
    )
    _inject_policy(claude_md)
    text = claude_md.read_text(encoding="utf-8")
    assert "TESSERA:START v2" not in text
    assert "TESSERA:START v3" in text
    assert text.count("<!-- TESSERA:START") == 1
    assert "Keep this." in text and "And this." in text and "## After" in text


def test_inject_is_idempotent(tmp_path: Path) -> None:
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# Project\n\nSome rules.\n", encoding="utf-8")
    _inject_policy(claude_md)
    first = claude_md.read_text(encoding="utf-8")
    _inject_policy(claude_md)
    assert claude_md.read_text(encoding="utf-8") == first


def test_inject_leaves_a_neighbouring_block_untouched(tmp_path: Path) -> None:
    other = "<!-- STARTER-KIT:WORKFLOW:START v1 -->\nworkflow text\n<!-- STARTER-KIT:WORKFLOW:END -->"
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text(f"# P\n\n{other}\n", encoding="utf-8")
    _inject_policy(claude_md)
    _inject_policy(claude_md)
    text = claude_md.read_text(encoding="utf-8")
    assert text.count(other) == 1
    assert text.count("<!-- TESSERA:START") == 1
