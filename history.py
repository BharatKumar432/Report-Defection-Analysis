"""Small JSON-backed local history store for enhanced defect reports."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

DEFAULT_HISTORY_PATH = Path(__file__).resolve().parent / "data" / "history.json"
MAX_HISTORY = 500


def history_path() -> Path:
    return Path(os.getenv("DEFECT_HISTORY_PATH", str(DEFAULT_HISTORY_PATH)))


def load_history(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or history_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        records = []
        for item in data:
            if not isinstance(item, dict) or not isinstance(item.get("report"), dict):
                continue
            try:
                item["quality_score"] = max(0, min(100, int(item.get("quality_score", 0))))
                item["original_quality_score"] = max(0, min(100, int(item.get("original_quality_score", 0))))
                item["score_improvement"] = int(item.get("score_improvement", item["quality_score"] - item["original_quality_score"]))
            except (TypeError, ValueError):
                continue
            for field, default in (("title", item["report"].get("title", "Untitled defect")),
                                   ("category", item["report"].get("category", "Other")),
                                   ("severity", item["report"].get("severity", "Unknown")),
                                   ("original_text", ""), ("timestamp", "")):
                if not isinstance(item.get(field), str):
                    item[field] = default if isinstance(default, str) else "Not provided"
            records.append(item)
        return records
    except (OSError, json.JSONDecodeError):
        return []


def save_history(records: list[dict[str, Any]], path: Path | None = None) -> None:
    path = path or history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(records[-MAX_HISTORY:], ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def add_history(
    raw_text: str,
    report: dict[str, Any],
    quality: dict[str, Any],
    original_quality: dict[str, Any],
    path: Path | None = None,
) -> dict[str, Any]:
    path = path or history_path()
    record = {
        "id": uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "title": report.get("title", "Untitled defect"),
        "category": report.get("category", "Other"),
        "severity": report.get("severity", "Unknown"),
        "quality_score": quality.get("overall", 0),
        "original_quality_score": original_quality.get("overall", 0),
        "score_improvement": quality.get("overall", 0) - original_quality.get("overall", 0),
        "original_text": raw_text,
        "report": report,
    }
    records = load_history(path)
    records.insert(0, record)
    save_history(records, path)
    return record
