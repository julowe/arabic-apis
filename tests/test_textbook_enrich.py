import unittest
from unittest.mock import patch


class TestTextbookEnrich(unittest.TestCase):
    def test_enrich_dedupes_and_attaches(self):
        data = {
            "vocabulary": [
                {"sing_perf": "قال", "quranic_reference": "1:1"},
                {"sing_perf": "كتاب", "quranic_reference": "1:1"},
            ],
            "exercises": [
                {"exercise_text": "اقرأ", "quranic_reference": "2:255"},
            ],
        }

        with patch("textbook_enrich.get_access_token", return_value="TOKEN") as mock_tok, \
             patch("textbook_enrich.get_verse", side_effect=[{"v": "1:1"}, {"v": "2:255"}]) as mock_verse:
            from textbook_enrich import enrich_with_quran_api

            out = enrich_with_quran_api(data, "oauth", "api", "cid", "secret")

            # Token once, verse fetched twice (unique keys only)
            mock_tok.assert_called_once()
            self.assertEqual(mock_verse.call_count, 2)

            # Ensure attachments present
            self.assertIn("quran_api", out["vocabulary"][0])
            self.assertIn("verse", out["vocabulary"][0]["quran_api"])
            self.assertIn("quran_api", out["exercises"][0])
            self.assertIn("verse", out["exercises"][0]["quran_api"])
