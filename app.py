"""Streamlit dashboard for AI Defect Intelligence & Quality Assurance."""

import json
import os
from pathlib import Path

import streamlit as st

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(dotenv_path: Path) -> bool:
        if not dotenv_path.is_file():
            return False
        loaded = False
        for line in dotenv_path.read_text(encoding="utf-8").splitlines():
            clean = line.strip()
            if clean and not clean.startswith("#") and "=" in clean:
                name, value = clean.split("=", 1)
                if name.strip() and value.strip():
                    os.environ.setdefault(name.strip(), value.strip().strip("\"'"))
                    loaded = True
        return loaded

from duplicate_detector import find_possible_duplicate
from enhancer import DEFAULT_MODEL, DEMO_EXAMPLES, MAX_INPUT_LENGTH, enhance_defect, redact_sensitive_text
from exporter import csv_export, format_jira, format_report, json_export
from history import add_history, load_history
from scoring import score_defect, score_original_text
from ui_helpers import as_qa_question, history_view, show_environment, show_list


def _evidence_supplied(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.casefold()
    return bool(normalized.strip()) and not any(term in normalized for term in ("not provided", "no attachment", "not available"))



load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"))
st.set_page_config(page_title="Defect Intelligence AI", page_icon="🐞", layout="wide")
st.title("🐞 DEFECT INTELLIGENCE AI")
st.caption("Transform vague defect descriptions into actionable, developer-ready reports.")

history_records = load_history()
if history_records:
    total = len(history_records)
    average = round(sum(int(item.get("quality_score", 0)) for item in history_records) / total)
    average_improvement = round(sum(int(item.get("score_improvement", 0)) for item in history_records) / total)
    high_count = sum(item.get("severity") in ("High", "Critical") for item in history_records)
    evidence_gaps = sum(
        not isinstance(item.get("report", {}).get("evidence"), list)
        or not any(_evidence_supplied(value) for value in item.get("report", {}).get("evidence", []))
        for item in history_records
    )
    dashboard = st.columns(6)
    dashboard[0].metric("Saved Defects", total)
    dashboard[1].metric("Average Quality", f"{average}/100")
    dashboard[2].metric("Average Score Change", f"{average_improvement:+d}")
    dashboard[3].metric("High / Critical", high_count)
    dashboard[4].metric("Missing Evidence", evidence_gaps)
    duplicate_count = sum(
        find_possible_duplicate(item.get("original_text", ""), history_records[index + 1:]) is not None
        for index, item in enumerate(history_records)
    )
    dashboard[5].metric("Possible Duplicates", duplicate_count)
else:
    st.info("Not enough historical data yet. Save an enhanced defect to begin the QA dashboard.")

with st.sidebar:
    st.header("Processing Mode")
    configured = bool(os.getenv("GROQ_API_KEY"))
    default_mode = 0 if configured else 1
    mode = st.radio("Choose mode", ["AI Mode", "Demo Mode"], index=default_mode, horizontal=True)
    st.caption(f"Active: **{mode}**" + (f" · Model: `{os.getenv('GROQ_MODEL', DEFAULT_MODEL)}`" if mode == "AI Mode" else " · Local rules, no API key required"))
    st.divider()
    st.caption("Application Quality Score is a deterministic readiness estimate, not a human evaluation or certification.")

if "raw_text" not in st.session_state:
    st.session_state.raw_text = ""
if "last_sample" not in st.session_state:
    st.session_state.last_sample = "—"
sample = st.selectbox("Example defects", ["—", *DEMO_EXAMPLES], key="sample_selection")
if sample != st.session_state.last_sample and sample != "—":
    st.session_state.raw_text = DEMO_EXAMPLES[sample]["raw"]
st.session_state.last_sample = sample

raw = st.text_area(
    "Describe your defect",
    value=st.session_state.raw_text,
    height=150,
    placeholder='Example: "payment is failing sometimes when I checkout"',
    help=f"Maximum {MAX_INPUT_LENGTH:,} characters. Input is kept as provided; over-limit text gets a validation message.",
)
st.session_state.raw_text = raw
st.caption(f"{len(raw):,} / {MAX_INPUT_LENGTH:,} characters")
enhance_col, clear_col = st.columns([1, 1])
enhance_clicked = enhance_col.button("✨ Enhance Defect", type="primary")


def clear_form() -> None:
    st.session_state.raw_text = ""
    st.session_state.pop("result", None)
    st.session_state.pop("result_raw", None)
    st.session_state.pop("duplicate", None)
    st.session_state.pop("saved_history_id", None)
    st.session_state.sample_selection = "—"
    st.session_state.last_sample = "—"


clear_col.button("Clear", on_click=clear_form)


if enhance_clicked:
    try:
        safe_raw = redact_sensitive_text(raw)
        if safe_raw != raw:
            st.warning("Credential-like text was redacted before analysis and will not be shown in reports or saved to history.")
        with st.spinner("Analyzing the defect…"):
            result = enhance_defect(safe_raw, demo_mode=(mode == "Demo Mode"))
        st.session_state.result = result
        st.session_state.raw_text = safe_raw
        st.session_state.result_raw = safe_raw.strip()
        st.session_state.original_quality = score_original_text(safe_raw)
        st.session_state.duplicate = find_possible_duplicate(safe_raw, history_records)
        st.session_state.duplicate_ignored = False
        st.session_state.saved_history_id = None
    except (ValueError, RuntimeError) as exc:
        st.error(str(exc))
    except Exception:
        st.error("The report could not be generated. Please try again or switch to Demo Mode.")

result = st.session_state.get("result")
if result:
    raw_input = st.session_state.get("result_raw", raw)
    enhanced_quality = score_defect(result)
    original_quality = st.session_state.get("original_quality", score_original_text(raw_input))
    improvement = enhanced_quality["overall"] - original_quality["overall"]

    duplicate = st.session_state.get("duplicate")
    if duplicate and not st.session_state.get("duplicate_ignored", False):
        prior = duplicate["record"]
        st.warning(f"⚠ Possible Duplicate · {duplicate['similarity']}% text similarity")
        with st.expander(f"Compare with: {prior.get('title', 'Previous defect')}"):
            st.text(prior.get("original_text", ""))
            st.json(prior.get("report", {}))
            st.caption("Text similarity is a review hint, not a confirmed duplicate.")
        if st.button("Continue Anyway", key="continue_duplicate"):
            st.session_state.duplicate_ignored = True
            st.rerun()

    before, after, delta = st.columns(3)
    before.metric("Original Quality", f"{original_quality['overall']}/100")
    after.metric("Enhanced Quality", f"{enhanced_quality['overall']}/100")
    delta.metric("Score Change", f"{improvement:+d} points")
    st.caption("Application Quality Score estimates report completeness. It is not an industry certification.")

    tabs = st.tabs(["📝 Enhanced Report", "📊 Quality Analysis", "⚠️ Missing Information", "👨‍💻 Developer View", "📚 History"])

    with tabs[0]:
        st.subheader(result["title"])
        st.markdown("**Summary**")
        st.text(result["summary"])
        st.markdown("**Description**")
        st.text(result["description"])
        class_cols = st.columns(5)
        class_cols[0].metric("Category", result["category"])
        class_cols[1].metric("Component", result["component"])
        class_cols[2].metric("Defect Type", result["defect_type"])
        class_cols[3].metric("AI Suggested Severity", result["severity"])
        class_cols[4].metric("AI Suggested Priority", result["priority"])
        st.caption(f"Severity: {result['severity_reason']} · Priority: {result['priority_reason']}")
        st.markdown("**Reproducibility**")
        st.text(result["reproducibility"])
        left, right = st.columns(2)
        with left:
            st.markdown("**Preconditions**")
            show_list(result["preconditions"])
            st.markdown("**Steps to Reproduce**")
            show_list(result["steps_to_reproduce"], numbered=True)
            st.markdown("**Expected Result**")
            st.text(result["expected_result"])
        with right:
            st.markdown("**Actual Result**")
            st.text(result["actual_result"])
            st.markdown("**Environment**")
            show_environment(result["environment"])
            st.markdown("**Evidence**")
            show_list(result["evidence"])
        st.markdown("**Information Provenance**")
        p1, p2, p3 = st.columns(3)
        with p1:
            st.markdown("🟢 Provided by User")
            show_list(result["provided_information"])
        with p2:
            st.markdown("🟡 AI Derived")
            show_list(result["ai_derived_information"])
        with p3:
            st.markdown("🔴 Missing")
            show_list(result["missing_information"])
        with st.expander("Enhancement Notes"):
            show_list(result["enhancement_notes"])

        st.markdown("**Before vs After**")
        before_col, after_col = st.columns(2)
        with before_col:
            st.caption("Original defect")
            st.text(raw_input)
            st.progress(original_quality["overall"] / 100)
        with after_col:
            st.caption("Enhanced report")
            st.text(result["title"])
            st.progress(enhanced_quality["overall"] / 100)

        jira_text = format_jira(result)
        st.markdown("**Jira-ready report**")
        st.code(jira_text, language="text")
        export_cols = st.columns(3)
        export_cols[0].download_button("Download JSON", json_export(result), "defect_report.json", "application/json")
        export_cols[1].download_button("Download TXT", format_report(result), "defect_report.txt", "text/plain")
        export_cols[2].download_button("Download CSV", csv_export(result, raw_input, enhanced_quality["overall"]), "defect_report.csv", "text/csv")
        st.caption("Use the code block copy control for clipboard copy. No browser clipboard permission is required by the app.")
        save_label = "Save to History Anyway" if duplicate and not st.session_state.get("duplicate_ignored", False) else "Save to History"
        if st.button("📚 " + save_label, key="save_history"):
            record = add_history(raw_input, result, enhanced_quality, original_quality)
            st.session_state.saved_history_id = record["id"]
            st.rerun()
        if st.session_state.get("saved_history_id"):
            st.success("Saved in local history.")

    with tabs[1]:
        st.subheader("Quality Analysis")
        st.metric("Application Quality Score", f"{enhanced_quality['overall']}/100")
        st.progress(enhanced_quality["overall"] / 100)
        for name, detail in enhanced_quality["dimensions"].items():
            col_name, col_bar, col_score = st.columns([2, 5, 1])
            col_name.write(name)
            col_bar.progress(detail["score"] / 100)
            col_score.write(detail["score"])
            st.caption(detail["reason"])
        st.caption("Weighted dimensions: " + " · ".join(f"{name} {weight}%" for name, weight in enhanced_quality["weights"].items()))

    with tabs[2]:
        st.subheader("Missing Information")
        provided_count = sum(_evidence_supplied(value) for value in result["evidence"])
        evidence_completeness = 100 if provided_count else 0
        st.metric("Evidence Completeness", f"{evidence_completeness}%")
        st.progress(evidence_completeness / 100)
        st.markdown("**Questions QA should answer**")
        show_list([as_qa_question(item) for item in result["missing_information"]])
        st.markdown("**Evidence currently supplied**")
        show_list(result["evidence"])

    with tabs[3]:
        st.subheader("Developer View")
        st.markdown("**Technical Summary**")
        st.text(result["summary"])
        for label, value in (("Component", result["component"]), ("Category", result["category"]),
                             ("Defect Type", result["defect_type"]), ("AI Suggested Severity", result["severity"]),
                             ("AI Suggested Priority", result["priority"]), ("Reproducibility", result["reproducibility"]),
                             ("Technical Context", result["technical_context"])):
            st.markdown(f"**{label}**")
            st.text(value)
        st.markdown("**Environment**")
        show_environment(result["environment"])
        st.markdown("**Expected Result**")
        st.text(result["expected_result"])
        st.markdown("**Actual Result**")
        st.text(result["actual_result"])
        st.markdown("**Evidence**")
        show_list(result["evidence"])
        st.markdown("🔎 **Possible Investigation Areas**")
        st.caption("AI-generated investigation suggestions — not confirmed root cause.")
        show_list(result["investigation_suggestions"])
        st.markdown("**Missing Information**")
        show_list(result["missing_information"])
        st.download_button("Download Developer Report", format_report(result), "developer_report.txt", "text/plain")
        st.markdown("**Jira Format**")
        st.code(format_jira(result), language="text")
        st.download_button("Download Jira Report", format_jira(result), "jira_report.txt", "text/plain")

    with tabs[4]:
        history_view(history_records)
else:
    tabs = st.tabs(["📝 Enhanced Report", "📊 Quality Analysis", "⚠️ Missing Information", "👨‍💻 Developer View", "📚 History"])
    for tab, message in zip(tabs[:4], ("Enter a defect and select Enhance Defect to see the structured report.",
                                      "Scores appear after the defect is analyzed.", "No defect has been analyzed yet.",
                                      "The developer report will appear here after analysis.")):
        with tab:
            st.info(message)
    with tabs[4]:
        history_view(history_records)
