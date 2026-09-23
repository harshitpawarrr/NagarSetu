# NagarSetu System Architecture & Design Specification

## 1. Architectural Philosophy & Operating Principles

**NagarSetu (नगर सेतु)** is an operator-facing, read-only AI civic complaint triage and accountability engine designed to process exported municipal complaint datasets.

Its architecture is governed by four core design tenets:
1. **Source Immutability**: Operations over raw imported complaint datasets (`data/raw/`) are strictly read-only. The database layer strictly rejects updates and deletions via `ImmutableDataError`.
2. **Deterministic Governance over AI Recommendations**: AI models propose department classifications, urgency scores, and routing. Deterministic business logic (`config/departments.json`, `config/urgency_rules.json`, `config/routing_rules.json`, `data/gazetteer/`) validates boundaries and unconditionally overrides AI recommendations when public safety hazards are detected.
3. **Human-in-the-Loop Transparency**: Acknowledgements are drafted by AI but require human operator confirmation before being marked as approved. Every recommendation includes inspectable keywords, department charter clauses, rule IDs, and numerical confidence scores.
4. **Absolute Isolation from Production & Government Systems**: Zero live network connections to government helplines, CM/State endpoints, municipal ERPs (e.g. e-Nagarpalika), or external social media APIs. No external dispatch gateways (SMS/email) are connected.

---

## 2. End-to-End Pipeline Data Flow

The canonical processing lifecycle spans 14 distinct stages:

```
[1. Exported Raw Multimodal Dataset (CSV, JSON, Audio WAV, Photo JPG)]
                               │
                               ▼ (Read-Only Stream Parser)
[2. Ingestion & Raw Staging]
  - Idempotent registration into `raw_complaints` (skips existing IDs)
  - Column normalization & metadata preservation in `extra_metadata`
  - Modality presence validation (rejects empty records without hallucination)
                               │
                               ▼
[3. Multimodal Preprocessing & Language Normalization]
  - Text extraction, cleanup, and canonical summary normalization
  - Audio asset linking (`sample_voice_01.wav`) with transcription staging
  - Photo asset linking (`sample_issue_01.jpg`) with caption & visual metadata
  - Language detection & normalization (Hindi Devanagari, English, Hinglish hi-Latn)
                               │
                               ▼
[4. AI Classification Engine]
  - Google Gemini API (`gemini-2.5-flash`) via structured JSON schema
  - Enforces official municipal taxonomy (`config/departments.json`, `config/categories.json`)
  - Automatic fallback to Deterministic Keyword Engine if API key is missing or quota exhausted
                               │
                               ▼
[5. Urgency Scoring & Deterministic Safety Overrides]
  - Transparent 3-component urgency scoring (Safety 0-40, Outage 0-30, Duration 0-30)
  - Non-negotiable deterministic safety override engine (`config/urgency_rules.json`):
    * Exposed live wire / damaged pole -> FORCED CRITICAL (`URG_RULE_001`)
    * Open manhole cover -> FORCED CRITICAL (`URG_RULE_002`)
    * AI cannot downgrade safety hazard triggers
                               │
                               ▼
[6. Locality Normalization]
  - Token match & alias resolution against `data/gazetteer/sample_wards_gazetteer.json`
  - Deterministic resolution to Canonical Locality, Ward ID, Ward Name, and Zone
  - Unmatched locations marked `UNKNOWN` without landmark hallucination
                               │
                               ▼
[7. Explainable Routing Recommendation]
  - Synthesizes `routing_evidence` citing matched keywords, department charter, and rule ID
  - Assigns `routing_confidence` (0.0 to 1.0) and human-readable explanation
  - Assigns confidence review tiers: `NORMAL` (>=0.80), `ATTENTION` (0.50-0.79), `MANUAL_REVIEW` (<0.50)
                               │
                               ▼
[8. Incident Clustering & Duplicate Detection]
  - Multi-signal pairwise similarity engine (Semantic text, Category, Locality, Ward, Time, Keywords)
  - Connected-component DSU graph clustering with false-positive prevention rules
  - Deterministic cluster representative selection and ticket reduction metric calculation:
    `Reduction % = (Total Raw Complaints - Unique Incidents) / Total Raw Complaints * 100%`
                               │
                               ▼
[9. Structured Ticket Construction & Operator Decision Desk]
  - Operator workbench displays canonical ticket, evidence, urgency breakdown, and multimodal assets
  - Operator can approve or override department, category, urgency, locality, or ward
  - Mandatory operator justification recorded for every override
                               │
                               ▼
[10. Human-in-the-Loop Citizen Acknowledgement Workflow]
  - AI generates draft acknowledgement in bilingual/accessible phrasing
  - Operator edits or approves draft (`draft` -> `edited` -> `approved`)
  - Strictly internal state transition; zero autonomous or external message dispatch
                               │
                               ▼
[11. Chronological Audit Logging]
  - Immutable audit trail in `complaint_audits` capturing `operator_id`, action, and field-level diffs
                               │
                               ▼
[12. Weekly Departmental Accountability Digest]
  - Computes departmental workload tallies (received, resolved, pending, high urgency)
  - Truthfully computes median resolution time strictly from records with valid `created_at` and `resolved_at`
  - Returns `null` when resolution timestamps are absent; zero fabricated SLAs
                               │
                               ▼
[13. Emerging Issue Volume Surge Alerts]
  - Early-warning heuristic engine comparing recent volume (72h) against baseline historical volume
  - Explicitly tagged with `[PROTOTYPE_ASSUMPTION]` non-statistical disclaimer
                               │
                               ▼
[14. Held-Out Benchmark Evaluation]
  - Formal evaluation against held-out labelled test set (`data/test/benchmark_held_out_30.csv`)
  - Computes accuracy, multi-class confusion matrix, precision/recall, and misclassifications inspector
  - Prominently tagged with `DEMO / SYNTHETIC BENCHMARK` badge
```

