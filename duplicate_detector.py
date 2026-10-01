"""Best-effort text similarity for warning about possible duplicate reports."""

from __future__ import annotations

import re
from typing import Any

STOP_WORDS = {"the", "a", "an", "is", "are", "was", "were", "when", "after", "before", "to", "in", "on", "of", "and", "or", "it", "i", "my", "user", "users"}


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[^\W_]+", text.casefold()) if len(token) > 1 and token not in STOP_WORDS}


def similarity(left: str, right: str) -> float:
    first, second = _tokens(left), _tokens(right)
    if not first or not second:
        return 1.0 if left.strip().casefold() == right.strip().casefold() else 0.0
    return len(first & second) / len(first | second)


def find_possible_duplicate(raw_text: str, records: list[dict[str, Any]], threshold: float = 0.65) -> dict[str, Any] | None:
    best: tuple[float, dict[str, Any]] | None = None
    for record in records:
        previous = record.get("original_text", "")
        if not isinstance(previous, str) or not previous:
            continue
        score = similarity(raw_text, previous)
        if score >= threshold and (best is None or score > best[0]):
            best = (score, record)
    if best is None:
        return None
    return {"record": best[1], "similarity": round(best[0] * 100)}
