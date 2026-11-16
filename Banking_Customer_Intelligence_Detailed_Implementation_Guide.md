# Banking Customer Intelligence & Whitespace Discovery Platform

## Detailed Project Implementation Guide

**Version:** 1.0\
**Date:** 16 November 2026\
**Status:** Engineering implementation specification --- blueprint
phase\
**Execution model:** Local-first, local NLP/embedding/generative models\
**Primary inputs:** 15,000+ banking customer feedback records and Jira
engineering backlog\
**Implementation rule:** Do not begin full implementation until the data
contracts, source files, taxonomy, hardware and model choices have been
inspected and the open decisions in this guide have been recorded.

------------------------------------------------------------------------

# Document purpose and usage

This document is the implementation guide for the Banking Customer
Intelligence & Whitespace Discovery Platform. It translates the supplied
unified architecture and engineering specification into an actionable
engineering plan. It is intended for developers and coding agents who
need to implement the system without relying on undocumented
assumptions.

It covers:

1.  System scope, architecture and execution principles.
2.  Repository and local environment setup.
3.  Source data inspection and canonical data contracts.
4.  SQLite database design and migrations.
5.  Module A: customer feedback ingestion and normalization.
6.  Module B: structured signal extraction, taxonomy mapping and
    workaround tagging.
7.  Module C: weighted TF-IDF and behavioral distance representations.
8.  Module D: HDBSCAN clustering, mega-cluster handling and open-set
    grouping.
9.  Module E: medoid selection, canonical problem synthesis, priority
    calculation and MDS.
10. Module F: Jira ingestion, profiling and dense embeddings.
11. Module G: semantic backlog alignment and gray-zone validation.
12. Module H: graph, spatial and combinatorial whitespace lenses, plus
    triangulation.
13. Cross-track merging, candidate enrichment and prioritization.
14. Pipeline orchestration, artifact persistence and resumability.
15. FastAPI contracts and React application implementation.
16. Testing, evaluation, performance, privacy and acceptance criteria.
17. Implementation sequence, coding-agent task boundaries and release
    gates.

## 1. Project objective and boundaries

### 1.1 Business objective

Build a local-first analytical platform that uses banking customer
feedback and engineering backlog data to identify:

-   Explicit, recurring customer problems.
-   Customer problems not adequately represented by existing Jira work.
-   Behavioral patterns and workaround use that may indicate structural
    product friction.
-   High-effort combinations of journey, intent, symptom, emotion,
    channel and workaround.
-   Potential product capability gaps that are supported by traceable
    customer evidence.

The platform has two discovery tracks:

**Track 1 --- Direct Gap Discovery (Modules C--G):** discovers recurring
and explicit customer problems through structured text representation,
clustering, canonical problem synthesis and semantic backlog validation.

**Track 2 --- Structural Whitespace Discovery (Module H):** investigates
structural and behavioral signals using an evidence graph, spatial
residual analysis, taxonomy lattice and NMF. It promotes a whitespace
candidate only when at least two of the three analytical lenses
independently flag it, subject to the specified triangulation rule.

The outputs are combined by a unified merger and prioritizer.

### 1.2 Expected user-facing outcome

A product or engineering stakeholder should be able to inspect a
candidate and answer:

-   What is the customer problem?
-   Which feedback records support it?
-   What exact text supports the extracted symptom?
-   Which customer journey, intent and aspect are involved?
-   How many records support the candidate?
-   What customer effort and sentiment patterns are present?
-   Which Jira tickets were considered?
-   What is the strongest semantic match?
-   Why was a Jira ticket considered relevant or insufficient?
-   Which discovery track or whitespace lens identified the candidate?
-   Why did the candidate receive its score?
-   What capability hypothesis and acceptance criteria are proposed?

### 1.3 Scope

**Included in the initial implementation**

-   Local CSV/JSON feedback ingestion.
-   Local Jira export ingestion.
-   Data normalization and near-duplicate grouping.
-   Structured NLP extraction and evidence-span preservation.
-   Hierarchical banking taxonomy mapping.
-   Weighted TF-IDF and behavioral feature construction.
-   HDBSCAN and open-set micro-grouping.
-   Canonical problem synthesis and MDS layout.
-   Jira profiling and dense semantic matching.
-   Graph, spatial and combinatorial whitespace analysis.
-   Triangulation and cross-track candidate merging.
-   Local LLM use through a provider abstraction.
-   SQLite persistence and local artifact storage.
-   FastAPI endpoints and React analytical views.
-   Evaluation, reproducibility and evidence lineage.

**Not included unless separately approved**

-   Automatic creation or modification of Jira issues.
-   Production deployment or multi-user enterprise hosting.
-   Automatic regulatory compliance conclusions.
-   Claims that correlations or graph paths prove root cause.
-   Automatic decisions about product investment without human review.
-   Cloud model calls in the local execution mode.

### 1.4 Non-negotiable engineering principles

1.  Preserve original source text and original Jira fields.
2.  Never invent a missing customer tier, journey, intent or Jira field.
3.  Store model confidence and uncertainty where available.
4.  Every extracted insight must link to its source feedback.
5.  Every candidate must retain supporting feedback and detector
    provenance.
6.  Every Jira match must identify the exact Jira issue and
    model/version used.
7.  Similarity is a retrieval signal, not proof that a ticket resolves a
    problem.
8.  A ticket's status is not proof that the customer problem is
    resolved.
9.  A graph relationship is not automatically causal.
10. An MDS void is a candidate analytical signal, not proof of a missing
    feature.
11. A latent NMF component is not automatically a meaningful business
    segment.
12. Preserve individual scores; do not expose only one opaque composite
    score.
13. All important thresholds and weights must be configurable and
    captured in a run configuration.
14. A pipeline run must be inspectable and reproducible from its input
    and configuration manifest.

------------------------------------------------------------------------

# 2. System architecture

## 2.1 End-to-end architecture

``` mermaid
flowchart TD
    F[15,000+ Customer Feedback] --> A[Module A: Ingestion and Normalization]
    J[Jira Backlog Export] --> FJ[Module F: Jira Ingestion and Profiling]
    A --> B[Module B: Structured Signal Extraction]
    B --> C[Module C: Weighted TF-IDF and Behavioral Features]
    C --> D[Module D: Clustering and Open-Set Grouping]
    D --> E[Module E: Canonical Problems and MDS]
    E --> G[Module G: Semantic Backlog Validation]
    FJ --> G
    B --> H1[H1: Evidence Graph]
    E --> H2[H2: Spatial Void Analysis]
    FJ --> H1
    FJ --> H2
    B --> H3[H3: Taxonomy Lattice and NMF]
    FJ --> H3
    G --> H1
    G --> H3
    H1 --> T[H4: Triangulation]
    H2 --> T
    H3 --> T
    G --> M[Unified Merger]
    T --> M
    M --> P[Candidate Prioritization and Enrichment]
    P --> DB[(SQLite and Run Artifacts)]
    DB --> API[FastAPI]
    API --> UI[React Analytical Workspace]
```

### 2.2 Execution dependency clarification

The two discovery tracks are conceptually complementary, but they are
not fully independent in their data dependencies.

-   Both consume the shared Module A--B foundation.
-   Track 1 consumes Modules C--G.
-   The graph and combinatorial lenses consume backlog alignment
    information from Module G.
-   The spatial lens consumes canonical problem coordinates from Module
    E and backlog profiles from Module F.
-   The unified merger consumes Track 1 findings and Track 2
    triangulated candidates.

Therefore, the initial execution order is:

`A → B → C → D → E → F → G → H1/H2/H3 → H4 → Unified Merger`

Some operations can later run in parallel after their inputs are stable.
Do not implement parallel execution before the sequential pipeline is
correct and testable.

## 2.3 Main runtime processes

Use three logical processes:

1.  **Frontend process:** React development server and browser UI.
2.  **API process:** FastAPI for run creation, status, result retrieval
    and exports.
3.  **Worker process:** performs long-running ingestion and analytical
    modules.

The API must not perform the entire 15,000-record pipeline inside the
request-response lifecycle. The API creates a run and schedules the
local worker. The UI polls the run status endpoint.

## 2.4 Technology baseline

  -----------------------------------------------------------------------
  Area                    Technology              Purpose
  ----------------------- ----------------------- -----------------------
  Runtime                 Python 3.13             Backend and analytical
                                                  execution

  API                     FastAPI + Uvicorn       REST API

  Contracts               Pydantic v2             Request and response
                                                  validation

  Database                SQLite3                 Persistent source and
                                                  analytical records

  DB mode                 WAL + foreign keys      Read/write behavior and
                                                  referential integrity

  Data processing         pandas, NumPy           Tabular processing

  Scientific computing    SciPy                   Distances, sparse
                                                  matrices, KDE and
                                                  numerical operations

  ML                      scikit-learn            TF-IDF, SVD, MDS, NMF
                                                  and preprocessing

  Clustering              hdbscan                 Density-based
                                                  clustering

  Graph                   NetworkX                Typed evidence graph
                                                  and motif analysis

  NLP                     transformers + PyTorch  Local BERT-family
                                                  extraction

  Embeddings              sentence-transformers   Dense semantic
                                                  representations

  Local generation        Ollama-compatible       Optional local LLM
                          provider or equivalent  tasks

  Frontend                React + TypeScript      User interface

  Styling                 Tailwind CSS            UI styling

  Spatial visualization   Plotly                  MDS scatter and density
                                                  surfaces

  Lineage visualization   React Flow              Evidence and processing
                                                  lineage
  -----------------------------------------------------------------------

**Version policy:** pin dependencies after a clean environment
installation. Confirm Python 3.13 wheel compatibility for PyTorch,
HDBSCAN and all native dependencies. Do not leave floating dependency
versions in the reproducible implementation.

------------------------------------------------------------------------

# 3. Repository structure

Create the repository with clear separation between API, persistence,
analytical modules, orchestration, evaluation and frontend.

``` text
banking-customer-intelligence/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── pipeline.py
│   │   │   │   ├── runs.py
│   │   │   │   ├── gaps.py
│   │   │   │   ├── spatial.py
│   │   │   │   ├── graph.py
│   │   │   │   └── exports.py
│   │   │   └── schemas/
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   ├── migrations/
│   │   │   └── repositories/
│   │   ├── intelligence/
│   │   │   ├── providers/
│   │   │   │   ├── base.py
│   │   │   │   ├── local_embedder.py
│   │   │   │   ├── local_llm.py
│   │   │   │   └── deterministic.py
│   │   │   ├── ingestion/
│   │   │   │   └── module_a_ingestion.py
│   │   │   ├── extraction/
│   │   │   │   └── module_b_extraction.py
│   │   │   ├── direct_gap/
│   │   │   │   ├── module_c_vectorize.py
│   │   │   │   ├── module_d_clustering.py
│   │   │   │   ├── module_e_canonical.py
│   │   │   │   ├── module_f_backlog.py
│   │   │   │   └── module_g_validator.py
│   │   │   ├── whitespace/
│   │   │   │   ├── graph_analyzer.py
│   │   │   │   ├── spatial_analyzer.py
│   │   │   │   ├── combinatorial_analyzer.py
│   │   │   │   └── triangulator.py
│   │   │   └── unified_merger.py
│   │   ├── orchestration/
│   │   │   ├── pipeline.py
│   │   │   ├── worker.py
│   │   │   ├── run_context.py
│   │   │   └── artifact_manager.py
│   │   └── evaluation/
│   │       ├── extraction_eval.py
│   │       ├── clustering_eval.py
│   │       ├── backlog_eval.py
│   │       ├── whitespace_eval.py
│   │       └── end_to_end_eval.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── fixtures/
│   │   └── evaluation/
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── services/
│   │   ├── hooks/
│   │   └── types/
│   └── package.json
├── taxonomy/
│   └── taxonomy.yaml
├── data/
│   ├── raw/
│   │   ├── feedback/
│   │   └── jira/
│   ├── reference/
│   └── processed/
├── models/
│   └── model_registry/
├── artifacts/
├── docs/
│   ├── architecture/
│   ├── data_contracts/
│   ├── algorithms/
│   └── evaluation/
└── README.md
```

