import io
import unittest
from unittest.mock import patch


class TestArabicTextbookIntegration(unittest.TestCase):
    def test_write_vocabulary_table_uses_tex_utils_cleanup(self):
        # Patch the shared tex_utils cleanup to verify integration
        with patch("tex_utils.tex_cleanup_text", side_effect=lambda s: f"CLEAN[{s}]") as mock_cleanup:
            import importlib
            module = importlib.import_module("arabic-textbook-to-tex-file")

            fh = io.StringIO()
            vocab = [
                {
                    'Sing. / Perf.': 'كَتَبَ',
                    'Dual / Imperf.': 'يَكْتُبَانِ',
                    'Plural / Verbal N.': 'كُتُب',
                    'English': 'write'
                }
            ]

            module.write_vocabulary_table(fh, vocab)
            output = fh.getvalue()

            # Our patched function should have been called and its output present
            self.assertTrue(mock_cleanup.called)
            self.assertIn("CLEAN[", output)


if __name__ == "__main__":
    unittest.main()
