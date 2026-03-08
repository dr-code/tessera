"""Retrieval scorer for the info graph.

Scores files against a query using term matching, intent classification,
role weights, symbol presence, and graph degree.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ..core.database import Database


@dataclass
class ScoredFile:
    path: str
    score: float
    summary: str
    keywords: list[str]
    role: str
    language: str
    edge_count: int
    symbols: list[str]


# ── Intent classification ─────────────────────────────────────────────────────

_INTENT_PATTERNS: dict[str, list[str]] = {
    "debug": ["bug", "error", "fix", "crash", "exception", "traceback", "broken", "fail"],
    "explain": ["what", "how", "why", "explain", "understand", "describe"],
    "test": ["test", "spec", "assert", "coverage", "mock", "unit", "integration"],
    "refactor": ["refactor", "rename", "move", "reorganize", "extract", "clean"],
    "feature": ["add", "implement", "create", "new feature", "build"],
    "edit": ["edit", "update", "modify", "change", "alter", "patch"],
}


def classify_intent(query: str) -> str:
    q = query.lower()
    for intent, keywords in _INTENT_PATTERNS.items():
        if any(k in q for k in keywords):
            return intent
    return "general"


# ── Role weights per intent ──────────────────────────────────────────────────

_ROLE_WEIGHTS: dict[str, dict[str, float]] = {
    "debug": {"logic": 4.0, "code": 3.0, "test": 2.0, "shared_ui": 1.0, "ui_surface": 0.5, "docs": -1.0},
    "explain": {"docs": 3.0, "logic": 2.0, "code": 2.0, "shared_ui": 1.0, "ui_surface": 1.0, "test": 0.5},
    "test": {"test": 5.0, "logic": 3.0, "code": 2.0, "shared_ui": 1.0, "ui_surface": 0.5, "docs": 0.5},
    "refactor": {"logic": 4.0, "shared_ui": 3.0, "code": 2.0, "ui_surface": 1.0, "test": 2.0, "docs": 0.0},
    "feature": {"logic": 3.0, "code": 3.0, "shared_ui": 2.0, "ui_surface": 2.0, "test": 1.0, "docs": 1.0},
    "edit": {"code": 3.0, "logic": 3.0, "ui_surface": 2.0, "shared_ui": 2.0, "test": 1.0, "docs": 0.5},
    "general": {"code": 2.0, "logic": 2.0, "shared_ui": 1.0, "ui_surface": 1.0, "test": 1.0, "docs": 0.5},
}


def _intent_role_weight(intent: str, role: str) -> float:
    weights = _ROLE_WEIGHTS.get(intent, _ROLE_WEIGHTS["general"])
    return weights.get(role, 0.0)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _term_overlap(terms: list[str], target: str) -> int:
    target_lower = target.lower()
    return sum(1 for t in terms if t in target_lower)


# ── Main scorer ───────────────────────────────────────────────────────────────

def score_files(
    db: Database,
    query: str,
    top_n: int = 5,
    top_edges: int = 12,
) -> list[ScoredFile]:
    """Score all files in the DB against *query* and return the top *top_n*."""
    intent = classify_intent(query)
    query_terms = _tokenize(query)

    files = db.get_all_files()
    if not files:
        return []

    # Build edge count map
    edge_counts: dict[int, int] = {}
    for f in files:
        edges = db.get_edges_from(f["id"])
        edge_counts[f["id"]] = len(edges)

    scored: list[ScoredFile] = []
    for f in files:
        path = f["path"]
        summary = f["summary"] or ""
        keywords_raw = f["keywords"] or "[]"
        try:
            keywords: list[str] = json.loads(keywords_raw)
        except Exception:
            keywords = []
        role = f["role"] or "code"
        lang = f["language"] or "unknown"

        # Path term matches × 3
        path_score = _term_overlap(query_terms, path) * 3.0
        # Summary term matches × 3
        summary_score = _term_overlap(query_terms, summary) * 3.0
        # Keyword term matches × 2
        kw_text = " ".join(keywords)
        kw_score = _term_overlap(query_terms, kw_text) * 2.0
        # Intent × role weight
        role_score = _intent_role_weight(intent, role)
        # Code file boost / penalties
        code_boost = 4.0 if lang not in ("markdown", "json", "yaml", "toml") else 0.0
        md_penalty = -2.0 if lang == "markdown" else 0.0
        generated_penalty = (
            -10.0
            if any(g in path for g in ("generated", "dist/", "build/", ".min."))
            else 0.0
        )
        # Graph degree boost
        ec = edge_counts.get(f["id"], 0)
        degree_boost = min(4.0, ec / 3.0)

        # Symbol boost
        syms = db.get_symbols_for_file(f["id"])
        sym_names = [s["name"] for s in syms]
        sym_boost = 0.0
        for sym in syms:
            conf = sym["confidence"]
            if any(t in sym["name"].lower() for t in query_terms):
                sym_boost += 3.0 if conf == "high" else 2.0

        total = (
            path_score + summary_score + kw_score + role_score
            + code_boost + md_penalty + generated_penalty
            + degree_boost + sym_boost
        )

        scored.append(
            ScoredFile(
                path=path,
                score=total,
                summary=summary,
                keywords=keywords,
                role=role,
                language=lang,
                edge_count=ec,
                symbols=sym_names[:10],
            )
        )

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_n]