## 3.1 Directory rules

-   `data/raw/` contains read-only source copies. Never overwrite source
    files during processing.
-   `data/processed/` contains normalized or intermediate tabular data
    when persistence outside SQLite is needed.
-   `data/reference/` contains taxonomy, mappings, evaluation labels and
    other controlled reference files.
-   `models/` contains model metadata and local references. Large model
    weights may remain in the model runtime cache; do not commit weights
    to Git.
-   `artifacts/<run_id>/` contains run-specific analytical artifacts.
-   `docs/` contains the authoritative architecture, contracts and
    algorithm definitions.
-   `tests/` contains deterministic unit, integration and evaluation
    tests.

Add `data/`, `models/`, local databases, secrets and generated artifacts
to `.gitignore` unless a specific sanitized fixture is deliberately
committed.

------------------------------------------------------------------------

# 4. Local environment and setup

## 4.1 Hardware discovery

Before selecting the local generative model, record:

-   Operating system and version.
-   CPU model and logical core count.
-   Total RAM.
-   Available disk space.
-   GPU model, VRAM and driver/CUDA compatibility, if present.
-   Whether model inference must run on CPU.
-   Whether the machine can keep the embedding model and generative
    model loaded simultaneously.

Commands for Linux:

``` bash
uname -a
lscpu
free -h
df -h
nvidia-smi
```

`nvidia-smi` may not exist or may fail on machines without a compatible
NVIDIA GPU. Treat that as a hardware discovery result, not an
application failure.

## 4.2 Python environment

``` bash
mkdir banking-customer-intelligence
cd banking-customer-intelligence

mkdir -p backend frontend data/raw/feedback data/raw/jira \
  data/reference data/processed models/model_registry artifacts \
  taxonomy docs tests

cd backend
python3.13 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
```

Install dependencies in compatible groups. Verify PyTorch and HDBSCAN
compatibility before freezing the final lock.

``` bash
pip install fastapi uvicorn pydantic
pip install pandas numpy scipy scikit-learn
pip install networkx hdbscan
pip install transformers torch sentence-transformers
pip install pytest pytest-cov httpx
```

Create a pinned requirements or lock file after a clean installation and
test run:

``` bash
pip freeze > requirements-lock.txt
```

Do not treat `pip freeze` from an unstable environment as a reviewed
dependency lock. Review and test the resolved versions.

## 4.3 Frontend environment

Use a supported Node.js version compatible with the selected Vite/React
toolchain. Record the Node and package-manager versions in the README.

Install:

-   React
-   TypeScript
-   Vite
-   Tailwind CSS
-   Plotly React integration
-   React Flow (`@xyflow/react`)
-   API client
-   UI component dependencies selected by the implementation team

## 4.4 Configuration

Create a typed configuration layer. Do not scatter constants through
algorithm files.

Example configuration categories:

``` yaml
runtime:
  mode: local
  random_seed: 42
  batch_size: 32

ingestion:
  duplicate_similarity_threshold: 0.90
  duplicate_window_hours: 24

extraction:
  taxonomy_confidence_threshold: 0.55
  enable_workaround_tagger: true

clustering:
  svd_components: 100
  min_cluster_size: 15
  min_samples: 5
  mega_cluster_fraction: 0.08

backlog_validation:
  covered_threshold: 0.75
  gray_zone_lower: 0.60

whitespace:
  triangulation_min_lenses: 2
  feedback_jaccard_threshold: 0.30

providers:
  embedding_provider: local
  generation_provider: local
  allow_cloud_calls: false
```

The values shown above are the supplied specification's baseline where
specified. Additional operational values must be tuned and versioned.
The actual configuration file should be validated with Pydantic before a
run begins.

------------------------------------------------------------------------

# 5. Source data inspection and canonical contracts

Do not start analytical modules before inspecting the real customer and
Jira source files.

## 5.1 Feedback source inspection

The source specification expects:

  -----------------------------------------------------------------------
  Field                   Expected meaning        Required handling
  ----------------------- ----------------------- -----------------------
  `feedback_id`           Stable feedback         Required, unique or
                          identifier              deterministically
                                                  assigned with audit

  `customer_id`           Customer identifier     Hash before analytical
                                                  persistence

  `timestamp`             Feedback submission     Parse and normalize
                          time                    timezone

  `channel`               Source channel          Preserve raw and
                                                  normalized values

  `customer_tier`         Customer category       Nullable if not
                                                  supplied

  `raw_text`              Original feedback text  Preserve exactly
  -----------------------------------------------------------------------

Create a source profiling report before ingestion:

-   Row count.
-   Column names and inferred types.
-   Null count per column.
-   Duplicate ID count.
-   Empty/whitespace feedback count.
-   Text length distribution.
-   Language distribution if measured.
-   Timestamp range and parse failures.
-   Channel distribution.
-   Customer tier distribution.
-   Customer identifier missingness.
-   Exact and near-duplicate counts from a sample.

Do not assume the dataset has the same column names as the
specification. Create an explicit source-to-canonical mapping.

## 5.2 Jira source inspection

The original specification describes a generic backlog CSV/JSON input.
This implementation uses Jira as the source, so first inspect the actual
Jira export.

Expected canonical fields:

  Canonical field   Likely Jira field   Handling
  ----------------- ------------------- --------------------------------------------------
  `backlog_id`      Issue key           Stable primary identifier
  `title`           Summary             Required
  `description`     Description         Nullable; normalize rich text
  `status`          Status              Preserve original status and normalized category
  `issue_type`      Issue Type          Preserve
  `priority`        Priority            Preserve
  `created_at`      Created             Parse timezone
  `updated_at`      Updated             Parse timezone
  `resolution`      Resolution          Preserve if present
  `labels`          Labels              Preserve as list
  `components`      Components          Preserve as list
  `parent_id`       Parent / Epic       Preserve if available
  `dependencies`    Issue links         Preserve if available
  `assignee`        Assignee            Optional; consider privacy and UI exposure
  `project_key`     Project             Preserve

The mapping is conditional on the actual export. Missing fields must
remain null or be represented as unavailable. Do not synthesize Jira
status, resolution or relationships.

### Jira ingestion rules

1.  Retain the original issue key.
2.  Preserve original summary and description.
3.  Normalize rich-text content to searchable text while retaining raw
    content or source reference.
4.  Keep status separate from semantic alignment.
5.  Keep issue type separate from coverage.
6.  Deduplicate repeated exports by issue key and source version.
7.  Record Jira export timestamp and file checksum.
8.  Retain issue links and dependencies when supplied.
9.  Record missing descriptions and empty summaries as data-quality
    warnings.
10. Do not assume every backlog item is a customer-facing feature; bugs,
    technical tasks, epics and maintenance tickets may have different
    meanings.

## 5.3 Taxonomy contract

The source specification describes a hierarchy:

`Module > Feature > Stage`

Each taxonomy node must have:

-   Stable `node_id`.
-   `module`.
-   `feature`.
-   `stage`.
-   `signature_path`.
-   Optional parent identifier.
-   Taxonomy version.

Example only:

``` yaml
version: "1.0"
nodes:
  - node_id: "cards_credit_international"
    module: "Cards"
    feature: "Credit Card"
    stage: "International Transactions"
    signature_path: "Cards > Credit Card > International Transactions"
```

The example is illustrative, not a claim about the actual approved
banking taxonomy.

Taxonomy validation must check: - Unique IDs. - Unique or explicitly
disambiguated paths. - Valid parent references. - No cycles. - Required
hierarchy fields. - Version consistency. - Unknown categories handled as
open-set rather than silently forced into an existing node.

## 5.4 Canonical extraction contract

One feedback record may contain more than one distinct issue. The
implementation must decide whether Module B emits one insight per
feedback or multiple insight records per feedback. The database design
should support multiple insights per feedback even if the first baseline
emits one.

Required fields from the source:

  Field                 Type / constraint
  --------------------- -------------------------
  `insight_id`          Stable unique ID
  `feedback_id`         FK to feedback
  `journey_node_id`     Nullable FK to taxonomy
  `intent`              Text/category
  `aspect`              Text/category
  `symptom`             Text
  `sentiment`           Numeric range \[-1, 1\]
  `emotion`             Category
  `effort_score`        Numeric range \[1, 5\]
  `outcome`             Nullable text/category
  `workarounds_json`    JSON array
  `evidence_span`       Exact source substring
  `enriched_sentence`   Deterministic template
  `is_open_set`         Boolean/integer

Recommended additions: - Per-field confidence. - Evidence character
start/end offsets. - Model name and version. - Taxonomy version. -
Extraction timestamp. - Extraction status. - Error/warning code. -
Language identifier if supported.

### Evidence-span contract

The exact evidence span must be verifiable against the original
`raw_text`. If text cleaning changes punctuation or whitespace, offsets
into cleaned text are not interchangeable with offsets into raw text.
Store either raw-text offsets or a deterministic alignment mapping.
Never highlight a quote using offsets that refer to a different text
representation.

------------------------------------------------------------------------

# 6. Database implementation

## 6.1 Database configuration

Use SQLite with:

-   `PRAGMA foreign_keys = ON` on every connection.
-   WAL mode.
-   A configured busy timeout.
-   Explicit transactions.
-   Migration scripts.
-   One controlled writer at a time for analytical writes.

Recommended connection initialization:

``` python
import sqlite3

def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn
```

Use a connection context manager and explicit transaction boundaries in
repository functions. Do not share one SQLite connection arbitrarily
across worker threads.

## 6.2 Source tables

The supplied specification defines these principal tables:

-   `pipeline_runs`
-   `taxonomy_nodes`
-   `feedback_records`
-   `extracted_insights`
-   `canonical_problems`
-   `backlog_items`
-   `validation_findings`
-   `whitespace_candidates`

Use the consolidated schema in the supplied Section 1.3 as the starting
point. The earlier draft's `linked_cluster_id` field conflicts with the
later `linked_problem_id` design. Use `linked_problem_id` as the
canonical relationship unless a later approved schema decision changes
it.

## 6.3 Recommended schema extensions

