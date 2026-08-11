"""Tests for server.py dispatcher helpers — path/paths alias handling."""

from __future__ import annotations

import json

from tessera.mcp.server import _resolve_read_path


# ── _resolve_read_path ────────────────────────────────────────────────────────

def test_path_plain_string():
    assert _resolve_read_path({"path": "main.py"}) == "main.py"


def test_paths_list_first_element():
    assert _resolve_read_path({"paths": ["main.py", "utils.py"]}) == "main.py"


def test_paths_json_encoded_array():
    """Claude sends paths as a JSON-encoded string when given an array."""
    payload = json.dumps(["client/src/GridView.jsx", "client/src/CalendarView.jsx"])
    assert _resolve_read_path({"paths": payload}) == "client/src/GridView.jsx"


def test_paths_json_encoded_single():
    payload = json.dumps(["main.py"])
    assert _resolve_read_path({"paths": payload}) == "main.py"


def test_paths_plain_string():
    assert _resolve_read_path({"paths": "utils.py"}) == "utils.py"


def test_path_takes_priority_over_paths():
    result = _resolve_read_path({"path": "main.py", "paths": ["other.py"]})
    assert result == "main.py"


def test_empty_args_returns_empty_string():
    assert _resolve_read_path({}) == ""


def test_empty_paths_list_returns_empty_string():
    assert _resolve_read_path({"paths": []}) == ""


def test_empty_json_array_returns_empty_string():
    assert _resolve_read_path({"paths": "[]"}) == ""


def test_malformed_json_falls_through_as_string():
    """Malformed JSON in paths is returned as-is (a plain string)."""
    result = _resolve_read_path({"paths": "[not valid json"})
    assert result == "[not valid json"


# graph_scan's project_root containment is covered end-to-end in
# test_mcp_server_integration.py (real dispatcher, not a standalone helper —
# the fix is to ignore the caller-supplied value entirely, so there's no
# pure function left to unit test here).
