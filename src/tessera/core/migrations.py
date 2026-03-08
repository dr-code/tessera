"""SQLite migration runner using PRAGMA user_version.

Each migration is a tuple of (version, name, fn).  The runner compares
the stored user_version to the migration list and applies only those
with a higher version number.  Migrations are applied in a single
transaction per step.
"""

from __future__ import annotations

import sqlite3
from typing import Callable


def _create_v1_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        -- ── Info graph ──────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS files (
            id           INTEGER PRIMARY KEY,
            path         TEXT UNIQUE NOT NULL,
            extension    TEXT,
            language     TEXT,
            size_bytes   INTEGER,
            content_hash TEXT,
            summary      TEXT,
            keywords     TEXT,
            role         TEXT DEFAULT 'code',
            last_scanned REAL
        );

        CREATE TABLE IF NOT EXISTS symbols (
            id         INTEGER PRIMARY KEY,
            file_id    INTEGER REFERENCES files(id) ON DELETE CASCADE,
            name       TEXT NOT NULL,
            kind       TEXT NOT NULL,
            line_start INTEGER,
            line_end   INTEGER,
            body_hash  TEXT,
            signature  TEXT,
            exported   INTEGER DEFAULT 0,
            confidence TEXT DEFAULT 'medium'
        );

        CREATE TABLE IF NOT EXISTS edges (
            id           INTEGER PRIMARY KEY,
            from_file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
            to_path      TEXT NOT NULL,
            rel          TEXT NOT NULL,
            import_name  TEXT
        );

        -- ── Action graph ─────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS sessions (
            id           TEXT PRIMARY KEY,
            project_root TEXT NOT NULL,
            started_at   REAL DEFAULT (unixepoch('now')),
            last_active  REAL
        );

        CREATE TABLE IF NOT EXISTS actions (
            id          INTEGER PRIMARY KEY,
            session_id  TEXT REFERENCES sessions(id),
            action_type TEXT NOT NULL,
            file_path   TEXT,
            symbol_name TEXT,
            query       TEXT,
            query_terms TEXT,
            metadata    TEXT,
            created_at  REAL DEFAULT (unixepoch('now'))
        );

        CREATE TABLE IF NOT EXISTS decisions (
            id         INTEGER PRIMARY KEY,
            session_id TEXT REFERENCES sessions(id),
            summary    TEXT NOT NULL,
            files      TEXT,
            scope      TEXT DEFAULT 'file',
            created_at REAL DEFAULT (unixepoch('now'))
        );

        CREATE TABLE IF NOT EXISTS decisions_archive (
            id         INTEGER PRIMARY KEY,
            content    TEXT,
            updated_at REAL
        );

        -- ── Retrieval cache ───────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS retrieval_cache (
            id          INTEGER PRIMARY KEY,
            query       TEXT NOT NULL,
            results     TEXT NOT NULL,
            file_hashes TEXT NOT NULL,
            created_at  REAL DEFAULT (unixepoch('now'))
        );

        -- ── Plan archive ─────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS projects (
            id         INTEGER PRIMARY KEY,
            name       TEXT UNIQUE NOT NULL,
            created_at REAL DEFAULT (unixepoch('now'))
        );

        CREATE TABLE IF NOT EXISTS subtasks (
            id         INTEGER PRIMARY KEY,
            project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            name       TEXT NOT NULL,
            status     TEXT DEFAULT 'active',
            created_at REAL DEFAULT (unixepoch('now')),
            UNIQUE(project_id, name)
        );

        CREATE TABLE IF NOT EXISTS plans (
            id                INTEGER PRIMARY KEY,
            subtask_id        INTEGER REFERENCES subtasks(id) ON DELETE CASCADE,
            debate_transcript TEXT,
            final_plan_xml    TEXT,
            plan_file_path    TEXT,
            status            TEXT DEFAULT 'pending',
            created_at        REAL DEFAULT (unixepoch('now')),
            completed_at      REAL
        );

        CREATE TABLE IF NOT EXISTS plan_checklist (
            id              INTEGER PRIMARY KEY,
            plan_id         INTEGER REFERENCES plans(id) ON DELETE CASCADE,
            task_id_in_plan TEXT,
            description     TEXT NOT NULL,
            keywords        TEXT,
            file_target     TEXT,
            status          TEXT DEFAULT 'pending',
            completed_at    REAL,
            sort_order      INTEGER
        );

        -- ── Token savings ─────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS token_savings (
            id               INTEGER PRIMARY KEY,
            session_id       TEXT REFERENCES sessions(id),
            turn_number      INTEGER,
            files_skipped    INTEGER DEFAULT 0,
            chars_saved      INTEGER DEFAULT 0,
            chars_read_total INTEGER DEFAULT 0,
            created_at       REAL DEFAULT (unixepoch('now'))
        );

        -- ── Indexes ───────────────────────────────────────────────────────────
        CREATE INDEX IF NOT EXISTS idx_actions_session
            ON actions(session_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_actions_file
            ON actions(file_path);
        CREATE INDEX IF NOT EXISTS idx_symbols_file
            ON symbols(file_id);
        CREATE INDEX IF NOT EXISTS idx_edges_from
            ON edges(from_file_id);
        CREATE INDEX IF NOT EXISTS idx_files_path
            ON files(path);
        CREATE INDEX IF NOT EXISTS idx_retrieval_cache_query
            ON retrieval_cache(query);
        CREATE INDEX IF NOT EXISTS idx_subtasks_project
            ON subtasks(project_id);
        CREATE INDEX IF NOT EXISTS idx_plans_subtask
            ON plans(subtask_id);
        CREATE INDEX IF NOT EXISTS idx_checklist_plan
            ON plan_checklist(plan_id);
        """
    )


# Registry: (target_version, migration_name, migration_fn)
MigrationFn = Callable[[sqlite3.Connection], None]

MIGRATIONS: list[tuple[int, str, MigrationFn]] = [
    (1, "initial_schema", _create_v1_tables),
]


def run_migrations(conn: sqlite3.Connection) -> None:
    """Apply any pending migrations to *conn* in version order."""
    current: int = conn.execute("PRAGMA user_version").fetchone()[0]
    for version, _name, fn in MIGRATIONS:
        if version > current:
            fn(conn)
            conn.execute(f"PRAGMA user_version = {version}")
            conn.commit()