Add tables to preserve detailed analytical evidence rather than storing
all relationships only as JSON:

  -----------------------------------------------------------------------
  Table                               Purpose
  ----------------------------------- -----------------------------------
  `pipeline_module_runs`              Per-module execution status, timing
                                      and errors

  `model_versions`                    Model names, versions, hashes and
                                      parameters

  `artifact_manifest`                 Run artifact paths, checksums and
                                      types

  `cluster_memberships`               Insight-to-cluster mapping

  `problem_feedback_membership`       Canonical problem to feedback
                                      relation

  `backlog_problem_matches`           Top-k problem-to-ticket comparisons

  `graph_motifs`                      Detected graph motif records

  `graph_motif_evidence`              Exact supporting graph edges and
                                      feedback

  `spatial_void_regions`              Detected void region metadata

  `spatial_region_evidence`           Problems/feedback supporting a
                                      region

  `nmf_components`                    Component metadata and scores

  `nmf_memberships`                   Feedback-to-component weights

  `lens_detections`                   Per-lens candidate detections

  `candidate_feedback_evidence`       Unified candidate evidence

  `evaluation_runs`                   Evaluation execution metadata

  `evaluation_labels`                 Human-reviewed reference labels

  `evaluation_metrics`                Module and run metrics
  -----------------------------------------------------------------------

## 6.4 Indexes and integrity

Create indexes for common access patterns:

-   Feedback by `run_id`, `feedback_id`, `customer_id_hash`, timestamp.
-   Insights by `feedback_id`, `journey_node_id`, `intent`, `symptom`.
-   Problems by `run_id`, `cluster_label`, `priority_score`.
-   Backlog by `backlog_id`, `upload_batch_id`, `journey_node_id`.
-   Findings by `run_id`, `problem_id`, `relationship_type`.
-   Candidates by `run_id`, `discovery_source`, `whitespace_score`.
-   Evidence links by candidate/problem and feedback ID.

Add unique constraints for source identifiers within their source scope.
Use foreign keys for relationships that must be referentially valid.
Validate JSON payloads before persistence.

## 6.5 Database migration procedure

1.  Create migration `001_initial_schema.sql`.
2.  Create all base tables and foreign keys.
3.  Create indexes.
4.  Create migration tracking table.
5.  Run migration against a fresh database in tests.
6.  Insert a small fixture dataset.
7.  Test foreign-key enforcement.
8.  Test transaction rollback.
9.  Test migration idempotency policy.
10. Record schema version in each run manifest.

Never modify an already-applied migration silently. Create a new
migration.

------------------------------------------------------------------------

# 7. Module A --- Feedback ingestion and normalization

## 7.1 Responsibility

Module A converts raw customer feedback files into validated,
privacy-aware and normalized feedback records. It must preserve the
original customer text for evidence tracing.

**Input:** CSV/JSON feedback source.\
**Output:** `feedback_records`, ingestion report and duplicate groups.\
**Downstream:** Module B and all subsequent modules.

## 7.2 Implementation steps

### Step A1 --- File and schema validation

-   Accept supported CSV/JSON formats.
-   Verify file exists and is within configured size limits.
-   Parse encoding.
-   Map source fields to canonical names.
-   Validate mandatory fields.
-   Reject malformed records or quarantine them with row-level error
    details.
-   Record source file checksum and ingestion batch ID.

Do not abort an entire ingestion because of one malformed row unless the
file-level contract is invalid. Report accepted, rejected and warning
counts.

### Step A2 --- Stable feedback IDs

If the source provides a unique `feedback_id`, preserve it. If not,
generate a deterministic identifier based on source file identity and
stable row/source attributes. Record the generation method. Do not
generate random IDs on every rerun because that breaks provenance.

### Step A3 --- Customer identifier hashing

The supplied specification requires SHA-256 hashing of `customer_id`.

Recommended implementation: - Normalize the identifier consistently. -
Use a controlled secret salt/HMAC where operationally possible; a plain
SHA-256 hash of predictable identifiers may be vulnerable to dictionary
attacks. - Never log the original customer ID. - Store only the approved
pseudonymous representation in analytical tables. - Keep any
mapping/re-identification capability outside this analytical application
and under separate access control.

Hashing is pseudonymization, not proof that free text contains no
personal data.

### Step A4 --- Raw and cleaned text

Store: - `raw_text`: original source string, unchanged. -
`cleaned_text`: normalized analytical string.

Cleaning may include: - Unicode normalization. - Trimming
leading/trailing whitespace. - Normalizing repeated whitespace. -
Removing explicitly approved boilerplate. - Preserving meaning,
negation, numbers and product terms.

Do not remove words such as "not", "never", "failed", transaction
amounts or dates if they carry meaning. Avoid aggressive stemming or
paraphrasing in the evidence layer.

### Step A5 --- Near-duplicate detection

Source baseline: - MinHash or normalized character n-gram Jaccard. -
Similarity threshold `>= 0.90`. - Compare within a 24-hour window per
`customer_id_hash`.

Implementation sequence: 1. Normalize text for duplicate comparison
only. 2. Partition by customer hash and time window. 3. Generate
candidate pairs efficiently. 4. Compute exact similarity for candidates.
5. Group records meeting the configured threshold. 6. Assign
`duplicate_group_id`. 7. Preserve every original record.

Do not delete duplicate submissions. Downstream volume calculations
should apply the documented representative-record policy. Keep duplicate
counts available because repeated submissions may themselves be
meaningful.

### Step A6 --- Ingestion quality report

Produce: - Source row count. - Accepted row count. - Rejected row
count. - Missing field counts. - Timestamp parsing failures. - Duplicate
group count. - Duplicate member count. - Empty feedback count. - Channel
and tier distributions. - Text length statistics. - PII warning count if
a detector is implemented. - Input checksum and schema mapping.

## 7.3 Module A outputs

-   Validated `feedback_records`.
-   Duplicate group mapping.
-   `ingestion_quality_report.json`.
-   Input file manifest.
-   Rejected-row report.

## 7.4 Module A tests

-   Valid CSV and JSON.
-   Missing mandatory column.
-   Null customer ID.
-   Invalid timestamp.
-   Duplicate feedback ID.
-   Unicode text.
-   Empty text.
-   Exact duplicate.
-   Near duplicate above and below threshold.
-   Same text from different customers.
-   Same customer outside the 24-hour window.
-   Hash consistency across reruns.
-   Raw text remains unchanged after cleaning.

**Completion gate:** all source rows are accounted for as accepted,
rejected or explicitly skipped, and every accepted feedback record can
be traced to its original source row.

------------------------------------------------------------------------

# 8. Module B --- BERT signal extraction, taxonomy and workaround tagging

## 8.1 Responsibility

Module B transforms cleaned free text into structured signals. It does
not generate a canonical cluster-level problem. It extracts record-level
evidence and builds the deterministic enriched sentence.

**Input:** normalized feedback records and taxonomy.\
**Output:** `extracted_insights` and extraction-quality report.

## 8.2 Extraction fields

Extract:

-   Intent.
-   Aspect.
-   Symptom.
-   Sentiment.
-   Emotion.
-   Effort score.
-   Outcome.
-   Evidence span.
-   Journey taxonomy mapping.
-   Workaround tags.

## 8.3 Model strategy

The source calls for fine-tuned BERT classifiers/extractors but does not
supply a trained model, labeled dataset, annotation instructions or
model evaluation results.

Therefore, implementation must not assume a ready-made model can
reliably produce all required fields.

Use an explicit model adapter with separately configured tasks:

  Task        Model output
  ----------- -------------------------------
  Intent      Label + confidence
  Aspect      Label/span + confidence
  Symptom     Text/span + confidence
  Sentiment   Score/class + confidence
  Emotion     Label + confidence
  Effort      Score 1--5 + confidence
  Outcome     Label/span + confidence
  Evidence    Exact source span and offsets

Possible implementation strategies: 1. Load existing approved fine-tuned
local models if available. 2. If not available, create a labeled
annotation sample and train/evaluate appropriate task-specific heads. 3.
Use a clearly labeled provisional extraction method for development
fixtures only. 4. Do not present unvalidated model outputs as
production-quality customer insight.

## 8.4 Taxonomy mapping

Map `(aspect, symptom, cleaned_text)` to taxonomy nodes.

Source baseline: - If mapping confidence `< 0.55`, set
`journey_node_id = NULL`. - Set `is_open_set = 1`.

Store the confidence and top candidate mappings. Do not force
low-confidence feedback into a known journey.

The threshold must be evaluated on manually reviewed examples.

## 8.5 Workaround lexicon

The source provides these initial patterns:

  -----------------------------------------------------------------------
  Tag                                 Initial pattern examples
  ----------------------------------- -----------------------------------
  `BRANCH_VISIT`                      branch, teller, in-person, counter

  `CALL_CENTER`                       call center, helpline, phone
                                      support, IVR

  `MANUAL_EXPORT`                     Excel, CSV, spreadsheet, download
                                      statement, manually

  `SCREENSHOT_PROOF`                  screenshot, screen shot, photo of
                                      receipt, PDF proof

  `THIRD_PARTY_CHAT`                  WhatsApp, email support, Twitter/X,
                                      social media
  -----------------------------------------------------------------------

Use case-insensitive token-aware matching and carefully reviewed regular
expressions. Store the exact matched phrase and character offsets where
possible. Lexicon matches are evidence of a phrase, not proof that the
workaround was necessary or successful.

## 8.6 Deterministic enriched sentence

Use the specified template:

``` python
signature = signature_path or "Unmapped Banking Journey"

enriched_sentence = (
    f"Under {signature}, the customer experiences "
    f"{symptom} and states: {cleaned_text}"
)
```

The enriched sentence must not add a new inferred problem or root cause.
It is a structured representation of the extracted taxonomy, symptom and
customer voice.

## 8.7 Evidence validation

For every evidence span: 1. Check it is non-empty when a span is
required. 2. Check exact occurrence in the correct source text
representation. 3. Verify offsets against raw text. 4. If normalization
changes offsets, store alignment information. 5. Mark invalid spans as
failed/uncertain; do not silently replace them with approximate text.

## 8.8 Module B quality report

Include: - Extraction success/failure rate. - Per-field missingness. -
Confidence distribution. - Intent distribution. - Aspect distribution. -
Emotion distribution. - Effort distribution. - Taxonomy mapped/open-set
percentage. - Evidence-span exactness rate. - Workaround-tag
frequency. - Model name/version and taxonomy version.

## 8.9 Module B tests and gate

Test each task independently, including negation, multiple issues in one
feedback, ambiguous journey, no workaround, multiple workarounds, very
short feedback, long feedback, misspellings, unsupported language and
malformed model output.

**Completion gate:** extracted insights are structurally valid, evidence
spans are verifiable, and model limitations are documented with measured
evaluation results.

------------------------------------------------------------------------

# 9. Module C --- Weighted TF-IDF and behavioral distance

## 9.1 Responsibility

Module C creates two distinct analytical representations:

1.  Weighted sparse text representation for clustering.
2.  Behavioral distance representation for downstream spatial analysis.

## 9.2 Input selection and deduplication policy

Read insights from the current run. Apply the representative-record
policy for duplicate groups. Preserve the complete member list so
evidence is not lost.

The implementation must define whether clustering uses: - One
representative feedback per duplicate group, or - All feedbacks with
volume adjusted by duplicate-group weighting.

The source specifies filtering secondary records where a duplicate group
is already represented. Use that as the initial baseline, but preserve
duplicate group metadata for later analysis.

## 9.3 Weighted TF-IDF

Source baseline:

