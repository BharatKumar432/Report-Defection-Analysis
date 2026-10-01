import unittest

from enhancer import local_enhancement
from scoring import DIMENSION_WEIGHTS, score_defect, score_original_text


class ScoringTests(unittest.TestCase):
    def test_score_is_numeric_bounded_and_deterministic(self):
        report = local_enhancement("A defect is observed when action is performed.")
        first = score_defect(report)
        second = score_defect(report)
        self.assertEqual(first, second)
        self.assertIsInstance(first["overall"], int)
        self.assertGreaterEqual(first["overall"], 0)
        self.assertLessEqual(first["overall"], 100)

    def test_missing_information_and_unprovided_expected_reduce_score(self):
        report = local_enhancement("A defect is observed.")
        baseline = score_defect(report)["overall"]
        report["missing_information"] = []
        report["expected_result"] = "The expected behavior should be this clearly stated outcome."
        self.assertGreater(score_defect(report)["overall"], baseline)

    def test_stronger_report_scores_higher_than_incomplete_report(self):
        weak = {"title": "x", "description": "x", "preconditions": [], "steps_to_reproduce": [],
                "expected_result": "Not provided", "actual_result": "x", "environment": {},
                "missing_information": ["environment"]}
        strong = {"title": "Search action produces no results", "description": "The search button does not return product results when the user enters a query.",
                  "preconditions": ["Search page is available"], "steps_to_reproduce": ["Open search", "Enter a product query", "Select Search"],
                  "expected_result": "Relevant products should appear for the entered query.", "actual_result": "No results are returned after search.",
                  "environment": {"browser": "Chrome 140"}, "missing_information": []}
        self.assertGreater(score_defect(strong)["overall"], score_defect(weak)["overall"])

    def test_dimensions_are_bounded_weighted_and_original_score_is_deterministic(self):
        raw = "payment is not working sometimes when I checkout"
        report = local_enhancement(raw)
        enhanced = score_defect(report)
        original = score_original_text(raw)
        self.assertEqual(sum(DIMENSION_WEIGHTS.values()), 100)
        self.assertEqual(set(enhanced["dimensions"]), set(DIMENSION_WEIGHTS))
        self.assertEqual(score_original_text(raw), original)
        self.assertLessEqual(original["overall"], 100)
        self.assertLessEqual(enhanced["overall"], 100)


if __name__ == "__main__":
    unittest.main()
