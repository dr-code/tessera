#!/usr/bin/env bash
# install.sh — one-line installer for tessera
#
# Usage (recommended):
#   curl -fsSL https://raw.githubusercontent.com/dr-code/tessera/main/install.sh | bash
#
# 1. Installs the `tessera` command from GitHub. (The name "tessera" on PyPI is
#    an unrelated project, so installing it by name gets the wrong software.)
# 2. When the `claude` CLI is present, installs the Claude Code plugin, which
#    adds the skills, slash commands and Plannotator hooks and registers an MCP
#    server that runs the `tessera` command from step 1.

set -e

REPO_URL="git+https://github.com/dr-code/tessera"

# ── 1. The tessera command ─────────────────────────────────────────────────
python3 -c "
import sys
assert sys.version_info >= (3, 10), \
    f'Python 3.10+ required (found {sys.version_info.major}.{sys.version_info.minor})'
" || exit 1

if command -v pipx &>/dev/null; then
    echo "Installing the tessera command with pipx..."
    pipx install --force "${REPO_URL}"
elif command -v uv &>/dev/null; then
    echo "Installing the tessera command with uv..."
    uv tool install --force "${REPO_URL}"
else
    echo "Installing the tessera command with pip (user install)..."
    python3 -m pip install --user --upgrade "${REPO_URL}"
    echo "Make sure your user scripts folder is on PATH (for example ~/.local/bin)."
fi

if ! command -v tessera &>/dev/null; then
    echo ""
    echo "Installed, but 'tessera' is not on your PATH yet. Open a new terminal or add"
    echo "the folder printed above to PATH, then run 'tessera --version' to check."
fi

# ── 2. Claude Code plugin (when the claude CLI is present) ──────────────────
if command -v claude &>/dev/null; then
    echo ""
    echo "Claude Code detected — installing the plugin..."
    claude plugin marketplace add dr-code/tessera
    claude plugin install tessera@tessera
    echo ""
    echo "Done.  Run 'tessera scan .' in your project to build the graph."
    exit 0
fi

echo ""
echo "Done. Run 'tessera scan .' in your project to build the graph."
echo "tessera scan writes .mcp.json (the MCP server runs 'tessera mcp') and updates CLAUDE.md."

# ── Optional: install Claude Code skills ────────────────────────────────────
SKILLS_DIR="${HOME}/.claude/skills"
if [ -d "${SKILLS_DIR}" ]; then
    echo ""
    printf "Install tessera Claude Code skills to %s? [y/N] " "${SKILLS_DIR}"
    read -r INSTALL_SKILLS
    if [ "${INSTALL_SKILLS}" = "y" ] || [ "${INSTALL_SKILLS}" = "Y" ]; then
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        for skill in debate build cleanup plan-review codex-review; do
            mkdir -p "${SKILLS_DIR}/${skill}"
            cp "${SCRIPT_DIR}/skills/${skill}/SKILL.md" "${SKILLS_DIR}/${skill}/SKILL.md"
            echo "  installed: ${skill}"
        done
        echo "Skills installed. Restart Claude Code to pick them up."
    fi
fi

# ── Optional: connect ChatGPT subscription (no API key needed) ─────────────
echo ""
if command -v codex &>/dev/null; then
    printf "Connect your ChatGPT subscription now (codex auth login)? [y/N] "
    read -r SETUP_CODEX
    if [ "${SETUP_CODEX}" = "y" ] || [ "${SETUP_CODEX}" = "Y" ]; then
        codex auth login
    fi
else
    echo "To enable debate mode (Claude vs GPT), install the codex CLI and sign in"
    echo "with your ChatGPT Plus/Pro subscription — no API key required:"
    echo ""
    echo "  npm install -g @openai/codex"
    echo "  codex auth login"
fi