-   Separate `TfidfVectorizer` instances.
-   `ngram_range=(1, 2)`.
-   `sublinear_tf=True`.
-   English stop words removed.
-   `max_features` as specified below.

  Matrix    Source field           Weight   Maximum features
  --------- -------------------- -------- ------------------
  `V_sig`   Taxonomy signature       0.40              1,000
  `V_sym`   Symptom                  0.35              1,500
  `V_txt`   Cleaned text             0.25              5,000

Formula:

\[ X\_{tfidf} = \[0.40V\_{sig};\|;0.35V\_{sym};\|;0.25V\_{txt}\] \]

Then L2-normalize rows.

Implementation steps: 1. Extract ordered insight IDs. 2. Build taxonomy
signature strings. 3. Build symptom strings. 4. Build cleaned feedback
strings. 5. Fit vectorizers on the current training corpus. 6. Transform
each field. 7. Multiply each sparse matrix by its weight. 8.
Horizontally concatenate with `scipy.sparse.hstack`. 9. L2-normalize
rows. 10. Persist matrix and vectorizer metadata.

Do not refit vectorizers independently for different downstream modules
within the same run. Save vocabulary and IDF state.

## 9.4 Behavioral distance representation

Source dimensions: - Categorical: journey node (or `OPEN_SET`), symptom,
emotion. - Numerical: effort score scaled to \[0,1\].

The source calls for pairwise Gower distance, averaging categorical
exact-match distance and numerical Manhattan distance.

Important implementation requirements: - Define how missing categorical
values are handled. - Define feature weights. - Validate numerical
bounds. - Ensure distances lie within \[0,1\]. - Store the feature order
and scaling metadata.

A full dense 15,000 × 15,000 float64 matrix is approximately 1.8 GB
before overhead. Avoid blindly materializing it. Use block-wise
computation, sparse/condensed representations or calculate only the
distances required by the next stage. Record the chosen strategy.

## 9.5 Module C outputs

-   `tfidf_matrix.npz`
-   `insight_ids.json`
-   Vectorizer vocabulary/IDF metadata.
-   Behavioral feature table.
-   Distance artifact or reproducible distance-computation manifest.
-   Module configuration snapshot.

## 9.6 Tests and gate

Test empty vocabulary, all-empty fields, one record, missing taxonomy,
constant effort, unknown categories, normalization, row ordering, matrix
shape and deterministic repeatability.

**Completion gate:** every matrix row maps to exactly one persisted
insight ID in the same order, and the distance implementation passes
numerical validation.

------------------------------------------------------------------------

# 10. Module D --- Granular clustering and open-set isolation

## 10.1 Responsibility

Discover groups of semantically similar customer insights without
forcing every record into a cluster.

## 10.2 Primary clustering pipeline

Source baseline:

1.  Apply `TruncatedSVD(n_components=100, random_state=42)` to the
    weighted TF-IDF matrix.
2.  L2-normalize the reduced representation.
3.  Run HDBSCAN:
    -   `min_cluster_size=15`
    -   `min_samples=5`
    -   `metric='euclidean'`
    -   `cluster_selection_method='eom'`

Validate that the feature count and sample count support the requested
SVD dimension. If not, reduce the component count under an explicit rule
and record the effective value. Never allow a dimension error to
silently skip clustering.

## 10.3 Mega-cluster guard

Source baseline: if a cluster contains more than 8% of the total
feedback, run `MiniBatchKMeans(n_clusters=8, random_state=42)` on that
cluster.

Implementation steps: 1. Calculate cluster size / eligible record count.
2. Identify clusters above configured fraction. 3. Extract their
members. 4. Run the fallback only when sample count supports it. 5.
Persist parent cluster ID and child cluster ID. 6. Compare subcluster
sizes and coherence. 7. Preserve original cluster assignment for audit.

The fixed value of eight clusters can over-partition or under-partition.
Keep it configurable and evaluate it.

## 10.4 Open-set micro-grouping

Source baseline: - Include `is_open_set = 1`, and/or HDBSCAN noise
records with `effort_score >= 4.0`. - Group by exact
`(intent, lower(symptom))`. - Retain groups with count `>= 5`.

Define normalization of symptom text carefully. Exact lowercasing alone
may leave punctuation and minor variants. If normalization is added,
version it and preserve original text.

Do not force ungrouped open-set records into a canonical problem.
Preserve them as unassigned/open-set evidence.

## 10.5 Cluster output contract

Each cluster record should contain: - `run_id`. - `cluster_id` /
label. - Parent cluster ID if subclustered. - Member insight IDs. -
Member feedback IDs. - Cluster size. - Noise flag. - Cluster method and
parameters. - Cluster centroid or representative vector reference. -
Cluster quality metrics where available.

## 10.6 Module D tests and gate

Test: - Fewer than 100 features. - Fewer than 15 records. - All records
identical. - All records noise. - One very large cluster. - Multiple
clusters. - Missing effort values. - Open-set groups below and above
threshold. - Repeated execution with fixed seed.

**Completion gate:** every eligible insight has an explicit
cluster/noise/open-set status and no record disappears during
sub-clustering.

------------------------------------------------------------------------

# 11. Module E --- Medoids, canonical problems, priority and MDS

## 11.1 Responsibility

Convert raw clusters into canonical customer problem records with
representative evidence, interpretable keywords, business priority and
two-dimensional visualization coordinates.

## 11.2 Medoid selection

The source describes computing the cluster centroid in SVD-normalized
space and selecting the record with minimum Euclidean distance to the
centroid.

Strictly, the point closest to a centroid is a centroid-nearest
representative; a mathematical medoid is the member minimizing total
distance to all other members. Choose one definition and name it
accurately.

For the source baseline, implement centroid-nearest representative and
label it as such unless the team explicitly chooses pairwise medoid
calculation.

Persist: - Representative insight ID. - Representative feedback ID. -
Distance to centroid. - Method name. - Cluster vector artifact
reference.

## 11.3 Representative evidence

Source baseline: - Top-10 closest enriched sentences. - c-TF-IDF top-8
distinguishing keywords.

Persist the exact feedback IDs and evidence spans used. Ensure the
selected examples represent the cluster rather than only its most
frequent wording.

## 11.4 Canonical problem synthesis

Two modes:

**Deterministic offline mode**

``` text
[Dominant Journey Node] Dominant Symptom (top 3 c-TF-IDF terms)
```

**Local LLM mode**

Prompt the local model with: - Top-10 enriched sentences. - c-TF-IDF
keywords. - Explicit instruction to produce one specific sentence,
maximum 20 words. - Instruction not to add facts absent from evidence.

Validate output: - Exactly one problem statement. - Word limit. - No
unsupported root-cause claim. - No invented customer or product
detail. - No empty/generic filler. - Evidence support review.

Keep original deterministic label and LLM label separately. Store prompt
version, model version and generation result.

## 11.5 Priority calculation

Source formula:

\[ Priority_k = 100(0.35`\tilde `{=tex}V_k + 0.35`\tilde `{=tex}E_k +
0.15`\tilde `{=tex}S_k + 0.15`\tilde `{=tex}T_k) \]

Where: - (`\tilde `{=tex}V_k): log-normalized cluster feedback count. -
(`\tilde `{=tex}E_k): normalized mean effort score. -
(`\tilde `{=tex}S_k): share of insights with sentiment \< -0.3. -
(`\tilde `{=tex}T_k): share of high-value customer tier records.

Implementation must define: - Exact log normalization formula. - Min/max
reference population. - Missing tier behavior. - Whether duplicated
records count. - Treatment of unknown sentiment. - Handling of
zero/constant ranges.

Do not silently set missing customer tier to a low-value tier. Use a
documented missing-data policy and expose the missing share.

## 11.6 Cluster-level MDS

The source proposes: 1. Compute cluster-to-cluster behavioral distance
as mean pairwise Gower distance between members of each cluster. 2. Fit
two-dimensional MDS using precomputed dissimilarities. 3. Persist
`mds_x`, `mds_y`.

Source baseline:

``` python
MDS(
    n_components=2,
    dissimilarity="precomputed",
    random_state=42,
    normalized_stress="auto"
)
```

Persist: - Cluster distance matrix. - MDS coordinates. - MDS stress. -
Random seed. - Input cluster order. - Behavioral feature version.

MDS coordinates are a relative visualization of dissimilarities. Do not
interpret coordinate axes as named business dimensions or use them as
causal evidence.

## 11.7 Module E tests and gate

Test: - Single-member cluster. - Very large cluster. - Missing
effort/tier. - Equal distances. - Non-finite distances. - Duplicate
cluster coordinates. - MDS reproducibility. - LLM malformed output. -
Unsupported canonical claims.

**Completion gate:** every canonical problem has representative
evidence, a transparent score decomposition, a reproducible coordinate
artifact and a validated problem statement.

------------------------------------------------------------------------

# 12. Module F --- Jira ingestion, profiling and embeddings

## 12.1 Responsibility

Convert Jira engineering backlog records into a searchable, profiled and
versioned backlog representation.

## 12.2 Jira adapter

Implement an adapter interface so the internal pipeline does not depend
on a specific Jira export format.

``` python
class JiraSourceAdapter:
    def inspect(self, source_path): ...
    def read_records(self, source_path): ...
    def normalize_issue(self, raw_issue): ...
    def validate_issue(self, normalized_issue): ...
```

For the initial local build, the adapter may read CSV or JSON exported
from Jira. A live Jira API connector is not required unless separately
approved.

## 12.3 Backlog normalization

For each issue: 1. Preserve issue key. 2. Preserve original summary and
description. 3. Normalize searchable text. 4. Parse status and issue
type. 5. Preserve priority and dates where available. 6. Preserve
labels, components, parent and issue links where available. 7. Map to
taxonomy. 8. Profile intents and aspects. 9. Record mapping confidence.
10. Mark unmapped/uncertain tickets.

Do not assume a ticket's summary alone adequately represents the work.
Description quality should be measured.

## 12.4 Dense embeddings

Source baseline: - Concatenate `title + description`. - Use
`SentenceTransformer('BAAI/bge-large-en-v1.5')` or configured local
embedder. - L2-normalize float32 vectors. - Use the same embedder for
canonical problems in Module G.

Implementation: 1. Load local model. 2. Record model identifier and
revision. 3. Batch encode normalized ticket text. 4. Handle empty
description. 5. Normalize vectors. 6. Persist vector and metadata. 7.
Cache by content hash + model version. 8. Recompute when ticket text or
model version changes.

The embedding dimension must be stored and validated before similarity
calculation. Do not compare vectors generated by different model
versions or dimensions.

## 12.5 Backlog profile fields

Source fields: - `journey_node_id` - `profiled_intents_json` -
`profiled_aspects_json`

Recommended additional fields: - `profile_confidence_json` -
`embedding_model_version` - `content_hash` - `source_export_id` -
`status_normalized` - `issue_type_normalized`

## 12.6 Module F tests and gate

Test missing title, empty description, duplicate issue key, updated
ticket content, missing status, multiple labels, malformed rich text,
taxonomy ambiguity, embedding cache hit/miss and vector dimension
mismatch.

**Completion gate:** every Jira item is traceable to the source export
and has a valid profile or an explicit profiling failure state.

------------------------------------------------------------------------

# 13. Module G --- Dense semantic backlog validation

## 13.1 Responsibility

