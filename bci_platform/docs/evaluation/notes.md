# Evaluation notes
- Run full pipeline on bundled 15k: `POST /api/v1/pipeline/run` (or execute_run). Artifacts/manifests under `artifacts/<run_id>/`.
- Validate: module statuses, counts, sample evidence trace (candidate→problem→feedback evidence_span in raw_text→validation finding/top backlog candidates).
- Known baseline gaps: provisional extraction (needs labeled benchmark), heuristic spatial/KDE & TFIDF semantic proxy (replace with model embeddings when available), NMF/lens sensitivity and false-coverage/merge rates require reviewed datasets per guide §19.
