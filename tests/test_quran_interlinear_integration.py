import io
import unittest
from unittest.mock import patch


class TestQuranInterlinearIntegration(unittest.TestCase):
    def test_tex_write_verse_uses_tex_utils_cleanup(self):
        with patch("tex_utils.tex_cleanup_text", side_effect=lambda s: f"CLEAN[{s}]") as mock_cleanup:
            import importlib
            module = importlib.import_module("quran-interlinear")

            # Minimal verse structure expected by tex_write_verse
            verse = {
                "verse": {
                    "translations": [
                        {"resource_id": 19, "text": "In the name of Allah &"}
                    ],
                    "text_uthmani": "بِسْمِ اللّٰهِ",
                }
            }

            fh = io.StringIO()
            module.tex_write_verse(fh, verse, 1, 1)
            output = fh.getvalue()

            self.assertTrue(mock_cleanup.called)
            self.assertIn("CLEAN[", output)


if __name__ == "__main__":
    unittest.main()
