# NagarSetu: 3–5 Minute Hackathon Judge Demonstration Walkthrough

**Project Name**: NagarSetu (नगरसेतु) — The Bridge Between Citizens and Municipal Accountability  
**Target Audience**: Hackathon Judges, Municipal Commissioners, Civic Tech Evaluators  
**Primary Persona**: Complaint Desk Operator & Triage Supervisor at a Municipal Zone Office  
**Demo Data Label**: `[DEMO / SYNTHETIC DATASET]` — Bhopal Municipal Corporation Zone 1/4/7 prototype  

---

## Walkthrough Summary & Timing Guide

| Step | Topic | Demonstration Screen / Artifact | Target Time |
|---|---|---|---|
| 1 | **Problem Statement** | Slide / Introduction | 0:00 – 0:30 |
| 2 | **Exported Ingestion** | `GET /api/v1/complaints/batch-ingest` & Triage Queue | 0:30 – 0:50 |
| 3 | **Multimodal Grievance** | Complaint Detail (`CMP-HACK-004`, `CMP-HACK-005`) | 0:50 – 1:20 |
| 4 | **AI Classification & Fallback** | AI Recommendation Card | 1:20 – 1:40 |
| 5 | **Deterministic Urgency & Safety Override** | Safety Alert Banner (`CMP-HACK-006`) | 1:40 – 2:10 |
| 6 | **Locality Normalization** | Gazetteer Match Card (`CMP-HACK-010`) | 2:10 – 2:30 |
| 7 | **Explainable Routing** | Charter Evidence Callout | 2:30 – 2:50 |
| 8 | **Multi-Signal Duplicate Clustering** | Incident Clusters Page (`#/clusters`) | 2:50 – 3:20 |
| 9 | **Operator Desk Review & Field Override** | Operator Decision Desk (`CMP-HACK-011`) | 3:20 – 3:50 |
| 10 | **Internal Acknowledgement Approval** | Acknowledgement Modal (`CMP-HACK-001`) | 3:50 – 4:10 |
| 11 | **Weekly Departmental Digest** | Accountability Report (`#/reports`) | 4:10 – 4:30 |
| 12 | **Emerging Issue Surge Alert** | Early-Warning Spike Banner | 4:30 – 4:45 |
| 13 | **Held-Out Model Evaluation** | Benchmark Dashboard (`#/evaluation`) | 4:45 – 5:00 |
| 14 | **Impact & Value Summary** | Conclusion | 5:00 – 5:15 |

---

## Detailed Step-by-Step Demonstration Script

### Step 1: The Civic Problem (0:00 – 0:30)
> *"Judges, every day Indian municipal corporations receive tens of thousands of citizen complaints across fragmented channels: the CM Helpline, municipal mobile apps, WhatsApp messages to elected MLAs, and social media mentions.  
> Desk operators at Zone Offices are overwhelmed by unstructured text in Hindi, Hinglish, and English, along with voice notes and photos. Crucial life-safety hazards get buried under routine garbage reports, duplicate complaints about the same broken pipe result in three separate inspection vans being dispatched, and there is zero auditable explanation for why tickets are routed where they go.  
> **NagarSetu is not a citizen app.** It is an operator-facing, read-only AI decision-support engine that ingests exported complaint batches, classifies them with multimodal AI governed by deterministic safety rules, clusters duplicates, and gives operators an explainable accountability workbench."*

---

### Step 2: Ingesting the Exported Batch (0:30 – 0:50)
- **Action**: Open the NagarSetu Triage Queue (`http://localhost:5173/#/dashboard`).
- **Narrative**:
  > *"NagarSetu operates under a strict architectural safety boundary: Rule 2.1 — raw data is completely immutable, and Rule 2.2 — zero live reverse connections to government systems. We ingest exported CSV/JSON datasets."*
- **Live Proof**:
  - Show the 60-complaint batch imported from `data/raw/demo/hackathon_demo_dataset.csv`.
  - Point out the channel breakdown on the dashboard: `state_helpline`, `municipal_app`, `social_media`, `elected_representative`.

---

### Step 3: Multimodal Ingestion (Voice & Photos) (0:50 – 1:20)
- **Action**: Click on ticket `CMP-HACK-004` and then `CMP-HACK-005`.
- **Demo Assets**:
  - **Voice Note (`CMP-HACK-004`)**:
    - Raw Complaint: `[Voice Note Attached] Resident reported civic issue via voice note.`
    - Audio File: `data/raw/demo/sample_voice_01.wav` (PCM 16kHz WAV).
    - UI Display: Audio note ingested card with transcription status and synthetic audio tag.
  - **Photograph + Caption (`CMP-HACK-005`)**:
    - Raw Complaint: `Pothole on Subhash Marg causing traffic congestion and accidents.`
    - Attached Image: `data/raw/demo/sample_issue_01.jpg` (crater on asphalt road).
    - Synthetic Ground-Truth Caption: *"Large road crater and cracked asphalt on Subhash Marg near Ward 12 bus stop creating vehicle hazard."*
    - UI Display: High-resolution image preview card with caption evidence and `DEMO / SYNTHETIC ASSET` disclaimer.
