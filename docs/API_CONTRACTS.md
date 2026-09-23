# NagarSetu REST API Specification & Contracts

Base URL: `http://localhost:8000`
API Prefix: `/api/v1`

All responses are formatted in JSON. Timestamps follow ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`).
All operations strictly respect raw data immutability and internal non-dispatch boundaries.

---

## 0. System Health & Status Endpoints

### `GET /health`
Comprehensive system readiness and health check. Verifies database connectivity, AI service configuration (or fallback mode), existence of core configuration files, and presence of all 11 relational database tables without exposing API keys or credentials.

- **Response**: `200 OK`
  ```json
  {
    "status": "healthy",
    "service": "nagarsetu-backend",
    "version": "0.6.0",
    "phase": "Phase 6 / Final Release QA",
    "checks": {
      "database": "healthy",
      "ai_configuration": "configured",
      "configuration_files": "all_present",
      "database_tables": "all_present"
    },
    "details": {
      "ai_service": {
        "model_version": "gemini-2.5-flash",
        "prompt_version": "classification_v1.0",
        "mode": "Live Gemini API"
      },
      "tables_verified": 11
    },
    "scope": "Operator-facing read-only municipal triage engine"
  }
  ```

### `GET /api/v1/status`
API V1 operational status and primary endpoint directory.

- **Response**: `200 OK`
  ```json
  {
    "status": "operational",
    "active_phase": "Phase 6: Complete Pipeline, Digests & Evaluation",
    "endpoints": [
      "/api/v1/complaints",
      "/api/v1/complaints/batch-ingest",
      "/api/v1/clusters",
      "/api/v1/clusters/detect",
      "/api/v1/analytics/weekly-digest",
      "/api/v1/analytics/repeat-localities",
      "/api/v1/analytics/emerging-alerts",
      "/api/v1/eval/benchmark"
    ]
  }
  ```

---

## 1. Ingestion Endpoints

### `POST /api/v1/complaints/batch-ingest`
Ingests an exported CSV file of raw complaint records via `multipart/form-data`. Idempotently registers records in `raw_complaints` (skipping existing complaint IDs), maps disparate columns, extracts unmapped metadata, and stages triaged complaint tickets in `PREPROCESSED` state.

- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file` (required): Exported CSV file (supports UTF-8, UTF-8-SIG, Latin-1 encoding).
  - `source_name` (optional): Identifier for the export batch file (defaults to filename).
- **Response**: `200 OK` -> `BatchIngestSummaryResponse`
  ```json
  {
    "batch_source_name": "hackathon_demo_dataset.csv",
    "total_rows_processed": 60,
    "accepted_count": 58,
    "rejected_count": 1,
    "skipped_duplicate_count": 1,
    "accepted_ids": ["CMP-HACK-001", "CMP-HACK-002", "CMP-HACK-003"],
    "rejected_rows": [
      {
        "row_number": 59,
        "complaint_id": "CMP-ERR-001",
        "reason": "Complaint contains no usable content: text, audio, and image are all missing or empty."
      }
    ]
  }
  ```

### `POST /api/v1/complaints/batch-ingest-json`
Ingests a structured JSON payload of complaint records into the raw staging and preprocessing queue.

- **Content-Type**: `application/json`
- **Request Body**: `BatchIngestRequest`
  ```json
  {
    "batch_source_name": "CM_Helpline_Export_2026_09_15.json",
    "items": [
      {
        "source_reference_id": "HELPLINE-88219",
        "original_channel": "state_helpline",
        "raw_text": "Shivaji Nagar main road ke paas open manhole cover gayab hai, bacha gir sakta hai.",
        "reported_at": "2026-09-15T09:30:00Z",
        "raw_locality_hint": "Shivaji Nagar"
      }
    ]
  }
  ```
- **Response**: `200 OK` -> `BatchIngestSummaryResponse`

---

## 2. Complaint Triage & Review Endpoints

### `GET /api/v1/complaints`
Returns a paginated list of canonical complaints matching optional filter criteria.

- **Query Parameters**:
  - `department` (optional string): e.g. `DEPT_SWM`
  - `urgency` (optional enum): `CRITICAL` | `HIGH` | `MEDIUM` | `LOW`
  - `status` (optional enum): `OPERATOR_REVIEW_PENDING` | `OPERATOR_APPROVED`
  - `ward` (optional string): e.g. `Ward 46`
  - `zone` (optional string): e.g. `Zone 10`
  - `cluster_id` (optional string)
  - `search_query` (optional string)
  - `page` (default: 1)
  - `page_size` (default: 25, max: 100)

