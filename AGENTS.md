# Agent guide

## Project goal

This repository demonstrates a Crossref-to-RAG data pipeline with data quality,
freshness monitoring, evaluation, corruption, and repair artifacts.

## Run and UI

- Create/activate `.venv`, then run `python script/run_phase1.py` for Phase 1.
- Run the dashboard with `streamlit run app.py`.
- The dashboard reads existing artifacts only; it must not call APIs or run heavy
  pipeline steps when the page opens.

## Guardrails

- Keep pipeline logic, artifact schemas, and benchmark results unchanged for UI work.
- Resolve artifact paths through `core.config.load_settings()`.
- Treat missing or malformed artifacts as an explicit empty/error state; never invent
  metrics or records.
- Do not expose `.env`, API keys, or other secrets in the UI.