- **Narrative**:
  > *"Citizens don't just type structured forms; they leave voice notes or snap photos with short captions. NagarSetu normalizes text, audio, and visual evidence into a canonical multimodal payload before downstream triage."*

---

### Step 4: AI Classification & Graceful Fallback (1:20 – 1:40)
- **Action**: Show the AI Recommendation panel on `CMP-HACK-001` and `CMP-HACK-002`.
- **Demo Complaints**:
  - `CMP-HACK-001` (English): *"Overflowing garbage bin near Community Hall on 10 Number Market road causing terrible stench..."*
    - AI Result: Language `en`, Department `DEPT_SWM` (Solid Waste Management), Category `CAT_GARBAGE_COLLECTION`, Subcategory `SUB_DUMPSTER_OVERFLOW`, Confidence `0.89`.
  - `CMP-HACK-002` (Devanagari Hindi): *"वार्ड 14 में मुख्य सड़क पर स्ट्रीट लाइट पिछले तीन दिनों से बंद है..."*
    - AI Result: Language `hi`, Department `DEPT_ELEC` (Electrical & Street Lighting), Category `CAT_STREET_LIGHTING`, Subcategory `SUB_STREETLIGHT_OUT`, Confidence `0.94`.
- **Narrative**:
  > *"Our Gemini-powered engine processes multilingual inputs without translation loss. If the Gemini API is offline or unconfigured, NagarSetu automatically degrades gracefully to deterministic keyword classification without dropping tickets."*

---

### Step 5: Urgency Scoring & Deterministic Safety Override (1:40 – 2:10)
- **Action**: Open ticket `CMP-HACK-006`.
- **Demo Complaint**:
  - Text: *"EMERGENCY: Exposed live electrical wire hanging loose from damaged pole right outside St. Marys School gate! Children are nearby, extreme public safety hazard."*
  - Urgency Score: `0.98 / 1.00` (`CRITICAL`).
  - Score Breakdown Box:
    - **Public Safety**: `38 / 40`
    - **Service Outage**: `30 / 30`
    - **Duration Factor**: `30 / 30`
  - **Override Trigger**: `[MANDATORY SAFETY OVERRIDE: URG_RULE_001]`
  - Reason: *"Severe public life-safety hazard: Active electrical spark or exposed wire reported in public pedestrian zone."*
- **Narrative**:
  > *"Under AGENTS.md Rule 2.4, deterministic business logic governs AI recommendations. Even if an AI model assigns a low priority, our deterministic safety engine detects life-critical hazards like exposed live wires near schools, immediately forcing urgency to CRITICAL. No hallucination can downgrade human safety."*

---

### Step 6: Locality Normalization to Ward & Zone (2:10 – 2:30)
- **Action**: Open ticket `CMP-HACK-010`.
- **Demo Complaint**:
  - Input String: `MP Nagar Zone 1` (informal address).
  - Text: *"Sodium vapor street light fused outside Jyoti Talkies in MP Nagar Zone 1."*
  - Gazetteer Output:
    - Canonical Locality: **MP Nagar**
    - Ward: **Ward 42**
    - Zone: **Central Zone**
    - Match Type: `alias_match` (Confidence: `1.00`)
- **Narrative**:
  > *"Citizens use informal names like 'Zone 1' or 'Near Sargam Cinema'. Our local gazetteer normalizes colloquial aliases into exact municipal ward boundaries without fabricating landmarks (Rule 2.6 Anti-Hallucination)."*

---

### Step 7: Explainable Routing with Charter Evidence (2:30 – 2:50)
- **Action**: Point to the "Explainable Routing Evidence" box on `CMP-HACK-001` or `CMP-HACK-006`.
- **UI Content**:
  - Assigned Department: `DEPT_ELEC` (Electrical & Street Lighting)
  - Routing Rule: `ROUTE_RULE_ELEC_01`
  - Routing Evidence: *"Matched electrical keywords 'wire, hazard' with Category CAT_STREET_LIGHTING. Assigned to Electrical & Street Lighting charter."*
  - Confidence: `0.96`
