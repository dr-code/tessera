#!/usr/bin/env bash
set -e

echo "Installing tessera..."

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
echo "Then add the MCP server to your Claude Code session:"
echo "  tessera scan .     # builds graph, writes .mcp.json and CLAUDE.md"

# Optional: install Claude Code skills
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
    echo "Requires: codex CLI (npm install -g @openai/codex)"
  fi
fi
