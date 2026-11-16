# Open decisions / recorded assumptions
- Feedback schema: voice-analytics 15k synthetic CSV mapped (feedback_id, submitted_at, source_channel, synthetic_customer_ref, feedback_text, rating_1_to_5, platform, language).
- Jira/backlog: synthetic `sample_backlog_upload.csv` treated as Jira-export baseline (backlog_id/title/description/acceptance_criteria/product_area/priority/status fields as available); status not proof of delivery.
- Taxonomy: copied `banking_taxonomy_v1.yaml`.
- Extraction: deterministic rule-based provisional (no bundled fine-tuned BERT/labels); confidences & evidence spans emitted, measured-eval hooks pending labeled set.
- Medoid: centroid-nearest representative (documented). H1 motif path supported via explicit WORKAROUND_OF + ESCAPES_TO evidence edges.
- Distances/MDS/KDE: TFIDF-centroid cosine for cluster MDS baseline; Gower on-demand strategy documented; spatial projection heuristic & min-max residual baseline with sensitivity caveats.
- Traffic residual (H3): **unavailable** (no real denominators). Cross-track scores not calibrated to a single business scale (components preserved).
- LLM: Gemini key configured for optional gray-zone judge/generation; offline/unverified fallback when unavailable.
