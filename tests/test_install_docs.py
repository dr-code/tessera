"""Guards for the install instructions.

The name "tessera" on PyPI is an unrelated project (a Graphite dashboard), so any
instruction that installs it by name installs the wrong software. Tessera must be
installed from GitHub, and the installer must install the command before the
plugin (the plugin's MCP server runs the `tessera` command).
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GITHUB = "git+https://github.com/dr-code/tessera"

# `pip install tessera`, `pipx install tessera[all]`, `uv tool install tessera`, `uvx --from tessera`
WRONG_BY_NAME = re.compile(r"(pip3?|pipx)\s+(install\s+)?(--\S+\s+)*\"?tessera(\[|\s|\"|$)|uv\s+tool\s+install\s+tessera|--from\s+tessera\b")


def _lines(name: str) -> list[str]:
    return (ROOT / name).read_text(encoding="utf-8").splitlines()


def test_no_instruction_installs_tessera_from_pypi_by_name() -> None:
    for name in ("README.md", "install.sh", "CLAUDE.md", "docs/PROJECT_CONTEXT.md"):
        for number, line in enumerate(_lines(name), 1):
            if "@ git+" in line:  # a direct GitHub reference (with extras) is the correct form
                continue
            assert not WRONG_BY_NAME.search(line), f"{name}:{number}: {line.strip()}"


def test_readme_and_installer_install_from_github() -> None:
    assert GITHUB in (ROOT / "README.md").read_text(encoding="utf-8")
    assert GITHUB in (ROOT / "install.sh").read_text(encoding="utf-8")


def test_generated_mcp_config_uses_the_command_not_uvx() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert '"command": "tessera"' in readme
    assert '"command": "uvx"' not in readme


def _stub(directory: Path, name: str, log: Path, exit_code: int = 0) -> None:
    path = directory / name
    path.write_text(f'#!/bin/sh\necho "{name} $*" >> "{log}"\nexit {exit_code}\n', encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _run_installer(tmp_path: Path, tools: list[str]) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    log.write_text("")
    for tool in tools:
        _stub(bin_dir, tool, log)
    # a Python >= 3.10 must be on PATH (the installer checks); stubs come first
    base = f"{bin_dir}:{Path(sys.executable).parent}:/usr/bin:/bin"
    env = {"PATH": base, "HOME": str(tmp_path / "home")}
    (tmp_path / "home").mkdir()
    result = subprocess.run(
        ["bash", str(ROOT / "install.sh")], env=env, capture_output=True, text=True, input="n\nn\n", check=False
    )
    return result, log.read_text().splitlines()


def test_installer_installs_command_then_plugin_when_claude_is_present(tmp_path: Path) -> None:
    result, calls = _run_installer(tmp_path, ["pipx", "claude", "tessera"])
    assert result.returncode == 0, result.stderr
    assert calls[0] == f"pipx install --force {GITHUB}"
    assert calls[1:] == [
        "claude plugin marketplace add dr-code/tessera",
        "claude plugin install tessera@tessera",
    ]


def test_installer_uses_uv_when_pipx_is_missing(tmp_path: Path) -> None:
    result, calls = _run_installer(tmp_path, ["uv", "tessera"])
    assert result.returncode == 0, result.stderr
    assert calls == [f"uv tool install --force {GITHUB}"]


def test_installer_without_claude_does_not_touch_plugins(tmp_path: Path) -> None:
    result, calls = _run_installer(tmp_path, ["pipx", "tessera"])
    assert result.returncode == 0, result.stderr
    assert all("plugin" not in c for c in calls)
    assert os.path.exists(ROOT / "install.sh")