Determine whether existing Jira backlog items semantically align with
each canonical customer problem.

This module identifies candidate relationships; it does not prove a
feature has shipped or resolved the customer problem.

## 13.2 Similarity calculation

For each canonical problem: 1. Construct a problem text using
synthesized problem and representative evidence. 2. Encode with the same
dense embedder used by Module F. 3. Compare against all backlog
embeddings. 4. Compute cosine similarity. 5. Rank the top-k Jira
tickets. 6. Persist best ticket and top-k candidates.

For normalized vectors, cosine similarity is the dot product. Validate
normalization and numeric bounds.

## 13.3 Three-tier classification

Source baseline:

  Score                    Initial classification
  ------------------------ ----------------------------------------
  `>= 0.75`                `COVERED`
  `0.60 <= score < 0.75`   `PARTIAL_GRAY_ZONE` pending validation
  `< 0.60`                 `UNCOVERED_GAP`

The thresholds are configurable initial values and must be calibrated on
reviewed problem-ticket pairs.

## 13.4 Gray-zone local LLM judge

Inputs: - Canonical customer problem. - Top-5 supporting evidence
spans. - Top-3 candidate Jira tickets. - Relevant Jira metadata,
including status and issue type. - Explicit instruction to distinguish
topical similarity from actual resolution coverage.

Expected JSON:

``` json
{
  "covered": true,
  "best_ticket_id": "JIRA-123",
  "reason": "The ticket explicitly implements the customer-facing capability described by the evidence."
}
```

The example is illustrative.

Validation: - JSON parses. - `covered` is boolean. - `best_ticket_id` is
one of the supplied ticket IDs or null under an explicitly supported
contract. - Reason is non-empty and evidence-grounded. - No ticket
outside the supplied candidates is invented.

Store: - Original similarity score. - Top-k candidate IDs and scores. -
Judge decision. - Judge reason. - Model/prompt version. - Judge
execution status. - Whether the result was human reviewed.

In strict offline deterministic mode, retain `PARTIAL_GRAY_ZONE` as
unverified rather than falsely asserting coverage.

## 13.5 Coverage semantics

Keep separate: - Semantic alignment. - Backlog existence. - Ticket
status. - Implementation/shipping status, if available. - Verified
resolution evidence, if available.

A ticket in `Done` status may not resolve the exact problem. A ticket in
`To Do` status may describe a relevant planned capability but is not a
delivered solution. These states must not be collapsed.

## 13.6 Module G tests and gate

Create a reviewed benchmark of problem-ticket pairs: - Exact resolving
ticket. - Related but not resolving ticket. - Same journey, different
symptom. - Similar vocabulary, different intent. - UI-only ticket vs
backend failure. - Generic epic vs specific problem. - No relevant
ticket. - Multiple partially relevant tickets.

Measure precision, recall, false coverage rate and calibration. The
false coverage rate is especially important because an incorrect
`COVERED` result hides a potential customer gap.

**Completion gate:** every canonical problem has a reproducible top-k
backlog audit and an explicit coverage status with uncertainty.

------------------------------------------------------------------------

# 14. Module H --- Structural whitespace engine

Module H contains three analytical lenses and a triangulation component.
Implement and test each lens independently before merging them.

## 14.1 H1 --- Heterogeneous Evidence Graph

### Input data

-   Feedback records.
-   Extracted insights.
-   Customer hashes.
-   Timestamps.
-   Workaround tags.
-   Backlog items.
-   Validation findings.

### Node types

Use typed prefixes to prevent ID collisions:

  Node           Prefix
  -------------- ------------
  Customer       `cust:`
  Journey node   `node:`
  Intent         `intent:`
  Aspect         `aspect:`
  Symptom        `symp:`
  Workaround     `work:`
  Backlog item   `backlog:`

### Edge types

**CO_OCCURS**

Connect journey, intent, aspect and symptom nodes that occur in the same
feedback. Weight may use effort score as specified. Retain the feedback
ID as edge evidence.

**FOLLOWED_BY**

Connect symptom A to symptom B when the same customer submits distinct
feedback records within the configured time window, source baseline
seven days. Order records by timestamp and avoid self-links from the
same feedback record.

This indicates temporal association, not proof that A caused B.

**ESCAPES_TO**

Connect intent/journey nodes to workaround nodes based on extracted
workaround tags. The supplied graph construction specifies
intent-to-workaround and journey-to-workaround edges.

**ADDRESSED_BY**

Connect journey/intent nodes to backlog nodes where alignment score \>=
0.60 or an explicit taxonomy/intent match exists. Label this as
provisional association because the threshold includes gray-zone
matches.

### Motif 1 --- Workaround escape

Source concept: - Identify friction paths involving intent, symptom and
workaround. - Require supporting feedback count \>= 5. - Require no
outgoing `ADDRESSED_BY` coverage from the relevant intent. - Raw score =
count × mean effort.

**Schema issue to resolve:** the prose describes
`Intent → Symptom → Workaround`, but the listed edge construction does
not explicitly create `Symptom → Workaround`. Before coding the
detector, either: 1. Add an evidence-backed `symptom → workaround`
relation from the same feedback record, or 2. Define a different valid
path using the existing edges.

Do not implement a path that cannot exist in the constructed graph.

### Motif 2 --- Temporal friction chain

For symptom transition A → B:

\[ Lift(A `\rightarrow `{=tex}B)= `\frac{P(B|A)}{P(B)}`{=tex} =
`\frac{count(A\rightarrow B)\times N_{transitions}}`{=tex}
{out_count(A)`\times `{=tex}in_count(B)} \]

Source thresholds: - Transition count \>= 5. - Lift \>= 2.0. -
Downstream symptom has no `ADDRESSED_BY` edge.

Raw score:

\[ `\log`{=tex}(1+count)`\times `{=tex}Lift \]

Implementation must define transition counting, unique customer
counting, repeated transitions and denominator zero handling. Use a
consistent unit of analysis.

### Motif 3 --- Structural bridge nodes

-   Build an undirected projection over journey and aspect nodes.
-   Calculate normalized betweenness centrality.
-   Select top 15th percentile.
-   Retain nodes with no `ADDRESSED_BY` edges.

A bridge node is structurally central in the observed graph; this alone
does not mean it is a root cause.

### Graph score normalization

Source baseline: min-max normalize raw detector scores to \[0,1\].

Edge cases: - No candidates. - All scores equal. - Extreme outlier. -
Missing effort. - Isolated nodes.

When all scores are equal, avoid division by zero and document the
chosen neutral score behavior.

### H1 output

-   Graph nodes and edges.
-   Motif records.
-   Motif score.
-   Detector type.
-   Exact supporting feedback IDs.
-   Supporting edge IDs.
-   Coverage evidence.
-   Run and configuration references.

## 14.2 H2 --- MDS spatial void and backlog projection

### Inputs

-   Canonical problem MDS coordinates.
-   Cluster behavioral distances/centroids.
-   Jira behavioral profiles.
-   Canonical problem priority and effort.
-   Backlog coverage information.

### Backlog projection

Source baseline: - Compute Gower distance from a backlog item to
canonical problems. - Default backlog effort to 3.0 and emotion to
Neutral where the source specification calls for those defaults. -
Project into MDS space using inverse-distance weighted 5-nearest
neighbors.

\[ (x_b,y_b)= `\frac{\sum_{j\in KNN(b)}w_j(x_j,y_j)}`{=tex}
{`\sum`{=tex}\_{j`\in `{=tex}KNN(b)}w_j} \]

\[ w_j=`\frac{1}{d(b,C_j)+\epsilon}`{=tex}, `\quad`{=tex}
`\epsilon=10`{=tex}\^{-6} \]

This is a heuristic projection into the existing 2D layout, not a
mathematically exact out-of-sample MDS transform. Label it accordingly
in code and UI.

### KDE surfaces

Source baseline: - 100 × 100 grid. - Customer pain KDE weighted by
`priority_score × mean_effort_score`. - Backlog coverage KDE over
projected backlog coordinates. - If backlog is empty, backlog surface is
zero. - Add controlled jitter only when covariance is near-singular.

Residual surface:

\[ S\_{void}(x,y)=
`\max`{=tex}(0,KDE\_{pain}(x,y)-0.85KDE\_{backlog}(x,y)) \]

The source specifies independently min-max normalizing the surfaces
before subtraction. This is a heuristic and can make the two values
appear comparable when they are not calibrated probability densities.
Preserve this as the baseline only for experimental evaluation; record
raw surfaces, normalization parameters and bandwidth.

### Void extraction

Source baseline: - `maximum_filter` size 5. - Candidate peak where
nearest projected backlog distance exceeds: \[
R=0.25`\times`{=tex}`\max`{=tex}(`\Delta `{=tex}x,`\Delta `{=tex}y) \] -
Collect canonical problems and feedback within radius R. - Spatial score
is residual surface value at peak.

### H2 failure cases

Handle: - No canonical problems. - One canonical problem. - Fewer than
required points for KDE. - Singular covariance. - No backlog. - All
coordinates identical. - Very small coordinate range. - Invalid
distances. - Empty grid. - Sensitivity to KDE bandwidth and MDS seed.

### H2 output

-   Canonical coordinates.
-   Backlog projected coordinates.
-   Pain density grid.
-   Backlog density grid.
-   Residual density grid.
-   Void peak records.
-   Supporting problem IDs and feedback IDs.
-   Projection method and parameters.
-   MDS stress and sensitivity metadata.

A spatial void is a candidate signal requiring validation; it is not
proof of a missing capability.

## 14.3 H3 --- Combinatorial taxonomy lattice and NMF

### Taxonomy lattice

Cross-tabulate `(journey_node_id, intent)` across deduplicated extracted
insights.

Source baseline candidate criteria: - Insight count \>= 10. - Mean
effort \>= 3.8. - Maximum backlog alignment \< 0.25.

Include open-set micro-groups from Module D with count \>= 5.

Define what "maximum backlog alignment" means when there is no linked
canonical problem or no Jira item. Missing alignment must not silently
be treated as zero unless the intended semantics are explicitly "no
evidence of coverage."

### Behavioral matrix

Construct nonnegative sparse matrix over one-hot/count encoded:

-   Intent.
-   Symptom.
-   Emotion.
-   Workaround tags.
-   Channel.

Keep feature vocabulary and column ordering persisted. Ensure no
negative values enter NMF.

### NMF

Source baseline:

``` python
NMF(
    n_components=12,
    init="nndsvda",
    max_iter=500,
    random_state=42
)
```

For each component: - Rank feedbacks by document-topic weight. - Inspect
top-50 feedbacks. - Calculate mean effort. - Calculate share associated
with covered canonical problems. - Retain if mean effort \>= 4.0 and
less than 20% of member feedbacks belong to a `COVERED` canonical
problem.

The 12-component count is an initial fixed baseline, not a proven
optimal factor count. Evaluate component stability and interpretability.
Persist factor loadings, feature weights, member IDs and component
configuration.

### Traffic-adjusted residual

The source proposes Poisson regression to predict complaint volume by
journey from channel traffic baseline and flag standardized Pearson
residual \> 2.

This requires actual exposure/traffic denominators. Feedback records
alone are not traffic data.