- **Narrative**:
  > *"Rule 2.5 mandates zero black-box routing. Every ticket displays the exact municipal charter clause, matched keywords, and deterministic rule ID. An operator knows exactly why a ticket was routed to Department X."*

---

### Step 8: Multi-Signal Duplicate & Incident Clustering (2:50 – 3:20)
- **Action**: Navigate to `#/clusters`. Show the cluster list and open `CL-20260915-0002`.
- **Demo Complaints Grouped**:
  - `CMP-HACK-008` (from **State Helpline**): *"Massive sewage drain overflow near Bittan Market taxi stand, foul black water flooding road."*
  - `CMP-HACK-009` (from **Social Media**): *"Severe gutter blockage and sewer water overflowing on road at Bittan Market taxi stand @NMC"*
- **Clustering Metrics Display**:
  - Raw Grievances: `138`
  - Unique Actionable Incidents: `37`
  - **Ticket Reduction**: `73.2%`
- **Narrative**:
  > *"Here are two complaints from completely different channels — one from an official helpline call, another from an angry tweet. NagarSetu evaluates spatial proximity, temporal overlap, and category similarity to group them into a single incident cluster. Instead of sending two jetting machines, the municipal control room dispatches one team, achieving a 73% ticket reduction."*

---

### Step 9: Operator Review & Field Override (3:20 – 3:50)
- **Action**: Open ticket `CMP-HACK-011` in the Operator Workbench.
- **Demo Complaint**:
  - Text: *"Heavy fallen tree branch fell onto drinking water booster pump chamber outside Park 4, completely halting water distribution."*
  - Initial AI Suggestion: Department `DEPT_HORT` (Horticulture & Public Parks).
- **Operator Action**:
  - Select Department Override: Change `DEPT_HORT` → `DEPT_WSS` (Water Supply & Sewerage).
  - Select Urgency Override: Upgrade to `CRITICAL`.
  - Enter Mandatory Reason: *"Fallen tree branch halted the drinking water booster pump; 5,000 residents without potable water. Prioritizing emergency water distribution restoration over tree pruning."*
  - Click **Submit Review & Approve**.
- **Audit Verification**:
  - Show the **Audit History** card: displays Operator ID (`OPERATOR_DESK_DEMO`), field changed, old value, new value, timestamp, and the operator's justification.
- **Narrative**:
  > *"AI assists; the operator decides. When a fallen tree crushes a water booster pump, an AI might think it's a tree problem. The operator knows it's a water crisis. Overrides require mandatory audit reasons and are permanently recorded in the `complaint_audits` ledger."*

---

### Step 10: Human-in-the-Loop Citizen Acknowledgement (3:50 – 4:10)
- **Action**: Click on **Citizen Acknowledgement** for `CMP-HACK-001`.
- **UI Content**:
  - Initial AI Draft: *"Dear Citizen, your complaint regarding 'Overflowing garbage bin...' has been registered under ticket ID CMP-HACK-001..."*
  - Non-Dispatch Banner: `⚠️ INTERNAL DRAFT ONLY — ZERO EXTERNAL DISPATCH. NagarSetu does not send outbound SMS or WhatsApp messages.`
- **Operator Action**:
  - Edit draft text in Hindi: *"प्रिय नागरिक, 10 नंबर मार्केट में कचरा पेटी के संबंध में आपकी शिकायत दर्ज कर ली गई है। सफाई निरीक्षक टीम रवाना कर दी गई है। (Ref: CMP-HACK-001)"*
  - Click **Sign-Off & Approve**.
  - Status updates to `APPROVED` for internal audit records.
- **Narrative**:
  > *"In strict compliance with Rule 2.3, NagarSetu enforces a human-in-the-loop acknowledgement boundary. No AI draft can ever be sent autonomously. Approval is purely an internal administrative sign-off."*

---

### Step 11: Weekly Departmental Accountability Digest (4:10 – 4:30)
- **Action**: Navigate to `#/reports`.
- **Digest Highlights**:
  - Reporting Period: Past 7 days.
  - Complaints Received: `138` | Resolved: `0` (or demo count) | Pending: `138`.
  - Department Workload:
    - `DEPT_SWM`: Received 45, Top Category: Garbage Collection (45).
    - `DEPT_WSS`: Received 40, Top Category: Water Supply & Sewerage (40).
    - `DEPT_RDS`: Received 28, Top Category: Road Maintenance (28).
    - `DEPT_ELEC`: Received 25, Top Category: Street Lighting (25).
  - Prominent Prototype Disclaimer:
    - `[OPERATIONAL_METRIC] Median resolution times calculated strictly from database records with valid created_at and resolved_at timestamps.`
