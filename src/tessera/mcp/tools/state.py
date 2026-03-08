"""Per-turn state — reset on every graph_continue call."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...core.config import READ_BUDGET_CHARS


@dataclass
class TurnState:
    read_budget_chars: int = READ_BUDGET_CHARS
    chars_read: int = 0
    grep_calls: int = 0
    retrieve_called: bool = False
    seen_reads: dict[str, str] = field(default_factory=dict)   # path → 300-char fingerprint
    files_read_this_turn: set[str] = field(default_factory=set)
    turn_number: int = 0

    def reset(self) -> None:
        self.read_budget_chars = READ_BUDGET_CHARS
        self.chars_read = 0
        self.grep_calls = 0
        self.retrieve_called = False
        self.seen_reads = {}
        self.files_read_this_turn = set()
        self.turn_number += 1

    def remaining_budget(self) -> int:
        return max(0, self.read_budget_chars - self.chars_read)

    def register_read(self, path: str, content: str) -> None:
        self.chars_read += len(content)
        self.files_read_this_turn.add(path)
        self.seen_reads[path] = content[:300]
