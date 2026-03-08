"""Symbol extraction from source files.

- Python: stdlib `ast` module
- JS/TS: tree-sitter
- Other: file-level only (no symbols extracted)

Each symbol gets a body_hash (MD5[:8]) for staleness detection.
"""

from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tree_sitter_python as tspython  # type: ignore[import-untyped]
    import tree_sitter_javascript as tsjavascript  # type: ignore[import-untyped]
    import tree_sitter_typescript as tstypescript  # type: ignore[import-untyped]
    from tree_sitter import Language, Parser  # type: ignore[import-untyped]
    _HAS_TREE_SITTER = True
except ImportError:
    _HAS_TREE_SITTER = False


@dataclass
class Symbol:
    name: str
    kind: str          # function | class | variable
    line_start: int    # 1-based
    line_end: int      # 1-based
    body_hash: str     # MD5[:8] of the body lines
    signature: str = ""
    exported: bool = False
    confidence: str = "medium"


def _body_hash(lines: list[str], start: int, end: int) -> str:
    body = "\n".join(lines[start - 1 : end])
    return hashlib.md5(body.encode()).hexdigest()[:8]


# ── Python parser (stdlib ast) ──────────────────────────────────────────────

def _parse_python(content: str) -> list[Symbol]:
    lines = content.splitlines()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    symbols: list[Symbol] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            line_start = node.lineno
            line_end = node.end_lineno or node.lineno
            # Build signature from args
            args = [arg.arg for arg in node.args.args]
            sig = f"def {name}({', '.join(args)})"
            if isinstance(node, ast.AsyncFunctionDef):
                sig = "async " + sig
            bh = _body_hash(lines, line_start, line_end)
            symbols.append(
                Symbol(
                    name=name,
                    kind="function",
                    line_start=line_start,
                    line_end=line_end,
                    body_hash=bh,
                    signature=sig,
                    exported=not name.startswith("_"),
                    confidence="high",
                )
            )
        elif isinstance(node, ast.ClassDef):
            name = node.name
            line_start = node.lineno
            line_end = node.end_lineno or node.lineno
            bh = _body_hash(lines, line_start, line_end)
            symbols.append(
                Symbol(
                    name=name,
                    kind="class",
                    line_start=line_start,
                    line_end=line_end,
                    body_hash=bh,
                    signature=f"class {name}",
                    exported=not name.startswith("_"),
                    confidence="high",
                )
            )

    return symbols


# ── JS/TS parser (tree-sitter) ───────────────────────────────────────────────

def _make_ts_parser(language_module: object) -> "Parser | None":
    if not _HAS_TREE_SITTER:
        return None
    try:
        lang = Language(language_module.language())
        parser = Parser(lang)
        return parser
    except Exception:
        return None


_TS_QUERY_JS = """
(function_declaration
  name: (identifier) @name) @def

(class_declaration
  name: (identifier) @name) @def

(lexical_declaration
  (variable_declarator
    name: (identifier) @name
    value: [(arrow_function) (function_expression)] @fn)) @def

(export_statement
  declaration: [
    (function_declaration name: (identifier) @name)
    (class_declaration name: (identifier) @name)
    (lexical_declaration (variable_declarator name: (identifier) @name))
  ]) @def
"""


def _parse_js_ts(content: str, is_typescript: bool = False) -> list[Symbol]:
    if not _HAS_TREE_SITTER:
        return _parse_js_regex(content)
    try:
        if is_typescript:
            lang_mod = tstypescript.language_typescript()
        else:
            lang_mod = tsjavascript.language()
        lang = Language(lang_mod)
        parser = Parser(lang)
        tree = parser.parse(content.encode())
    except Exception:
        return _parse_js_regex(content)

    lines = content.splitlines()
    symbols: list[Symbol] = []
    seen: set[str] = set()

    def _visit(node: object) -> None:
        node_type = getattr(node, "type", "")
        children = getattr(node, "children", [])
        if node_type in (
            "function_declaration", "class_declaration",
            "lexical_declaration", "export_statement",
        ):
            name = _extract_name_from_node(node)
            if name and name not in seen:
                seen.add(name)
                start_line = getattr(node, "start_point", (0, 0))[0] + 1
                end_line = getattr(node, "end_point", (0, 0))[0] + 1
                kind = "class" if "class" in node_type else "function"
                exported = node_type == "export_statement"
                bh = _body_hash(lines, start_line, end_line)
                symbols.append(
                    Symbol(
                        name=name,
                        kind=kind,
                        line_start=start_line,
                        line_end=end_line,
                        body_hash=bh,
                        signature=name,
                        exported=exported,
                        confidence="medium",
                    )
                )
        for child in children:
            _visit(child)

    _visit(tree.root_node)
    return symbols


def _extract_name_from_node(node: object) -> str | None:
    children = getattr(node, "children", [])
    for child in children:
        if getattr(child, "type", "") == "identifier":
            return getattr(child, "text", b"").decode("utf-8", errors="replace")
    # Recurse one level for export_statement
    for child in children:
        result = _extract_name_from_node(child)
        if result:
            return result
    return None


def _parse_js_regex(content: str) -> list[Symbol]:
    """Fallback regex-based JS/TS symbol extraction when tree-sitter unavailable."""
    lines = content.splitlines()
    symbols: list[Symbol] = []
    pattern = re.compile(
        r"^(?:export\s+(?:default\s+)?)?(?:async\s+)?(?:function|class)\s+(\w+)"
        r"|^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(",
        re.MULTILINE,
    )
    for m in pattern.finditer(content):
        name = m.group(1) or m.group(2)
        if not name:
            continue
        line_start = content[: m.start()].count("\n") + 1
        line_end = min(line_start + 30, len(lines))
        bh = _body_hash(lines, line_start, line_end)
        kind = "class" if "class" in m.group(0) else "function"
        symbols.append(
            Symbol(
                name=name,
                kind=kind,
                line_start=line_start,
                line_end=line_end,
                body_hash=bh,
                signature=name,
                exported="export" in m.group(0),
                confidence="low",
            )
        )
    return symbols


# ── Public API ───────────────────────────────────────────────────────────────

def parse_symbols(content: str, file_extension: str) -> list[Symbol]:
    """Extract symbols from *content* based on *file_extension*."""
    ext = file_extension.lower()
    if ext == ".py":
        return _parse_python(content)
    if ext in (".js", ".jsx"):
        return _parse_js_ts(content, is_typescript=False)
    if ext in (".ts", ".tsx"):
        return _parse_js_ts(content, is_typescript=True)
    return []


def compute_body_hash(lines: list[str], line_start: int, line_end: int) -> str:
    """Public helper — compute body hash for freshness comparison."""
    return _body_hash(lines, line_start, line_end)
