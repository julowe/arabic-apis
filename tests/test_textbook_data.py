import io
import os
import json
import tempfile
import unittest


class TestTextbookData(unittest.TestCase):
    def test_read_csv_and_build_json(self):
        from textbook_data import read_csv, build_json_from_rows

        sample_csv = "Sing. / Perf.,Dual / Imperf.,Plural / Verbal N.,English\nكَتَبَ,يَكْتُبَانِ,كُتُب,write\n,,,"  # second empty row ignored
        with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(sample_csv)
            path = f.name
        try:
            rows = read_csv(path)
            self.assertEqual(len(rows), 1)
            data = build_json_from_rows(rows, {"lesson_name": "L1"})
            self.assertIn("vocabulary", data)
            self.assertEqual(len(data["vocabulary"]), 1)
            self.assertEqual(data["vocabulary"][0]["english"], "write")
        finally:
            os.unlink(path)

    def test_read_ods_multiple_sheets(self):
        import pandas as pd
        from textbook_data import read_ods

        # Create a temporary ODS file with two sheets
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "sample.ods")
            with pd.ExcelWriter(p, engine="odf") as writer:
                pd.DataFrame([
                    {"Sing. / Perf.": "قال", "English": "say"},
                ]).to_excel(writer, sheet_name="Vocab", index=False)
                pd.DataFrame([
                    {"Exercise": "اقرأ", "Sura": 1, "Verse": 1},
                ]).to_excel(writer, sheet_name="Exercises", index=False)
            sheets = read_ods(p)
            self.assertIn("Vocab", sheets)
            self.assertIn("Exercises", sheets)
            self.assertEqual(len(sheets["Vocab"]), 1)
