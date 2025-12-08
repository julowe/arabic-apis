import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


class TestCliPipeline(unittest.TestCase):
    def test_json_input_bypasses_api(self):
        # Build a minimal JSON structure expected by renderer
        data = {
            "lesson": {"name": "Lesson 1"},
            "vocabulary": [
                {"sing_perf": "قال", "dual_imperf": "", "plural_vn": "", "english": "say"}
            ],
            "exercises": [
                {"exercise_text": "اقرأ", "quranic_reference": "1:1"}
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            json_path = os.path.join(tmp, "data.json")
            tex_path = os.path.join(tmp, "out.tex")
            with open(json_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)

            from contextlib import ExitStack
            with ExitStack() as stack:
                mock_tok = stack.enter_context(patch("quran_api.get_access_token"))
                mock_verse = stack.enter_context(patch("quran_api.get_verse"))
                # Run main with --json-input
                import importlib
                mod = importlib.import_module("arabic-textbook-to-tex-file")
                argv = ["prog", "--json-input", json_path, "-o", tex_path, "--no-api"]
                with patch.object(sys, "argv", argv):
                    mod.main()

                # Ensure API was not called
                mock_tok.assert_not_called()
                mock_verse.assert_not_called()
                self.assertTrue(os.path.exists(tex_path))

    def test_csv_pipeline_writes_json_next_to_tex(self):
        # Minimal CSV with one vocab row
        csv_content = "Sing. / Perf.,Dual / Imperf.,Plural / Verbal N.,English\nقال,,,say\n"
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, "in.csv")
            out_tex = os.path.join(tmp, "out.tex")
            with open(csv_path, "w", encoding="utf-8") as fh:
                fh.write(csv_content)

            # Patch enrich to avoid external calls; just echo input
            with patch("textbook_enrich.enrich_with_quran_api", side_effect=lambda d, *a, **k: d):
                import importlib
                mod = importlib.import_module("arabic-textbook-to-tex-file")
                argv = ["prog", csv_path, "-o", out_tex, "--no-api"]
                with patch.object(sys, "argv", argv):
                    mod.main()

            self.assertTrue(os.path.exists(out_tex))
            out_json = os.path.splitext(out_tex)[0] + ".json"
            self.assertTrue(os.path.exists(out_json))
            with open(out_json, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                self.assertIn("vocabulary", data)


if __name__ == "__main__":
    unittest.main()