Implementation rule: - If reliable channel/journey traffic counts exist,
document their period, scope and join logic before fitting. - If no
denominator exists, mark traffic-adjusted residual analysis
unavailable. - Do not substitute feedback count as traffic volume. - Do
not fabricate traffic baselines.

### H3 output

-   Journey × Intent lattice table.
-   Candidate holes.
-   Open-set groups.
-   NMF component records.
-   Component membership weights.
-   Feature vocabulary.
-   Traffic residuals only if valid exposure data exists.
-   Exact supporting feedback IDs.

## 14.4 H4 --- Triangulation

### Candidate matching

Source baseline: - Shared `(journey_node_id, intent)` OR feedback-ID
Jaccard \>= 0.30.

Jaccard:

\[ J(A,B)=`\frac{|A\cap B|}{|A\cup B|}`{=tex} \]

A shared journey and intent can identify possible overlap but may
combine different symptoms or distinct problems. Treat it as a candidate
match, then compare symptom, aspect and evidence before merging.

### Triangulation gate

Source baseline:

\[ VerifiedWhitespace
`\iff `{=tex}`\text{at least 2 of 3 lenses trigger}`{=tex} \]

Persist: - Which lenses triggered. - Which did not trigger. - Individual
scores. - Supporting feedback. - Candidate merge rationale. - Whether
evidence overlap or taxonomy overlap created the match.

The three lenses are not automatically statistically independent. Graph,
spatial and combinatorial analyses reuse some of the same underlying
records and features. Therefore, two-lens agreement is a corroboration
rule, not a calibrated probability of truth.

### Composite score

Source baseline:

\[ WhitespaceScore = 0.35S\_{graph}+ 0.30S\_{spatial}+
0.20S\_{combinatorial}+ 0.15(1-C\_{backlog}) \]

Where `C_backlog` is the maximum alignment score across linked canonical
problems.

Define behavior when no linked canonical problem exists. Do not silently
set unknown coverage to zero if that would inflate the score. Store
missingness and use an explicitly approved policy.

### H module acceptance gate

Every verified candidate must have: - At least two triggered lens
records. - Exact supporting feedback IDs. - Reproducible detector
parameters. - Valid graph/spatial/combinatorial evidence. - Backlog
coverage context. - A score decomposition. - A clear uncertainty
statement.

------------------------------------------------------------------------

# 15. Unified merger and candidate prioritization

## 15.1 Responsibility

Combine Track 1 uncovered canonical problems and Track 2 verified
whitespace candidates into a unified product opportunity feed.

## 15.2 Candidate matching

Source baseline: - Feedback Jaccard \>= 0.30, or - Exact
`(journey_node_id, intent)` match.

Recommended additional validation: - Symptom compatibility. - Aspect
compatibility. - Evidence overlap. - Whether the two candidates describe
the same customer problem rather than merely the same journey.

## 15.3 Discovery source

Allowed values:

-   `DIRECT_CLUSTER`
-   `TRIANGULATED_WHITESPACE`
-   `BOTH`

For `BOTH`: - Link the canonical problem. - Union supporting feedback
IDs. - Append `DIRECT_GAP` to triggered lens list. - Preserve original
whitespace score. - Preserve adjusted score separately.

The source baseline proposes multiplying whitespace score by 1.20 and
capping at 1.0. Treat this as an initial rule to evaluate, not proof
that dual discovery deserves a 20% business-priority increase.

For Track 1 only, source baseline:

\[ Score = 0.50(ProblemPriority/100)+ 0.50(1-AlignmentScore) \]

For Track 2 only, retain the triangulation score.

## 15.4 Separate scoring dimensions

The implementation should keep three concepts separate:

1.  **Discovery evidence strength:** how strongly the analytical
    evidence supports the candidate.
2.  **Backlog coverage uncertainty:** how certain the system is that
    existing work does or does not address it.
3.  **Business priority:** how important the problem may be based on
    volume, effort, sentiment, customer tier and approved business
    factors.

Do not compare scores from different formulas as if they were calibrated
on one common scale until an evaluation and calibration process supports
that interpretation.

## 15.5 Local LLM narrative enrichment

For selected top-ranked candidates, the local LLM may generate: -
Capability title, maximum 10 words. - Two-sentence hypothesis. - Three
acceptance criteria in Given/When/Then format.

Inputs: - Top-15 evidence spans. - Taxonomy path. - Triggered
graph/spatial/combinatorial motifs. - Closest Jira tickets and
reasons. - Explicit uncertainty and unsupported-claim constraints.

Validate generated JSON and retain deterministic fallback output.

LLM output is a proposal, not a verified product requirement. Require
human review before export or Jira creation.

## 15.6 Unified output contract

Each candidate should expose: - `whitespace_id` - `run_id` -
`discovery_source` - `linked_problem_id` - `title` - `hypothesis` -
`acceptance_criteria` - `whitespace_score` - `priority_score` -
`semantic_max_sim` - `graph_score` - `spatial_score` -
`combinatorial_score` - `lenses_triggered` - `supporting_feedback_ids` -
`matched_backlog_ids` - `score_components` - `created_at`

------------------------------------------------------------------------

# 16. Pipeline orchestration and resumability

## 16.1 Run lifecycle

Suggested run states: - `PENDING` - `RUNNING` - `COMPLETED` - `FAILED` -
`CANCELLED`

Each module should also have its own state: - `NOT_STARTED` -
`RUNNING` - `COMPLETED` - `FAILED` - `SKIPPED`

Persist: - Start and end time. - Input row count. - Output row count. -
Error message and stack reference. - Effective configuration. - Model
versions. - Artifact manifest. - Warnings.

## 16.2 Execution DAG

``` mermaid
flowchart TD
    V[Validate source files and configuration] --> R[Create run]
    R --> A[Module A: feedback ingestion]
    A --> B[Module B: extraction]
    B --> C[Module C: vectorization]
    C --> D[Module D: clustering]
    D --> E[Module E: canonical problems and MDS]
    E --> F[Module F: Jira ingestion and profiling]
    F --> G[Module G: backlog validation]
    G --> H1[Graph lens]
    G --> H2[Spatial lens]
    G --> H3[Combinatorial lens]
    H1 --> H4[Triangulation]
    H2 --> H4
    H3 --> H4
    H4 --> M[Unified merger]
    G --> M
    M --> Q[Quality checks and evaluation]
    Q --> DONE[Complete run]
```

The exact placement of Module F can be adjusted operationally: Jira
ingestion can happen before the feedback pipeline because it is a
separate source. It must be complete before Module G and the relevant
Module H computations.

## 16.3 Artifact manifest

Example run directory:

``` text
artifacts/<run_id>/
  manifest.json
  config_snapshot.json
  model_versions.json

  ingestion/
    ingestion_quality_report.json
    rejected_rows.csv

  extraction/
    extraction_quality_report.json
    extracted_insights.parquet

  direct/
    tfidf_matrix.npz
    insight_ids.json
    vectorizer_metadata.json
    clusters.parquet
    canonical_problems.json
    mds_coordinates.csv
    backlog_matches.json

  graph/
    nodes.json
    edges.json
    motifs.json

  spatial/
    canonical_coordinates.csv
    backlog_coordinates.csv
    pain_density.npy
    backlog_density.npy
    residual_surface.npy
    void_regions.json

  combinatorial/
    taxonomy_lattice.csv
    nmf_components.json
    nmf_memberships.parquet

  triangulation/
    candidate_signals.json
    verified_whitespaces.json

  unified/
    candidates.json

  evaluation/
    metrics.json
```

Use Parquet only if the dependency is included and its use is approved;
CSV/JSON/NPZ are acceptable initial artifact formats.

## 16.4 Cache and resume rules

Cache a module output only when all relevant inputs match: - Source file
checksum. - Upstream artifact checksum. - Module code/config version. -
Model name and version. - Taxonomy version. - Random seed.

If any dependency changes, invalidate the affected downstream artifacts.
Do not reuse embeddings after changing the embedding model. Do not reuse
clusters after changing the vectorizer or feature weights.

## 16.5 Failure handling

-   Write module failure state before propagating the error.
-   Preserve completed upstream artifacts.
-   Record a concise user-facing error and detailed local log reference.
-   Do not mark a partially completed module as successful.
-   Allow retry from the failed module only when upstream artifact
    checksums remain valid.
-   Ensure partial writes are transactionally safe.

------------------------------------------------------------------------

# 17. FastAPI implementation

## 17.1 API responsibilities

FastAPI should: - Validate pipeline requests. - Create run records. -
Start or signal the worker. - Expose run status. - Serve candidate and
evidence data. - Serve graph and spatial artifacts. - Export selected
candidates.

It should not contain analytical algorithms. Keep business logic in
service/repository modules.

## 17.2 Endpoint contracts

### Start pipeline

`POST /api/v1/pipeline/run`

Request example:

``` json
{
  "feedback_file_id": "feedback-batch-001",
  "jira_file_id": "jira-export-001",
  "provider_mode": "local",
  "configuration_profile": "baseline"
}
```

The source specification uses file paths in its example. Prefer
server-registered file IDs or validated paths restricted to approved
data directories. Never accept arbitrary filesystem paths without
validation.

Response:

``` json
{
  "run_id": "run_...",
  "status": "PENDING"
}
```

### Run status

`GET /api/v1/runs/{run_id}/status`

Return: - Run ID. - Overall status. - Current module. - Module
statuses. - Feedback count. - Cluster count. - Uncovered gap count. -
Verified whitespace count. - Warnings/errors.

### Candidate feed

`GET /api/v1/runs/{run_id}/gaps`

Support: - Source filter. - Journey filter. - Minimum score. - Lens
filter. - Pagination. - Sorting. - Search.

Return score decomposition and provenance summary.

### Evidence

`GET /api/v1/runs/{run_id}/gaps/{whitespace_id}/evidence`

Return: - Candidate detail. - Supporting feedback records. - Exact
evidence spans and offsets. - Extracted signals. - Customer tier
distribution where available. - Top Jira candidates. - Similarity
scores. - Judge reasoning. - Coverage/status caveats.

### Lineage

`GET /api/v1/runs/{run_id}/gaps/{whitespace_id}/lineage`

Return a graph-oriented representation of: - Feedback nodes. - Extracted
signal nodes. - Track 1 cluster. - Module H lens detections. - Unified
candidate. - Jira backlog audit nodes. - Edges with evidence and scores.

### Spatial map

`GET /api/v1/runs/{run_id}/spatial-map`

Return: - Canonical problem coordinates. - Backlog projected
coordinates. - Grid x/y coordinates. - Pain density. - Backlog
density. - Residual grid. - Void regions and evidence.

### Graph motifs

`GET /api/v1/runs/{run_id}/graph-motifs`

Return nodes, edges, motifs, score and supporting evidence IDs.

### Export

`POST /api/v1/runs/{run_id}/export-backlog`

Allow selected candidate IDs and `csv` or `json` format. This exports a
proposed backlog artifact. It does not create or modify Jira issues.

## 17.3 API quality requirements

-   Pydantic request and response models.
-   Consistent error response format.
-   Pagination for evidence.
-   Input validation.
-   File path restrictions.
-   No raw customer identifiers in logs.
-   Stable response field names.
-   API tests with temporary SQLite database.
-   No long-running pipeline work in API request handlers.

------------------------------------------------------------------------

# 18. Frontend implementation

## 18.1 Main application views

