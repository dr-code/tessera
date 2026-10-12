#!/usr/bin/env python3
"""Build tessera's bundled Superpowers skills from a pinned upstream checkout plus overlays.

Tessera bundles skills from https://github.com/obra/superpowers. The upstream files are
kept byte for byte (apart from one documented skill-reference substitution), and tessera's
own additions live in overlays/skills/<skill>.md, each pinned to an exact upstream heading.
overlays/UPSTREAM.json records the upstream tag and commit and a hash of every file, so the
claim "this is upstream plus these overlays" can be checked.

Usage:
  python scripts/build_skills.py build --upstream /path/to/superpowers [--update-pin]
    (--update-pin is only needed to move to a different upstream commit)
  python scripts/build_skills.py check --upstream /path/to/superpowers
  python scripts/build_skills.py verify

  build   write skills/<name>/ for every managed skill from the upstream checkout
  check   rebuild in a temp folder and compare with the committed skills/
  verify  no upstream needed: check the committed skills/ against UPSTREAM.json

Standard library only. Re-basing on a new upstream release:
  1. git clone --branch <new tag> https://github.com/obra/superpowers /tmp/superpowers
  2. python scripts/build_skills.py build --upstream /tmp/superpowers --update-pin
     (a moved or renamed upstream heading makes this fail loudly: fix that overlay)
  3. review the diff, run the tests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
OVERLAY_DIR = ROOT / "overlays" / "skills"
PIN_FILE = ROOT / "overlays" / "UPSTREAM.json"
REPO_URL = "https://github.com/obra/superpowers"

# Upstream skills that tessera bundles. Others (for example diagnosing-superpowers, which
# reads session transcripts and files issues for upstream maintainers) are deliberately not bundled.
MANAGED = [
    "brainstorming",
    "dispatching-parallel-agents",
    "executing-plans",
    "finishing-a-development-branch",
    "receiving-code-review",
    "requesting-code-review",
    "subagent-driven-development",
    "systematic-debugging",
    "test-driven-development",
    "using-git-worktrees",
    "using-superpowers",
    "verification-before-completion",
    "writing-plans",
    "writing-skills",
]

# Upstream refers to its skills as "superpowers:<name>". In this plugin they are "tessera:<name>".
SUBSTITUTION_PATTERN = r"\bsuperpowers:(" + "|".join(re.escape(n) for n in MANAGED) + r")\b"
SUBSTITUTION_REPLACEMENT = r"tessera:\1"
SUBSTITUTION = re.compile(SUBSTITUTION_PATTERN)

DIRECTIVE = re.compile(r'^<!-- overlay: (before|after-section|after-frontmatter)(?: "(.*)")? -->$')
BLOCK_BEGIN = re.compile(r"^<!-- TESSERA:OVERLAY begin (\S+) -->$")
BLOCK_END = re.compile(r"^<!-- TESSERA:OVERLAY end (\S+) -->$")
HEADING = re.compile(r"^(#{1,6}) (.*)$")


class BuildError(Exception):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def substitute(text: str) -> str:
    return SUBSTITUTION.sub(SUBSTITUTION_REPLACEMENT, text)


# ── markdown helpers ────────────────────────────────────────────────────────


def frontmatter_end(lines: list[str]) -> int:
    """Index of the closing --- of the YAML frontmatter."""
    if not lines or lines[0] != "---":
        raise BuildError("SKILL.md does not start with frontmatter")
    for i in range(1, len(lines)):
        if lines[i] == "---":
            return i
    raise BuildError("frontmatter is not closed")


def headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """(line index, level, full heading line) for headings outside code fences."""
    found: list[tuple[int, int, str]] = []
    fence: str | None = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        marker = stripped[:3]
        if marker in ("```", "~~~"):
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            continue
        if fence is not None:
            continue
        m = HEADING.match(line)
        if m:
            found.append((i, len(m.group(1)), line))
    return found


def find_heading(lines: list[str], text: str, skill: str) -> tuple[int, int]:
    hits = [(i, level) for i, level, line in headings(lines) if line == text]
    if len(hits) != 1:
        raise BuildError(
            f"{skill}: overlay anchor {text!r} matched {len(hits)} headings in upstream SKILL.md "
            "(upstream may have renamed or moved it; update the overlay)"
        )
    return hits[0]


def section_end(lines: list[str], index: int, level: int, skill: str, text: str) -> int:
    for i, lvl, _ in headings(lines):
        if i > index and lvl <= level:
            return i
    raise BuildError(f"{skill}: section {text!r} runs to the end of the file; anchor on a different heading")


# ── overlays ────────────────────────────────────────────────────────────────


def parse_overlay(path: Path) -> list[tuple[str, str | None, list[str]]]:
    directives: list[tuple[str, str | None, list[str]]] = []
    current: tuple[str, str | None, list[str]] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = DIRECTIVE.match(line)
        if m:
            if current:
                directives.append(current)
            current = (m.group(1), m.group(2), [])
            if m.group(1) != "after-frontmatter" and not m.group(2):
                raise BuildError(f"{path.name}: {m.group(1)} needs a quoted heading")
        elif current is not None:
            current[2].append(line)
        elif line.strip():
            raise BuildError(f"{path.name}: text before the first overlay directive")
    if current:
        directives.append(current)
    return directives


def make_block(block_id: str, content: list[str]) -> list[str]:
    body = list(content)
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    return [f"<!-- TESSERA:OVERLAY begin {block_id} -->", *body, f"<!-- TESSERA:OVERLAY end {block_id} -->"]


def provenance_lines(skill: str, tag: str, commit: str, has_overlay: bool) -> list[str]:
    source = f"overlays/skills/{skill}.md" if has_overlay else "no tessera overlay"
    return [
        f"<!-- Generated from obra/superpowers {tag} ({commit[:7]}) + {source}. "
        "Do not edit by hand: edit the overlay and run scripts/build_skills.py. -->"
    ]


def apply_overlays(skill: str, text: str, tag: str, commit: str) -> str:
    lines = text.split("\n")
    overlay_path = OVERLAY_DIR / f"{skill}.md"
    directives = parse_overlay(overlay_path) if overlay_path.exists() else []

    inserts: list[tuple[int, int, list[str]]] = []  # (index, order, block lines)
    end = frontmatter_end(lines)
    at = end + 1
    if at < len(lines) and lines[at] == "":
        at += 1
    inserts.append((at, 0, make_block("provenance", provenance_lines(skill, tag, commit, bool(directives)))))

    for n, (kind, anchor, content) in enumerate(directives, 1):
        block = make_block(f"{skill}-{n}", content)
        if kind == "after-frontmatter":
            inserts.append((at, n, block))
        elif kind == "before":
            idx, _ = find_heading(lines, anchor or "", skill)
            inserts.append((idx, n, block))
        else:
            idx, level = find_heading(lines, anchor or "", skill)
            inserts.append((section_end(lines, idx, level, skill, anchor or ""), n, block))

    out: list[str] = []
    cursor = 0
    for idx, _, block in sorted(inserts, key=lambda t: (t[0], t[1])):
        out.extend(lines[cursor:idx])
        out.extend(block)
        out.append("")
        cursor = idx
    out.extend(lines[cursor:])
    return "\n".join(out)


def strip_overlays(text: str) -> str:
    """Remove every overlay block (and the one blank line after it)."""
    out: list[str] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = BLOCK_BEGIN.match(lines[i])
        if m:
            j = i + 1
            while j < len(lines):
                end = BLOCK_END.match(lines[j])
                if end and end.group(1) == m.group(1):
                    break
                j += 1
            if j >= len(lines):
                raise BuildError(f"unterminated overlay block {m.group(1)}")
            i = j + 1
            if i < len(lines) and lines[i] == "":
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


# ── building ────────────────────────────────────────────────────────────────


def upstream_info(upstream: Path) -> tuple[str, str]:
    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(upstream), *args], capture_output=True, text=True, check=True).stdout.strip()

    commit = git("rev-parse", "HEAD")
    try:
        tag = git("describe", "--tags", "--exact-match")
    except subprocess.CalledProcessError:
        tag = "untagged"
    return tag, commit


def read_pin() -> dict:
    if not PIN_FILE.exists():
        raise BuildError(f"{PIN_FILE.relative_to(ROOT)} is missing; run build with --update-pin")
    return json.loads(PIN_FILE.read_text(encoding="utf-8"))


def build_skill(skill: str, upstream: Path, tag: str, commit: str) -> dict[str, tuple[bytes, int, dict]]:
    """relative path -> (bytes, mode, pin record)"""
    src = upstream / "skills" / skill
    if not src.is_dir():
        raise BuildError(f"upstream has no skills/{skill}")
    files: dict[str, tuple[bytes, int, dict]] = {}
    for path in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = path.relative_to(src).as_posix()
        original = path.read_bytes()
        mode = path.stat().st_mode & 0o777
        record: dict = {"upstream_sha256": sha256(original), "mode": oct(mode)[2:]}
        if rel.endswith(".md"):
            patched = substitute(original.decode("utf-8"))
            record["patched_sha256"] = sha256(patched.encode("utf-8"))
            if rel == "SKILL.md":
                record["overlay_sha256"] = (
                    sha256((OVERLAY_DIR / f"{skill}.md").read_bytes()) if (OVERLAY_DIR / f"{skill}.md").exists() else None
                )
                final = apply_overlays(skill, patched, tag, commit)
            else:
                final = patched
            data = final.encode("utf-8")
        else:
            data = original
        files[rel] = (data, mode, record)
    return files


def write_skills(upstream: Path, target: Path, tag: str, commit: str) -> dict:
    pin_skills: dict = {}
    for skill in MANAGED:
        built = build_skill(skill, upstream, tag, commit)
        dest = target / skill
        if dest.exists():
            shutil.rmtree(dest)
        for rel, (data, mode, _) in built.items():
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            out.chmod(mode)
        pin_skills[skill] = {"files": {rel: rec for rel, (_, _, rec) in built.items()}}
    return pin_skills


def cmd_build(args: argparse.Namespace) -> int:
    upstream = Path(args.upstream).resolve()
    tag, commit = upstream_info(upstream)
    if not args.update_pin:
        pin = read_pin()
        if pin["commit"] != commit:
            raise BuildError(
                f"upstream checkout is {commit[:7]} ({tag}) but the pin is {pin['commit'][:7]} ({pin['tag']}); "
                "use --update-pin to re-base onto the new upstream release"
            )
    pin_skills = write_skills(upstream, SKILLS_DIR, tag, commit)
    # The pin is rewritten on every build so overlay edits are recorded; --update-pin is only
    # needed to move to a different upstream commit.
    pin = {
        "repo": REPO_URL,
        "tag": tag,
        "commit": commit,
        "substitution": {"pattern": SUBSTITUTION_PATTERN, "replacement": SUBSTITUTION_REPLACEMENT},
        "not_bundled": sorted(p.name for p in (upstream / "skills").iterdir() if p.is_dir() and p.name not in MANAGED),
        "skills": pin_skills,
    }
    PIN_FILE.write_text(json.dumps(pin, indent=2) + "\n", encoding="utf-8")
    print(f"built {len(MANAGED)} skills from superpowers {tag} ({commit[:7]}); pin recorded")
    return 0


def tree(path: Path) -> dict[str, tuple[bytes, int]]:
    return {
        p.relative_to(path).as_posix(): (p.read_bytes(), p.stat().st_mode & 0o777)
        for p in sorted(path.rglob("*"))
        if p.is_file()
    }


def cmd_check(args: argparse.Namespace) -> int:
    upstream = Path(args.upstream).resolve()
    tag, commit = upstream_info(upstream)
    pin = read_pin()
    if pin["commit"] != commit:
        raise BuildError(f"upstream checkout is {commit[:7]} but the pin is {pin['commit'][:7]}")
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        write_skills(upstream, Path(tmp), tag, commit)
        for skill in MANAGED:
            built, committed = tree(Path(tmp) / skill), tree(SKILLS_DIR / skill) if (SKILLS_DIR / skill).is_dir() else {}
            for rel in sorted(set(built) | set(committed)):
                if rel not in committed:
                    problems.append(f"{skill}/{rel}: missing from skills/")
                elif rel not in built:
                    problems.append(f"{skill}/{rel}: not produced by the build")
                elif built[rel] != committed[rel]:
                    problems.append(f"{skill}/{rel}: differs from a fresh build")
    return report(problems, "committed skills match a fresh build from upstream + overlays")


def verify() -> list[str]:
    """Check committed skills against UPSTREAM.json without needing an upstream checkout."""
    pin = read_pin()
    problems: list[str] = []
    if sorted(pin["skills"]) != sorted(MANAGED):
        problems.append("UPSTREAM.json skill list differs from MANAGED")
    for skill in MANAGED:
        base = SKILLS_DIR / skill
        record = pin["skills"].get(skill, {}).get("files", {})
        present = {p.relative_to(base).as_posix(): p for p in base.rglob("*") if p.is_file()} if base.is_dir() else {}
        for rel in sorted(set(record) | set(present)):
            if rel not in present:
                problems.append(f"{skill}/{rel}: missing")
                continue
            if rel not in record:
                problems.append(f"{skill}/{rel}: not in UPSTREAM.json (hand-added or stale)")
                continue
            path, rec = present[rel], record[rel]
            data = path.read_bytes()
            if (path.stat().st_mode & 0o111 != 0) != (int(rec["mode"], 8) & 0o111 != 0):
                problems.append(f"{skill}/{rel}: executable bit differs from upstream")
            if rel == "SKILL.md":
                text = data.decode("utf-8")
                expected_blocks = 1 + (len(parse_overlay(OVERLAY_DIR / f"{skill}.md")) if (OVERLAY_DIR / f"{skill}.md").exists() else 0)
                begins = [l for l in text.split("\n") if BLOCK_BEGIN.match(l)]
                if len(begins) != expected_blocks:
                    problems.append(f"{skill}/SKILL.md: {len(begins)} overlay blocks, overlay file defines {expected_blocks}")
                if sha256(strip_overlays(text).encode("utf-8")) != rec["patched_sha256"]:
                    problems.append(f"{skill}/SKILL.md: text outside the overlay blocks differs from upstream")
                overlay = OVERLAY_DIR / f"{skill}.md"
                current = sha256(overlay.read_bytes()) if overlay.exists() else None
                if current != rec.get("overlay_sha256"):
                    problems.append(f"{skill}: overlays/skills/{skill}.md changed since the last build; run scripts/build_skills.py")
            elif rel.endswith(".md"):
                if sha256(data) != rec["patched_sha256"]:
                    problems.append(f"{skill}/{rel}: differs from upstream (after the reference substitution)")
            elif sha256(data) != rec["upstream_sha256"]:
                problems.append(f"{skill}/{rel}: differs from upstream")
    return problems


def report(problems: list[str], ok: str) -> int:
    if problems:
        print("\n".join(problems))
        print(f"{len(problems)} problem(s)")
        return 1
    print(ok)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--upstream", required=True)
    build.add_argument("--update-pin", action="store_true")
    check = sub.add_parser("check")
    check.add_argument("--upstream", required=True)
    sub.add_parser("verify")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            return cmd_build(args)
        if args.command == "check":
            return cmd_check(args)
        return report(verify(), "committed skills match UPSTREAM.json (upstream text intact, overlays accounted for)")
    except BuildError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
