# Banking Customer Intelligence Platform (New A–H Implementation)

Local-first, evidence-backed platform implementing the **Modules A–H** approach (direct gap discovery + structural whitespace + triangulation + unified merger) for banking customer feedback and backlog/Jira validation.

> **Synthetic data:** Bundled 15k feedback and sample backlog are synthetic/testing data. Not real customer data.
> **Interpretation:** Scores/similarity/voids/motifs/factors are analytical signals, **not proof** of root cause, missing capability, or delivered resolution. Alignment ≠ coverage/shipping. H3 traffic-adjusted residual is **unavailable** (no real channel/journey traffic denominators).

## What’s implemented (A–H)
- **A Ingestion:** source profiling/mapping, normalization, pseudonymous customer hash, raw+cleaned text, near-dup grouping (no deletion), quality/reject reports, artifacts.
- **B Extraction:** structured signals (intent/aspect/symptom/sentiment/emotion/effort/outcome/workarounds), taxonomy mapping with open-set, verifiable evidence spans, deterministic enriched sentence (rule-based, auditable; BERT task models not bundled).
- **C–E Direct discovery:** weighted TF-IDF (0.4/0.35/0.25) + SVD/HDBSCAN + mega-cluster guard + open-set micro-groups, canonical problems (centroid-nearest reps, c-TF-IDF/keywords, priority decomposition), cluster MDS coords.
- **F–G Jira/backlog validation:** backlog ingestion+profiling, dense-like TFIDF semantic top-k, 3-tier coverage (COVERED/GRAY/UNCOVERED, calibrated thresholds) + optional Gemini gray-zone judge (unverified fallback), explicit alignment-vs-resolution semantics.
- **H1–H4 Whitespace:** evidence graph motifs (workaround escape, temporal chain, bridges), spatial residual voids (heuristic MDS/KDE, labeled), taxonomy lattice + NMF components (traffic residual unavailable), 2-of-3 triangulation with per-lens provenance.
- **Unified merger:** DIRECT_CLUSTER / TRIANGULATED_WHITESPACE / BOTH with evidence/score decomposition.
- **Platform:** FastAPI + background worker run, SQLite (WAL/FK/migrations), per-run artifacts/manifest, React UI (gap feed, spatial map, graph motifs, evidence drawer, 5-lane lineage), export.

## Layout
- `backend/app/{api,db,intelligence,orchestration}` – API, pipeline, modules A–H
- `frontend/` – React+TS UI
- `taxonomy/` – `banking_taxonomy_v1.yaml`
- `data/raw/{feedback,jira}` – bundled synthetic sources
- `artifacts/<run_id>/` – run manifests/reports/matrices/maps
- `docs/` – architecture/data/eval notes

## Setup & run
```bash
cd new_implementation/bci_platform
cp .env.example .env  # or use provided .env (contains configured key)
python3 -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements.txt

# API
PYTHONPATH=backend uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# Frontend
cd frontend && npm install && npm run dev   # http://127.0.0.1:5173 (proxies /api)
```

## Run the pipeline
- UI: **Start Run** (runs full A–H on bundled sources), then browse status/gaps/evidence/spatial/graph/lineage.
- API: `POST /api/v1/pipeline/run` → poll `GET /api/v1/runs/{id}/status` → `GET /api/v1/runs/{id}/gaps` (+ `/evidence`, `/lineage`, `/spatial-map`, `/graph-motifs`, export).

## Config
`.env` / `backend/app/config.py`: source paths, thresholds (clustering, covered/gray, triangulation), provider keys/models (`GEMINI_API_KEY`), seed. Backlog treated as Jira-export baseline; status not proof of delivery.

## Notes & limitations
- Extraction is a deterministic rule-based provisional implementation (auditable, verifiable spans) — not a claimed-validated fine-tuned BERT suite.
- Spatial projection/KDE and clustering are heuristic/baseline; interpret as candidates with sensitivity in mind.
- Gray-zone judge uses Gemini when configured else marks unverified; never auto-creates/modifies Jira issues.
- No real traffic denominators → H3 traffic residual reported unavailable.
