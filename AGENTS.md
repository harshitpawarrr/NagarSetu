# AGENTS.md — Persistent Engineering & Operational Rules for NagarSetu

This document specifies immutable operating constraints, scope boundaries, and development principles for any AI agent or human contributor working on the **NagarSetu** project.

---

## 1. Core Purpose & User Persona

- **System Purpose**: NagarSetu is an operator-facing, read-only AI civic complaint triage and accountability engine designed to process exported municipal complaint datasets.
- **Primary User Persona**: Complaint desk operator or triage supervisor situated at a municipal Zone Office.
- **Explicit Anti-Goal**: NagarSetu is **NOT** a citizen-facing mobile app or public complaint submission portal. It is an administrative decision-support workbench.

---

## 2. Hard Architectural & Safety Constraints

### Rule 2.1: Read-Only & Immutability of Source Data
- All operations over the raw imported dataset (`data/raw/`) are **strictly read-only**.
- The raw imported dataset is immutable. Under no circumstance should scripts, workers, or transformations modify, overwrite, truncate, or delete raw input files.
- Processed artefacts must be persisted separately into `data/processed/` or the application database.

### Rule 2.2: Absolute Isolation from Production & Government Systems
- **Zero Live Connectors**: Never attempt or configure live network connections to government helplines, CM/State helpline endpoints, municipal ERPs (e.g. e-Nagarpalika), or live social media APIs.
- **No Reverse Sync**: Never write, push, or sync data back to original source systems. All actions are self-contained within NagarSetu.

### Rule 2.3: Human-in-the-Loop Acknowledgement Dispatch
- AI models generate *draft* acknowledgements only.
- **No autonomous dispatch**: An acknowledgement message draft can **never** be marked as sent or dispatched without explicit approval/confirmation from the human operator.
- The UI and API contracts must enforce human review workflows (`OPERATOR_REVIEW_PENDING` -> `OPERATOR_APPROVED`).

### Rule 2.4: Deterministic Validation Governs AI Recommendations
- AI models propose:
  - Department routing
  - Urgency categorization
  - Locality / ward resolution
- **Deterministic business logic validates**:
  - AI outputs must pass deterministic schema and boundary validation against official configuration files (`config/departments.json`, `config/urgency_rules.json`, `config/routing_rules.json`, `data/gazetteer/`).
  - If AI confidence falls below configured operational thresholds or contradicts deterministic rules (e.g. hazard detection rule marked critical), deterministic logic overrides or flags the ticket for high-priority operator review.

### Rule 2.5: Explainability at Individual Ticket Level
- Every routing and urgency recommendation must carry clear, auditable evidence:
  - `routing_evidence`: Keywords, matched department charter clauses, or rule IDs justifying why the ticket was routed to Department X.
  - `routing_confidence`: Numerical confidence score (0.0 to 1.0).
  - `urgency_reason`: Deterministic trigger (e.g. "Public safety hazard: exposed live wire detected near school") or structured rationale.
- Black-box decisions with no evidence string are strictly disallowed.

### Rule 2.6: Anti-Hallucination & Truthfulness Directive
- **Never invent missing information**: If a complaint lacks a clear locality, phone number, ward, or timestamp, mark it as `UNKNOWN` or `UNSPECIFIED`. Never fabricate geographic landmarks or citizen identities.
- **No fabricated municipal regulations or SLAs**: Use only the explicit rules defined in the `config/` directory. If an SLA is not defined, mark it as unassigned or prototype-default with an explicit disclaimer.
- **No fabricated evaluation results**: All benchmark metrics (accuracy, agreement, duplicate reduction) must be computed directly against ground-truth held-out data (`data/test/`). Never generate fake metrics.
- **Separation of Prototype Assumptions**: Prototype assumptions (such as synthetic gazetteer boundaries or sample SLA days) must be cleanly tagged as `[PROTOTYPE_ASSUMPTION]` and separated from verified municipal data.

---

## 3. Technology Stack Boundaries

- **Frontend**: React (v18+) with TypeScript, Vite build tool, Tailwind CSS for styling, Recharts for data visualization, Lucide React for iconography.
- **Backend**: FastAPI (Python 3.10+), Pydantic v2 for data contracts and validation, Uvicorn as ASGI server.
- **Database**: PostgreSQL with async driver (SQLAlchemy / asyncpg).
- **AI / LLM**: Google Gemini API via official SDK (`google-genai` / `google-generativeai`).
- **Dependency Philosophy**: Keep dependencies lean, robust, and necessary. Do not add bloated or unmaintained libraries.

---

## 4. Canonical Pipeline Order

Every complaint record must strictly traverse these pipeline phases:
```
Raw Export Ingestion
  ↓
Multimodal Preprocessing (Text, Audio transcription, Image+Caption)
  ↓
Language Handling (Detection & Normalization)
  ↓
Classification (Department, Category, Subcategory)
  ↓
Urgency Scoring (AI Recommendation + Deterministic Safety Rules)
  ↓
Locality Normalization (Gazetteer Ward/Zone Match)
  ↓
Duplicate / Cluster Detection
  ↓
Routing Recommendation (with Explainability Evidence & Confidence)
  ↓
Structured Ticket Construction
  ↓
Operator Review & Human-in-the-Loop Workbench
  ↓
Acknowledgement Drafting & Approval
  ↓
Weekly Departmental Digest & Held-Out Test Evaluation
```

---

## 5. Development Guidelines for Future Phases

1. **Phase Discipline**: Only implement features assigned to the currently approved development phase.
2. **Schema Integrity**: Any change to `backend/app/schemas/complaint.py` must be mirrored in `frontend/src/types/complaint.ts`.
3. **Graceful Degradation**: If Gemini API is unreachable or rate-limited, the system must fall back to deterministic keyword routing with a low-confidence tag, allowing operators to manually triage without system failure.
4. **Comprehensive Test Coverage**: All schema validations, deterministic rule checks, and data parsers must have accompanying unit tests in `tests/`.
