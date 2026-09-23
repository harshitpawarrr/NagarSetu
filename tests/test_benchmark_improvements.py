import unittest
import sys
from pathlib import Path

from app.services.classification.classifier import ClassificationService
from app.rules.urgency_engine import UrgencyEngine
from app.rules.locality_normalizer import LocalityNormalizer

class TestBenchmarkImprovements(unittest.TestCase):
    def setUp(self):
        # Instantiate services without AI clients (tests offline fallback)
        self.classifier = ClassificationService(client=None)
        # Note: We want to mock client.is_configured to False if it's there
        if self.classifier.client:
            self.classifier.client.is_configured = lambda: False
        self.urgency_engine = UrgencyEngine()
        self.locality_normalizer = LocalityNormalizer()

    def test_devanagari_road(self):
        res = self.classifier.classify("सड़क पर बड़ा गड्ढा है")
        self.assertEqual(res.department, "DEPT_RDS")
        self.assertEqual(res.category, "CAT_ROAD_MAINTENANCE")

    def test_devanagari_water(self):
        res = self.classifier.classify("पानी की पाइप लाइन टूट गई है, पानी बह रहा है")
        self.assertEqual(res.department, "DEPT_WSS")
        self.assertEqual(res.category, "CAT_WATER_SUPPLY")

    def test_devanagari_electrical(self):
        res = self.classifier.classify("स्ट्रीट लाइट बंद है, बिजली नहीं है")
        self.assertEqual(res.department, "DEPT_ELEC")
        self.assertEqual(res.category, "CAT_STREET_LIGHTING")

    def test_devanagari_sewerage(self):
        res = self.classifier.classify("नाली जाम है, गंदा पानी भर गया है")
        self.assertEqual(res.department, "DEPT_WSS")
        self.assertEqual(res.category, "CAT_DRAINAGE_SEWAGE")

    def test_hindi_streetlight(self):
        res = self.classifier.classify("स्ट्रीट लाइटें काम नहीं कर रही हैं")
        self.assertEqual(res.department, "DEPT_ELEC")
        self.assertEqual(res.category, "CAT_STREET_LIGHTING")

    def test_plural_streetlights(self):
        res = self.classifier.classify("The streetlights are not working on my street.")
        self.assertEqual(res.department, "DEPT_ELEC")
        self.assertEqual(res.category, "CAT_STREET_LIGHTING")

    def test_road_damaged_inversion(self):
        res = self.classifier.classify("The road damaged completely near the school.")
        self.assertEqual(res.department, "DEPT_RDS")
        self.assertEqual(res.category, "CAT_ROAD_MAINTENANCE")

    def test_live_electrical_wire(self):
        res = self.classifier.classify("Live electrical wire snapped and fallen on the road.")
        self.assertEqual(res.department, "DEPT_ELEC")
        self.assertEqual(res.category, "CAT_STREET_LIGHTING")

    def test_tree_branch(self):
        res = self.classifier.classify("A large neem tree branch has fallen.")
        self.assertEqual(res.department, "DEPT_HORT")
        self.assertEqual(res.category, "CAT_HORTICULTURE") # Canonical alias

    def test_traffic_signal(self):
        res = self.classifier.classify("Traffic signal at the square is dead.")
        self.assertEqual(res.department, "DEPT_ELEC")
        self.assertEqual(res.category, "CAT_STREET_LIGHTING")

    def test_garden_swings_slide(self):
        res = self.classifier.classify("The children's slide in the botanical garden is broken.")
        self.assertEqual(res.department, "DEPT_HORT")
        self.assertEqual(res.category, "CAT_HORTICULTURE") # Canonical alias

    def test_gazetteer_additions(self):
        res1 = self.locality_normalizer.normalize(complaint_text="Garbage near Railway Station")
        self.assertEqual(res1.ward, "Ward 10")
        
        res2 = self.locality_normalizer.normalize(complaint_text="Issue at BDA Complex")
        self.assertEqual(res2.ward, "Ward 45")
        
        res3 = self.locality_normalizer.normalize(complaint_text="Karond mandi")
        self.assertEqual(res3.ward, "Ward 15")
        
        res4 = self.locality_normalizer.normalize(complaint_text="Govindpura industrial area")
        self.assertEqual(res4.ward, "Ward 60")
        
        res5 = self.locality_normalizer.normalize(complaint_text="Board Office square")
        self.assertEqual(res5.ward, "Ward 40")

    def test_safety_override(self):
        res = self.urgency_engine.evaluate("Live wire snapped near school.")
        self.assertTrue(res.safety_override_applied)
        self.assertEqual(res.urgency.value, "CRITICAL")
        self.assertGreaterEqual(res.safety_score, 36)

    def test_normal_medium_priority_civic_complaints(self):
        res1 = self.urgency_engine.evaluate("There is a large pothole near the school gate.")
        # Pothole (outage=18) + School (safety=22) + duration=4 -> 44 (MEDIUM)
        self.assertEqual(res1.urgency.value, "MEDIUM")
        
        res2 = self.urgency_engine.evaluate("Waterlogging outside my house.")
        # Waterlogging (outage=18) + (safety=22) + duration=4 -> 44 (MEDIUM)
        self.assertEqual(res2.urgency.value, "MEDIUM")

        res3 = self.urgency_engine.evaluate("We are getting very low water pressure.")
        # low water pressure (outage=26 area impact) + (safety=10) + duration=4 -> 40 (MEDIUM)
        self.assertEqual(res3.urgency.value, "MEDIUM")

    def test_false_positive_road_address(self):
        # Generic word "Road" without defect terms
        res = self.classifier.classify("Garbage dumped on Road No. 5, MP Nagar")
        self.assertNotEqual(res.department, "DEPT_RDS")
        self.assertEqual(res.department, "DEPT_SWM")
        self.assertEqual(res.category, "CAT_GARBAGE_COLLECTION")

if __name__ == '__main__':
    unittest.main()
