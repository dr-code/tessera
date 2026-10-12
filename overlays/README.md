# Bundled Superpowers skills: how they are built

The 14 Superpowers skills under `skills/` are **upstream files plus tessera overlays**, not hand-edited copies.

| Piece | What it is |
|-------|------------|
| `overlays/UPSTREAM.json` | The upstream tag and commit, and the hash of every upstream file (and of the text left after tessera's one substitution). |
| `overlays/skills/<name>.md` | Tessera's additions for one skill. Each block is pinned to an exact upstream heading. |
| `scripts/build_skills.py` | Builds `skills/` from an upstream checkout plus the overlays, and verifies the result. |
| `skills/<name>/` | The generated output. Do not edit by hand. |

What the build does to upstream's files:

- Copies every file of each bundled skill folder, including helper scripts and prompt templates (executable bits kept).
- Rewrites skill cross-references from `superpowers:<skill>` to `tessera:<skill>`, only for skills that tessera bundles.
- Inserts the overlay blocks, each wrapped in `<!-- TESSERA:OVERLAY begin ... -->` / `end` markers, and a provenance note after the frontmatter.

Nothing else is changed, and the tests prove it: stripping the overlay blocks from a built `SKILL.md` gives back exactly the recorded upstream text.

## Overlay file format

```
<!-- overlay: before "## Some Upstream Heading" -->
Markdown to insert before that heading.

<!-- overlay: after-section "## Another Heading" -->
Markdown to insert after that whole section (before the next heading of the same or higher level).
```

Anchors are matched exactly against headings outside code fences and must match exactly one. If upstream renames or moves a heading, the build stops with a message naming the overlay, so a re-base cannot silently drop tessera's behavior. Overlay text that calls tessera tools must say it applies only when the tessera MCP is configured, so the skills still work without it.

## Re-basing on a new upstream release

```bash
git clone --branch <new tag> https://github.com/obra/superpowers /tmp/superpowers
python scripts/build_skills.py build --upstream /tmp/superpowers --update-pin
```

Then read the diff, adjust any overlay whose anchor moved, run `python -m pytest`, and run `claude plugin validate .`. For a stronger check run `SUPERPOWERS_CHECKOUT=/tmp/superpowers python -m pytest tests/test_skills_build.py`.

Editing only an overlay needs no `--update-pin`: run `build` with the same checkout.

## Not bundled

`diagnosing-superpowers` is not bundled. It reads session transcripts from disk and has a workflow for filing issues with the upstream project; that is a tool for upstream maintainers, not tessera functionality. The list of upstream skills that are not bundled is recorded in `UPSTREAM.json`.