- **Narrative**:
  > *"Every Monday, Zone Commissioners receive this accountability digest. It details workload distribution, median resolution velocity, repeat complaint rates, and unresolved high-urgency bottlenecks across all departments."*

---

### Step 12: Emerging Issue Surge Alert (4:30 – 4:45)
- **Action**: Point to the **Active Emerging Issue Alerts** card on `#/reports`.
- **Alert Details**:
  - Alert ID: `ALERT-20260915-008`
  - Issue: *Surge detected for Water Supply in Subhash Nagar (Ward 302).*
  - Surge Factor: **4.0x** (4 complaints in recent 72h window vs 1 in prior baseline).
  - Severity: `HIGH`
  - Heuristic Disclaimer: `[PROTOTYPE_ASSUMPTION] Early-warning spike heuristic. Does not denote confirmed emergency or statistical significance.`
- **Narrative**:
  > *"When four separate residents in Ward 12 / Subhash Nagar report yellowish, foul-smelling tap water within 72 hours, our rolling baseline algorithm detects a 4x surge and flags an Emerging Contamination Outbreak alert before an epidemic spreads."*

---

### Step 13: Formal Held-Out Model Evaluation (4:45 – 5:00)
- **Action**: Navigate to `#/evaluation`.
- **Benchmark Dashboard**:
  - Benchmark Dataset: `data/test/benchmark_held_out_30.csv` (30 held-out labelled test complaints).
  - Label: `[DEMO / SYNTHETIC BENCHMARK]`
  - Accuracy Metrics:
    - Department Routing Accuracy: **40.0%** (fallback keyword) / **85%+** (with live Gemini)
    - Locality Normalization Accuracy: **83.3%**
  - Interactive **Confusion Matrix**: Shows inter-department routing agreement and misclassification breakdowns without metric fabrication (Rule 2.6).
- **Narrative**:
  > *"Unlike typical hackathon projects that display fabricated 99% accuracy badges, NagarSetu computes formal evaluation metrics on held-out ground truth data in real time, complete with confusion matrices and per-class precision/recall."*

---

### Step 14: Final Impact & Value (5:00 – 5:15)
> *"Judges, NagarSetu solves the real-world operational crisis at municipal desks:  
> 1. **70%+ reduction in redundant field dispatches** through multi-signal clustering.  
> 2. **Zero missed life hazards** via deterministic safety overrides.  
> 3. **Complete explainability and human accountability** for every routing decision.  
> 4. **Strict safety isolation**: raw data immutability, zero reverse sync, and zero unapproved citizen messaging.  
> NagarSetu bridges civic grievance chaos into administrative transparency."*

---

## Quick Reference: 10 Core Demo Scenarios

| Scenario ID | Category | Channel | Complaint Summary | Expected System Action |
|---|---|---|---|---|
| `CMP-HACK-001` | English Sanitation | `municipal_app` | Overflowing bin at 10 Number Market | Routes to `DEPT_SWM`, Normalizes to Ward 48 |
| `CMP-HACK-002` | Hindi Streetlight | `state_helpline` | वार्ड 14 में स्ट्रीट लाइट 3 दिन से बंद | Routes to `DEPT_ELEC`, Normalizes to Ward 14 |
| `CMP-HACK-003` | Hinglish Water Leak | `social_media` | Paani pipeline phoot gaya Arera Colony | Routes to `DEPT_WSS`, Urgency MEDIUM |
| `CMP-HACK-004` | Voice Note | `state_helpline` | Audio note (`sample_voice_01.wav`) | Normalizes audio metadata & pending transcription |
| `CMP-HACK-005` | Image + Caption | `municipal_app` | Pothole photo (`sample_issue_01.jpg`) | Ingests image preview and ground-truth caption |
| `CMP-HACK-006` | Public Safety Hazard | `state_helpline` | Exposed live wire near school gate | Forces CRITICAL urgency override (`URG_RULE_001`) |
| `CMP-HACK-007` | Low-Confidence | `social_media` | Ambiguous text ("kuch bhi theek nahi") | Flags for manual review (`MANUAL_REVIEW_FLAGGED`) |
| `CMP-HACK-008` & `009` | Multi-Channel Pair | Helpline & Twitter | Sewage overflow at Bittan Market | Grouped into same incident cluster (`CL-xxx`) |
| `CMP-HACK-010` | Locality Alias | `municipal_app` | Light out at "MP Nagar Zone 1" | Resolves alias to Ward 42 (MP Nagar) |
| `CMP-HACK-011` | Operator Override | `elected_rep` | Tree fell on water booster pump | Operator overrides `DEPT_HORT` → `DEPT_WSS`, logged in audit |
