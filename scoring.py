"""Deterministic report quality metrics. Scores are readiness signals, not certification."""

from __future__ import annotations

import re
from typing import Any

DIMENSION_WEIGHTS = {
    "Clarity": 20, "Completeness": 15, "Reproducibility": 20, "Expected vs Actual": 15,
    "Environment": 10, "Evidence": 10, "Technical Context": 10,
}


def score_defect(result: dict[str, Any]) -> dict[str, Any]:
    environment = result.get("environment", {})
    known_environment = sum(1 for value in environment.values() if _known(value)) if isinstance(environment, dict) else 0
    steps = result.get("steps_to_reproduce", [])
    steps = steps if isinstance(steps, list) else []
    expected = result.get("expected_result", "")
    actual = result.get("actual_result", "")
    evidence = result.get("evidence", [])
    missing = result.get("missing_information", [])
    dimensions = {
        "Clarity": _dimension(100 if len(str(result.get("title", ""))) >= 12 and len(str(result.get("description", ""))) >= 40 else 55 if result.get("title") and result.get("description") else 15,
                              "Based on the presence and useful length of the title and description."),
        "Completeness": _dimension(max(0, 100 - min(70, len(missing) * 8)) if isinstance(missing, list) else 20,
                                   "Starts full and subtracts points for each identified information gap."),
        "Reproducibility": _dimension(min(100, 25 + 25 * min(len(steps), 3) + (15 if result.get("reproducibility") not in (None, "Not provided", "Unknown") else 0)),
                                       "Based on actionable steps and a stated failure frequency."),
        "Expected vs Actual": _dimension((50 if _known(expected) else 10) + (50 if _known(actual) else 0),
                                          "Rewards separately documented expected and actual behavior."),
        "Environment": _dimension(round(known_environment / max(1, len(environment)) * 100) if isinstance(environment, dict) and environment else 0,
                                   "Based on environment values explicitly supplied in the defect."),
        "Evidence": _dimension(100 if isinstance(evidence, list) and any(_known(item) for item in evidence) else 0,
                               "Based on supplied logs, screenshots, error text, or other evidence."),
        "Technical Context": _dimension(100 if _known(result.get("technical_context")) else 50 if result.get("investigation_suggestions") else 0,
                                        "Separates supplied technical context from suggested investigation areas."),
    }
    overall = round(sum(item["score"] * DIMENSION_WEIGHTS[name] for name, item in dimensions.items()) / 100)
    return {
        "overall": max(0, min(100, overall)),
        "dimensions": dimensions,
        "weights": DIMENSION_WEIGHTS.copy(),
        "message": "Application Quality Score — a deterministic completeness/readiness estimate, not an industry certification or human quality result.",
    }


def score_original_text(raw_text: str) -> dict[str, Any]:
    """Estimate how much actionable QA detail is present before enhancement."""
    text = re.sub(r"\s+", " ", raw_text).strip()
    lower = text.casefold()
    words = re.findall(r"[^\W_]+", lower)
    known_environment = sum(bool(re.search(pattern, lower)) for pattern in (
        r"\bchrome\b|\bedge\b|\bfirefox\b|\bsafari\b", r"\bwindows\b|\bmacos\b|\blinux\b|\bandroid\b|\bios\b",
        r"\bversion\s*[: ]\s*[\w.-]+", r"\bmobile\b|\bdesktop\b|\btablet\b"))
    has_expected = bool(re.search(r"\b(expected|should|instead of|rather than)\b", lower))
    has_action = bool(re.search(r"\b(click|tap|open|select|enter|submit|upload|save|search|checkout|navigate)\w*\b", lower))
    has_condition = bool(re.search(r"\b(when|after|before|while|if|sometimes|occasionally|every time)\b", lower))
    has_evidence = bool(re.search(r"\b(error|exception|screenshot|log|trace|http\s+\d{3})\b", lower))
    dimensions = {
        "Clarity": _dimension(min(100, 15 + len(words) * 5), "Estimated from the amount of specific defect detail provided."),
        "Completeness": _dimension(min(100, 15 + sum((has_action, has_expected, has_evidence, known_environment > 0, has_condition)) * 17), "Checks for an action, expected behavior, evidence, environment, and conditions."),
        "Reproducibility": _dimension((25 if has_action else 0) + (35 if has_condition else 0) + min(40, len(words) * 2), "Estimates whether the raw note gives an action and reproduction condition."),
        "Expected vs Actual": _dimension(65 if has_expected else 20, "Checks whether expected behavior is stated alongside the observed symptom."),
        "Environment": _dimension(min(100, known_environment * 25), "Based only on environment clues present in the raw note."),
        "Evidence": _dimension(100 if has_evidence else 0, "Checks for a stated error or referenced evidence."),
        "Technical Context": _dimension(70 if re.search(r"\b(api|database|server|browser|network|gateway|version|http)\b", lower) else 10,
                                          "Checks for explicit technical terms, without inferring a root cause."),
    }
    overall = round(sum(item["score"] * DIMENSION_WEIGHTS[name] for name, item in dimensions.items()) / 100)
    return {"overall": overall, "dimensions": dimensions, "weights": DIMENSION_WEIGHTS.copy(),
            "message": "Original Quality Score — estimated from details in the raw note."}


def _dimension(score: int, reason: str) -> dict[str, Any]:
    return {"score": max(0, min(100, int(score))), "reason": reason}


def _known(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.strip().casefold()
    return (normalized not in {"unknown", "none"} and "not provided" not in normalized
            and "no attachment" not in normalized and "not available" not in normalized)
