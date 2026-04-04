"""SQLite database layer for Tessera.

Single-writer WAL mode with a 10-second busy timeout and a 3-attempt
retry wrapper around write operations.  Multiple processes (MCP server,
dashboard, CLI) can all open separate connections safely.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from .config import (
    CACHE_MAX_ENTRIES,
    CACHE_TTL_SECONDS,
    DB_FILENAME,
    MAX_ACTIONS_PER_SESSION,
    MAX_DECISIONS,
    TESSERA_DIR,
)
from .migrations import run_migrations


def _db_path(project_root: str) -> Path:
    root = Path(project_root).resolve()
    tessera_dir = root / TESSERA_DIR
    tessera_dir.mkdir(parents=True, exist_ok=True)
    return tessera_dir / DB_FILENAME


class Database:
    """Wrapper around a single SQLite connection with all Tessera queries."""

    def __init__(self, project_root: str) -> None:
        self.project_root = str(Path(project_root).resolve())
        db_path = _db_path(self.project_root)
        self._conn = sqlite3.connect(str(db_path), timeout=10, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=10000")
        self._conn.execute("PRAGMA foreign_keys=ON")
        run_migrations(self._conn)

    def close(self) -> None:
        self._conn.close()

    # ── Internal helpers ────────────────────────────────────────────────────

    def _retry_write(self, fn: Any, max_retries: int = 3) -> Any:
        for attempt in range(max_retries):
            try:
                return fn()
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc).lower() and attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                else:
                    raise

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._conn.execute(sql, params)

    def _executemany(self, sql: str, params_seq: list) -> sqlite3.Cursor:
        return self._conn.executemany(sql, params_seq)

    # ── Sessions ────────────────────────────────────────────────────────────

    def get_or_create_session(self, project_root: str | None = None) -> str:
        root = project_root or self.project_root
        existing = self._execute(
            "SELECT id FROM sessions WHERE project_root=? ORDER BY started_at DESC LIMIT 1",
            (root,),
        ).fetchone()
        if existing:
            session_id = existing["id"]
            self._retry_write(
                lambda: (
                    self._execute(
                        "UPDATE sessions SET last_active=unixepoch('now') WHERE id=?",
                        (session_id,),
                    ),
                    self._conn.commit(),
                )
            )
            return session_id
        session_id = str(uuid.uuid4())

        def _create():
            self._execute(
                "INSERT INTO sessions(id, project_root, last_active) VALUES(?,?,unixepoch('now'))",
                (session_id, root),
            )
            self._conn.commit()

        self._retry_write(_create)
        return session_id

    def create_new_session(self, project_root: str | None = None) -> str:
        root = project_root or self.project_root
        session_id = str(uuid.uuid4())

        def _create():
            self._execute(
                "INSERT INTO sessions(id, project_root, last_active) VALUES(?,?,unixepoch('now'))",
                (session_id, root),
            )
            self._conn.commit()

        self._retry_write(_create)
        return session_id

    # ── Files ───────────────────────────────────────────────────────────────

    def upsert_file(
        self,
        path: str,
        ext: str,
        lang: str,
        size: int,
        content_hash: str,
        summary: str,
        keywords: list[str],
        role: str,
    ) -> int:
        def _do():
            self._execute(
                """
                INSERT INTO files(path, extension, language, size_bytes, content_hash,
                                  summary, keywords, role, last_scanned)
                VALUES(?,?,?,?,?,?,?,?,unixepoch('now'))
                ON CONFLICT(path) DO UPDATE SET
                    extension=excluded.extension,
                    language=excluded.language,
                    size_bytes=excluded.size_bytes,
                    content_hash=excluded.content_hash,
                    summary=excluded.summary,
                    keywords=excluded.keywords,
                    role=excluded.role,
                    last_scanned=unixepoch('now')
                """,
                (path, ext, lang, size, content_hash, summary, json.dumps(keywords), role),
            )
            self._conn.commit()

        self._retry_write(_do)
        row = self._execute("SELECT id FROM files WHERE path=?", (path,)).fetchone()
        if row is None:
            raise RuntimeError(f"upsert_file: failed to fetch id for path={path!r}")
        return row["id"]

    def get_file_by_path(self, path: str) -> sqlite3.Row | None:
        return self._execute("SELECT * FROM files WHERE path=?", (path,)).fetchone()

    def get_all_files(self) -> list[sqlite3.Row]:
        return self._execute("SELECT * FROM files ORDER BY path").fetchall()

    def delete_file(self, path: str) -> None:
        def _do():
            self._execute("DELETE FROM files WHERE path=?", (path,))
            self._conn.commit()

        self._retry_write(_do)

    # ── Symbols ─────────────────────────────────────────────────────────────

    def upsert_symbol(
        self,
        file_id: int,
        name: str,
        kind: str,
        line_start: int,
        line_end: int,
        body_hash: str,
        signature: str = "",
        exported: bool = False,
        confidence: str = "medium",
    ) -> int:
        def _do():
            self._execute(
                """
                INSERT INTO symbols(file_id, name, kind, line_start, line_end,
                                    body_hash, signature, exported, confidence)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT DO NOTHING
                """,
                (file_id, name, kind, line_start, line_end, body_hash,
                 signature, int(exported), confidence),
            )
            self._conn.commit()

        self._retry_write(_do)
        row = self._execute(
            "SELECT id FROM symbols WHERE file_id=? AND name=? AND kind=?",
            (file_id, name, kind),
        ).fetchone()
        return row["id"] if row else -1

    def get_symbols_for_file(self, file_id: int) -> list[sqlite3.Row]:
        return self._execute(
            "SELECT * FROM symbols WHERE file_id=? ORDER BY line_start",
            (file_id,),
        ).fetchall()

    def update_symbol(
        self,
        symbol_id: int,
        line_start: int,
        line_end: int,
        body_hash: str,
        signature: str,
    ) -> None:
        def _do():
            self._execute(
                """UPDATE symbols
                   SET line_start=?, line_end=?, body_hash=?, signature=?
                   WHERE id=?""",
                (line_start, line_end, body_hash, signature, symbol_id),
            )
            self._conn.commit()

        self._retry_write(_do)

    def delete_symbols_for_file(self, file_id: int) -> None:
        def _do():
            self._execute("DELETE FROM symbols WHERE file_id=?", (file_id,))
            self._conn.commit()

        self._retry_write(_do)

    # ── Edges ───────────────────────────────────────────────────────────────

    def add_edge(
        self, from_file_id: int, to_path: str, rel: str, import_name: str = ""
    ) -> None:
        def _do():
            self._execute(
                """
                INSERT OR IGNORE INTO edges(from_file_id, to_path, rel, import_name)
                VALUES(?,?,?,?)
                """,
                (from_file_id, to_path, rel, import_name),
            )
            self._conn.commit()

        self._retry_write(_do)

    def get_edges_from(self, file_id: int) -> list[sqlite3.Row]:
        return self._execute(
            "SELECT * FROM edges WHERE from_file_id=?", (file_id,)
        ).fetchall()

    def get_edges_to(self, path: str) -> list[sqlite3.Row]:
        return self._execute(
            "SELECT e.*, f.path AS from_path FROM edges e "
            "JOIN files f ON f.id=e.from_file_id WHERE e.to_path=?",
            (path,),
        ).fetchall()

    def delete_edges_for_file(self, file_id: int) -> None:
        def _do():
            self._execute("DELETE FROM edges WHERE from_file_id=?", (file_id,))
            self._conn.commit()

        self._retry_write(_do)

    # ── Actions ─────────────────────────────────────────────────────────────

    def record_action(
        self,
        session_id: str,
        action_type: str,
        file_path: str = "",
        symbol_name: str = "",
        query: str = "",
        query_terms: list[str] | None = None,
        metadata: dict | None = None,
    ) -> None:
        def _do():
            self._execute(
                """
                INSERT INTO actions(session_id, action_type, file_path, symbol_name,
                                    query, query_terms, metadata)
                VALUES(?,?,?,?,?,?,?)
                """,
                (
                    session_id,
                    action_type,
                    file_path,
                    symbol_name,
                    query,
                    json.dumps(query_terms or []),
                    json.dumps(metadata or {}),
                ),
            )
            # Enforce cap in the same transaction to keep it atomic and idempotent
            self._execute(
                """
                DELETE FROM actions WHERE session_id=?
                  AND id NOT IN (
                      SELECT id FROM actions WHERE session_id=?
                      ORDER BY created_at DESC LIMIT ?
                  )
                """,
                (session_id, session_id, MAX_ACTIONS_PER_SESSION),
            )
            self._conn.commit()

        self._retry_write(_do)

    def get_session_actions(self, session_id: str, limit: int = 300) -> list[sqlite3.Row]:
        return self._execute(
            "SELECT * FROM actions WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()

    def search_action_history(
        self, session_id: str, query_terms: list[str], limit: int = 5
    ) -> list[sqlite3.Row]:
        if not query_terms:
            return []
        conditions = " OR ".join(
            ["query LIKE ? OR file_path LIKE ? OR symbol_name LIKE ?"] * len(query_terms)
        )
        params: list = []
        for term in query_terms:
            like = f"%{term}%"
            params += [like, like, like]
        params += [session_id, limit]
        sql = (
            f"SELECT * FROM actions WHERE ({conditions}) AND session_id=? "
            f"ORDER BY created_at DESC LIMIT ?"
        )
        return self._execute(sql, tuple(params)).fetchall()

    def clear_action_graph(self, session_id: str) -> None:
        def _do():
            self._execute("DELETE FROM actions WHERE session_id=?", (session_id,))
            self._execute("DELETE FROM decisions WHERE session_id=?", (session_id,))
            self._conn.commit()

        self._retry_write(_do)

    # ── Decisions ───────────────────────────────────────────────────────────

    def add_decision(
        self,
        session_id: str,
        summary: str,
        files: list[str] | None = None,
        scope: str = "file",
    ) -> None:
        def _do():
            self._execute(
                "INSERT INTO decisions(session_id, summary, files, scope) VALUES(?,?,?,?)",
                (session_id, summary, json.dumps(files or []), scope),
            )
            self._conn.commit()
            # Enforce rolling window
            count = self._execute(
                "SELECT COUNT(*) FROM decisions WHERE session_id=?", (session_id,)
            ).fetchone()[0]
            if count > MAX_DECISIONS:
                overflow = self._execute(
                    """SELECT summary FROM decisions WHERE session_id=?
                       ORDER BY created_at ASC LIMIT ?""",
                    (session_id, count - MAX_DECISIONS),
                ).fetchall()
                archive_text = " | ".join(r["summary"][:300] for r in overflow)
                self._execute(
                    """INSERT INTO decisions_archive(content, updated_at)
                       VALUES(?, unixepoch('now'))""",
                    (archive_text,),
                )
                self._execute(
                    """DELETE FROM decisions WHERE session_id=?
                       AND id IN (
                           SELECT id FROM decisions WHERE session_id=?
                           ORDER BY created_at ASC LIMIT ?
                       )""",
                    (session_id, session_id, count - MAX_DECISIONS),
                )
                self._conn.commit()

        self._retry_write(_do)

    def get_decisions(self, session_id: str | None = None, limit: int = 20) -> list[sqlite3.Row]:
        if session_id:
            return self._execute(
                "SELECT * FROM decisions WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return self._execute(
            "SELECT * FROM decisions ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()

    # ── Retrieval cache ─────────────────────────────────────────────────────

    def get_cached_retrieval(
        self, query: str, ttl: int = CACHE_TTL_SECONDS
    ) -> list | None:
        row = self._execute(
            "SELECT * FROM retrieval_cache WHERE query=? ORDER BY created_at DESC LIMIT 1",
            (query,),
        ).fetchone()
        if not row:
            return None
        age = time.time() - row["created_at"]
        if age > ttl:
            return None
        stored_hashes: dict = json.loads(row["file_hashes"])
        # Validate content hashes still match
        for path, stored_hash in stored_hashes.items():
            file_row = self._execute(
                "SELECT content_hash FROM files WHERE path=?", (path,)
            ).fetchone()
            if not file_row or file_row["content_hash"] != stored_hash:
                return None
        return json.loads(row["results"])

    def cache_retrieval(
        self, query: str, results: list, file_hashes: dict[str, str]
    ) -> None:
        def _do():
            self._execute(
                """INSERT INTO retrieval_cache(query, results, file_hashes)
                   VALUES(?,?,?)""",
                (query, json.dumps(results), json.dumps(file_hashes)),
            )
            self._conn.commit()
            # Enforce cap
            self._execute(
                """DELETE FROM retrieval_cache
                   WHERE id NOT IN (
                       SELECT id FROM retrieval_cache
                       ORDER BY created_at DESC LIMIT ?
                   )""",
                (CACHE_MAX_ENTRIES,),
            )
            self._conn.commit()

        self._retry_write(_do)

    def invalidate_cache_for_files(self, file_paths: list[str]) -> None:
        if not file_paths:
            return

        def _do():
            rows = self._execute("SELECT id, file_hashes FROM retrieval_cache").fetchall()
            ids_to_delete = []
            for row in rows:
                hashes = json.loads(row["file_hashes"])
                if any(p in hashes for p in file_paths):
                    ids_to_delete.append(row["id"])
            if ids_to_delete:
                placeholders = ",".join("?" * len(ids_to_delete))
                self._execute(
                    f"DELETE FROM retrieval_cache WHERE id IN ({placeholders})",
                    tuple(ids_to_delete),
                )
                self._conn.commit()

        self._retry_write(_do)

    # ── Plan Archive ─────────────────────────────────────────────────────────

    def list_projects(self) -> list[sqlite3.Row]:
        return self._execute("SELECT * FROM projects ORDER BY name").fetchall()

    def create_project(self, name: str) -> int:
        def _do():
            self._execute(
                "INSERT OR IGNORE INTO projects(name) VALUES(?)", (name,)
            )
            self._conn.commit()

        self._retry_write(_do)
        row = self._execute("SELECT id FROM projects WHERE name=?", (name,)).fetchone()
        return row["id"]

    def list_subtasks(self, project_id: int) -> list[sqlite3.Row]:
        return self._execute(
            "SELECT * FROM subtasks WHERE project_id=? ORDER BY name",
            (project_id,),
        ).fetchall()

    def create_subtask(self, project_id: int, name: str) -> int:
        def _do():
            self._execute(
                "INSERT OR IGNORE INTO subtasks(project_id, name) VALUES(?,?)",
                (project_id, name),
            )
            self._conn.commit()

        self._retry_write(_do)
        row = self._execute(
            "SELECT id FROM subtasks WHERE project_id=? AND name=?",
            (project_id, name),
        ).fetchone()
        return row["id"]

    def save_plan(
        self,
        subtask_id: int,
        debate_transcript: str,
        final_plan_xml: str,
        plan_file_path: str,
    ) -> int:
        def _do():
            self._execute(
                """INSERT INTO plans(subtask_id, debate_transcript, final_plan_xml,
                                    plan_file_path, status)
                   VALUES(?,?,?,?,'pending')""",
                (subtask_id, debate_transcript, final_plan_xml, plan_file_path),
            )
            self._conn.commit()

        self._retry_write(_do)
        row = self._execute(
            "SELECT id FROM plans WHERE subtask_id=? ORDER BY created_at DESC LIMIT 1",
            (subtask_id,),
        ).fetchone()
        return row["id"]

    def get_plan(self, plan_id: int) -> sqlite3.Row | None:
        return self._execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()

    def get_active_plan(self) -> sqlite3.Row | None:
        return self._execute(
            "SELECT * FROM plans WHERE status='in_progress' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()

    def update_plan_status(self, plan_id: int, status: str) -> None:
        def _do():
            extra = ", completed_at=unixepoch('now')" if status == "completed" else ""
            self._execute(
                f"UPDATE plans SET status=?{extra} WHERE id=?", (status, plan_id)
            )
            self._conn.commit()

        self._retry_write(_do)

    def get_plan_checklist(self, plan_id: int) -> list[sqlite3.Row]:
        return self._execute(
            "SELECT * FROM plan_checklist WHERE plan_id=? ORDER BY sort_order",
            (plan_id,),
        ).fetchall()

    def add_checklist_item(
        self,
        plan_id: int,
        task_id_in_plan: str,
        description: str,
        keywords: list[str],
        file_target: str,
        sort_order: int,
    ) -> int:
        def _do():
            self._execute(
                """INSERT INTO plan_checklist(plan_id, task_id_in_plan, description,
                                              keywords, file_target, sort_order)
                   VALUES(?,?,?,?,?,?)""",
                (plan_id, task_id_in_plan, description,
                 json.dumps(keywords), file_target, sort_order),
            )
            self._conn.commit()

        self._retry_write(_do)
        row = self._execute(
            "SELECT id FROM plan_checklist WHERE plan_id=? AND task_id_in_plan=?",
            (plan_id, task_id_in_plan),
        ).fetchone()
        return row["id"] if row else -1

    def update_checklist_item(
        self, item_id: int, status: str, completed_at: float | None = None
    ) -> None:
        def _do():
            ts = completed_at or (time.time() if status == "done" else None)
            self._execute(
                "UPDATE plan_checklist SET status=?, completed_at=? WHERE id=?",
                (status, ts, item_id),
            )
            self._conn.commit()

        self._retry_write(_do)

    def auto_check_by_file_path(
        self, plan_id: int, file_path: str
    ) -> list[sqlite3.Row]:
        """Match pending checklist items solely by file_target substring.

        Only items with a non-empty file_target are considered — items with no
        file target (verification tasks) must be completed via explicit
        checklist_item_id.  The caller is responsible for deciding what to do
        when multiple items match the same file (ambiguous case).
        """
        rows = self._execute(
            "SELECT * FROM plan_checklist WHERE plan_id=? AND status='pending' ORDER BY sort_order",
            (plan_id,),
        ).fetchall()
        return [
            row for row in rows
            if row["file_target"] and row["file_target"] in file_path
        ]

    # ── Token savings ────────────────────────────────────────────────────────

    def record_token_savings(
        self,
        session_id: str,
        turn_number: int,
        files_skipped: int,
        chars_saved: int,
        chars_read_total: int,
    ) -> None:
        def _do():
            self._execute(
                """INSERT INTO token_savings(session_id, turn_number, files_skipped,
                                             chars_saved, chars_read_total)
                   VALUES(?,?,?,?,?)""",
                (session_id, turn_number, files_skipped, chars_saved, chars_read_total),
            )
            self._conn.commit()

        self._retry_write(_do)

    def get_token_savings(self, session_id: str | None = None) -> list[sqlite3.Row]:
        if session_id:
            return self._execute(
                "SELECT * FROM token_savings WHERE session_id=? ORDER BY created_at",
                (session_id,),
            ).fetchall()
        return self._execute(
            "SELECT * FROM token_savings ORDER BY created_at"
        ).fetchall()

    # ── Stats ────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        file_count = self._execute("SELECT COUNT(*) FROM files").fetchone()[0]
        symbol_count = self._execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
        edge_count = self._execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        session_count = self._execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        return {
            "files": file_count,
            "symbols": symbol_count,
            "edges": edge_count,
            "sessions": session_count,
        }