### View 1 --- Prioritized Gap Feed

Purpose: allow product stakeholders to browse and filter product
opportunities.

Display: - Candidate title. - Discovery source. - Journey. - Feedback
count. - Mean effort. - Backlog coverage status. - Triggered lenses. -
Discovery score. - Business priority. - Review status.

Interactions: - Filter by discovery source. - Filter by journey. -
Filter by lens. - Sort by priority or evidence strength. - Open
candidate evidence. - Export selected candidates.

Do not use one score badge as the only explanation of ranking. Provide
score decomposition.

### View 2 --- Spatial Void Map

Purpose: inspect canonical problems, projected backlog points and
residual pain regions.

Display: - Canonical problems as points. - Point size based on
priority. - Backlog projections with a distinct marker. - Residual pain
contour/heatmap. - Void peak markers.

Interactions: - Hover for problem/ticket details. - Select a void to
show supporting canonical problems. - Drill down to supporting
feedback. - Show projection method and uncertainty. - Show MDS stress
and KDE parameters.

Do not label a spatial region "missing feature" without additional
evidence. Use "candidate residual pain region" or equivalent.

### View 3 --- Friction and Workaround Graph

Purpose: explore evidence graph relationships.

Display: - Journey nodes. - Intent nodes. - Symptom nodes. - Workaround
nodes. - Jira nodes. - Typed edges. - Motif and lift details.

Interactions: - Select motif. - Expand local subgraph. - Filter by
journey or time window. - Open supporting feedback. - Inspect
`ADDRESSED_BY` edges and match evidence.

### View 4 --- Evidence Drawer

Purpose: audit one candidate.

Display: - Candidate hypothesis. - Exact quotes. - Evidence span
highlighting. - Extracted signals. - Supporting feedback IDs. - Customer
tier/effort distribution if available. - Top Jira matches. - Reasons for
rejection or uncertainty. - Detector scores. - LLM enrichment metadata.

### View 5 --- Lineage Canvas

Use five columns:

1.  Verbatim customer voice.
2.  Extracted signals.
3.  Direct cluster and whitespace lenses.
4.  Unified candidate.
5.  Jira backlog audit.

Allow reverse tracing from candidate to original feedback and forward
tracing from one feedback record to all candidates it supports.

For large evidence sets, paginate or virtualize records.

## 18.2 UI data principles

-   Show missing/unknown separately from zero.
-   Show provisional and verified statuses distinctly.
-   Explain similarity as similarity, not resolution.
-   Show model-generated content as generated content.
-   Keep exact quotes immutable.
-   Provide method/version details in an inspectable panel.
-   Do not hide rejected Jira candidates; they explain the audit.

------------------------------------------------------------------------

# 19. Evaluation and testing plan

The project is not complete when the pipeline executes. It is complete
only when its outputs have been evaluated against reviewed examples and
the system's limitations are visible.

## 19.1 Evaluation dataset

Create a manually reviewed sample with: - Feedback record. - Correct
intent. - Correct aspect. - Correct symptom. - Correct evidence span. -
Correct journey or open-set label. - Sentiment/emotion/effort labels
where feasible. - Relevant Jira issue(s), if any. - Whether the Jira
item actually addresses the problem. - Human-reviewed canonical problem
grouping.

Use a documented annotation guide and allow "uncertain" labels.
Double-review a subset to estimate reviewer agreement.

## 19.2 Module evaluation

  -----------------------------------------------------------------------
  Module                              Evaluation
  ----------------------------------- -----------------------------------
  A                                   Source row reconciliation,
                                      duplicate precision sample,
                                      normalization checks

  B                                   Per-field precision/recall/F1,
                                      evidence exactness, taxonomy
                                      accuracy

  C                                   Matrix correctness, distance
                                      validity, reproducibility

  D                                   Cluster coherence, noise rate,
                                      stability, cluster size
                                      distribution

  E                                   Representative quality, naming
                                      faithfulness, score sensitivity,
                                      MDS stress

  F                                   Jira field completeness, profiling
                                      accuracy, embedding cache integrity

  G                                   Backlog match precision/recall,
                                      false coverage rate, threshold
                                      calibration

  H1                                  Motif validity, edge evidence
                                      audit, temporal correctness

  H2                                  MDS/KDE sensitivity, void
                                      stability, projection limitations

  H3                                  Lattice validity, NMF stability and
                                      interpretability, traffic data
                                      validity

  H4                                  False merge rate, lens agreement
                                      and evidence consistency

  Merger                              Candidate deduplication precision,
                                      score consistency, lineage
                                      completeness

  API/UI                              Contract tests, pagination, visual
                                      traceability and error handling
  -----------------------------------------------------------------------

## 19.3 Required evaluation scenarios

At minimum test: 1. A clear customer problem with an exact Jira ticket.
2. A clear customer problem with no Jira ticket. 3. A related Jira
ticket that does not solve the problem. 4. A generic Jira epic with weak
detail. 5. Multiple feedback records describing one problem. 6. One
feedback record describing multiple problems. 7. A high-effort
low-volume problem. 8. A high-volume low-effort problem. 9. An open-set
journey. 10. A workaround-heavy problem. 11. A temporal chain with
insufficient evidence. 12. A candidate detected by only one lens. 13. A
candidate detected by two lenses. 14. Two candidates sharing
journey/intent but describing different symptoms. 15. Empty Jira
backlog. 16. Missing customer tier. 17. Invalid or missing timestamps.
18. Duplicate feedback submissions. 19. Local LLM unavailable. 20. Model
output malformed or unsupported.

## 19.4 Sensitivity analysis

Test how candidate outputs change when: - TF-IDF weights change. -
HDBSCAN parameters change. - Similarity thresholds change. - MDS random
seed changes. - KDE bandwidth changes. - NMF component count changes. -
Triangulation threshold changes. - Priority weights change.

Record: - Candidates stable across settings. - Candidates appearing only
under narrow settings. - Candidates whose ranking changes materially. -
Candidates whose supporting evidence changes.

Do not claim robustness without these tests.

------------------------------------------------------------------------

# 20. Privacy, security and governance

This is banking customer data. Local execution does not remove the need
for privacy controls.

Requirements: - Restrict access to raw feedback files. -
Hash/pseudonymize customer identifiers. - Detect or redact sensitive
free-text content where required. - Never place raw account numbers or
credentials in logs. - Keep local LLM prompts and model logs under
controlled storage. - Do not call cloud model endpoints in local-only
mode. - Validate all file paths and file types. - Avoid arbitrary file
read access through API requests. - Keep raw and derived data access
separate. - Record data source and processing provenance. - Apply
retention and deletion requirements defined by the data owner. - Review
whether exports can contain personal or sensitive information. - Ensure
any human evaluation dataset is appropriately access-controlled.

Hashing a customer ID does not anonymize free-text feedback. A customer
may identify themselves inside the message.

------------------------------------------------------------------------

# 21. Performance and operational engineering

## 21.1 Main performance risks

-   BERT inference across 15,000 records.
-   Large embedding batches.
-   Pairwise Gower distance computation.
-   Dense distance matrices.
-   MDS and KDE numerical operations.
-   NetworkX graph size and centrality.
-   NMF matrix construction and convergence.
-   Local generative model latency.

## 21.2 Required mitigations

-   Batch inference.
-   Cache embeddings by content hash and model version.
-   Persist sparse matrices.
-   Avoid dense pairwise matrices unless memory has been calculated.
-   Use block-wise distance computation.
-   Store intermediate artifacts.
-   Separate API and worker processes.
-   Make module execution resumable.
-   Record elapsed time and peak memory where practical.
-   Use configurable batch sizes.
-   Profile actual data before optimizing prematurely.

## 21.3 Operational metrics

Per run, record: - Total elapsed time. - Per-module elapsed time. -
Records processed per second. - Model inference time. - Embedding
throughput. - Artifact sizes. - Peak memory where available. - Number of
warnings and failures. - Cache hit/miss counts.

------------------------------------------------------------------------

# 22. Detailed implementation sequence and gates

## Milestone 0 --- Blueprint freeze

Tasks: 1. Inspect actual feedback file. 2. Inspect actual Jira export.
3. Inspect local hardware. 4. Confirm taxonomy availability and version.
5. Confirm model availability and licenses. 6. Resolve schema conflicts.
7. Resolve graph motif edge inconsistency. 8. Define Gower scaling and
missing-value behavior. 9. Define MDS/KDE evaluation approach. 10.
Confirm traffic data availability. 11. Define local LLM and embedding
runtime. 12. Freeze canonical contracts.

Deliverables: - Source data profile. - Final data dictionary. - Approved
taxonomy mapping. - Database schema. - Configuration schema. - Model
plan. - Open decisions register.

**Gate:** no unknown source fields or unrecorded model assumptions
remain in the implementation contract.

## Milestone 1 --- Repository, environment and database

Tasks: 1. Create repository. 2. Configure Python and Node environments.
3. Pin dependencies. 4. Implement typed configuration. 5. Implement
SQLite connection manager. 6. Implement migrations. 7. Implement run and
module-run tracking. 8. Implement artifact manager. 9. Add logging and
error conventions. 10. Add test fixtures.

Deliverables: - Running API. - Working database. - Migration tests. -
Empty run creation/status retrieval. - Artifact manifest support.

**Gate:** fresh checkout can install, migrate, start and pass foundation
tests.

## Milestone 2 --- Ingestion

Tasks: 1. Implement feedback source adapter. 2. Implement Jira source
adapter. 3. Implement schema validation. 4. Implement normalization. 5.
Implement pseudonymous customer identifier. 6. Implement duplicate
grouping. 7. Implement source checksums. 8. Implement ingestion reports.
9. Add ingestion tests.

Deliverables: - Validated feedback records. - Validated Jira records. -
Source quality reports.

**Gate:** input/output reconciliation and source traceability pass.

## Milestone 3 --- Extraction

Tasks: 1. Select/prepare extraction models. 2. Define
annotation/evaluation sample. 3. Implement model adapter. 4. Implement
intent/aspect/symptom extraction. 5. Implement
sentiment/emotion/effort/outcome tasks. 6. Implement evidence span
validation. 7. Implement taxonomy mapping. 8. Implement workaround
lexicon. 9. Implement enriched sentence. 10. Persist extraction
metadata. 11. Generate quality report.

Deliverables: - Structured insights. - Extraction evaluation report. -
Evidence validation report.

**Gate:** fields are measured and uncertainty is visible.

## Milestone 4 --- Direct discovery

Tasks: 1. Build weighted TF-IDF. 2. Build behavioral feature
representation. 3. Implement scalable Gower computation. 4. Implement
SVD and HDBSCAN. 5. Implement mega-cluster guard. 6. Implement open-set
grouping. 7. Implement representative selection. 8. Implement c-TF-IDF
keywords. 9. Implement priority calculation. 10. Implement MDS. 11.
Implement canonical naming. 12. Ingest/profile Jira. 13. Generate
backlog embeddings. 14. Implement similarity matrix. 15. Implement
three-tier validation. 16. Implement local gray-zone judge. 17. Evaluate
against reviewed pairs.

Deliverables: - Canonical customer problems. - Jira coverage findings. -
Direct uncovered-gap list.

**Gate:** reviewed sample shows acceptable and documented backlog
validation behavior.

