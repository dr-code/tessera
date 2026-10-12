"""Tests for the bundled Superpowers skills and the script that builds them.

The skills under skills/ are upstream obra/superpowers files plus tessera overlays
(overlays/skills/*.md). These tests prove that the upstream text is intact, that the
overlays are accounted for, and that the builder behaves on awkward input.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "build_skills.py"

spec = importlib.util.spec_from_file_location("build_skills", SCRIPT)
bs = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
sys.modules["build_skills"] = bs
spec.loader.exec_module(bs)  # type: ignore[union-attr]

PIN = json.loads((ROOT / "overlays" / "UPSTREAM.json").read_text(encoding="utf-8"))

DOC = """---
name: demo
description: demo skill
---

# Demo

Intro.

## Alpha

alpha text

```bash
## not a heading
# nor this
```

### Alpha child

child text

## Beta

beta text
"""


# ── the committed result ────────────────────────────────────────────────────


def test_committed_skills_match_the_pin() -> None:
    assert bs.verify() == []


def test_pin_records_tag_commit_and_what_is_not_bundled() -> None:
    assert re.fullmatch(r"[0-9a-f]{40}", PIN["commit"])
    assert PIN["tag"].startswith("v")
    assert "diagnosing-superpowers" in PIN["not_bundled"]
    assert sorted(PIN["skills"]) == sorted(bs.MANAGED)


def test_every_managed_skill_has_frontmatter_matching_its_folder() -> None:
    for name in bs.MANAGED:
        text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        front = text.split("---")[1]
        assert re.search(rf"^name:\s*{re.escape(name)}\s*$", front, re.M), name
        assert re.search(r"^description:\s*\S", front, re.M), name
        assert text.startswith("---\n"), f"{name}: frontmatter must stay first"


def test_no_upstream_namespace_is_left_in_cross_references() -> None:
    names = "|".join(bs.MANAGED)
    leftover = []
    for name in bs.MANAGED:
        for path in (ROOT / "skills" / name).rglob("*.md"):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(rf"\bsuperpowers:({names})\b", line):
                    leftover.append(f"{path.relative_to(ROOT)}:{number}")
    assert leftover == []


def test_every_overlay_belongs_to_a_managed_skill_and_is_gated_on_the_tessera_mcp() -> None:
    for overlay in sorted((ROOT / "overlays" / "skills").glob("*.md")):
        assert overlay.stem in bs.MANAGED, overlay.name
        for kind, _anchor, content in bs.parse_overlay(overlay):
            body = "\n".join(content)
            assert "superpowers:" not in body, f"{overlay.name}: use the tessera: namespace"
            if re.search(r"graph_|plan_save|tessera-verify|tessera scan", body):
                assert re.search(r"tessera MCP is configured", body, re.I) or kind == "after-frontmatter", (
                    f"{overlay.name}: a block that calls tessera tools must say it applies "
                    "only when the tessera MCP is configured"
                )


def test_helper_scripts_keep_their_executable_bit() -> None:
    for rel in ("executing-plans/scripts/task-start", "subagent-driven-development/scripts/sdd-workspace"):
        assert os.access(ROOT / "skills" / rel, os.X_OK), rel


@pytest.mark.skipif("SUPERPOWERS_CHECKOUT" not in os.environ, reason="set SUPERPOWERS_CHECKOUT to an upstream clone at the pinned commit")
def test_fresh_build_from_upstream_matches_committed() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "check", "--upstream", os.environ["SUPERPOWERS_CHECKOUT"]],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# ── tampering is detected ───────────────────────────────────────────────────


@pytest.fixture
def copy_of_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for sub in ("skills", "overlays"):
        shutil.copytree(ROOT / sub, tmp_path / sub)
    monkeypatch.setattr(bs, "SKILLS_DIR", tmp_path / "skills")
    monkeypatch.setattr(bs, "OVERLAY_DIR", tmp_path / "overlays" / "skills")
    monkeypatch.setattr(bs, "PIN_FILE", tmp_path / "overlays" / "UPSTREAM.json")
    return tmp_path


def test_verify_catches_an_edit_to_upstream_text(copy_of_repo: Path) -> None:
    path = copy_of_repo / "skills" / "writing-plans" / "SKILL.md"
    path.write_text(path.read_text(encoding="utf-8").replace("# Writing Plans", "# Writing Plans (edited)", 1), encoding="utf-8")
    assert any("outside the overlay blocks differs from upstream" in p for p in bs.verify())


def test_verify_catches_an_edit_inside_an_overlay_without_rebuilding(copy_of_repo: Path) -> None:
    overlay = copy_of_repo / "overlays" / "skills" / "writing-plans.md"
    overlay.write_text(overlay.read_text(encoding="utf-8") + "\nextra line\n", encoding="utf-8")
    assert any("changed since the last build" in p for p in bs.verify())


def test_verify_catches_a_hand_added_file_and_a_missing_one(copy_of_repo: Path) -> None:
    (copy_of_repo / "skills" / "brainstorming" / "stray.md").write_text("x", encoding="utf-8")
    (copy_of_repo / "skills" / "brainstorming" / "visual-companion.md").unlink()
    problems = bs.verify()
    assert any("stray.md" in p and "not in UPSTREAM.json" in p for p in problems)
    assert any("visual-companion.md" in p and "missing" in p for p in problems)


def test_verify_catches_a_lost_executable_bit(copy_of_repo: Path) -> None:
    (copy_of_repo / "skills" / "executing-plans" / "scripts" / "task-start").chmod(0o644)
    assert any("executable bit" in p for p in bs.verify())


def test_verify_catches_a_removed_overlay_block(copy_of_repo: Path) -> None:
    path = copy_of_repo / "skills" / "brainstorming" / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"<!-- TESSERA:OVERLAY begin brainstorming-1 -->.*?<!-- TESSERA:OVERLAY end brainstorming-1 -->\n\n", "", text, flags=re.S), encoding="utf-8")
    assert any("overlay blocks" in p for p in bs.verify())


# ── the builder on synthetic documents ──────────────────────────────────────


def overlay_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    directory = tmp_path / "ov"
    directory.mkdir(exist_ok=True)
    (directory / "demo.md").write_text(body, encoding="utf-8")
    monkeypatch.setattr(bs, "OVERLAY_DIR", directory)


def test_overlays_insert_at_the_right_places_and_strip_back_exactly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    overlay_file(
        tmp_path,
        monkeypatch,
        '<!-- overlay: before "## Alpha" -->\nBEFORE ALPHA\n\n<!-- overlay: after-section "## Alpha" -->\nAFTER ALPHA (and its child)\n',
    )
    built = bs.apply_overlays("demo", DOC, "v1", "a" * 40)
    assert built.index("BEFORE ALPHA") < built.index("## Alpha") < built.index("alpha text")
    # after-section skips the child heading and lands before "## Beta"
    assert built.index("child text") < built.index("AFTER ALPHA") < built.index("## Beta")
    assert bs.strip_overlays(built) == DOC


def test_headings_inside_code_fences_are_not_anchors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    overlay_file(tmp_path, monkeypatch, '<!-- overlay: before "## not a heading" -->\nx\n')
    with pytest.raises(bs.BuildError, match="matched 0 headings"):
        bs.apply_overlays("demo", DOC, "v1", "a" * 40)


def test_a_missing_or_duplicated_anchor_fails_loudly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    overlay_file(tmp_path, monkeypatch, '<!-- overlay: before "## Gamma" -->\nx\n')
    with pytest.raises(bs.BuildError, match="matched 0 headings"):
        bs.apply_overlays("demo", DOC, "v1", "a" * 40)
    overlay_file(tmp_path, monkeypatch, '<!-- overlay: before "## Alpha" -->\nx\n')
    with pytest.raises(bs.BuildError, match="matched 2 headings"):
        bs.apply_overlays("demo", DOC.replace("## Beta", "## Alpha"), "v1", "a" * 40)


def test_after_section_at_the_end_of_the_file_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    overlay_file(tmp_path, monkeypatch, '<!-- overlay: after-section "## Beta" -->\nx\n')
    with pytest.raises(bs.BuildError, match="runs to the end"):
        bs.apply_overlays("demo", DOC, "v1", "a" * 40)


def test_a_skill_without_an_overlay_still_gets_a_provenance_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bs, "OVERLAY_DIR", tmp_path / "nothing-here")
    built = bs.apply_overlays("demo", DOC, "v7.0.0", "b" * 40)
    assert built.startswith("---\nname: demo\ndescription: demo skill\n---\n\n<!-- TESSERA:OVERLAY begin provenance -->")
    assert "no tessera overlay" in built
    assert bs.strip_overlays(built) == DOC


def test_text_before_the_first_directive_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "bad.md"
    path.write_text("stray text\n<!-- overlay: before \"## Alpha\" -->\nx\n", encoding="utf-8")
    with pytest.raises(bs.BuildError, match="before the first overlay directive"):
        bs.parse_overlay(path)


def test_reference_substitution_only_touches_bundled_skill_names() -> None:
    assert bs.substitute("use superpowers:writing-plans now") == "use tessera:writing-plans now"
    assert bs.substitute("superpowers:diagnosing-superpowers") == "superpowers:diagnosing-superpowers"
    assert bs.substitute("docs/superpowers/specs and .superpowers/sdd") == "docs/superpowers/specs and .superpowers/sdd"
    assert bs.substitute("xsuperpowers:writing-plans") == "xsuperpowers:writing-plans"
