"""
Unit and Integration Tests for NagarSetu Phase 3 Ingestion and Multimodal Preprocessing.
Verifies column mapping, validation, multimodal staging, immutability, idempotency,
and REST API endpoints.
"""

import sys
import unittest
import io
from pathlib import Path

# Bootstrap backend directory
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import get_db
from app.db.init_db import create_tables
from app.models.complaint import RawComplaint, TriagedComplaint, ImmutableDataError
from app.services.ingestion.column_mapper import ColumnMapper, normalize_channel
from app.services.ingestion.validator import IngestionValidator
from app.services.ingestion.csv_parser import CSVParser
from app.services.ingestion.ingestion_service import IngestionService
from app.services.preprocessing.multimodal import MultimodalPreprocessor
from scripts.seed_data import seed_departments, seed_categories, seed_gazetteer

TEST_DB_PATH = ROOT_DIR / "data" / "test_ingestion.db"
test_engine = create_engine(f"sqlite:///{TEST_DB_PATH}", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestIngestionAndPreprocessing(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if TEST_DB_PATH.exists():
            try:
                TEST_DB_PATH.unlink()
            except Exception:
                pass

        create_tables(bind_engine=test_engine)
        seed_db = TestSessionLocal()
        try:
            dept_map = seed_departments(seed_db)
            seed_categories(seed_db, dept_map)
            seed_gazetteer(seed_db)
        finally:
            seed_db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        test_engine.dispose()
        if TEST_DB_PATH.exists():
            try:
                TEST_DB_PATH.unlink()
            except Exception:
                pass

    def setUp(self):
        self.db = TestSessionLocal()

    def tearDown(self):
        try:
            self.db.rollback()
        except Exception:
            pass
        self.db.close()

    def test_01_channel_normalization(self):
        """Test channel name normalization for various colloquial and case-varied inputs."""
        self.assertEqual(normalize_channel("CM Helpline"), "state_helpline")
        self.assertEqual(normalize_channel("cm_helpline"), "state_helpline")
        self.assertEqual(normalize_channel("181"), "state_helpline")
        self.assertEqual(normalize_channel("Municipal App"), "municipal_app")
        self.assertEqual(normalize_channel("mobile_app"), "municipal_app")
        self.assertEqual(normalize_channel("Twitter"), "social_media")
        self.assertEqual(normalize_channel("Social Media"), "social_media")
        self.assertEqual(normalize_channel("MLA"), "elected_rep_message")
        self.assertEqual(normalize_channel("Corporator Message"), "elected_rep_message")
        self.assertEqual(normalize_channel("walk-in"), "walk_in_petition")
        self.assertEqual(normalize_channel(None), "state_helpline")

    def test_02_column_mapper_variations_and_unknown_columns(self):
        """Test column mapper header variation resolution and unknown column preservation."""
        mapper = ColumnMapper()
        raw_row = {
            "Ticket_Number": "TKT-991",
            "Reported_At": "2026-09-15 14:00:00",
            "Source": "CM Helpline",
            "Grievance": "Overflowing drain in MP Nagar",
            "Photo_URL": "data/raw/images/drain.jpg",
            "Area": "MP Nagar",
            "Custom_Operator_Tag": "Urgent attention",
            "Ward_Supervisor": "Mr. Sharma"
        }
        canonical, metadata = mapper.map_row(raw_row)

        self.assertEqual(canonical["complaint_id"], "TKT-991")
        self.assertEqual(canonical["channel"], "state_helpline")
        self.assertEqual(canonical["text"], "Overflowing drain in MP Nagar")
        self.assertEqual(canonical["image_path"], "data/raw/images/drain.jpg")
        self.assertEqual(canonical["source_location"], "MP Nagar")

        # Verify unmapped columns are preserved in metadata
        self.assertIn("Custom_Operator_Tag", metadata)
        self.assertEqual(metadata["Custom_Operator_Tag"], "Urgent attention")
        self.assertIn("Ward_Supervisor", metadata)
        self.assertEqual(metadata["Ward_Supervisor"], "Mr. Sharma")

    def test_03_validator_missing_id_and_duplicate_batch(self):
        """Test validator rejects rows without ID or with duplicate IDs within import."""
        validator = IngestionValidator()

        # Missing ID
        res_no_id = validator.validate_row(1, {"complaint_id": "", "text": "Some text"})
        self.assertFalse(res_no_id.is_valid)
        self.assertIn("Missing mandatory complaint ID", res_no_id.rejection_reason)

        # Valid row
        res_valid = validator.validate_row(2, {"complaint_id": "CMP-T1", "text": "Valid issue"})
        self.assertTrue(res_valid.is_valid)

        # Duplicate ID in same batch
        res_dup = validator.validate_row(3, {"complaint_id": "CMP-T1", "text": "Duplicate issue"})
        self.assertFalse(res_dup.is_valid)
        self.assertIn("Duplicate complaint ID", res_dup.rejection_reason)

    def test_04_validator_missing_all_content_rejected(self):
        """Test validator rejects rows missing text, audio, and image."""
        validator = IngestionValidator()
        row = {
            "complaint_id": "CMP-EMPTY",
            "text": None,
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": "MP Nagar"
        }
        res = validator.validate_row(1, row)
        self.assertFalse(res.is_valid)
        self.assertIn("Missing all complaint content", res.rejection_reason)

    def test_05_validator_single_modality_accepted(self):
        """Test voice-only and image-only complaints are accepted without text."""
        validator = IngestionValidator()

        # Voice-only
        v_res = validator.validate_row(1, {"complaint_id": "V-01", "audio_path": "sample.mp3"})
        self.assertTrue(v_res.is_valid)

        # Image caption-only
        i_res = validator.validate_row(2, {"complaint_id": "I-01", "image_caption": "Broken road"})
        self.assertTrue(i_res.is_valid)

    def test_06_csv_parser_decoding_and_blank_rows(self):
        """Test CSV parser handles trailing whitespace and blank lines cleanly."""
        csv_text = """id,complaint,channel
CMP-CSV-01,Water pipe broken,municipal_app

CMP-CSV-02,Streetlight flickering,social_media
  ,  ,  
"""
        rows, warnings = CSVParser.parse_string(csv_text)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["id"], "CMP-CSV-01")
        self.assertEqual(rows[1]["id"], "CMP-CSV-02")

    def test_07_multimodal_preprocessor_classification(self):
        """Test preprocessing produces canonical multimodal payload with pending status."""
        data_voice = {
            "complaint_id": "V-100",
            "text": None,
            "audio_path": "audio/clip.mp3",
            "image_path": None,
            "image_caption": None
        }
        payload_v, cat_v = MultimodalPreprocessor.preprocess(data_voice)
        self.assertEqual(cat_v, "voice")
        self.assertEqual(payload_v["audio"]["transcription_status"], "pending")
        self.assertEqual(payload_v["image"]["analysis_status"], "none")

        data_mixed = {
            "complaint_id": "M-100",
            "text": "Huge crater",
            "audio_path": "audio/clip.mp3",
            "image_path": "images/crater.jpg",
            "image_caption": "Crater on road"
        }
        payload_m, cat_m = MultimodalPreprocessor.preprocess(data_mixed)
        self.assertEqual(cat_m, "multimodal")
        self.assertEqual(payload_m["audio"]["transcription_status"], "pending")
        self.assertEqual(payload_m["image"]["analysis_status"], "pending")
        self.assertIn("text", payload_m["modalities"])
        self.assertIn("voice", payload_m["modalities"])
        self.assertIn("image", payload_m["modalities"])

    def test_08_ingestion_service_synthetic_demo_csv(self):
        """Test IngestionService on the 45-row synthetic demo CSV."""
        csv_path = ROOT_DIR / "data" / "raw" / "demo" / "synthetic_complaints_40.csv"
        self.assertTrue(csv_path.exists(), "synthetic_complaints_40.csv must exist")

        ingestion = IngestionService(self.db)
        result = ingestion.ingest_csv_file(csv_path)

        self.assertEqual(result.total_rows, 45)
        self.assertEqual(result.accepted_rows, 42)
        self.assertEqual(result.rejected_rows, 3)
        self.assertGreater(result.created_complaints_count, 0)
        self.assertGreater(result.voice_rows, 0)
        self.assertGreater(result.image_rows, 0)
        self.assertGreater(result.multimodal_rows, 0)

        # Verify rejection reasons
        reasons = [d.reason for d in result.rejected_details]
        self.assertTrue(any("Missing all complaint content" in r for r in reasons))
        self.assertTrue(any("Missing mandatory complaint ID" in r for r in reasons))
        self.assertTrue(any("Duplicate complaint ID" in r for r in reasons))

    def test_09_raw_data_immutability_after_ingestion(self):
        """Verify ingested rows in raw_complaints cannot be modified or purged."""
        raw = self.db.query(RawComplaint).filter(RawComplaint.complaint_id == "CMP-DEMO-001").first()
        self.assertIsNotNone(raw)

        # Attempt to modify raw text
        raw.text = "Hacked text"
        with self.assertRaises(ImmutableDataError):
            self.db.commit()
        self.db.rollback()

    def test_10_ingestion_idempotency_repeated_import(self):
        """Verify importing the same file twice does not create duplicate raw complaints."""
        csv_path = ROOT_DIR / "data" / "raw" / "demo" / "synthetic_complaints_40.csv"
        ingestion = IngestionService(self.db)

        # Re-importing the same CSV
        result_repeat = ingestion.ingest_csv_file(csv_path)
        # All previously accepted records should now be idempotently skipped
        self.assertEqual(result_repeat.created_complaints_count, 0)
        self.assertEqual(result_repeat.total_rows, 45)
        self.assertGreaterEqual(len(result_repeat.duplicate_ids), 42)

    def test_11_multilingual_utf8_preservation(self):
        """Verify Devanagari Hindi text is preserved cleanly without corruption."""
        raw_hindi = self.db.query(RawComplaint).filter(RawComplaint.complaint_id == "CMP-DEMO-016").first()
        self.assertIsNotNone(raw_hindi)
        self.assertIn("पीने का पानी", raw_hindi.text)

    def test_12_api_batch_ingest_endpoint(self):
        """Test POST /api/v1/complaints/batch-ingest with CSV file upload."""
        csv_data = """ticket_id,source_channel,complaint_text,address
CMP-API-001,cm_helpline,Broken water pipe flooding street,Civil Lines
CMP-API-002,mobile_app,Streetlight outage,Gandhi Chowk
"""
        files = {
            "file": ("test_upload.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")
        }
        response = self.client.post("/api/v1/complaints/batch-ingest", files=files)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["total_rows"], 2)
        self.assertEqual(data["accepted_rows"], 2)
        self.assertEqual(data["rejected_rows"], 0)

    def test_13_api_get_complaints_pagination_and_filter(self):
        """Test GET /api/v1/complaints with pagination and department/search filters."""
        # Query page 1
        res = self.client.get("/api/v1/complaints?page=1&page_size=10")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertIn("data", payload)
        self.assertIn("pagination", payload)
        self.assertLessEqual(len(payload["data"]), 10)
        self.assertGreater(payload["pagination"]["total_records"], 0)

        # Query with search_query filter
        res_search = self.client.get("/api/v1/complaints?search_query=Sargam")
        self.assertEqual(res_search.status_code, 200)
        search_data = res_search.json()["data"]
        for c in search_data:
            matches = "sargam" in c["summary"].lower() or "sargam" in c["original_text"].lower() or "sargam" in str(c["normalized_locality"]).lower()
            self.assertTrue(matches)

    def test_14_api_get_single_complaint(self):
        """Test GET /api/v1/complaints/{complaint_id}."""
        res = self.client.get("/api/v1/complaints/CMP-DEMO-001")
        self.assertEqual(res.status_code, 200)
        ticket = res.json()
        self.assertEqual(ticket["complaint_id"], "CMP-DEMO-001")
        self.assertEqual(ticket["original_channel"], "state_helpline")

        # 404 on nonexistent ID
        res_404 = self.client.get("/api/v1/complaints/NONEXISTENT-999")
        self.assertEqual(res_404.status_code, 404)


if __name__ == "__main__":
    unittest.main()
