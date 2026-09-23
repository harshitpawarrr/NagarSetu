# Raw Exported Complaints (Immutable)

This folder contains raw batch export files (e.g., CSV, JSON, XLSX, or media folders) originating from civic channels:
- State CM Helpline exports
- Municipal WhatsApp / Mobile App dumps
- Grievance petitions submitted to elected representatives
- Social media grievance scrapes / mentions

## IMMUTABILITY CONSTRAINT
Files stored in this directory represent original municipal audit records and **MUST NEVER BE MODIFIED, OVERWRITTEN, OR PURGED** by any automated process or agent.
All parsing and cleaning must output new records into `data/processed/` or the database.
