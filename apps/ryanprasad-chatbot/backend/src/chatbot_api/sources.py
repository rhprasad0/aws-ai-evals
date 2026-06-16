from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


class SourceBudgetError(ValueError):
    """Raised when a source cannot fit safely into the prompt budget."""


@dataclass(frozen=True)
class LoadedSource:
    path: Path
    raw_text: str
    sanitized_text: str


ROLE_MARKERS = re.compile(r"\b(?:System|Developer|Human|Assistant|User|Tool):", re.IGNORECASE)
CONTROL_TOKENS = re.compile(r"\[/?INST\]|</?s>|<\|[^>]+\|>")


def sanitize_source_text(text: str) -> str:
    """Escape prompt-control-looking markers while preserving facts."""
    without_roles = ROLE_MARKERS.sub(lambda match: match.group(0).replace(":", "﹕"), text)
    return CONTROL_TOKENS.sub("", without_roles)


def load_profile_source(path: Path, *, max_chars: int = 51200) -> LoadedSource:
    resolved = path.resolve()
    raw_text = resolved.read_text(encoding="utf-8")
    if len(raw_text) > max_chars:
        raise SourceBudgetError(f"profile source exceeds budget: {len(raw_text)} > {max_chars}")
    sanitized_text = sanitize_source_text(raw_text)
    if len(sanitized_text) > max_chars:
        raise SourceBudgetError(f"sanitized profile source exceeds budget: {len(sanitized_text)} > {max_chars}")
    return LoadedSource(path=resolved, raw_text=raw_text, sanitized_text=sanitized_text)
