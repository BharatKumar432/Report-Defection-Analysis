# Defect Intelligence AI

A Streamlit application for the TCS Technology Day challenge **“IT Quality Assurance: Automated Defect Description Enhancer.”** It structures arbitrary QA notes into reviewable reports, classifies defects, identifies unknowns, estimates report readiness, and supports local history and export.

## Features

- Groq AI mode with strict JSON Schema output and a local, key-free Demo Mode.
- Defect summary, classification, AI-suggested severity and priority, reproducibility, expected and actual results, evidence, environment, and investigation suggestions.
- Provenance sections distinguish user-provided information, AI-derived classifications, and missing information. Unknown environment fields are `Not provided`.
- Seven deterministic quality dimensions and an original-versus-enhanced score comparison. Scores are readiness estimates, not certification or the TCS 85% human-evaluation target.
- Five views: Enhanced Report, Quality Analysis, Missing Information, Developer View, and History.
- JSON, text/Jira-style, and CSV exports. The Jira text block's copy control is provided by Streamlit.
- Optional local JSON history and token similarity warnings for possible duplicates. No database server or Jira account is required.
- Maximum input size: 10,000 characters.

## Architecture

`Streamlit UI → enhancer.py (Groq JSON Schema or local Demo Mode) → response validation and anti-hallucination normalization → scoring.py → exporter.py / history.py / duplicate_detector.py`

History is stored in `data/history.json` only after the user chooses **Save to History**. It includes the original report text and generated report, so it may contain project information. It stays local and is ignored by Git. History contains no API key.

## Requirements and installation

Python 3.12 is supported. From the project directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Groq configuration

Copy `.env.example` to `.env`, then set:

```dotenv
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
```

The provider uses `https://api.groq.com/openai/v1`. Store the key only in `.env` or the process environment. Do not put a real key in `.env.example`, source files, exports, or screenshots. `.env` is ignored by Git. The default model is configurable; availability and account permissions are controlled by Groq.

## Run

```powershell
streamlit run app.py
```

Choose **AI Mode** or **Demo Mode** in the sidebar. Demo Mode runs locally and processes arbitrary user input; the sample defects are optional examples. With no key configured, Demo Mode is selected by default.

## Test

Tests use standard-library `unittest` and mock Groq calls, so no live key is needed:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q -x '\\.venv[\\\\/]' .
```

To run the same suite with pytest, install pytest in the development environment (`python -m pip install pytest`) and run `python -m pytest -q`. Pytest is a test runner only and is not required by the deployed application.

## Quality evaluation

The score weights clarity (20%), completeness (15%), reproducibility (20%), expected versus actual behavior (15%), environment (10%), evidence (10%), and technical context (10%). Missing information lowers completeness; missing evidence or environment values lower their dimensions. The comparison score for raw text is a separate heuristic, not a guarantee that every enhanced score increases.

To assess the challenge's 85% target, build a dataset of at least 100 synthetic or anonymized defects, have multiple QA reviewers apply a shared acceptance rubric, calculate the percentage accepted, record reviewer agreement, and report response latency. This project does not claim to have achieved that target.

## Project structure

```text
app.py                   Streamlit dashboard and workflow
enhancer.py              Groq integration, schema, local enhancement, classification
scoring.py               Quality dimensions and before/after estimate
history.py               Local JSON history
duplicate_detector.py    Possible duplicate similarity check
exporter.py               JSON, CSV, text, and Jira-style exports
ui_helpers.py            Safe plain-text UI helpers
data/sample_defects.json Optional sample data
tests/                   Offline regression and Streamlit UI tests
```

## Limitations

- Severity, priority, classification, and similarity are suggestions for human triage.
- Possible duplicate detection uses token overlap and does not establish that two reports describe the same defect.
- Demo Mode uses general rules and cannot match the context sensitivity of a live model.
- Local history is a plain JSON file; avoid saving sensitive production data on shared machines.
