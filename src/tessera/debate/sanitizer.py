"""DLP sanitizer — three-layer detection: regex, entropy, extension denylist.

Replacements are logged to .tessera/dlp_audit.log.
Allowlist via .tessera/config.json under {"dlp_allowlist": ["path/to/file"]}.
"""

from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path


# ── Layer 1: Regex patterns ──────────────────────────────────────────────────

_SECRET_PATTERNS: list[re.Pattern] = [
    # Generic key=value
    re.compile(
        r"""(?i)(api[_-]?key|secret|password|token|auth|passwd)\s*[:=]\s*['"][^'"]{6,}['"]"""
    ),
    # AWS
    re.compile(r"AKIA[0-9A-Z]{16}"),
    # GCP
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    # Stripe
    re.compile(r"sk_live_[0-9a-zA-Z]{24,}"),
    # GitHub
    re.compile(r"ghp_[0-9a-zA-Z]{36}"),
    re.compile(r"gho_[0-9a-zA-Z]{36}"),
    # Generic bearer
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]{20,}"),
    # Connection strings
    re.compile(r"(?i)(mongodb|postgres|mysql|redis)://[^\s'\"]+:[^\s'\"]+@"),
]

# ── Layer 2: Entropy threshold ───────────────────────────────────────────────

_ENTROPY_THRESHOLD = 4.5
_MIN_ENTROPY_LEN = 20


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    length = len(s)
    return -sum((c / length) * math.log2(c / length) for c in freq.values())


_TOKEN_RE = re.compile(r"[A-Za-z0-9+/=_\-]{20,}")


def _find_high_entropy_strings(text: str) -> list[str]:
    found = []
    for m in _TOKEN_RE.finditer(text):
        token = m.group(0)
        if len(token) >= _MIN_ENTROPY_LEN and _shannon_entropy(token) > _ENTROPY_THRESHOLD:
            found.append(token)
    return found


# ── Layer 3: Extension denylist ──────────────────────────────────────────────

_DENIED_EXTENSIONS: frozenset[str] = frozenset(
    {".env", ".pem", ".key", ".pfx", ".p12", ".jks"}
)
_DENIED_NAME_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)secret"),
    re.compile(r"(?i)credential"),
    re.compile(r"(?i)private[_-]?key"),
]


def _is_denied_file(path: str) -> bool:
    p = Path(path)
    if p.suffix.lower() in _DENIED_EXTENSIONS:
        return True
    if p.name.lower() in (".env", ".env.local", ".env.production"):
        return True
    for pat in _DENIED_NAME_PATTERNS:
        if pat.search(p.name):
            return True
    return False


# ── Audit log ────────────────────────────────────────────────────────────────

def _audit_log(project_root: str, message: str) -> None:
    log_path = Path(project_root) / ".tessera" / "dlp_audit.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {message}\n")


# ── Allowlist ────────────────────────────────────────────────────────────────

def _load_allowlist(project_root: str) -> list[str]:
    config_path = Path(project_root) / ".tessera" / "config.json"
    if not config_path.exists():
        return []
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return data.get("dlp_allowlist", [])
    except Exception:
        return []


# ── Public API ───────────────────────────────────────────────────────────────

def sanitize_text(
    text: str,
    source_path: str = "",
    project_root: str = "",
) -> tuple[str, list[str]]:
    """Sanitize *text*, replacing detected secrets with [REDACTED].

    Returns (sanitized_text, list_of_redaction_reasons).
    """
    if source_path and project_root:
        allowlist = _load_allowlist(project_root)
        if source_path in allowlist:
            return text, []

    reasons: list[str] = []
    result = text

    # Layer 3 check: deny entire file contents
    if source_path and _is_denied_file(source_path):
        reason = f"file_denied:{source_path}"
        reasons.append(reason)
        if project_root:
            _audit_log(project_root, reason)
        return "[REDACTED: file type denied]", reasons

    # Layer 1: regex
    for pattern in _SECRET_PATTERNS:
        def _replace(m: re.Match, pat_str: str = pattern.pattern) -> str:
            reasons.append(f"regex:{pat_str[:40]}")
            return "[REDACTED]"
        result = pattern.sub(_replace, result)

    # Layer 2: entropy
    for token in _find_high_entropy_strings(result):
        if token not in result:
            continue
        reasons.append(f"entropy:{token[:10]}...")
        result = result.replace(token, "[REDACTED]", 1)

    if reasons and project_root:
        _audit_log(
            project_root,
            f"Redacted {len(reasons)} item(s) from '{source_path or 'unknown'}': "
            + "; ".join(reasons[:5]),
        )

    return result, reasons


def check_file_allowed(path: str, project_root: str = "") -> tuple[bool, str]:
    """Return (allowed, reason). Denied files must not be sent externally."""
    if _is_denied_file(path):
        return False, f"File type/name denied: {path}"
    if project_root:
        allowlist = _load_allowlist(project_root)
        if path in allowlist:
            return True, ""
    return True, ""
