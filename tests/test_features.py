import csv
import json
import tempfile
import unittest
from pathlib import Path

from duplicate_detector import find_possible_duplicate, similarity
from enhancer import local_enhancement
from exporter import csv_export, format_jira, format_report, json_export
from history import add_history, load_history
from scoring import score_defect, score_original_text


class FeatureTests(unittest.TestCase):
    def test_history_roundtrip_is_local_and_contains_no_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.json"
            raw = "Search results are incorrect in the product finder."
            report = local_enhancement(raw)
            saved = add_history(raw, report, score_defect(report), score_original_text(raw), path)
            loaded = load_history(path)
            self.assertEqual(loaded[0]["id"], saved["id"])
            self.assertEqual(loaded[0]["original_text"], raw)
            self.assertNotIn("api_key", json.dumps(loaded).casefold())

    def test_corrupt_history_is_a_friendly_empty_state(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.json"
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(load_history(path), [])

    def test_malformed_history_rows_are_filtered_without_crashing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.json"
            path.write_text(json.dumps([None, {"report": [], "quality_score": "bad"},
                                        {"report": {}, "quality_score": "25", "timestamp": 123}]), encoding="utf-8")
            records = load_history(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["quality_score"], 25)
            self.assertEqual(records[0]["timestamp"], "")

    def test_possible_duplicate_is_a_similarity_hint(self):
        raw = "Payment sometimes fails during checkout after selecting a card."
        previous = {"title": "Old", "original_text": "Payment fails during checkout after selecting a card sometimes."}
        self.assertGreater(similarity(raw, previous["original_text"]), 0.65)
        match = find_possible_duplicate(raw, [previous])
        self.assertIsNotNone(match)
        self.assertGreaterEqual(match["similarity"], 65)
        self.assertIsNone(find_possible_duplicate("totally unrelated search issue", [previous]))
        self.assertIsNone(find_possible_duplicate(raw, []))

    def test_exports_are_parseable_and_contain_expected_fields(self):
        raw = "The search button does nothing for a product query."
        report = local_enhancement(raw)
        decoded = json.loads(json_export(report))
        self.assertEqual(decoded["actual_result"], raw)
        self.assertIn("Steps to Reproduce", format_report(report))
        self.assertIn("AI Suggested Severity", format_jira(report))
        rows = list(csv.DictReader(csv_export(report, raw, score_defect(report)["overall"]).splitlines()))
        self.assertEqual(rows[0]["original_text"], raw)
        self.assertEqual(rows[0]["category"], "Search")


if __name__ == "__main__":
    unittest.main()
