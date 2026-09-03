import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# To be implemented in format_arabic_diacritics.py
from format_arabic_diacritics import (
    reorder_diacritics,
    find_violations,
    format_diff,
    main,
    HARAKAT_CHARS,
    SHADDA,
)


class TestArabicDiacriticsReordering(unittest.TestCase):
    def test_reorder_single_fatha_shadda(self):
        # ba + fatha + shadda -> ba + shadda + fatha
        input_text = "\u0628\u064e\u0651"
        expected = "\u0628\u0651\u064e"
        result, count = reorder_diacritics(input_text)
        self.assertEqual(result, expected)
        self.assertEqual(count, 1)

    def test_already_ordered_remains_unchanged(self):
        # ba + shadda + fatha -> unchanged
        input_text = "\u0628\u0651\u064e"
        result, count = reorder_diacritics(input_text)
        self.assertEqual(result, input_text)
        self.assertEqual(count, 0)

    def test_all_harakat_with_shadda(self):
        # Test fatha, damma, kasra, fathatan, dammatan, kasratan, dagger alef
        harakat = [
            ("\u064e", "fatha"),
            ("\u064f", "damma"),
            ("\u0650", "kasra"),
            ("\u064b", "fathatan"),
            ("\u064c", "dammatan"),
            ("\u064d", "kasratan"),
            ("\u0670", "superscript alef"),
        ]
        for h, name in harakat:
            inverted = f"\u0628{h}\u0651"  # ba + harakah + shadda
            corrected = f"\u0628\u0651{h}"  # ba + shadda + harakah
            res, cnt = reorder_diacritics(inverted)
            self.assertEqual(res, corrected, f"Failed for {name}")
            self.assertEqual(cnt, 1)

    def test_csv_line_with_multiple_words(self):
        # Contains one inverted (جَنَّةٌ) and one correct (جَنَّاتٌ)
        # جَنَّةٌ has noon + fatha + shadda
        line = "27,3,Vocabulary,\u062c\u064e\u0646\u064e\u0651\u0629\u064c,,\u062c\u064e\u0646\u0651\u064e\u0627\u062a\u064c,garden"
        res, cnt = reorder_diacritics(line)
        self.assertEqual(cnt, 1)
        expected_line = "27,3,Vocabulary,\u062c\u064e\u0646\u0651\u064e\u0629\u064c,,\u062c\u064e\u0646\u0651\u064e\u0627\u062a\u064c,garden"
        self.assertEqual(res, expected_line)

    def test_non_arabic_text_preserved(self):
        english_text = "Hello, world! 12345, testing."
        res, cnt = reorder_diacritics(english_text)
        self.assertEqual(res, english_text)
        self.assertEqual(cnt, 0)

    def test_find_violations_location(self):
        text = "word1 \u0628\u064e\u0651 word2"
        violations = find_violations(text)
        self.assertEqual(len(violations), 1)
        v = violations[0]
        self.assertEqual(v["line_num"], 1)
        self.assertEqual(v["inverted_token"], "\u0628\u064e\u0651")
        self.assertEqual(v["corrected_token"], "\u0628\u0651\u064e")


class TestCLIBehavior(unittest.TestCase):
    def test_check_mode_exit_codes(self):
        with tempfile.NamedTemporaryFile(
            "w+", suffix=".csv", delete=False, encoding="utf-8"
        ) as f_dirty:
            f_dirty.write(
                "27,3,Vocabulary,\u062c\u064e\u0646\u064e\u0651\u0629\u064c\n"
            )
            dirty_path = f_dirty.name

        with tempfile.NamedTemporaryFile(
            "w+", suffix=".csv", delete=False, encoding="utf-8"
        ) as f_clean:
            f_clean.write(
                "27,3,Vocabulary,\u062c\u064e\u0646\u0651\u064e\u0629\u064c\n"
            )
            clean_path = f_clean.name

        try:
            # Check clean file -> exit 0
            ret_clean = main(["--check", clean_path, "-q"])
            self.assertEqual(ret_clean, 0)

            # Check dirty file -> exit 1
            ret_dirty = main(["--check", dirty_path, "-q"])
            self.assertEqual(ret_dirty, 1)
        finally:
            os.unlink(dirty_path)
            os.unlink(clean_path)

    def test_dry_run_does_not_modify_file(self):
        dirty_content = "\u062c\u064e\u0646\u064e\u0651\u0629\u064c\n"
        with tempfile.NamedTemporaryFile(
            "w+", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(dirty_content)
            path = f.name

        try:
            ret = main(["--dry-run", path, "-q"])
            self.assertEqual(ret, 1)
            with open(path, "r", encoding="utf-8") as rf:
                self.assertEqual(rf.read(), dirty_content)
        finally:
            os.unlink(path)

    def test_write_mode_modifies_file(self):
        dirty_content = "\u062c\u064e\u0646\u064e\u0651\u0629\u064c\n"
        expected_content = "\u062c\u064e\u0646\u0651\u064e\u0629\u064c\n"
        with tempfile.NamedTemporaryFile(
            "w+", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(dirty_content)
            path = f.name

        try:
            ret = main(["--write", path, "-q"])
            self.assertEqual(ret, 0)
            with open(path, "r", encoding="utf-8") as rf:
                self.assertEqual(rf.read(), expected_content)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