---

## 3. Core Subsystems & Components

### 3.1 Data Ingestion & Immutability Layer (`backend/app/services/ingestion/`)
- **`CSVParser`**: Stream-based parser supporting UTF-8, UTF-8-BOM (`utf-8-sig`), and Latin-1 encodings with automatic whitespace stripping and header normalization.
- **`ColumnMapper`**: Flexible header mapping dictionary handling colloquial CSV headers (`grivance_id`, `complainant_address`, `issue_detail`, etc.) while packing unmapped fields into `extra_metadata`.
- **`ComplaintValidator`**: Validates row integrity without hallucination:
  - Enforces uniqueness of complaint reference IDs within the batch.
  - Parses 14 ISO and standard Indian datetime formats (`DD/MM/YYYY`, `YYYY-MM-DD HH:MM:SS`).
  - Enforces modality presence (rejects rows where text, audio, and image are all absent).
- **`IngestionService`**: Idempotently inserts into `raw_complaints`, stages preprocessed records into `triaged_complaints`, and generates a detailed batch summary report (`accepted_count`, `rejected_count`, `skipped_duplicate_count`).
- **`RawComplaint` Model**: Enforces immutability at the ORM layer by raising `ImmutableDataError` on any attempted update or deletion of raw complaint records.

### 3.2 Multimodal Preprocessing Subsystem (`backend/app/services/preprocessing/`)
- **`MultimodalPreprocessor`**: Builds canonical `multimodal_payload` objects preserving metadata for text, audio, and images.
- **Voice Note Handling**: Integrates audio assets (e.g. `data/raw/demo/sample_voice_01.wav`). Ingests audio metadata, stages status (`transcription_status: "pending"` or completed), and extracts audio transcription text into the canonical analysis buffer.
- **Photographic Asset Handling**: Integrates image files (e.g. `data/raw/demo/sample_issue_01.jpg`) and citizen captions. Attaches visual asset URLs, dimensions, and caption metadata for operator inspection with `[DEMO / SYNTHETIC ASSET]` watermarking.
- **Language Detection**: Identifies language code (`hi`, `en`, `hi-Latn`) and marks script representation for downstream processing.

### 3.3 AI Classification & Deterministic Fallback (`backend/app/services/classification/`)
- **`GeminiClassificationClient`**: Integrates Google Gemini API (`gemini-2.5-flash`) using strict Pydantic JSON schema constraints and low temperature (0.1) for deterministic, structured triage recommendations.
- **Taxonomy Injection**: Automatically loads official municipal departments (`config/departments.json`) and categories (`config/categories.json`) into the versioned classification prompt template (`prompts/classification_prompt.txt`).
- **Graceful Deterministic Fallback**: If `GEMINI_API_KEY` is not configured, expired, or rate-limited, the system seamlessly engages the deterministic keyword classification engine without system error or operator disruption.

### 3.4 Urgency Scoring & Deterministic Safety Overrides (`backend/app/rules/`)
- **`UrgencyEngine`**: Calculates transparent 3-component urgency score:
  - Public Safety Impact (0 to 40)
  - Civic Service Outage Scope (0 to 30)
  - Grievance Age & Duration (0 to 30)
  - Normalized Priority: `CRITICAL` (>=0.80), `HIGH` (0.60-0.79), `MEDIUM` (0.40-0.59), `LOW` (<0.40).
- **Deterministic Safety Overrides (`config/urgency_rules.json`)**:
  - `URG_RULE_001`: Exposed live electrical wire, damaged pole, high-voltage transformer spark -> **FORCED CRITICAL** (Urgency Score: 0.95).
  - `URG_RULE_002`: Open manhole, missing storm drain cover -> **FORCED CRITICAL** (Urgency Score: 0.95).
  - Safety overrides are non-negotiable and cannot be downgraded by AI models.

### 3.5 Locality Normalization & Gazetteer (`backend/app/rules/locality_normalizer.py`)
- Resolves colloquial location mentions, colony names, and landmarks against `data/gazetteer/sample_wards_gazetteer.json`.
- Uses deterministic alias dictionary mapping (e.g. *"Bittan Mkt"* -> *"Bittan Market"*, *"MP Ngr"* -> *"Maharana Pratap Nagar"*).
- Normalizes location to Canonical Locality, Ward Number (e.g. `Ward 46`), and Administrative Zone (e.g. `Zone 10 - South Zone`).
- If location cannot be resolved with certainty, marks as `UNKNOWN` rather than hallucinating landmarks.

