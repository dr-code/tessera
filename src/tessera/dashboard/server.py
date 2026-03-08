"""Tessera dashboard — Flask app at localhost:5050.

Read-only SQLite access (WAL handles concurrent MCP writes).
Start with: tessera dashboard
"""

from __future__ import annotations

import os
from pathlib import Path

from ..core.config import (
    DASHBOARD_HOST,
    DASHBOARD_PORT,
    ENABLE_DASHBOARD,
    PROJECT_ROOT,
)
from ..core.database import Database


def create_app(project_root: str = "") -> "Flask":  # type: ignore[name-defined]
    try:
        from flask import Flask, jsonify, send_from_directory
    except ImportError:
        raise ImportError(
            "flask not installed. Run: pip install tessera[dashboard]"
        )

    root = project_root or PROJECT_ROOT or os.getcwd()
    db = Database(root)

    static_dir = Path(__file__).parent / "static"
    app = Flask(__name__, static_folder=str(static_dir), static_url_path="")

    @app.route("/")
    def index():
        return send_from_directory(str(static_dir), "index.html")

    @app.route("/api/stats")
    def api_stats():
        stats = db.get_stats()
        stats["project_root"] = root
        return jsonify(stats)

    @app.route("/api/sessions")
    def api_sessions():
        rows = db._execute(
            "SELECT s.id, s.project_root, s.started_at, s.last_active, "
            "COALESCE(ts.chars_saved,0) AS chars_saved "
            "FROM sessions s "
            "LEFT JOIN (SELECT session_id, SUM(chars_saved) AS chars_saved "
            "           FROM token_savings GROUP BY session_id) ts ON ts.session_id=s.id "
            "ORDER BY s.started_at DESC LIMIT 20"
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/actions")
    def api_actions():
        from flask import request
        session_id = request.args.get("session_id", "")
        if session_id:
            rows = db.get_session_actions(session_id, limit=100)
        else:
            rows = db._execute(
                "SELECT * FROM actions ORDER BY created_at DESC LIMIT 100"
            ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/decisions")
    def api_decisions():
        from flask import request
        session_id = request.args.get("session_id", "")
        rows = db.get_decisions(session_id=session_id or None, limit=50)
        return jsonify([dict(r) for r in rows])

    @app.route("/api/savings")
    def api_savings():
        rows = db._execute(
            "SELECT s.id, s.started_at, "
            "COALESCE(SUM(ts.chars_saved), 0) AS chars_saved, "
            "COALESCE(SUM(ts.chars_read_total), 0) AS chars_read_total "
            "FROM sessions s "
            "LEFT JOIN token_savings ts ON ts.session_id = s.id "
            "GROUP BY s.id ORDER BY s.started_at ASC"
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/files/top")
    def api_files_top():
        from flask import request
        session_id = request.args.get("session_id", "")
        limit = min(int(request.args.get("limit", 10)), 50)
        if session_id:
            rows = db._execute(
                "SELECT file_path, COUNT(*) AS hit_count FROM actions "
                "WHERE session_id=? AND file_path IS NOT NULL AND file_path != '' "
                "GROUP BY file_path ORDER BY hit_count DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        else:
            rows = db._execute(
                "SELECT file_path, COUNT(*) AS hit_count FROM actions "
                "WHERE file_path IS NOT NULL AND file_path != '' "
                "GROUP BY file_path ORDER BY hit_count DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/plans")
    def api_plans():
        projects = db.list_projects()
        result = []
        for p in projects:
            subs = db.list_subtasks(p["id"])
            for s in subs:
                plan = db._execute(
                    "SELECT * FROM plans WHERE subtask_id=? ORDER BY created_at DESC LIMIT 1",
                    (s["id"],),
                ).fetchone()
                checklist = []
                if plan:
                    checklist = [dict(i) for i in db.get_plan_checklist(plan["id"])]
                result.append(
                    {
                        "project": p["name"],
                        "subtask": s["name"],
                        "plan": dict(plan) if plan else None,
                        "checklist": checklist,
                    }
                )
        return jsonify(result)

    return app


def run_dashboard(project_root: str = "") -> None:
    if not ENABLE_DASHBOARD:
        print("Dashboard is disabled (TESSERA_ENABLE_DASHBOARD=0).")
        return
    app = create_app(project_root)
    print(f"Tessera dashboard: http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=False)
