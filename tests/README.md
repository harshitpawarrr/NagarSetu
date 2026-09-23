# NagarSetu Test Suite

This directory contains automated unit and contract tests verifying schemas, rule engines, and API models.

## Running Tests
Run from project root or backend folder:
```bash
python -m pytest tests -v
```
or
```bash
cd backend
python -m pytest ../tests -v
```

## Test Structure
- `conftest.py`: Shared pytest fixtures and sys.path setup.
- `test_schemas.py`: Verifies canonical complaint schema integrity, enum validation, bounding checks, and configuration file validity.
