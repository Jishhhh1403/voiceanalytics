PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS pipeline_runs (
  run_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  current_module TEXT,
  feedback_file TEXT,
  jira_file TEXT,
  config_json TEXT,
  config_hash TEXT,
  schema_version TEXT,
  code_version TEXT,
  feedback_count INTEGER DEFAULT 0,
  cluster_count INTEGER DEFAULT 0,
  uncovered_gap_count INTEGER DEFAULT 0,
  whitespace_candidate_count INTEGER DEFAULT 0,
  warnings_json TEXT,
  error TEXT,
  started_at TEXT,
  completed_at TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pipeline_module_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  module TEXT NOT NULL,
  status TEXT NOT NULL,
  input_count INTEGER,
  output_count INTEGER,
  message TEXT,
  error TEXT,
  artifact_json TEXT,
  started_at TEXT,
  completed_at TEXT,
  UNIQUE(run_id, module),
  FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id)
);

CREATE TABLE IF NOT EXISTS taxonomy_nodes (
  node_id TEXT PRIMARY KEY,
  parent_id TEXT,
  module TEXT,
  feature TEXT,
  stage TEXT,
  node_type TEXT,
  display_name TEXT,
  description TEXT,
  signature_path TEXT,
  synonyms_json TEXT,
  status TEXT,
  taxonomy_version TEXT
);

CREATE TABLE IF NOT EXISTS feedback_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  feedback_id TEXT NOT NULL,
  source_row INTEGER,
  customer_id_hash TEXT,
  timestamp TEXT,
  channel TEXT,
  customer_tier TEXT,
  platform TEXT,
  rating INTEGER,
  language TEXT,
  raw_text TEXT NOT NULL,
  cleaned_text TEXT,
  duplicate_group_id TEXT,
  is_duplicate_representative INTEGER DEFAULT 1,
  pii_redacted INTEGER DEFAULT 0,
  pii_types_json TEXT,
  ingestion_status TEXT DEFAULT 'accepted',
  reject_reason TEXT,
  source_file TEXT,
  UNIQUE(run_id, feedback_id),
  FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id)
);
CREATE INDEX IF NOT EXISTS idx_feedback_run ON feedback_records(run_id);
CREATE INDEX IF NOT EXISTS idx_feedback_dup ON feedback_records(duplicate_group_id);

CREATE TABLE IF NOT EXISTS extracted_insights (
  insight_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  feedback_id TEXT NOT NULL,
  journey_node_id TEXT,
  journey_confidence REAL,
  intent TEXT,
  aspect TEXT,
  symptom TEXT,
  sentiment REAL,
  emotion TEXT,
  effort_score REAL,
  outcome TEXT,
  workarounds_json TEXT,
  evidence_span TEXT,
  evidence_start INTEGER,
  evidence_end INTEGER,
  enriched_sentence TEXT,
  is_open_set INTEGER DEFAULT 0,
  extraction_confidence REAL,
  field_confidence_json TEXT,
  model_version TEXT,
  taxonomy_version TEXT,
  extraction_status TEXT DEFAULT 'ok',
  error TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id),
  FOREIGN KEY(journey_node_id) REFERENCES taxonomy_nodes(node_id)
);
CREATE INDEX IF NOT EXISTS idx_insights_run ON extracted_insights(run_id);
CREATE INDEX IF NOT EXISTS idx_insights_feedback ON extracted_insights(feedback_id);

CREATE TABLE IF NOT EXISTS cluster_memberships (
  run_id TEXT NOT NULL,
  cluster_id TEXT NOT NULL,
  insight_id TEXT NOT NULL,
  feedback_id TEXT,
  is_noise INTEGER DEFAULT 0,
  distance_to_centroid REAL,
  PRIMARY KEY(run_id, cluster_id, insight_id)
);
CREATE INDEX IF NOT EXISTS idx_cluster_run ON cluster_memberships(run_id);

