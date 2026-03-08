"""graph_read — read a file or file::symbol with turn budget enforcement.

Supports:
  graph_read("src/foo.py")              → full file (capped at max_chars)
  graph_read("src/foo.py::MyClass")     → just the symbol body
  graph_read("src/foo.py", anchor="def foo")  → anchor-based excerpt
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from ...core.database import Database
from ...graph.symbol_parser import compute_body_hash, parse_symbols
from .state import TurnState


def _body_hash_current(lines: list[str], start: int, end: int) -> str:
    body = "\n".join(lines[start - 1 : end])
    return hashlib.md5(body.encode()).hexdigest()[:8]


def run(
    db: Database,
    state: TurnState,
    session_id: str,
    project_root: str,
    file_ref: str,
    max_chars: int = 4000,
    query: str = "",
    anchor: str = "",
) -> dict:
    # Parse file::symbol notation
    symbol_name: str | None = None
    if "::" in file_ref:
        file_path, symbol_name = file_ref.split("::", 1)
    else:
        file_path = file_ref

    # Turn budget check
    if state.remaining_budget() <= 0:
        return {
            "ok": False,
            "error": f"Turn read budget exhausted ({state.read_budget_chars} chars). "
                     "Use graph_retrieve to identify the most relevant files first.",
        }

    # Check if already read this turn (return fingerprint)
    if file_path in state.seen_reads and not symbol_name:
        return {
            "ok": True,
            "path": file_path,
            "cached_turn": True,
            "fingerprint": state.seen_reads[file_path],
        }

    # Resolve absolute path
    abs_path = Path(project_root) / file_path
    if not abs_path.exists():
        # Try to find by path in DB (in case path is already absolute)
        abs_path_direct = Path(file_path)
        if abs_path_direct.exists():
            abs_path = abs_path_direct
        else:
            return {"ok": False, "error": f"File not found: {file_path}"}

    try:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"ok": False, "error": str(exc)}

    lines = content.splitlines()

    if symbol_name:
        # Symbol-specific read with stale revalidation
        file_row = db.get_file_by_path(file_path)
        stale = False
        if file_row:
            syms = db.get_symbols_for_file(file_row["id"])
            sym_row = next((s for s in syms if s["name"] == symbol_name), None)
            if sym_row:
                current_hash = _body_hash_current(lines, sym_row["line_start"], sym_row["line_end"])
                if current_hash != sym_row["body_hash"]:
                    # Stale — reparse
                    new_syms = parse_symbols(content, abs_path.suffix)
                    for ns in new_syms:
                        if ns.name == symbol_name:
                            db.update_symbol(
                                sym_row["id"],
                                ns.line_start,
                                ns.line_end,
                                ns.body_hash,
                                ns.signature,
                            )
                            sym_row = None  # Force re-fetch
                            break
                    stale = True

                # Re-fetch updated sym_row
                if sym_row is None:
                    updated_syms = db.get_symbols_for_file(file_row["id"])
                    sym_row = next((s for s in updated_syms if s["name"] == symbol_name), None)

                if sym_row:
                    body = "\n".join(lines[sym_row["line_start"] - 1 : sym_row["line_end"]])
                    excerpt = body[:max_chars]
                    state.register_read(file_path, excerpt)
                    db.record_action(
                        session_id=session_id,
                        action_type="graph_read_symbol",
                        file_path=file_path,
                        symbol_name=symbol_name,
                        metadata={"stale": stale, "chars": len(excerpt)},
                    )
                    return {
                        "ok": True,
                        "path": file_path,
                        "symbol": symbol_name,
                        "line_start": sym_row["line_start"],
                        "line_end": sym_row["line_end"],
                        "stale": stale,
                        "content": excerpt,
                        "chars": len(excerpt),
                    }

        # Symbol not found in index — fallback to regex search
        for i, line in enumerate(lines, 1):
            if symbol_name in line:
                start = max(0, i - 1)
                end = min(len(lines), i + 40)
                body = "\n".join(lines[start:end])
                excerpt = body[:max_chars]
                state.register_read(file_path, excerpt)
                return {
                    "ok": True,
                    "path": file_path,
                    "symbol": symbol_name,
                    "line_start": start + 1,
                    "line_end": end,
                    "stale": True,
                    "content": excerpt,
                    "chars": len(excerpt),
                    "warning": "Symbol not in index; returned line-search excerpt.",
                }

        return {"ok": False, "error": f"Symbol '{symbol_name}' not found in {file_path}"}

    # Full-file read
    if anchor:
        for i, line in enumerate(lines, 1):
            if anchor in line:
                start = max(0, i - 2)
                end = min(len(lines), i + 50)
                excerpt = "\n".join(lines[start:end])[:max_chars]
                break
        else:
            excerpt = content[:max_chars]
    else:
        excerpt = content[:max_chars]

    # Clamp to remaining budget
    remaining = state.remaining_budget()
    excerpt = excerpt[:remaining]

    state.register_read(file_path, excerpt)
    db.record_action(
        session_id=session_id,
        action_type="graph_read",
        file_path=file_path,
        metadata={"chars": len(excerpt), "anchor": anchor},
    )

    return {
        "ok": True,
        "path": file_path,
        "content": excerpt,
        "chars": len(excerpt),
        "total_chars": len(content),
        "truncated": len(content) > len(excerpt),
    }
