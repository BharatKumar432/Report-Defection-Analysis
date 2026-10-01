import unittest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from enhancer import local_enhancement
from history import add_history
from scoring import score_defect, score_original_text


class StreamlitSmokeTests(unittest.TestCase):
    def test_demo_mode_renders_report_and_download_without_api_key(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=10).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.radio[0].value, "Demo Mode")
        app.text_area[0].set_value("<script>alert(1)</script>")
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.tabs), 5)
        # User content is rendered as plain text, never interpolated into Markdown/HTML.
        self.assertTrue(any("<script>alert(1)</script>" in item.value for item in app.text))
        self.assertGreaterEqual(len(app.get("download_button")), 5)

    def test_sample_selection_does_not_overwrite_edits_and_reset_clears_report(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=10).run()
            app.selectbox[0].select("Login fails after password reset").run()
            self.assertIn("Login fails sometimes", app.text_area[0].value)
            app.text_area[0].set_value("My custom edit to the sample").run()
            self.assertEqual(app.text_area[0].value, "My custom edit to the sample")
            app.button[0].click().run()
            self.assertTrue(any("My custom edit" in item.value for item in app.subheader))
            app.button[1].click().run()
            self.assertEqual(app.text_area[0].value, "")
            self.assertFalse(any("My custom edit" in item.value for item in app.subheader))

    def test_history_save_and_possible_duplicate_warning(self):
        with tempfile.TemporaryDirectory() as folder:
            history_path = Path(folder) / "history.json"
            prior_text = "Payment sometimes fails during checkout after selecting a card."
            prior_report = local_enhancement(prior_text)
            add_history(prior_text, prior_report, score_defect(prior_report), score_original_text(prior_text), history_path)
            with patch.dict(os.environ, {"GROQ_API_KEY": "", "DEFECT_HISTORY_PATH": str(history_path)}):
                app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=10).run()
                app.text_area[0].set_value("Payment fails during checkout after selecting a card sometimes.").run()
                app.button[0].click().run()
                self.assertTrue(any("Possible Duplicate" in item.value for item in app.warning))
                save_button = next(button for button in app.button if "Save to History Anyway" in button.label)
                save_button.click().run()
                self.assertEqual(len(json.loads(history_path.read_text(encoding="utf-8"))), 2)


if __name__ == "__main__":
    unittest.main()
