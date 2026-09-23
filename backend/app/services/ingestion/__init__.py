"""
Ingestion package for NagarSetu.
Provides CSV parsing, column mapping, validation, and batch ingestion orchestration.
"""

from app.services.ingestion.column_mapper import ColumnMapper, normalize_channel
from app.services.ingestion.validator import IngestionValidator, ValidationResult
from app.services.ingestion.csv_parser import CSVParser
from app.services.ingestion.ingestion_service import IngestionService

__all__ = [
    "ColumnMapper",
    "normalize_channel",
    "IngestionValidator",
    "ValidationResult",
    "CSVParser",
    "IngestionService",
]
