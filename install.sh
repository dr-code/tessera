#!/usr/bin/env bash
# install.sh — one-line installer for tessera
#
# Usage (recommended):
#   curl -fsSL https://raw.githubusercontent.com/dr-code/tessera/main/install.sh | bash
#
# Installs via the Claude Code plugin marketplace when the `claude` CLI is
# present (registers MCP server + all skills automatically).  Falls back to pip
# when running in a plain terminal or CI environment.

set -e

# ── Plugin path (preferred) ─────────────────────────────────────────────────
if command -v claude &>/dev/null; then
    echo "Claude Code detected — installing via plugin marketplace..."
    claude plugin marketplace add dr-code/tessera
    claude plugin install tessera@tessera
    echo ""
    echo "Done.  Run 'tessera scan .' in your project to build the graph."
    exit 0
fi

# ── pip fallback (CI / plain terminal) ─────────────────────────────────────
echo "Installing tessera (pip path)..."

python3 -c "
import sys
assert sys.version_info >= (3, 10), \
    f'Python 3.10+ required (found {sys.version_info.major}.{sys.version_info.minor})'
" || exit 1

pip install tessera

echo ""
echo "Done. Run 'tessera scan .' in your project to build the graph."
echo "tessera scan writes .mcp.json and updates CLAUDE.md automatically."
echo ""
echo "The generated .mcp.json uses uvx to launch the MCP server:"
echo "  uvx --from tessera tessera mcp"
echo "No system PATH entry needed."

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
