# NagarSetu Engineering Roadmap (Phases 1 to 6)

This roadmap outlines the disciplined development stages for building NagarSetu into an operator-facing civic complaint triage and accountability engine.

---

## 🧭 Phase Overview

```
Phase 1 (Current): Foundation, Directory Scaffolding & Data Contracts
       ↓
Phase 2: Ingestion Engine, Multimodal Preprocessing & Locality Normalizer
       ↓
Phase 3: AI Classification, Deterministic Urgency Rules & Explainable Routing
       ↓
Phase 4: Operator Decision Desk & Human-in-the-Loop Review Workbench
       ↓
Phase 5: Weekly Departmental Digest, Cluster Analytics & Early-Warning Alerts
       ↓
Phase 6: Held-Out Test Set Evaluation & Hackathon Demo Polish
```

---

## 📌 Phase 1: Foundation, Directory Scaffolding & Data Contracts
**Status**: In Progress / Current Phase
- **Objectives**:
  - Establish repository layout (`frontend/`, `backend/`, `data/`, `config/`, `prompts/`, `tests/`, `docs/`).
  - Formulate persistent operational directives in `AGENTS.md`.
  - Author comprehensive `README.md` and `docs/ROADMAP.md`.
  - Specify canonical complaint schema (`backend/app/schemas/complaint.py`) and TypeScript mirrors (`frontend/src/types/`).
  - Draft placeholder configuration files (`departments.json`, `categories.json`, `urgency_rules.json`, `routing_rules.json`).
  - Author prompt templates and data immutability guards.
- **Exit Criteria**:
  - All folders and initial files created.
  - Test suite validates schema instantiation.
  - Zero application business logic or live API calls executed.

---

## 📌 Phase 2: Ingestion Engine, Multimodal Preprocessing & Locality Normalizer
**Target Capabilities**:
- **Data Loaders**:
  - Read-only parsers for tabular complaint exports (CSV, JSONL, Excel).
  - Multimodal loaders handling audio files (voice notes) and photo attachments with captions.
- **Speech & Image Preprocessing**:
  - Speech transcription abstraction (Whisper / Gemini Multimodal).
  - OCR and image description extraction.
- **Language Detection & Normalization**:
  - FastText / Gemini language detection (handling Hindi, Hinglish, Marathi, and regional variations).
- **Gazetteer Locality Resolver**:
  - Deterministic string distance (fuzzy match + alias lookup) mapping colloquial text to Ward and Zone.
- **Deliverables**:
  - `backend/app/services/ingestion.py`
  - `backend/app/services/multimodal.py`
  - `backend/app/services/locality_normalizer.py`

---

## 📌 Phase 3: AI Classification, Urgency Rules & Explainable Routing
**Target Capabilities**:
- **Gemini Triage Service**:
  - Batch / single complaint classification into Department, Category, and Subcategory using `prompts/classification_prompt.txt`.
- **Deterministic Urgency Rules Engine**:
  - Execution of `config/urgency_rules.json` rules overriding AI predictions for acute public hazards (exposed live wires, open manholes, contaminated water).
- **Explainable Routing Evidence Generator**:
  - Synthesis of `routing_evidence` citing matched keywords, department charter statements, and confidence metrics.
- **Acknowledgement Drafting Engine**:
  - Generation of respectful, bilingual draft acknowledgements awaiting operator sign-off.
- **Deliverables**:
  - `backend/app/services/ai_triage.py`
  - `backend/app/rules/urgency_engine.py`
  - `backend/app/rules/routing_engine.py`
  - `backend/app/services/acknowledgement.py`

---

## 📌 Phase 4: Operator Decision Desk & Human-in-the-Loop Workbench (React UI)
**Target Capabilities**:
- **Operator Inbox & Triage View**:
  - High-density tabular view with sorting, filtering (by Ward, Urgency, Department, Status).
  - Color-coded urgency badges (CRITICAL: Red, HIGH: Amber, MEDIUM: Blue, LOW: Slate).
- **Detailed Complaint Inspection Panel**:
  - Side-by-side view: Raw citizen submission (text/audio/image) vs. AI Structured Recommendation.
  - Explainability card showing routing confidence and citation of matched evidence.
- **Operator Review & Override Flow**:
  - One-click approval of AI recommendation.
  - Department or urgency manual override with required operator notes.
  - Inline editing of draft acknowledgement before marking `OPERATOR_APPROVED`.
- **Deliverables**:
  - `frontend/src/components/OperatorDesk.tsx`
  - `frontend/src/components/TicketDetailModal.tsx`
  - `frontend/src/components/AcknowledgementEditor.tsx`

---

## 📌 Phase 5: Weekly Departmental Digest, Cluster Analytics & Alerts
**Target Capabilities**:
- **Incident Clustering Engine**:
  - Spatial-temporal clustering grouping repeated reports for the same incident (e.g. 15 calls for one burst water main).
  - Duplicate confidence scoring and cluster linking.
- **Weekly Accountability Digest**:
  - Aggregated metrics: complaints received, resolved, pending, median resolution time per department.
  - Repeat complaints by locality table.
- **Emerging Cluster Early-Warning Alerts**:
  - Sudden volume spike detection (>150% in 24 hours in a single ward) alerting zone commissioners.
- **Interactive Recharts Visualizations**:
  - Departmental volume bars, SLA compliance donuts, and cluster distribution charts.
- **Deliverables**:
  - `backend/app/services/clustering.py`
  - `backend/app/services/digest_service.py`
  - `frontend/src/components/WeeklyDigestDashboard.tsx`
  - `frontend/src/components/ClusterAnalytics.tsx`

---

## 📌 Phase 6: Held-Out Test Set Evaluation & Hackathon Demo Polish
**Target Capabilities**:
- **Evaluation Runner**:
  - Automated benchmark harness running against held-out labelled test records in `data/test/`.
  - Computes exact metrics without fabrication:
    - Department routing accuracy
    - Category accuracy
    - Urgency level agreement (quadratic weighted kappa / accuracy)
    - Locality normalization accuracy
    - Duplicate reduction percentage
- **Operator Audit & Demo Scripts**:
  - Pre-packaged demo scenario showcasing multimodal complaints (Hindi voice note, photo of pothole, tweet).
  - End-to-end verification and documentation walkthrough.
- **Deliverables**:
  - `backend/app/services/evaluator.py`
  - `tests/test_evaluation_pipeline.py`
  - `docs/EVALUATION_REPORT.md`
