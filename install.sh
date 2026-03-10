#!/usr/bin/env bash
# install.sh — manual / fallback install path
#
# The recommended way to install tessera is via the Claude Code plugin system:
#
#   claude plugin marketplace add dr-code/tessera
#   claude plugin install tessera@tessera
#
# That one command installs the MCP server (via uvx, no Python env needed)
# AND auto-installs all skills (build, cleanup, debate, plan-review, codex-review).
#
# Use this script if you prefer a manual pip install or need a local editable install.

set -e

echo "Installing tessera (manual / pip path)..."

# Check Python 3.10+
python3 -c "
import sys
assert sys.version_info >= (3, 10), \
    f'Python 3.10+ required (found {sys.version_info.major}.{sys.version_info.minor})'
" || exit 1

# Core install (no remote calls, no API keys needed)
pip install tessera

# Optional: debate mode (requires ANTHROPIC_API_KEY + codex CLI)
# pip install tessera[debate]

# Optional: dashboard
# pip install tessera[dashboard]

# Optional: everything
# pip install tessera[all]

echo ""
echo "Done. Run 'tessera scan .' in your project to build the graph."
echo "tessera scan writes .mcp.json and updates CLAUDE.md automatically."
echo ""
echo "The generated .mcp.json uses uvx to launch the MCP server:"
echo "  uvx --from tessera tessera mcp"
echo "No system PATH entry needed."

# Optional: manually install Claude Code skills
SKILLS_DIR="${HOME}/.claude/skills"
if [ -d "${SKILLS_DIR}" ]; then
  echo ""
  printf "Install tessera Claude Code skills to %s? [y/N] " "${SKILLS_DIR}"
  read -r INSTALL_SKILLS
  if [ "${INSTALL_SKILLS}" = "y" ] || [ "${INSTALL_SKILLS}" = "Y" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    for skill in debate build cleanup plan-review codex-review; do
      mkdir -p "${SKILLS_DIR}/${skill}"
      cp "${SCRIPT_DIR}/skills/${skill}/SKILL.md" "${SKILLS_DIR}/${skill}/SKILL.md"
      echo "  installed: ${skill}"
    done
    echo "Skills installed. Restart Claude Code to pick them up."
    echo "Note: the plugin marketplace install path does this automatically."
    echo "Requires: codex CLI (npm install -g @openai/codex)"
  fi
fi