## Milestone 5 --- Whitespace engine

Tasks: 1. Finalize graph node/edge contract. 2. Build graph. 3.
Implement workaround motif. 4. Implement temporal chain. 5. Implement
bridge detection. 6. Implement graph score. 7. Implement backlog
projection. 8. Implement KDE surfaces. 9. Implement void extraction. 10.
Implement taxonomy lattice. 11. Implement behavioral matrix. 12.
Implement NMF. 13. Implement optional traffic adjustment. 14. Implement
candidate matching. 15. Implement two-of-three gate. 16. Evaluate
stability and false positives.

Deliverables: - Graph motifs. - Spatial void candidates. - Combinatorial
candidates. - Verified whitespace candidates.

**Gate:** each candidate is backed by reproducible evidence and lens
outputs.

## Milestone 6 --- Unified intelligence

Tasks: 1. Generate candidate match pairs. 2. Validate candidate
equivalence. 3. Merge supporting feedback. 4. Preserve detector
provenance. 5. Apply discovery source classification. 6. Calculate score
components. 7. Implement score policy. 8. Generate local LLM narrative.
9. Validate acceptance criteria. 10. Implement export contract.

Deliverables: - Unified candidate feed. - Candidate lineage. - Proposed
capability descriptions.

**Gate:** no evidence is lost and scores remain interpretable.

## Milestone 7 --- API and frontend

Tasks: 1. Implement run endpoints. 2. Implement candidate endpoints. 3.
Implement evidence endpoint. 4. Implement lineage endpoint. 5. Implement
spatial endpoint. 6. Implement graph endpoint. 7. Implement export
endpoint. 8. Build gap feed. 9. Build spatial map. 10. Build graph
explorer. 11. Build evidence drawer. 12. Build lineage canvas. 13. Add
API integration tests.

Deliverables: - Working local analytical application.

**Gate:** a user can select a candidate and trace it back to exact
feedback and the Jira audit.

## Milestone 8 --- Evaluation and hardening

Tasks: 1. Run complete end-to-end pipeline. 2. Run extraction
evaluation. 3. Run cluster stability tests. 4. Run backlog match
evaluation. 5. Run whitespace sensitivity analysis. 6. Run
prioritization sensitivity analysis. 7. Run performance tests. 8. Run
privacy checks. 9. Run repeatability tests. 10. Review outputs with
business stakeholders. 11. Document limitations and known issues.

Deliverables: - Evaluation report. - Known limitations register. -
Reproducible baseline run. - Release checklist.

**Gate:** no critical provenance, data integrity or false-coverage
defect remains unresolved.

------------------------------------------------------------------------

# 23. Coding-agent execution rules

The implementation should be delegated in small, testable tasks. Do not
ask an agent to generate the entire application in one prompt.

## 23.1 Rules for every coding task

The agent must: 1. Read the current architecture and data contracts
first. 2. Inspect existing repository files before changing them. 3.
Implement only the assigned module/scope. 4. Preserve approved
interfaces. 5. Avoid inventing fields or source data. 6. Add unit tests
for the implementation. 7. Add integration tests where module boundaries
are affected. 8. Run tests and report actual results. 9. Document
assumptions and unresolved decisions. 10. Avoid modifying unrelated
modules. 11. Avoid changing scoring thresholds without explicit
approval. 12. Avoid replacing a specified algorithm with a different one
silently. 13. Persist provenance and configuration. 14. Report any
specification contradiction before coding around it.

## 23.2 Required agent completion report

For each task, require:

``` text
1. Scope implemented
2. Files created
3. Files modified
4. Input contract
5. Output contract
6. Algorithm implemented
7. Configuration values used
8. Database changes
9. Artifacts produced
10. Tests added
11. Commands executed
12. Actual test results
13. Known limitations
14. Open questions
15. Confirmation that unrelated modules were not changed
```

## 23.3 Module task boundaries

  -----------------------------------------------------------------------
  Task                    Agent scope             Must not implement
  ----------------------- ----------------------- -----------------------
  Foundation              Config, DB, migrations, NLP algorithms
                          run tracking            

  Module A                Feedback ingestion      Extraction

  Module B                Extraction, taxonomy,   Clustering
                          workaround tagging      

  Module C                Vectorization and       HDBSCAN
                          behavioral distances    

  Module D                Clustering and open-set Canonical synthesis
                          grouping                

  Module E                Canonical problems,     Jira validation
                          priority, MDS           

  Module F                Jira adapter,           Coverage classification
                          profiling, embeddings   

  Module G                Similarity and          Whitespace
                          gray-zone judge         triangulation

  H1                      Graph and motifs        Spatial/NMF

  H2                      MDS projection and KDE  Graph motifs

  H3                      Lattice and NMF         Cross-lens merge

  H4                      Triangulation           Cross-track merger

  Merger                  Cross-track candidate   Raw extraction
                          reconciliation          

  API/UI                  Contracts and           Reimplementing
                          presentation            algorithms
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 24. Final acceptance checklist

The platform should not be declared implementation-complete until all
applicable conditions are met.

## Data and provenance

-   [ ] Raw feedback is preserved.
-   [ ] Jira source records are traceable.
-   [ ] Customer identifiers are handled under the approved privacy
    policy.
-   [ ] Duplicate groups are preserved and handled consistently.
-   [ ] Every insight links to original feedback.
-   [ ] Evidence spans are verified.
-   [ ] Taxonomy versions are recorded.

## Direct gap discovery

-   [ ] Weighted TF-IDF matrix is reproducible.
-   [ ] Behavioral distances are numerically valid.
-   [ ] Clustering assignments cover all eligible insights.
-   [ ] Open-set records are preserved.
-   [ ] Canonical problems have representative evidence.
-   [ ] Priority components are inspectable.
-   [ ] MDS coordinates and stress are persisted.
-   [ ] Jira embeddings use a consistent model version.
-   [ ] Backlog validation is benchmarked.
-   [ ] Gray-zone outputs preserve uncertainty.

## Whitespace discovery

-   [ ] Graph nodes and edges are typed and traceable.
-   [ ] Motif paths exist in the implemented graph.
-   [ ] Temporal transitions are correctly counted.
-   [ ] Spatial projection assumptions are disclosed.
-   [ ] KDE edge cases are handled.
-   [ ] Lattice holes preserve source evidence.
-   [ ] NMF components are evaluated for interpretability.
-   [ ] Traffic adjustment is disabled when valid denominators are
    unavailable.
-   [ ] Triangulation retains individual lens results.
-   [ ] Two-lens agreement is not represented as proof.

## Unified intelligence

-   [ ] Cross-track merges are evidence-validated.
-   [ ] Discovery source is correctly assigned.
-   [ ] Individual detector scores are preserved.
-   [ ] Coverage certainty and business priority are distinct.
-   [ ] LLM output is validated.
-   [ ] Every recommendation has supporting feedback.
-   [ ] Jira candidates and rejection reasoning are visible.

## Application and operations

-   [ ] Pipeline runs are tracked.
-   [ ] Failed modules can be diagnosed.
-   [ ] Artifacts are versioned.
-   [ ] API contracts are tested.
-   [ ] UI lineage is functional.
-   [ ] Export does not silently create Jira tickets.
-   [ ] Local-only mode makes no cloud model calls.
-   [ ] Performance and repeatability are measured.
-   [ ] Known limitations are documented.

------------------------------------------------------------------------

# 25. Open decisions register

These items must be closed or explicitly deferred before the affected
implementation begins.

  ---------------------------------------------------------------------------------
  ID                Decision                Why it matters    Required resolution
  ----------------- ----------------------- ----------------- ---------------------
  D-01              Actual feedback columns Canonical         Inspect source
                    and quality             ingestion         
                                            contract          

  D-02              Actual Jira export      Jira adapter      Inspect source
                    fields                  contract          

  D-03              Approved banking        Journey mapping   Obtain/validate
                    taxonomy                                  taxonomy

  D-04              BERT model availability Extraction        Inspect local models
                                            implementation    and labels

  D-05              Extraction annotation   Accuracy          Define reviewed
                    strategy                measurement       sample

  D-06              Local machine resources Model feasibility Inspect RAM/CPU/GPU

  D-07              Local generative model  LLM enrichment    Select after hardware
                                                              test

  D-08              Gower                   Distance validity Specify and test
                    missing-value/weight                      
                    policy                                    

  D-09              Full distance strategy  15k scalability   Benchmark
                                                              block/sampled
                                                              approach

  D-10              Centroid-nearest vs     Representative    Approve definition
                    strict medoid           selection         
                                            semantics         

  D-11              Jira status-to-coverage Coverage          Define status
                    policy                  interpretation    semantics

  D-12              Graph                   Motif correctness Resolve graph
                    symptom-to-workaround                     contract
                    edge                                      

  D-13              Temporal transition     Lift validity     Define
                    counting unit                             customer/transition
                                                              unit

  D-14              MDS/KDE calibration     Spatial void      Evaluate against
                                            reliability       labeled cases

  D-15              Traffic denominator     Poisson residual  Inspect source
                    availability            validity          availability

  D-16              NMF component count     Factor stability  Evaluate baseline 12

  D-17              Cross-lens dependence   Triangulation     Document and evaluate
                                            interpretation    

  D-18              Unified score           Cross-source      Benchmark and approve
                    calibration             ranking           

  D-19              Human review workflow   Business trust    Define review
                                                              status/ownership

  D-20              Data retention and      Banking privacy   Confirm data-owner
                    access                                    policy
  ---------------------------------------------------------------------------------

------------------------------------------------------------------------

# 26. Definition of the first working release

The first working release should not attempt to demonstrate every
analytical visualization before the core evidence pipeline works.

A minimum credible release should:

1.  Ingest the actual customer feedback.
2.  Ingest the actual Jira backlog.
3.  Extract structured signals with measurable quality.
4.  Generate canonical customer problems.
5.  Match canonical problems against Jira.
6.  Produce covered, gray-zone and uncovered findings.
7.  Show exact customer evidence and Jira comparisons.
8.  Persist run configuration and reproducible artifacts.
9.  Provide a basic candidate feed and evidence inspection interface.

After this baseline is evaluated, implement and validate the graph,
spatial and combinatorial lenses, then integrate them through
triangulation and unified merging.

This does not remove Module H from the target architecture. It controls
implementation risk by ensuring its dependencies are trustworthy before
the whitespace engine is built.

# 27. Final implementation instruction

Treat this document as the engineering implementation guide, subject to
the open decisions register and actual source-data inspection.

Do not: - Generate all modules in one code-generation pass. - Invent
missing input fields. - Claim that an untrained BERT model is
validated. - Treat semantic similarity as proof of resolution. - Treat
graph association as causality. - Treat MDS/KDE voids as confirmed
missing capabilities. - Treat NMF factors as automatically meaningful. -
Treat two-lens agreement as business truth. - Hide missing data or
uncertainty. - Discard evidence or intermediate analytical outputs. -
Change algorithms, thresholds or weights without recording the change.

Implement one module at a time, with stable contracts, tests, persisted
outputs and an explicit completion gate. Only then allow downstream
modules to consume its outputs.

**The definition of success is not that the platform produces a large
number of gap candidates. It is that every candidate can be examined,
challenged, reproduced and traced to the customer evidence and
engineering backlog that support it.**
