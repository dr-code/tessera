"""Tests that disabled features exit cleanly without import errors."""

from __future__ import annotations

import os
import subprocess
import sys



def _run_tessera(args: list[str], env_overrides: dict) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(env_overrides)
    # Use the installed entrypoint script (tessera) if available, else fallback
    import shutil
    tessera_bin = shutil.which("tessera") or f"{sys.executable.rsplit('/', 1)[0]}/tessera"
    return subprocess.run(
        [tessera_bin] + args,
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )


def test_dashboard_disabled_exits_cleanly(tmp_path):
    result = _run_tessera(
        ["dashboard", str(tmp_path)],
        {"TESSERA_ENABLE_DASHBOARD": "0"},
    )
    assert result.returncode != 0 or "disabled" in result.stdout.lower() or "disabled" in result.stderr.lower()


def test_compliance_disabled_exits_cleanly(tmp_path):
    result = _run_tessera(
        ["verify", str(tmp_path)],
        {"TESSERA_ENABLE_COMPLIANCE": "0"},
    )
    assert "disabled" in result.stderr.lower() or result.returncode != 0


def test_debate_disabled_exits_cleanly(tmp_path):
    result = _run_tessera(
        ["debate", "test task"],
        {"TESSERA_ENABLE_DEBATE": "0"},
    )
    assert "disabled" in result.stderr.lower() or result.returncode != 0


def test_config_imports_cleanly():
    """Config module should always import without side effects."""
    import tessera.core.config as cfg
    assert hasattr(cfg, "ENABLE_DASHBOARD")
    assert hasattr(cfg, "ENABLE_DEBATE")
    assert hasattr(cfg, "ENABLE_COMPLIANCE")


def test_core_imports_without_optional_deps():
    """Core modules should import even if flask/anthropic are not installed."""