### 3.6 Explainable Routing Engine (`backend/app/rules/routing_engine.py`)
- Evaluates departmental charters and rule heuristics (`config/routing_rules.json`).
- Outputs auditable `routing_evidence` (matched keywords and category codes), `routing_rule_id`, and human-readable explanation.
- Evaluates confidence threshold tiers:
  - `NORMAL` (>=0.80): High confidence recommendation.
  - `ATTENTION` (0.50-0.79): Moderate confidence; highlighted for operator review.
  - `MANUAL_REVIEW` (<0.50): Low confidence; flagged as mandatory operator inspection.

### 3.7 Incident Clustering & Duplicate Reduction (`backend/app/services/clustering/`)
- **`SimilarityEngine`**: Evaluates 7 weighted similarity signals:
  1. Semantic text similarity (multilingual concept mapping across Hindi and English)
  2. Category match (exact category agreement)
  3. Locality normalization match
  4. Ward alignment
  5. Temporal proximity (decay function over operational window)
  6. Department alignment
  7. Key issue terms overlap
- **False-Positive Prevention Guards**:
  - Distance check: Complaints in different wards cannot be merged unless bordering.
  - Category check: Dissimilar categories (e.g. electrical vs garbage) receive heavy penalties.
- **Connected-Component Graph Clustering (DSU)**:
  - Groups pairwise matches above threshold (>=0.75 duplicate, >=0.55 related incident).
  - Chooses canonical cluster representative deterministically.
  - Computes ticket reduction metrics:
    $$\text{Reduction Percentage} = \frac{N_{\text{raw}} - N_{\text{unique issues}}}{N_{\text{raw}}} \times 100\%$$

### 3.8 Operator Decision Desk & Human-in-the-Loop (`backend/app/services/operator/`)
- **Triage Workbench**: Zone operators inspect incoming complaints filtered by confidence tier, urgency, or department.
- **Granular Field Overrides**: Operators can override department, category, urgency, locality, or summary. AI recommendations remain immutably preserved alongside operator decisions.
- **Mandatory Rationale**: Every override requires a human justification string for auditability.
- **Citizen Acknowledgement Sign-Off**:
  - AI generates bilingual draft acknowledgement referencing ticket ID, department, and SLA expectation.
  - Operator edits or approves draft.
  - System enforces internal boundary: approved acknowledgements remain in `acknowledgements` table with explicit disclaimer that external dispatch gateways are not connected.

### 3.9 Accountability Digest & Analytics Subsystem (`backend/app/services/analytics/`)
- **`WeeklyDigestService`**: Computes departmental workload metrics:
  - Complaints received, resolved, pending, high urgency.
  - Median resolution hours: calculated strictly from complaints with verified `created_at` and `resolved_at` timestamps. Returns `null` when timestamps are absent; zero fabricated SLAs.
  - Top recurring categories and major incident clusters per department.
- **`RepeatLocalityService`**: Aggregates complaint volume by ward and locality to identify recurring infrastructure failure hotspots, cleanly distinguishing multi-report clusters from unique incidents.
- **`EmergingAlertsService`**: Early-warning volume spike heuristic comparing recent 72h volume against baseline historical 72h volume. Triggers surge alerts when multiplier exceeds threshold (e.g. >=2.5x with minimum complaint volume), tagged with prototype heuristic disclaimer.

### 3.10 Held-Out Benchmark Evaluation Subsystem (`backend/app/services/evaluation/`)
- **`EvaluationService`**: Executes formal benchmarking against held-out labelled test dataset (`data/test/benchmark_held_out_30.csv`).
- **Truthful Metrics**: Evaluates model against ground-truth labels without modifying raw or production tables.
- **Outputs**:
  - Multi-class confusion matrix across all 7 municipal departments.
  - Per-class Precision, Recall, and F1 scores.
  - Department routing accuracy, category accuracy, urgency accuracy, locality accuracy, duplicate reduction.
  - Individual misclassification inspector detailing ground truth vs predicted values and text snippets.
  - Prominent `DEMO / SYNTHETIC BENCHMARK` badge and `[PROTOTYPE_ASSUMPTION]` disclaimer.

---

## 4. Security, Isolation & Safety Controls

1. **Zero External Sync**: NagarSetu operates in full network isolation from municipal live databases, citizen WhatsApp gateways, and external social media scrapers.
2. **Air-Gapped Ingestion**: All data enters via static exported CSV/JSON files. No write-back to source portals exists.
3. **Database Immutability**: `RawComplaint` records cannot be updated or deleted via ORM hooks.
4. **Environment Isolation**: API keys, database credentials, and secrets reside strictly in `.env` files (excluded from version control via `.gitignore`).
5. **Human Accountability**: All operator decisions record `operator_id`, timestamp, and reason in an append-only audit trail (`complaint_audits`).
6. **Anti-Fabrication Policy**: Resolution times, benchmark scores, and gazetteer matches are computed from verifiable data or explicitly marked as prototype defaults.