CREATE TABLE IF NOT EXISTS canonical_problems (
  problem_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  cluster_id TEXT,
  cluster_label TEXT,
  journey_node_id TEXT,
  title TEXT,
  problem_statement TEXT,
  deterministic_label TEXT,
  llm_label TEXT,
  representative_insight_id TEXT,
  representative_feedback_id TEXT,
  representative_text TEXT,
  keywords_json TEXT,
  member_count INTEGER DEFAULT 0,
  feedback_count INTEGER DEFAULT 0,
  mean_effort REAL,
  negative_share REAL,
  high_tier_share REAL,
  priority_components_json TEXT,
  priority_score REAL,
  mds_x REAL,
  mds_y REAL,
  mds_stress REAL,
  is_open_set INTEGER DEFAULT 0,
  supporting_feedback_ids_json TEXT,
  top_evidence_json TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id)
);
CREATE INDEX IF NOT EXISTS idx_problems_run ON canonical_problems(run_id);
CREATE INDEX IF NOT EXISTS idx_problems_priority ON canonical_problems(priority_score);

CREATE TABLE IF NOT EXISTS backlog_items (
  backlog_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  upload_batch_id TEXT,
  issue_key TEXT,
  title TEXT,
  description TEXT,
  raw_text TEXT,
  searchable_text TEXT,
  status TEXT,
  status_normalized TEXT,
  issue_type TEXT,
  priority TEXT,
  labels_json TEXT,
  components_json TEXT,
  parent_id TEXT,
  dependencies_json TEXT,
  journey_node_id TEXT,
  profiled_intents_json TEXT,
  profiled_aspects_json TEXT,
  profile_confidence_json TEXT,
  embedding_model_version TEXT,
  content_hash TEXT,
  source_export_id TEXT,
  created_at_source TEXT,
  updated_at_source TEXT,
  metadata_json TEXT,
  PRIMARY KEY(run_id, backlog_id),
  FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id)
);
CREATE INDEX IF NOT EXISTS idx_backlog_run ON backlog_items(run_id);

CREATE TABLE IF NOT EXISTS backlog_problem_matches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  problem_id TEXT NOT NULL,
  backlog_id TEXT NOT NULL,
  similarity_score REAL,
  rank INTEGER,
  judge_covered INTEGER,
  judge_reason TEXT,
  judge_model TEXT,
  judge_status TEXT,
  metadata_json TEXT,
  FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id),
  FOREIGN KEY(problem_id) REFERENCES canonical_problems(problem_id)
);
CREATE INDEX IF NOT EXISTS idx_matches_problem ON backlog_problem_matches(problem_id);

CREATE TABLE IF NOT EXISTS validation_findings (
  finding_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  problem_id TEXT NOT NULL,
  relationship_type TEXT,
  alignment_score REAL,
  best_ticket_id TEXT,
  top_candidates_json TEXT,
  judge_decision_json TEXT,
  confidence REAL,
  reason TEXT,
  status TEXT,
  metadata_json TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id),
  FOREIGN KEY(problem_id) REFERENCES canonical_problems(problem_id)
);
CREATE INDEX IF NOT EXISTS idx_findings_run ON validation_findings(run_id);

CREATE TABLE IF NOT EXISTS lens_detections (
  detection_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  lens TEXT NOT NULL,
  detector_type TEXT,
  journey_node_id TEXT,
  intent TEXT,
  score REAL,
  raw_score REAL,
  title TEXT,
  description TEXT,
  supporting_feedback_ids_json TEXT,
  evidence_json TEXT,
  metadata_json TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id)
);
CREATE INDEX IF NOT EXISTS idx_lens_run ON lens_detections(run_id);

CREATE TABLE IF NOT EXISTS whitespace_candidates (
  whitespace_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  discovery_source TEXT,
  linked_problem_id TEXT,
  title TEXT,
  hypothesis TEXT,
  acceptance_criteria_json TEXT,
  whitespace_score REAL,
  priority_score REAL,
  semantic_max_sim REAL,
  graph_score REAL,
  spatial_score REAL,
  combinatorial_score REAL,
  lenses_triggered_json TEXT,
  supporting_feedback_ids_json TEXT,
  matched_backlog_ids_json TEXT,
  score_components_json TEXT,
  evidence_json TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id)
);
CREATE INDEX IF NOT EXISTS idx_candidates_run ON whitespace_candidates(run_id);
CREATE INDEX IF NOT EXISTS idx_candidates_score ON whitespace_candidates(whitespace_score);

CREATE TABLE IF NOT EXISTS artifact_manifest (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  module TEXT,
  artifact_type TEXT,
  path TEXT,
  checksum TEXT,
  metadata_json TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id)
);
CREATE INDEX IF NOT EXISTS idx_artifacts_run ON artifact_manifest(run_id);

CREATE TABLE IF NOT EXISTS model_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  component TEXT,
  model_name TEXT,
  model_version TEXT,
  params_json TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id)
);
