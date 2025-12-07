import unittest


class TestTexUtils(unittest.TestCase):
    def test_tex_escape_text_escapes_and_removes_footnotes(self):
        # Arrange
        sample = "Text & 100% <sup foot_note=12>12</sup> ${}_#^~\\"

        # Act
        import tex_utils

        escaped = tex_utils.tex_escape_text(sample)

        # Assert
        self.assertNotIn("<sup foot_note=", escaped)
        self.assertIn(r"\&", escaped)
        self.assertIn(r"\%", escaped)
        self.assertIn(r"\$", escaped)
        self.assertIn(r"\_", escaped)
        self.assertIn(r"\#", escaped)
        self.assertIn(r"\{", escaped)
        self.assertIn(r"\}", escaped)
        self.assertIn(r"\textasciicircum", escaped)
        self.assertIn(r"\textasciitilde", escaped)
        self.assertIn(r"\textbackslash", escaped)

    def test_tex_cleanup_text_wraps_sallallah(self):
        text = "(ﷺ) &"
        import tex_utils

        cleaned = tex_utils.tex_cleanup_text(text)
        self.assertIn(r"(\ar{ﷺ})", cleaned)
        self.assertIn(r"\&", cleaned)

    def test_tex_remove_arabic_marks_removes_specific_codepoints(self):
        import tex_utils

        # Build a string including all characters slated for removal
        chars = "".join([
            "\u06D6", "\u06D7", "\u06D8", "\u06D9", "\u06DA", "\u06DB",
            "\u06DC", "\u06E0", "\u06E1", "\u06E2", "\u06E3", "\u06E4",
            "\u06E5", "\u06E6", "\u06E7", "\u06E8",
        ])
        chars = chars.encode("utf-8").decode("unicode_escape")
        sample = "بسم" + chars + "الله"

        result = tex_utils.tex_remove_arabic_marks(sample)

        # All extra marks should be removed, leaving base letters intact
        self.assertEqual(result, "بسمالله")


if __name__ == "__main__":
    unittest.main()
