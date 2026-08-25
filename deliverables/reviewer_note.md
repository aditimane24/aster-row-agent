ASTER ROW AGENT — Reviewer Note

Summary:
- This bundle contains the finalized mock-mode RAG agent for review, deterministic evaluation outputs, unit tests, and run instructions.

Included files:
- README.md — full project README and delivery checklist.
- deliverables/reviewer_note.md — this file.
- evaluation/results.json — deterministic evaluation summary.
- evaluation/mock_live_results.json — saved mock-run responses (mock LLM outputs).
- scripts/run_evaluation.py — deterministic evaluator (no LLM required).
- scripts/mock_evaluation.py — mock live evaluator that saves agent responses.
- tests/ — unit tests (run with pytest).
- src/ — source code for the agent, retriever, tools, and adapters.
- requirements.txt — Python dependencies.

Quick reproduction steps (Windows):

1) Create and activate venv
```powershell
python -m venv venv
. .\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

2) (Optional) Build embeddings index
```powershell
python -m src.ingest
```

3) Run unit tests
```powershell
venv\Scripts\python.exe -m pytest -q
```

4) Run deterministic evaluation (no LLM/api keys needed)
```powershell
venv\Scripts\python.exe scripts\run_evaluation.py
```

5) Run mock live evaluation (saves mock agent outputs)
```powershell
venv\Scripts\python.exe scripts\mock_evaluation.py
```

6) Release zip created at `dist/aster-row-agent-release.zip` (if produced). Unzip and inspect contents.

Notes:
- The repository is configured to run in mock-only mode without any paid LLM keys. To run against live providers, set the appropriate env vars in a `.env` and follow README warnings.
- Deterministic evaluation snapshot: see `evaluation/results.json`.

Contact:
- If you need a packaged artifact with a demo GIF or a recorded walkthrough, I can add `docs/demo.gif` or a short MP4 upon request.
