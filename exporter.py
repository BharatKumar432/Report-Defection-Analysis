"""Text, Jira-style, JSON, and CSV export helpers."""

from __future__ import annotations

import csv
import io
import json
from typing import Any


def format_report(report: dict[str, Any]) -> str:
    environment = report.get("environment", {})
    sections = [
        ("Summary", report.get("summary")), ("Description", report.get("description")),
        ("Category / Component / Type", f"{report.get('category')} / {report.get('component')} / {report.get('defect_type')}"),
        ("AI Suggested Severity", f"{report.get('severity')} — {report.get('severity_reason')}"),
        ("AI Suggested Priority", f"{report.get('priority')} — {report.get('priority_reason')}"),
        ("Reproducibility", report.get("reproducibility")),
        ("Preconditions", _numbered(report.get("preconditions", []))),
        ("Steps to Reproduce", _numbered(report.get("steps_to_reproduce", []))),
        ("Expected Result", report.get("expected_result")), ("Actual Result", report.get("actual_result")),
        ("Environment", "\n".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in environment.items())),
        ("Evidence", _numbered(report.get("evidence", []))),
        ("Technical Context", report.get("technical_context")),
        ("Investigation Suggestions (not confirmed root cause)", _numbered(report.get("investigation_suggestions", []))),
        ("Missing Information", _numbered(report.get("missing_information", []))),
    ]
    return f"Summary: {report.get('title', 'Not provided')}\n\n" + "\n\n".join(
        f"{heading}:\n{value or 'Not provided'}" for heading, value in sections
    )


def format_jira(report: dict[str, Any]) -> str:
    return format_report(report)


def json_export(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)


def csv_export(report: dict[str, Any], raw_text: str, quality: int) -> str:
    stream = io.StringIO(newline="")
    fields = ["title", "category", "component", "defect_type", "severity", "priority", "reproducibility",
              "quality_score", "original_text", "summary", "expected_result", "actual_result", "missing_information"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    row = {key: report.get(key, "") for key in fields}
    row.update({"quality_score": quality, "original_text": raw_text,
                "missing_information": "; ".join(report.get("missing_information", []))})
    writer.writerow(row)
    return stream.getvalue()


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, 1)) or "Not provided"