- **Response**: `200 OK` -> `PaginatedComplaintList`

### `GET /api/v1/complaints/{complaint_id}`
Retrieves full details of an individual complaint ticket including routing evidence, multimodal attachments, and draft citizen acknowledgement.

- **Response**: `200 OK` -> `CanonicalComplaint`

### `POST /api/v1/complaints/{complaint_id}/process`
Executes the full automated triage pipeline on a raw or preprocessed complaint:
1. Multimodal payload extraction (text, voice note transcription, photo OCR/caption)
2. Gemini AI classification & taxonomy validation against official municipal catalog
3. Locality normalization against gazetteer index
4. Deterministic urgency scoring with mandatory safety overrides (`URG_RULE_001`, `URG_RULE_002`)
5. Explainable routing recommendation with evidence keywords and rule ID
6. Operator review flag assignment (<0.50 triggers manual review)
7. Derived ticket persistence and status history logging

- **Response**: `200 OK` -> `ComplaintTriageResponse`
  ```json
  {
    "complaint_id": "CMP-HACK-001",
    "original_channel": "municipal_app",
    "original_text": "MP Nagar Zone-II mein 4 din se street light band hai, raat ko safety issue ho raha hai.",
    "processing_status": "OPERATOR_REVIEW_PENDING",
    "language": "hi-Latn",
    "summary": "Street lights reported non-functional in MP Nagar for 4 days.",
    "department": "DEPT_ELEC",
    "category": "CAT_STREET_LIGHTING",
    "subcategory": "SUB_STREETLIGHT_OUT",
    "urgency": "MEDIUM",
    "urgency_score": 0.45,
    "urgency_reason": "Evaluated priority score 45/100 (Safety: 22/40, Outage: 5/30, Duration: 18/30).",
    "normalized_locality": "MP Nagar",
    "ward": "Ward 42",
    "zone": "Central Zone",
    "routing_evidence": "streetlight, light not working, CAT_STREET_LIGHTING",
    "routing_confidence": 0.92,
    "acknowledgement_draft": "Dear Citizen, your grievance regarding 'Street lights non-functional' in MP Nagar has been registered under Ticket #CMP-HACK-001. It has been prioritized as MEDIUM and assigned to Electrical & Street Lighting. [DRAFT - Pending Operator Approval]",
    "triage_audit": {
      "classification": {
        "language": "hi-Latn",
        "summary": "Street lights reported non-functional in MP Nagar for 4 days.",
        "department": "DEPT_ELEC",
        "category": "CAT_STREET_LIGHTING",
        "subcategory": "SUB_STREETLIGHT_OUT",
        "routing_terms": ["street light", "band hai", "4 din"],
        "confidence": 0.94
      },
      "urgency_breakdown": {
        "urgency": "MEDIUM",
        "urgency_score": 0.45,
        "safety_score": 22,
        "outage_score": 5,
        "duration_score": 18,
        "urgency_reason": "Evaluated priority score 45/100 (Safety: 22/40, Outage: 5/30, Duration: 18/30).",
        "urgency_evidence": ["4 din", "street light"],
        "safety_override_applied": false,
        "safety_override_rule_id": null
      },
      "locality": {
        "canonical_locality": "MP Nagar",
        "ward": "Ward 42",
        "zone": "Central Zone",
        "match_type": "alias_match",
        "confidence": 1.0
      },
      "routing": {
        "recommended_department": "DEPT_ELEC",
        "routing_confidence": 0.92,
        "routing_evidence": ["streetlight", "CAT_STREET_LIGHTING"],
        "routing_rule_id": "ROUTE_RULE_ELEC_01",
        "routing_explanation": "Matched electrical keywords 'streetlight' with Category CAT_STREET_LIGHTING. Assigned to Electrical & Street Lighting charter."
      },
      "review_flags": {
        "requires_manual_review": false,
        "review_flagged": false,
        "review_reason": "Standard high-confidence triage recommendation.",
        "confidence_tier": "NORMAL"
      },
      "model_version": "gemini-2.5-flash",
      "prompt_version": "classification_v1.0",
      "processed_at": "2026-09-15T13:16:00Z"
    },
    "processed_at": "2026-09-15T13:16:00Z"
  }
  ```

### `GET /api/v1/complaints/{complaint_id}/triage`
Retrieves the full triage audit details for an already-processed complaint ticket.

