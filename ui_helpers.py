"""Small plain-text display helpers used by the Streamlit views."""

from typing import Any

import streamlit as st


def show_list(items: list[str], numbered: bool = False) -> None:
    if not items:
        st.text("Not provided")
    else:
        for index, value in enumerate(items, 1):
            st.text(f"{index}. {value}" if numbered else f"• {value}")


def show_environment(environment: dict[str, str]) -> None:
    for field, value in environment.items():
        st.text(f"{field.replace('_', ' ').title()}: {value}")


def history_view(records: list[dict[str, Any]]) -> None:
    st.subheader("📚 Local History")
    if not records:
        st.info("No saved defects yet. Save a report to build your local QA history.")
        return
    labels = [f"{item.get('title', 'Untitled')} · {item.get('timestamp', '')[:10]} · {item.get('quality_score', 0)}/100" for item in records]
    selected = st.selectbox("Select a previous defect", range(len(records)), format_func=lambda index: labels[index])
    record = records[selected]
    before, after, change = st.columns(3)
    before.metric("Original Quality", f"{record.get('original_quality_score', 0)}/100")
    after.metric("Enhanced Quality", f"{record.get('quality_score', 0)}/100")
    change.metric("Score Change", f"{record.get('score_improvement', 0):+d}")
    st.text(record.get("original_text", ""))
    st.json(record.get("report", {}))


def as_qa_question(item: str) -> str:
    questions = {
        "Expected behavior or acceptance criteria": "What should happen when this action works correctly?",
        "Browser and version": "Which browser and browser version were used?",
        "Operating system": "Which operating system and version were involved?",
        "Application version": "Which application version or build was used?",
        "Device type": "Which device type was used?",
        "Failure frequency and reproducibility rate": "How often does the issue occur, and can it be reproduced consistently?",
        "Exact error message, screenshot, or relevant logs": "What exact error message, screenshot, or relevant logs can be provided?",
        "Exact error message": "What exact error message appeared?",
        "Payment method, currency, and transaction reference (if applicable)": "Which payment method and currency were used, and is there a transaction reference?",
        "Whether a charge was completed": "Was a charge actually completed?",
        "Authentication method and account type": "Which authentication method and account type were used?",
        "Whether multi-factor authentication is enabled": "Was multi-factor authentication enabled?",
        "File type and size": "What file type and size were uploaded?",
        "Upload destination and whether one or multiple files were used": "Where was the file uploaded, and was one file or multiple files selected?",
        "Search term and expected matching result": "What search term was used, and which result was expected?",
    }
    return questions.get(item, item if item.endswith("?") else f"Can you provide {item[0].lower() + item[1:]}?")
