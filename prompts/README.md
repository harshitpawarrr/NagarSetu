# Governed LLM Prompts for NagarSetu

This directory houses governed system and task prompts used by the Gemini AI triage pipeline (`gemini-2.5-flash`).

## Prompt Inventory & Versions

- `classification_prompt.txt` (`classification_v1.0`):
  - Ingests multimodal complaint records across English, Devanagari Hindi, and Hinglish.
  - Dynamically binds official municipal taxonomy from `config/departments.json` and `config/categories.json`.
  - Produces structured JSON conforming to `AIClassificationResult`.
  - Enforces strict anti-hallucination rules: never invents missing wards, contact details, durations, or safety facts.
- `urgency_prompt.txt` (`urgency_v1.0`):
  - Evaluates public safety risk (0-40), service outage scale (0-30), and problem duration (0-30).
  - Subject to deterministic safety overrides from `config/urgency_rules.json` that AI cannot downgrade.
- `acknowledgement_prompt.txt`:
  - Drafts empathetic citizen responses in English and Indic languages for human operator approval prior to dispatch.

## Engineering Rules for Prompts
1. **Strict JSON Schema**: All prompts enforce machine-parseable JSON responses validating against Pydantic models.
2. **Deterministic Governance**: AI suggestions are strictly validated against `config/` rule files; safety rules override AI scores whenever severe hazards are detected.
3. **No Fabrication (Anti-Hallucination)**: If information is not in the source text, prompts mandate returning `null` or an explicit unknown state.
4. **Human-in-the-Loop**: Draft acknowledgements are generated as proposals and cannot be dispatched autonomously.
