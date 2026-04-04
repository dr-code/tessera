"""Graph and token-monitoring API routes for the Tessera dashboard."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask

    from ..core.database import Database


def register_graph_routes(app: "Flask", db: "Database", project_root: str) -> None:
    # Per-app scan state — closed over by the route handlers so multiple
    # create_app() calls each get their own independent state.
    _scan_state: dict = {"running": False, "result": None}
    _scan_lock = threading.Lock()

    from flask import jsonify

    # ── /api/bench-log ────────────────────────────────────────────────────────

    @app.route("/api/bench-log")
    def api_bench_log():
        rows = db._execute(
            "SELECT session_id, chars_saved, chars_read_total, turn_number, created_at "
            "FROM token_savings ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
        entries = [dict(r) for r in rows]

        total_saved = sum(e["chars_saved"] or 0 for e in entries)
        total_read = sum(e["chars_read_total"] or 0 for e in entries)
        pct = round((total_saved / total_read) * 100) if total_read > 0 else 0

        return jsonify(
            {
                "with_graph": total_read - total_saved,
                "without_graph": total_read,
                "saved": total_saved,
                "savings_pct": pct,
                "sessions_logged": len({e["session_id"] for e in entries}),
                "entries": entries,
            }
        )

    # ── /api/scan ─────────────────────────────────────────────────────────────

    @app.route("/api/scan", methods=["POST"])
    def api_scan_start():
        with _scan_lock:
            if _scan_state["running"]:
                return jsonify({"status": "already_running"}), 409
            _scan_state["running"] = True
            _scan_state["result"] = None

        def _run() -> None:
            # Use a fresh DB connection — the dashboard's connection is owned by
            # the Flask thread and must not be shared with background threads.
            from ..core.database import Database as _Database
            from ..graph.builder import build_graph

            scan_db = _Database(project_root)
            try:
                result = build_graph(project_root, scan_db)
                total = scan_db._execute("SELECT COUNT(*) FROM files").fetchone()[0]
                with _scan_lock:
                    _scan_state["result"] = {
                        "ok": True,
                        "files_scanned": result.get("files_scanned", 0),
                        "files_skipped": result.get("files_skipped", 0),
                        "total": total,
                    }
            except Exception as exc:
                with _scan_lock:
                    _scan_state["result"] = {"ok": False, "error": str(exc)}
            finally:
                scan_db.close()
                with _scan_lock:
                    _scan_state["running"] = False

        threading.Thread(target=_run, daemon=True).start()
        return jsonify({"status": "started"}), 202

    # ── /api/scan/status ──────────────────────────────────────────────────────

    @app.route("/api/scan/status")
    def api_scan_status():
        with _scan_lock:
            return jsonify({"running": _scan_state["running"], "result": _scan_state["result"]})

    # ── /api/graph/nodes ──────────────────────────────────────────────────────

    @app.route("/api/graph/nodes")
    def api_graph_nodes():
        rows = db._execute(
            "SELECT path, extension, size_bytes AS size FROM files ORDER BY path ASC"
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    # ── /api/token-summary ────────────────────────────────────────────────────

    @app.route("/api/token-summary")
    def api_token_summary():
        rows = db._execute(
            "SELECT session_id, chars_saved, chars_read_total, turn_number, created_at "
            "FROM token_savings ORDER BY created_at DESC"
        ).fetchall()
        entries = [dict(r) for r in rows]

        by_session: dict[str, int] = {}
        for e in entries:
            sid = e["session_id"] or "unknown"
            by_session[sid] = by_session.get(sid, 0) + (e["chars_saved"] or 0)

        total_chars = sum(e["chars_saved"] or 0 for e in entries)

        return jsonify(
            {
                "event_count": len(entries),
                "total_chars": total_chars,
                "by_session": by_session,
                "entries": entries,
            }
        )

    # ── /api/graph/tree ───────────────────────────────────────────────────────

    @app.route("/api/graph/tree")
    def api_graph_tree():
        rows = db._execute(
            "SELECT f.path AS from_path, e.rel, e.to_path "
            "FROM edges e JOIN files f ON f.id = e.from_file_id "
            "ORDER BY f.path"
        ).fetchall()

        if not rows:
            return jsonify({"tree": "(no edges — run a scan first)", "edge_count": 0})

        lines: list[str] = []
        current_from = None
        for r in rows:
            if r["from_path"] != current_from:
                current_from = r["from_path"]
                lines.append(current_from)
            rel = r["rel"] or "imports"
            lines.append(f"  └─ {rel}: {r['to_path']}")

        return jsonify({"tree": "\n".join(lines), "edge_count": len(rows)})
