"""Graph builder — orchestrates scan → parse → store.

Incremental mode: files with unchanged content_hash are skipped.
Full mode: rebuilds the entire graph.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..core.database import Database
from .scanner import walk_project
from .symbol_parser import parse_symbols


# ── Import extraction ────────────────────────────────────────────────────────

_PY_IMPORT_RE = re.compile(
    r"""^(?:from\s+([\w.]+)\s+import|import\s+([\w.,\s]+))""",
    re.MULTILINE,
)
_JS_IMPORT_RE = re.compile(
    r"""(?:import|require)\s*(?:\{[^}]*\}|[\w*]+)?\s*(?:from\s*)?['"]([^'"]+)['"]""",
)


def _extract_py_imports(content: str) -> list[tuple[str, str]]:
    """Return list of (module_path, import_name) for Python imports."""
    results = []
    for m in _PY_IMPORT_RE.finditer(content):
        module = m.group(1) or m.group(2)
        if module:
            module = module.strip().split(",")[0].strip()
            # Convert dotted module to relative path hint
            rel = module.replace(".", "/")
            results.append((rel, module))
    return results


def _extract_js_imports(content: str) -> list[tuple[str, str]]:
    """Return list of (import_path, import_name) for JS/TS imports."""
    results = []
    for m in _JS_IMPORT_RE.finditer(content):
        path = m.group(1).strip()
        if not path.startswith("."):
            # External package — record as-is
            results.append((path, path))
        else:
            results.append((path, path))
    return results


def _resolve_import(from_file: str, import_path: str, project_root: str) -> str:
    """Best-effort resolution of a relative import to a project-relative path."""
    if not import_path.startswith("."):
        return import_path
    base = Path(project_root) / from_file
    resolved = (base.parent / import_path).resolve()
    try:
        rel = resolved.relative_to(Path(project_root).resolve())
        rel_str = str(rel)
        # Add extension if missing
        for ext in (".py", ".ts", ".tsx", ".js", ".jsx"):
            candidate = rel_str + ext
            if (Path(project_root) / candidate).exists():
                return candidate
        return rel_str
    except ValueError:
        return import_path


# ── Main builder ─────────────────────────────────────────────────────────────

def build_graph(project_root: str, db: Database, incremental: bool = True) -> dict:
    """Scan *project_root* and populate the database.

    Returns a summary dict: {files_scanned, files_skipped, symbols_found, edges_found}.
    """
    stats = {"files_scanned": 0, "files_skipped": 0, "symbols_found": 0, "edges_found": 0}

    # Gather existing content hashes for incremental mode
    existing: dict[str, str] = {}
    if incremental:
        for row in db.get_all_files():
            existing[row["path"]] = row["content_hash"]

    for info in walk_project(project_root):
        # Incremental check
        if incremental and existing.get(info.path) == info.content_hash:
            stats["files_skipped"] += 1
            continue

        # Upsert file row
        file_id = db.upsert_file(
            path=info.path,
            ext=info.extension,
            lang=info.language,
            size=info.size_bytes,
            content_hash=info.content_hash,
            summary=info.summary,
            keywords=info.keywords,
            role=info.role,
        )
        stats["files_scanned"] += 1

        # Replace symbols for this file
        db.delete_symbols_for_file(file_id)
        symbols = parse_symbols(info.content, info.extension)
        for sym in symbols:
            db.upsert_symbol(
                file_id=file_id,
                name=sym.name,
                kind=sym.kind,
                line_start=sym.line_start,
                line_end=sym.line_end,
                body_hash=sym.body_hash,
                signature=sym.signature,
                exported=sym.exported,
                confidence=sym.confidence,
            )
        stats["symbols_found"] += len(symbols)

        # Replace edges for this file
        db.delete_edges_for_file(file_id)
        if info.extension == ".py":
            imports = _extract_py_imports(info.content)
            rel = "imports"
        elif info.extension in (".js", ".jsx", ".ts", ".tsx"):
            imports = _extract_js_imports(info.content)
            rel = "requires"
        else:
            imports = []
            rel = "references"

        for import_path, import_name in imports:
            resolved = _resolve_import(info.path, import_path, project_root)
            db.add_edge(file_id, resolved, rel, import_name)
            stats["edges_found"] += 1

    return stats
