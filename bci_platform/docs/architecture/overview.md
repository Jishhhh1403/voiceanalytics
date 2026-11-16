# Architecture overview
- **Pipeline:** A→B→C→D→E→F→G→H1/H2/H3→H4→Unified merger (sequential, per-run artifacts, resumability-ready manifests).
- **Storage:** SQLite WAL+FK (`data/local/bci.db`), artifacts under `artifacts/<run_id>/`.
- **API:** FastAPI (`/api/v1`) run orchestration/status, gaps/evidence/lineage/spatial/graph, export. Worker runs modules in background thread.
- **UI:** React views for gap feed, spatial void map, friction graph motifs, evidence drawer, 5-lane lineage with uncertainty labels.
- **Key semantics:** `linked_problem_id` canonical; evidence spans verifiable to raw text; similarity/alignment ≠ resolution; spatial/graph/NMF/triangulation = corroborated signals not proof; H3 traffic residual unavailable without denominators.
