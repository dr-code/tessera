"""File system scanner for the Tessera info graph.

Walks the project directory, respects .gitignore via pathspec, computes
MD5[:8] content hashes for incremental rescans, generates heuristic file
summaries, extracts keywords, and classifies file roles.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Iterator

try:
    import pathspec  # type: ignore[import-untyped]
    _HAS_PATHSPEC = True
except ImportError:
    _HAS_PATHSPEC = False


SKIP_DIRS: frozenset[str] = frozenset(
    {
        "node_modules", "venv", ".venv", "__pycache__", ".git",
        ".tessera", "dist", "build", ".next", ".nuxt", "coverage",
        ".mypy_cache", ".ruff_cache", ".pytest_cache",
    }
)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py", ".js", ".jsx", ".ts", ".tsx",
        ".go", ".swift",
        ".json", ".yaml", ".yml", ".md",
        ".toml", ".sh", ".bash",
    }
)

LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".swift": "swift",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".toml": "toml",
    ".sh": "shell",
    ".bash": "shell",
}


def _content_hash(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()[:8]


def _load_gitignore(project_root: Path) -> "pathspec.PathSpec | None":  # type: ignore[name-defined]
    if not _HAS_PATHSPEC:
        return None
    gitignore = project_root / ".gitignore"
    if not gitignore.exists():
        return None
    patterns = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def _is_gitignored(path: Path, project_root: Path, spec: "pathspec.PathSpec | None") -> bool:
    if spec is None:
        return False
    try:
        rel = path.relative_to(project_root)
    except ValueError:
        return False
    return spec.match_file(str(rel))


def _classify_role(path: Path, content: str) -> str:
    name = path.name.lower()
    parts = [p.lower() for p in path.parts]
    if path.suffix == ".md":
        return "docs"
    if any(p in ("test", "tests", "__tests__", "spec", "specs") for p in parts):
        return "test"
    if name.startswith("test_") or name.endswith(("_test.py", ".test.ts", ".spec.ts",
                                                   ".test.js", ".spec.js")):
        return "test"
    if any(p in ("components", "ui", "views", "pages", "screens") for p in parts):
        if any(kw in content[:500] for kw in ("import React", "from 'react'", "from \"react\"")):
            return "ui_surface"
        return "shared_ui"
    if any(p in ("utils", "helpers", "lib", "shared", "common") for p in parts):
        return "shared_ui"
    if any(p in ("logic", "services", "api", "controllers", "handlers", "routes") for p in parts):
        return "logic"
    return "code"


def _extract_summary(content: str, path: Path) -> str:
    lines = content.splitlines()
    if path.suffix == ".py":
        for line in lines[:20]:
            stripped = line.strip()
            for q in ('"""', "'''"):
                if stripped.startswith(q):
                    # Strip only the opening (and optional closing) triple-quote,
                    # not individual quote characters from the content itself.
                    text = stripped[len(q):]
                    if text.endswith(q):
                        text = text[: -len(q)]
                    text = text.strip()
                    if text:
                        return text[:250]
                    break
        for line in lines[:20]:
            stripped = line.strip()
            if stripped.startswith("#") and len(stripped) > 3:
                return stripped.lstrip("# ")[:250]
    if path.suffix == ".md":
        for line in lines[:10]:
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("# ")[:250]
    if path.suffix in (".js", ".ts", ".jsx", ".tsx"):
        for line in lines[:10]:
            stripped = line.strip()
            if stripped.startswith("//"):
                return stripped.lstrip("/ ")[:250]
            if stripped.startswith("/*") or stripped.startswith("*"):
                return stripped.lstrip("/* ")[:250]
    first_non_blank = next((ln.strip() for ln in lines if ln.strip()), "")
    return first_non_blank[:250]


def _extract_keywords(content: str, path: Path) -> list[str]:
    keywords: list[str] = []
    # Function/class names (Python)
    if path.suffix == ".py":
        for m in re.finditer(r"^(?:def|class|async def)\s+(\w+)", content, re.MULTILINE):
            keywords.append(m.group(1))
    # JS/TS exports and function names
    if path.suffix in (".js", ".ts", ".jsx", ".tsx"):
        for m in re.finditer(
            r"(?:export\s+(?:default\s+)?)?(?:function|class|const|let|var)\s+(\w+)",
            content,
        ):
            keywords.append(m.group(1))
        for m in re.finditer(r"export\s+\{([^}]+)\}", content):
            for name in m.group(1).split(","):
                keywords.append(name.strip().split(" ")[0])
    # Route patterns
    for m in re.finditer(r"""(?:app|router)\.\w+\(\s*['"]([^'"]+)['"]""", content):
        keywords.append(m.group(1))
    # Deduplicate, limit to 20
    seen: set[str] = set()
    result: list[str] = []
    for kw in keywords:
        kw = kw.strip()
        if kw and kw not in seen and len(kw) > 1:
            seen.add(kw)
            result.append(kw)
        if len(result) >= 20:
            break
    return result


class FileInfo:
    __slots__ = (
        "path", "extension", "language", "size_bytes",
        "content_hash", "summary", "keywords", "role", "content",
    )

    def __init__(
        self,
        path: str,
        extension: str,
        language: str,
        size_bytes: int,
        content_hash: str,
        summary: str,
        keywords: list[str],
        role: str,
        content: str,
    ) -> None:
        self.path = path
        self.extension = extension
        self.language = language
        self.size_bytes = size_bytes
        self.content_hash = content_hash
        self.summary = summary
        self.keywords = keywords
        self.role = role
        self.content = content


def scan_file(path: Path, project_root: Path) -> FileInfo | None:
    """Scan a single file and return a FileInfo, or None on read error."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    try:
        content = raw.decode("utf-8", errors="replace")
    except Exception:
        return None

    ext = path.suffix.lower()
    lang = LANGUAGE_MAP.get(ext, "unknown")
    ch = _content_hash(raw)
    summary = _extract_summary(content, path)
    keywords = _extract_keywords(content, path)
    role = _classify_role(path, content)
    rel_path = str(path.relative_to(project_root))

    return FileInfo(
        path=rel_path,
        extension=ext,
        language=lang,
        size_bytes=len(raw),
        content_hash=ch,
        summary=summary,
        keywords=keywords,
        role=role,
        content=content,
    )


def walk_project(project_root: str) -> Iterator[FileInfo]:
    """Yield FileInfo for every supported file under *project_root*."""
    root = Path(project_root).resolve()
    spec = _load_gitignore(root)

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        # Prune skipped directories in-place
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS
            and not _is_gitignored(current / d, root, spec)
        ]
        for filename in filenames:
            fpath = current / filename
            ext = fpath.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            if _is_gitignored(fpath, root, spec):
                continue
            info = scan_file(fpath, root)
            if info is not None:
                yield info
