"""
CSV Parser for NagarSetu Ingestion.
Reads CSV data from file paths, text streams, or raw bytes with multi-encoding fallback.
"""

import csv
import io
from typing import List, Dict, Tuple, Union
from pathlib import Path


class CSVParser:
    """
    Parses CSV content safely with encoding auto-detection and blank row skipping.
    """

    SUPPORTED_ENCODINGS = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]

    @classmethod
    def parse_bytes(cls, content_bytes: bytes) -> Tuple[List[Dict[str, str]], List[str]]:
        """
        Decodes bytes using supported encodings and parses CSV rows.
        Returns (rows, warnings).
        """
        warnings: List[str] = []
        text_content = None

        for encoding in cls.SUPPORTED_ENCODINGS:
            try:
                text_content = content_bytes.decode(encoding)
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if text_content is None:
            # Fallback with replacement
            text_content = content_bytes.decode("utf-8", errors="replace")
            warnings.append("CSV decoding encountered invalid bytes; replaced with standard replacement characters.")

        return cls.parse_string(text_content)

    @classmethod
    def parse_string(cls, text: str) -> Tuple[List[Dict[str, str]], List[str]]:
        """
        Parses a string of CSV content into a list of row dictionaries.
        """
        warnings: List[str] = []
        f = io.StringIO(text.strip())
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            warnings.append("CSV file appears empty or has no header row.")
            return [], warnings

        rows: List[Dict[str, str]] = []
        for idx, row in enumerate(reader, start=1):
            # Check if row is completely empty
            if not any(v.strip() for v in row.values() if v is not None):
                continue
            rows.append(row)

        return rows, warnings

    @classmethod
    def parse_file(cls, file_path: Union[str, Path]) -> Tuple[List[Dict[str, str]], List[str]]:
        """
        Reads and parses a CSV file from disk.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        raw_bytes = path.read_bytes()
        return cls.parse_bytes(raw_bytes)
