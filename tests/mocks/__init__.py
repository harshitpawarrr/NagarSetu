"""
Test mocks package for NagarSetu.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tests.mocks.mock_gemini import MockGeminiClient

__all__ = ["MockGeminiClient"]
