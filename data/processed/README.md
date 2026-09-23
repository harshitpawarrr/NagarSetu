# Processed Structured Complaints

This directory stores normalized, machine-readable JSON/JSONL datasets output by the NagarSetu ingestion and triage pipeline.

Each record conforms strictly to the canonical complaint schema (`backend/app/schemas/complaint.py`):
- Cleaned and normalized text
- Language code
- Assigned department and category
- Urgency score and deterministic justification
- Resolved ward, zone, and locality
- Assigned cluster ID
- Human-in-the-loop review status