- **Response**: `200 OK` -> `ComplaintTriageResponse`

### `POST /api/v1/complaints/{complaint_id}/reprocess`
Forces re-execution of the triage pipeline (e.g. after rule or prompt updates).

- **Response**: `200 OK` -> `ComplaintTriageResponse`

### `GET /api/v1/config/departments`
Retrieves the official municipal department registry, codes, escalation contacts, and keywords.

- **Response**: `200 OK` -> JSON list of departments

### `GET /api/v1/config/categories`
Retrieves the official category and subcategory taxonomy with department linkages and typical SLAs.

- **Response**: `200 OK` -> JSON list of categories

### `POST /api/v1/complaints/{complaint_id}/review`
Executes operator review, approval, or granular field overrides (department, category, urgency, locality, ward, summary).
- **Request Body**: `OperatorReviewRequest`
  ```json
  {
    "action": "override",
    "department": "DEPT_WSS",
    "urgency": "CRITICAL",
    "reason": "Water pipe rupture causing road collapse; escalated.",
    "operator_id": "OP_DESK_42"
  }
  ```
- **Response**: `200 OK` -> `OperatorReviewResponse`

### `GET /api/v1/complaints/{complaint_id}/audit`
Retrieves chronological audit trail of operator reviews and overrides.
- **Response**: `200 OK` -> `List[AuditEntryResponse]`

### `GET /api/v1/complaints/{complaint_id}/acknowledgement`
Retrieves draft citizen acknowledgement.
- **Response**: `200 OK` -> `AcknowledgementResponse`

### `PUT /api/v1/complaints/{complaint_id}/acknowledgement`
Operator edits citizen acknowledgement draft.
- **Request Body**: `AcknowledgementEditRequest`
- **Response**: `200 OK` -> `AcknowledgementResponse`

### `POST /api/v1/complaints/{complaint_id}/acknowledgement/approve`
Operator signs off on citizen acknowledgement draft (strictly internal state transition; zero external SMS/email dispatch).
- **Request Body**: `AcknowledgementApproveRequest`
- **Response**: `200 OK` -> `AcknowledgementResponse`

---

## 3. Incident Clustering & Duplicate Endpoints

### `POST /api/v1/clusters/detect`
Executes multi-signal duplicate and incident cluster detection across triaged complaints.
- **Request Body**: `ClusterDetectionRequest` (`recluster`, `threshold_duplicate`, `threshold_related`, `department`, `ward`)
- **Response**: `200 OK` -> `ClusterDetectionResponse` (clusters created, total clustered, reduction analytics)

### `GET /api/v1/clusters`
Lists active incident clusters, member counts, and dataset-wide reduction analytics.
- **Query Parameters**: `limit`, `offset`, `department`, `ward`, `is_active`
- **Response**: `200 OK` -> `ClusterListResponse`

### `GET /api/v1/clusters/{cluster_id}`
Retrieves detailed cluster information and all linked member complaints with similarity breakdown.
- **Response**: `200 OK` -> `ClusterDetailResponse`

### `POST /api/v1/clusters/{cluster_id}/review`
Executes operator action on a cluster (`confirm`, `remove_member`, `add_notes`).
- **Request Body**: `ClusterReviewRequest`
- **Response**: `200 OK` -> `ClusterReviewResponse`

---

## 4. Weekly Digest, Locality Repeats & Emerging Alerts Endpoints

### `GET /api/v1/analytics/weekly-digest`
Computes weekly departmental accountability report across all municipal departments. Computes median resolution times strictly from records with valid `created_at` and `resolved_at` timestamps (returns `null` if none exist).

- **Query Parameters**:
  - `days_back` (optional int, default 7)
  - `start_date` (optional YYYY-MM-DD)
  - `end_date` (optional YYYY-MM-DD)
- **Response**: `200 OK` -> `WeeklyDigestResponse`
  ```json
  {
    "report_period_start": "2026-09-08",
    "report_period_end": "2026-09-15",
    "overall_received": 78,
    "overall_resolved": 0,
    "overall_pending": 78,
    "overall_median_resolution_hours": null,
    "departments": [
      {
        "department": "DEPT_ROADS",
        "department_name": "Roads & Infrastructure",
        "complaints_received": 14,
        "complaints_resolved": 0,
        "complaints_pending": 14,
        "median_resolution_hours": null,
        "repeat_complaints": 2,
        "top_categories": [{"category": "CAT_POTHOLE", "count": 7}],
        "major_clusters": [],
        "high_urgency_unresolved": 6
      }
    ],
    "operational_summary": "Weekly Accountability Digest: 78 complaints received...",
    "disclaimer": "[OPERATIONAL_METRIC] Median resolution times calculated strictly from database records with valid created_at and resolved_at timestamps."
  }
  ```

### `GET /api/v1/analytics/departments/{department_id}`
Retrieves workload, resolution times, and top issues for a specific municipal department.
- **Response**: `200 OK` -> `DepartmentWeeklySummary`

### `GET /api/v1/analytics/repeat-localities` (Alias: `/api/v1/analytics/localities`)
Aggregates repeat complaints by ward and locality, distinguishing unique issues from repeated reports.
- **Query Parameters**: `department`, `ward`, `locality`, `days_back`
- **Response**: `200 OK` -> `LocalityRepeatResponse`

### `GET /api/v1/analytics/emerging-alerts`
Early-warning volume surge detection comparing recent complaint volume (default 72h) against baseline historical volume (default 72h).
- **Query Parameters**: `department`, `ward`, `min_recent`, `spike_multiplier`
- **Response**: `200 OK` -> `EmergingAlertsResponse`
  ```json
  {
    "alerts": [
      {
        "alert_id": "ALERT-WSS-101",
        "department": "DEPT_WATER",
        "locality": "Shivaji Nagar",
        "ward": "Ward 101",
        "baseline_count": 1,
        "recent_count": 4,
        "spike_multiplier": 4.0,
        "trigger_explanation": "Surge detected: 4 recent complaints vs 1 baseline (4.0x increase)",
        "heuristic_disclaimer": "[PROTOTYPE_ASSUMPTION] Early-warning spike heuristic. Does not denote confirmed emergency or statistical significance."
      }
    ],
    "total_alerts": 1,
    "evaluation_timestamp": "2026-09-15T09:30:00Z"
  }
  ```

---

## 5. Model Evaluation & Benchmark Endpoints

### `POST /api/v1/eval/benchmark` (Alias: `/api/v1/eval/run`)
Executes formal benchmark evaluation against a held-out labelled test set (`data/test/benchmark_held_out_30.csv`).
Never mutates raw complaint tables.
Computes multi-class confusion matrix, precision/recall, and stores individual misclassifications.

- **Request Body**: `EvaluationRunRequest`
  ```json
  {
    "test_set_file": "benchmark_held_out_30.csv",
    "test_set_version": "v1.0-synthetic",
    "is_synthetic": true,
    "notes": "Weekly model validation"
  }
  ```
- **Response**: `200 OK` -> `EvaluationResultResponse`
  ```json
  {
    "id": 1,
    "test_set_version": "v1.0-synthetic",
    "total_samples": 30,
    "department_accuracy": 0.40,
    "category_accuracy": 0.40,
    "urgency_accuracy": 0.5333,
    "locality_normalization_accuracy": 0.70,
    "duplicate_reduction": 36.67,
    "confusion_matrix": {
      "classes": ["DEPT_RDS", "DEPT_WSS", "DEPT_ELEC", "DEPT_SWM", "DEPT_HORT", "DEPT_PH", "DEPT_TOWN"],
      "matrix": [[2, 0, 0, 2, 0, 0, 0], [0, 4, 0, 5, 0, 0, 0]],
      "normalized_matrix": [[0.5, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0]],
      "per_class": {
        "DEPT_RDS": {"precision": 0.667, "recall": 0.5, "f1": 0.571, "support": 4}
      }
    },
    "incorrect_predictions": [
      {
        "complaint_id": "CMP-TEST-001",
        "field": "urgency",
        "ground_truth": "MEDIUM",
        "predicted": "LOW",
        "confidence": 0.19,
        "text_snippet": "Large pothole outside City School main gate in MP Nagar"
      }
    ],
    "is_synthetic_benchmark": true,
    "benchmark_badge": "DEMO / SYNTHETIC BENCHMARK",
    "disclaimer": "[PROTOTYPE_ASSUMPTION] Metrics computed strictly against held-out labelled records. Not an official municipal accuracy claim."
  }
  ```

### `GET /api/v1/eval/latest`
Retrieves the most recent held-out evaluation benchmark run result.
- **Response**: `200 OK` -> `EvaluationResultResponse`

### `GET /api/v1/eval/history`
Retrieves history of evaluation benchmark runs.
- **Query Parameters**: `limit` (default: 20)
- **Response**: `200 OK` -> `EvaluationHistoryResponse`
