#!/usr/bin/env python3

import argparse
import csv
import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pandas.io.sas.sas_constants import sas_datetime_formats

from tex_utils import tex_cleanup_text, tex_remove_arabic_marks

# Quran data for validation (114 chapters/suras)
QURAN_CHAPTERS = {
    1: 7,  # Al-Fatihah
    2: 286,  # Al-Baqarah
    3: 200,  # Ali 'Imran
    4: 176,  # An-Nisa
    5: 120,  # Al-Ma'idah
    6: 165,  # Al-An'am
    7: 206,  # Al-A'raf
    8: 75,  # Al-Anfal
    9: 129,  # At-Tawbah
    10: 109,  # Yunus
    11: 123,  # Hud
    12: 111,  # Yusuf
    13: 43,  # Ar-Ra'd
    14: 52,  # Ibrahim
    15: 99,  # Al-Hijr
    16: 128,  # An-Nahl
    17: 111,  # Al-Isra
    18: 110,  # Al-Kahf
    19: 98,  # Maryam
    20: 135,  # Ta-Ha
    21: 112,  # Al-Anbiya
    22: 78,  # Al-Hajj
    23: 118,  # Al-Mu'minun
    24: 64,  # An-Nur
    25: 77,  # Al-Furqan
    26: 227,  # Ash-Shu'ara
    27: 93,  # An-Naml
    28: 88,  # Al-Qasas
    29: 69,  # Al-Ankabut
    30: 60,  # Ar-Rum
    31: 34,  # Luqman
    32: 30,  # As-Sajdah
    33: 73,  # Al-Ahzab
    34: 54,  # Saba
    35: 45,  # Fatir
    36: 83,  # Ya-Sin
    37: 182,  # As-Saffat
    38: 88,  # Sad
    39: 75,  # Az-Zumar
    40: 85,  # Ghafir
    41: 54,  # Fussilat
    42: 53,  # Ash-Shura
    43: 89,  # Az-Zukhruf
    44: 59,  # Ad-Dukhan
    45: 37,  # Al-Jathiyah
    46: 35,  # Al-Ahqaf
    47: 38,  # Muhammad
    48: 29,  # Al-Fath
    49: 18,  # Al-Hujurat
    50: 45,  # Qaf
    51: 60,  # Adh-Dhariyat
    52: 49,  # At-Tur
    53: 62,  # An-Najm
    54: 55,  # Al-Qamar
    55: 78,  # Ar-Rahman
    56: 96,  # Al-Waqi'ah
    57: 29,  # Al-Hadid
    58: 22,  # Al-Mujadila
    59: 24,  # Al-Hashr
    60: 13,  # Al-Mumtahanah
    61: 14,  # As-Saff
    62: 11,  # Al-Jumu'ah
    63: 11,  # Al-Munafiqun
    64: 18,  # At-Taghabun
    65: 12,  # At-Talaq
    66: 12,  # At-Tahrim
    67: 30,  # Al-Mulk
    68: 52,  # Al-Qalam
    69: 52,  # Al-Haqqah
    70: 44,  # Al-Ma'arij
    71: 28,  # Nuh
    72: 28,  # Al-Jinn
    73: 20,  # Al-Muzzammil
    74: 56,  # Al-Muddaththir
    75: 40,  # Al-Qiyamah
    76: 31,  # Al-Insan
    77: 50,  # Al-Mursalat
    78: 40,  # An-Naba
    79: 46,  # An-Nazi'at
    80: 42,  # Abasa
    81: 29,  # At-Takwir
    82: 19,  # Al-Infitar
    83: 36,  # Al-Mutaffifin
    84: 25,  # Al-Inshiqaq
    85: 22,  # Al-Buruj
    86: 17,  # At-Tariq
    87: 19,  # Al-A'la
    88: 26,  # Al-Ghashiyah
    89: 30,  # Al-Fajr
    90: 20,  # Al-Balad
    91: 15,  # Ash-Shams
    92: 21,  # Al-Layl
    93: 11,  # Ad-Duha
    94: 8,  # Ash-Sharh
    95: 8,  # At-Tin
    96: 19,  # Al-Alaq
    97: 5,  # Al-Qadr
    98: 8,  # Al-Bayyinah
    99: 8,  # Az-Zalzalah
    100: 11,  # Al-Adiyat
    101: 11,  # Al-Qari'ah
    102: 8,  # At-Takathur
    103: 3,  # Al-Asr
    104: 9,  # Al-Humazah
    105: 5,  # Al-Fil
    106: 4,  # Quraysh
    107: 7,  # Al-Ma'un
    108: 3,  # Al-Kawthar
    109: 6,  # Al-Kafirun
    110: 3,  # An-Nasr
    111: 5,  # Al-Masad
    112: 4,  # Al-Ikhlas
    113: 5,  # Al-Falaq
    114: 6,  # An-Nas
}

CHARSET_ARABIC = sas_datetime_formats
CHARSET_ARABIC_ALL = "[\u0600–\u06FF\u0750–\u077F\u0870–\u089F\u08A0–\u08FF\uFB50–\uFDFF\uFE70–\uFEFF\u10E60–\u10E7F\u10EC0-\u10EFF\u1EC70–\u1ECBF\u1ED00–\u1ED4F\u1EE00–\u1EEFF]"

class TextbookProcessor:
    def __init__(self, output_prefix: str = "textbook-llm"):
        self.current_page = 0
        self.current_lesson = 0
        self.lesson_header = ""

        # Data collections
        self.arabic_words = defaultdict(lambda: {"count": 0, "pages": set()})
        self.vocabulary_data = []
        self.exercises_data = []

        # Output files
        self.output_prefix = output_prefix
        self.tex_content = []

        # State tracking
        self.in_vocabulary_section = False
        self.in_exercise_section = False
        self.vocabulary_headers = []
        self.current_vocab_type = "noun"  # "noun" or "verb"
        self.pending_vocabulary_entry = None  # For multi-line entries

        # Table processing state
        self.in_table = False
        self.table_rows = []
        self.original_table_text = []

    def convert_written_number(self, word: str) -> int:
        """Convert written numbers to integers"""
        number_words = {
            "One": 1,
            "Two": 2,
            "Three": 3,
            "Four": 4,
            "Five": 5,
            "Six": 6,
            "Seven": 7,
            "Eight": 8,
            "Nine": 9,
            "Ten": 10,
            "Eleven": 11,
            "Twelve": 12,
            "Thirteen": 13,
            "Fourteen": 14,
            "Fifteen": 15,
            "Sixteen": 16,
            "Seventeen": 17,
            "Eighteen": 18,
            "Nineteen": 19,
            "Twenty": 20,
            "Twenty-One": 21,
            "Twenty-Two": 22,
            "Twenty-Three": 23,
            "Twenty-Four": 24,
            "Twenty-Five": 25,
            "Twenty-Six": 26,
            "Twenty-Seven": 27,
            "Twenty-Eight": 28,
            "Twenty-Nine": 29,
            "Thirty": 30,
            "Thirty-One": 31,
            "Thirty-Two": 32,
            "Thirty-Three": 33,
            "Thirty-Four": 34,
            "Thirty-Five": 35,
            "Thirty-Six": 36,
            "Thirty-Seven": 37,
            "Thirty-Eight": 38,
            "Thirty-Nine": 39,
            "Forty": 40,
        }

        word_lower = word.lower()
        if word_lower in number_words:
            return number_words[word_lower]

        # Try to parse as integer
        try:
            return int(word)
        except ValueError:
            return 0

    def is_arabic_text(self, text: str) -> bool:
        """Check if text contains Arabic characters"""
        return bool(re.search(CHARSET_ARABIC_ALL, text))

    def extract_arabic_words(self, text: str, page_num: int):
        """Extract individual Arabic words from text and track them"""
        # Find all Arabic words (sequences of Arabic characters)
        # arabic_words = re.findall(r"[\u0600-\u06FF]+", text)
        arabic_words = re.findall(CHARSET_ARABIC_ALL + r"+", text)

        for word in arabic_words:
            # Clean up the word (remove diacritics for counting)
            clean_word = tex_remove_arabic_marks(word)
            if clean_word:
                self.arabic_words[clean_word]["count"] += 1
                self.arabic_words[clean_word]["pages"].add(page_num)

    def validate_quran_reference(self, surah: int, ayah: int) -> Tuple[bool, str]:
        """Validate Quran reference and return validation status and warning message"""
        if surah < 1 or surah > 114:
            return False, f"Chapter {surah} is invalid (valid range: 1-114)"

        if ayah < 1 or ayah > QURAN_CHAPTERS[surah]:
            return (
                False,
                f"Verse {ayah} is invalid for chapter {surah} (valid range: 1-{QURAN_CHAPTERS[surah]})",
            )

        return True, ""

    def parse_metadata_line(self, line: str) -> Optional[int]:
        """Parse metadata line to extract page number"""
        # Pattern: ### START FILE 10, Extracted Page 112
        match = re.match(r"### START FILE \d+, Extracted Page (\d+)", line)
        if match:
            return int(match.group(1))

        # Alternative pattern without page number
        match = re.match(r"### START FILE \d+, Extracted Page\s*$", line)
        if match:
            return self.current_page + 1  # Increment from last known page

        return None

    def detect_lesson_start(self, line: str) -> Optional[Tuple[int, str]]:
        """Detect lesson start and extract lesson number and header"""
        # Pattern: "Lesson NUMBER" followed by header on next lines
        match = re.match(r"^Lesson\s+(\d+)", line, re.IGNORECASE)
        if match:
            lesson_num = int(match.group(1))
            return lesson_num, line.strip()
        return None

    def detect_vocabulary_section(self, line: str) -> Optional[int]:
        """Detect vocabulary section start and return lesson number"""
        match = re.match(
            r"^VOCABULARY\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|EIGHTEEN|NINETEEN|TWENTY|\d+)",
            line,
            re.IGNORECASE,
        )
        if match:
            return self.convert_written_number(match.group(1))
        return None

    def detect_exercise_section(self, line: str) -> Optional[int]:
        """Detect exercise section start and return lesson number"""
        match = re.match(
            r"^EXERCISE\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|EIGHTEEN|NINETEEN|TWENTY|\d+)",
            line,
            re.IGNORECASE,
        )
        if match:
            return self.convert_written_number(match.group(1))
        return None

    def parse_vocabulary_headers(self, line: str) -> Optional[List[str]]:
        """Parse vocabulary table headers"""
        line = line.strip()

        # Check for verb headers
        if re.search(r"PERFECT.*IMPERFECT.*VERBAL\s+NOUN", line, re.IGNORECASE):
            return ["PERFECT", "IMPERFECT", "VERBAL NOUN"]

        # Check for noun headers
        if re.search(r"SINGULAR.*DUAL.*PLURAL", line, re.IGNORECASE):
            return ["SINGULAR", "DUAL", "PLURAL"]
        elif re.search(r"SINGULAR.*PLURAL", line, re.IGNORECASE):
            return ["SINGULAR", "PLURAL"]

        return None

    def parse_table_row(self, line: str) -> Optional[List[str]]:
        """Parse a table row, detecting column separators"""
        line = line.strip()
        if not line:
            return None

        # Split by multiple spaces or tabs (common table separators)
        columns = re.split(r"\s{2,}|\t+", line)
        columns = [col.strip() for col in columns if col.strip()]

        return columns if len(columns) > 1 else None

    def parse_vocabulary_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a vocabulary line that contains Arabic words and English translations"""
        line = line.strip()
        if not line or not self.is_arabic_text(line):
            return None

        # Pattern for vocabulary: Arabic transliteration [Arabic transliteration] English
        # Example: "اَللهُ Allāhu God" or "إِلٰهٌ ilāhun آلِهَةٌ ālihatun a god"

        # Split into parts and identify Arabic vs transliteration vs English
        parts = line.split()
        if len(parts) < 2:
            return None

        arabic_words = []
        transliterations = []
        english_parts = []

        i = 0
        while i < len(parts):
            part = parts[i]

            if self.is_arabic_text(part):
                # This is Arabic
                arabic_words.append(part)
                i += 1
                # The next part might be transliteration (lowercase, non-Arabic)
                if (
                    i < len(parts)
                    and not self.is_arabic_text(parts[i])
                    and parts[i][0].islower()
                ):
                    transliterations.append(parts[i])
                    i += 1
            else:
                # Check if this starts English (uppercase) or is continuation
                if part[0].isupper() or english_parts or part in ["a", "an", "the"]:
                    english_parts.append(part)
                i += 1

        english_text = " ".join(english_parts) if english_parts else ""

        # If no clear English found but we have transliterations,
        # the last transliteration might be English
        if not english_text and transliterations:
            # Check if last transliteration looks like English
            last_trans = transliterations[-1]
            if any(c.isupper() for c in last_trans) or last_trans in [
                "god",
                "book",
                "day",
                "mercy",
            ]:
                english_text = transliterations.pop()

        if not arabic_words:
            return None

        # Assign to columns based on count
        col1 = arabic_words[0] if len(arabic_words) > 0 else ""
        col2 = arabic_words[1] if len(arabic_words) > 1 else ""
        col3 = arabic_words[2] if len(arabic_words) > 2 else ""

        return {
            "page_number": self.current_page,
            "lesson_number": self.current_lesson,
            "column1": col1,
            "column2": col2,
            "column3": col3,
            "english_translations": english_text,
            "verb_form": "",
            "part_of_speech": self.current_vocab_type,
            "raw_line": line,  # Keep original for debugging
        }

    def parse_exercise_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse an exercise line to extract number, Arabic text, and Quran reference"""
        line = line.strip()

        # Look for exercise number at start
        exercise_match = re.match(r"^(\d+)\.?\s*(.*)", line)
        if not exercise_match:
            return None

        exercise_num = int(exercise_match.group(1))
        remaining_text = exercise_match.group(2)

        # Extract Quran reference [chapter:verse]
        quran_match = re.search(r"\[(\d+):(\d+)\]", remaining_text)
        surah = 0
        ayah = 0
        quran_ref = ""
        warning = ""

        if quran_match:
            surah = int(quran_match.group(1))
            ayah = int(quran_match.group(2))
            quran_ref = f"{surah}:{ayah}"

            # Validate reference
            is_valid, validation_msg = self.validate_quran_reference(surah, ayah)
            if not is_valid:
                warning = validation_msg

            # Remove reference from text
            remaining_text = re.sub(r"\[\d+:\d+\]", "", remaining_text).strip()

        return {
            "page_number": self.current_page,
            "lesson_number": self.current_lesson,
            "exercise_number": exercise_num,
            "arabic_text": remaining_text,
            "surah": surah,
            "ayah": ayah,
            "quranic_reference": quran_ref,
            "validation_warning": warning,
        }

    def convert_markdown_to_tex(self, line: str) -> str:
        """Convert markdown formatting to LaTeX"""
        # Bold: **text** or __text__ -> \textbf{text}
        line = re.sub(r"\*\*(.*?)\*\*", r"\\textbf{\1}", line)
        line = re.sub(r"__(.*?)__", r"\\textbf{\1}", line)

        # Italic: *text* or _text_ -> \textit{text}
        line = re.sub(r"\*(.*?)\*", r"\\textit{\1}", line)
        line = re.sub(r"_(.*?)_", r"\\textit{\1}", line)

        # Code: `text` -> \texttt{text}
        line = re.sub(r"`(.*?)`", r"\\texttt{\1}", line)

        return line

    def format_arabic_for_tex(self, text: str) -> str:
        """Format Arabic text appropriately for LaTeX"""
        if not self.is_arabic_text(text):
            return tex_cleanup_text(text)

        # If it's a short phrase (< 50 chars), use inline Arabic
        if len(text) < 50:
            return f"\\ar{{{tex_cleanup_text(text)}}}"
        else:
            # For longer text, use paragraph Arabic
            return f"\\arpar{{\n{tex_remove_arabic_marks(text)}\n}}"

    def write_tex_header(self) -> List[str]:
        """Generate LaTeX document header"""
        return [
            r"\documentclass[a4paper, notitlepage, openany, DIV = 14]{scrbook}",
            r"\usepackage[x11names]{xcolor}",
            r"\usepackage{hyperref}",
            r"\hypersetup{",
            r"    colorlinks=true,",
            r"    linktoc=all,",
            r"    linkcolor=Blue4,",
            r"}",
            r"\usepackage{longtable}",
            r"\usepackage{booktabs}",
            r"\usepackage{array}",
            r"",
            r"\usepackage{polyglossia}",
            r"\setmainlanguage{english}",
            r"\setotherlanguage{arabic}",
            r"\setmainfont{Charis}",
            r"\newfontfamily\arabicfont[Script=Arabic]{Noto Naskh Arabic}",
            r"\newfontfamily\arabicfonttt[Script=Arabic]{Noto Kufi Arabic}",
            r"\newfontfamily\symbolfont{Symbola}",
            r"\newcommand{\ar}[1]{{\textarabic{#1}}}",
            r"\newcommand{\arpar}[1]{",
            r"\begin{Arabic}{\Large #1}",
            r"\end{Arabic}}",
            r"",
            r"\setcounter{secnumdepth}{2}",
            r"",
            r"\title{Arabic Textbook (LLM Processed)}",
            r"\author{Processed from OCR output}",
            r"",
            r"\begin{document}",
            r"\maketitle",
            r"\tableofcontents",
            r"\clearpage",
            r"",
        ]

    def process_file(self, input_file: Path):
        """Main file processing logic"""
        with open(input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Start with LaTeX header
        self.tex_content = self.write_tex_header()

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # Check for metadata line (page number)
            page_num = self.parse_metadata_line(line)
            if page_num is not None:
                self.current_page = page_num
                i += 1
                continue

            # Check for lesson start
            lesson_info = self.detect_lesson_start(line)
            if lesson_info:
                self.current_lesson, self.lesson_header = lesson_info

                # Add chapter heading
                self.tex_content.append(
                    f"\\chapter{{{tex_cleanup_text(self.lesson_header)}}}"
                )
                self.tex_content.append("")

                # Reset section states
                self.in_vocabulary_section = False
                self.in_exercise_section = False

                i += 1
                continue

            # Check for vocabulary section
            vocab_lesson = self.detect_vocabulary_section(line)
            if vocab_lesson:
                self.in_vocabulary_section = True
                self.in_exercise_section = False
                self.pending_vocabulary_entry = None  # Reset
                if vocab_lesson != self.current_lesson:
                    self.current_lesson = vocab_lesson
                self.tex_content.append(f"\\section{{Vocabulary}}")
                self.tex_content.append("")
                i += 1
                continue

            # Check for exercise section
            exercise_lesson = self.detect_exercise_section(line)
            if exercise_lesson:
                self.in_exercise_section = True
                self.in_vocabulary_section = False
                self.pending_vocabulary_entry = None  # Reset
                if exercise_lesson != self.current_lesson:
                    self.current_lesson = exercise_lesson
                self.tex_content.append(f"\\section{{Exercises}}")
                self.tex_content.append("\\begin{{enumerate}}")
                i += 1
                continue

            # Process vocabulary headers
            if self.in_vocabulary_section:
                headers = self.parse_vocabulary_headers(line)
                if headers:
                    self.vocabulary_headers = headers
                    self.current_vocab_type = "verb" if "PERFECT" in headers else "noun"
                    i += 1
                    continue

                # Parse vocabulary lines (lines with Arabic text)
                vocab_entry = self.parse_vocabulary_line(line)
                if vocab_entry:
                    # Check if this completes a pending entry
                    if (
                        self.pending_vocabulary_entry
                        and not vocab_entry["english_translations"]
                    ):
                        # This line might be a continuation, skip it
                        i += 1
                        continue

                    self.vocabulary_data.append(vocab_entry)
                    self.pending_vocabulary_entry = vocab_entry
                    i += 1
                    continue

                # Check if this line continues a previous vocabulary entry
                if (
                    self.pending_vocabulary_entry
                    and line.strip()
                    and not self.is_arabic_text(line)
                    and not line.strip().isupper()
                ):

                    # This looks like a continuation line (e.g., "ment, book")
                    if (
                        self.pending_vocabulary_entry["english_translations"]
                        == "(translation on next line)"
                    ):
                        self.pending_vocabulary_entry["english_translations"] = (
                            line.strip()
                        )
                    else:
                        self.pending_vocabulary_entry["english_translations"] += (
                            " " + line.strip()
                        )
                    i += 1
                    continue

            # Process table rows in vocabulary section (fallback for table format)
            if self.in_vocabulary_section and self.vocabulary_headers:
                columns = self.parse_table_row(line)
                if columns and len(columns) >= 2:
                    # Use the new vocabulary parsing for table rows too
                    vocab_entry = {
                        "page_number": self.current_page,
                        "lesson_number": self.current_lesson,
                        "column1": columns[0] if len(columns) > 0 else "",
                        "column2": columns[1] if len(columns) > 1 else "",
                        "column3": columns[2] if len(columns) > 2 else "",
                        "english_translations": columns[-1] if columns else "",
                        "verb_form": "",
                        "part_of_speech": self.current_vocab_type,
                    }
                    self.vocabulary_data.append(vocab_entry)
                    i += 1
                    continue

            # Process exercise lines
            if self.in_exercise_section:
                exercise_data = self.parse_exercise_line(line)
                if exercise_data:
                    self.exercises_data.append(exercise_data)

                    # Add to TeX with warning if invalid reference
                    warning_comment = ""
                    if exercise_data["validation_warning"]:
                        warning_comment = (
                            f" % WARNING: {exercise_data['validation_warning']}"
                        )

                    self.tex_content.append(
                        f"\\item {self.format_arabic_for_tex(exercise_data['arabic_text'])}"
                        f" [{exercise_data['quranic_reference']}]{warning_comment}"
                    )
                    i += 1
                    continue

                # Check if we're leaving the exercise section
                if (
                    line.strip()
                    and not re.match(r"^\d+\.", line.strip())
                    and not line.startswith("###")
                    and not self.is_arabic_text(line)
                    and len(line.strip()) > 10
                ):  # Probably a new section
                    self.tex_content.append("\\end{enumerate}")
                    self.in_exercise_section = False

            # Regular content processing
            if line.strip() and not line.startswith("###"):
                # Extract Arabic words for tracking
                self.extract_arabic_words(line, self.current_page)

                # Convert markdown to TeX
                tex_line = self.convert_markdown_to_tex(line)

                # Handle Arabic text
                if self.is_arabic_text(line):
                    tex_line = self.format_arabic_for_tex(line)
                else:
                    tex_line = tex_cleanup_text(tex_line)

                # Handle headings
                if line.startswith("#"):
                    level = len(line) - len(line.lstrip("#"))
                    heading_text = line.lstrip("# ").strip()

                    if level == 1:
                        tex_line = f"\\chapter{{{tex_cleanup_text(heading_text)}}}"
                    elif level == 2:
                        tex_line = f"\\section{{{tex_cleanup_text(heading_text)}}}"
                    elif level == 3:
                        tex_line = f"\\subsection{{{tex_cleanup_text(heading_text)}}}"
                    else:
                        tex_line = (
                            f"\\subsubsection{{{tex_cleanup_text(heading_text)}}}"
                        )

                self.tex_content.append(tex_line)
                if not tex_line.startswith("\\"):
                    self.tex_content.append("")

            i += 1

        # Close document
        self.tex_content.append("\\end{document}")

    def write_outputs(self):
        """Write all output files"""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")

        # Write TeX file
        tex_file = f"{self.output_prefix}.tex"
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write("\n".join(self.tex_content))
        print(f"TeX file written to: {tex_file}")

        # Write Arabic words CSV
        words_csv = f"{self.output_prefix}-arabic-words.csv"
        with open(words_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Arabic Word", "Count", "Pages"])

            for word, data in sorted(self.arabic_words.items()):
                pages = ", ".join(map(str, sorted(data["pages"])))
                writer.writerow([word, data["count"], pages])
        print(
            f"Arabic words CSV written to: {words_csv} ({len(self.arabic_words)} words)"
        )

        # Write vocabulary CSV
        vocab_csv = f"{self.output_prefix}-vocabulary.csv"
        with open(vocab_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Page Number",
                    "Lesson Number",
                    "Column 1",
                    "Column 2",
                    "Column 3",
                    "English Translations",
                    "Verb Form",
                    "Part of Speech",
                ]
            )

            for entry in self.vocabulary_data:
                writer.writerow(
                    [
                        entry["page_number"],
                        entry["lesson_number"],
                        entry["column1"],
                        entry["column2"],
                        entry["column3"],
                        entry["english_translations"],
                        entry["verb_form"],
                        entry["part_of_speech"],
                    ]
                )
        print(f"Vocabulary CSV written to: {vocab_csv}")

        # Write exercises CSV
        exercises_csv = f"{self.output_prefix}-exercises.csv"
        with open(exercises_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Page Number",
                    "Lesson Number",
                    "Exercise Number",
                    "Arabic Text",
                    "Quran Chapter/Surah",
                    "Quran Verse/Ayah",
                    "Warning",
                ]
            )

            for entry in self.exercises_data:
                writer.writerow(
                    [
                        entry["page_number"],
                        entry["lesson_number"],
                        entry["exercise_number"],
                        entry["arabic_text"],
                        entry["surah"],
                        entry["ayah"],
                        entry["validation_warning"],
                    ]
                )
        print(f"Exercises CSV written to: {exercises_csv}")

        # Write JSON file compatible with arabic-textbook-to-tex-file.py
        self.write_json_output(timestamp)

    def write_json_output(self, timestamp: str):
        """Write JSON output compatible with existing textbook processor"""
        # Convert vocabulary data to expected format
        vocabulary_json = []
        for entry in self.vocabulary_data:
            if entry["part_of_speech"] == "verb":
                arabic_words = {
                    "perfect": entry["column1"],
                    "imperfect": entry["column2"],
                    "verbal-noun": entry["column3"],
                }
            else:
                arabic_words = {
                    "singular": entry["column1"],
                    "dual": entry["column2"],
                    "plural": entry["column3"],
                }

            # Extract sort letter from first non-empty Arabic word
            sort_word = entry["column1"] or entry["column2"] or entry["column3"]
            sort_letter = sort_word[0] if sort_word else ""

            # Parse English meanings for definitions
            english_meanings = entry["english_translations"]
            definitions = []
            if english_meanings:
                for meaning in english_meanings.split(","):
                    meaning = meaning.strip()
                    if meaning:
                        definitions.append(
                            {
                                "english_definition": meaning,
                                "source_name": "textbook_llm_ocr",
                                "english_sort_letter": (
                                    meaning[0].upper() if meaning else ""
                                ),
                                "english_sort_start_index": 0,
                            }
                        )

            vocab_entry = {
                "chapter_vocab": entry["lesson_number"],
                "part_of_speech": entry["part_of_speech"],
                "arabic_words": arabic_words,
                "arabic_sort_letter": sort_letter,
                "arabic_sort_start_index": 0,
                "english_meanings": english_meanings,
                "english_meanings_sort_letter": (
                    english_meanings[0].upper() if english_meanings else ""
                ),
                "english_meanings_sort_start_index": 0,
                "source_name": "textbook_llm_ocr",
                "definitions": definitions,
            }

            vocabulary_json.append(vocab_entry)

        # Convert exercises data to expected format
        exercises_json = []
        for entry in self.exercises_data:
            exercise_entry = {
                "exercise_text": entry["arabic_text"],
                "exercise_chapter": entry["lesson_number"],
                "exercise_number": entry["exercise_number"],
                "quranic_reference": entry["quranic_reference"],
                "surah": entry["surah"],
                "ayah": entry["ayah"],
                "quranic_sources": [],
                "validation_warning": entry["validation_warning"],
            }

            exercises_json.append(exercise_entry)

        # Create complete JSON structure
        json_data = {
            "lesson": {
                "source": f"LLM OCR processed on {timestamp}",
                "processing_date": timestamp,
            },
            "vocabulary": vocabulary_json,
            "exercises": exercises_json,
        }

        # Write JSON file
        json_file = f"arabic-textbook-llm-{timestamp.replace(':', '')}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        print(f"JSON file written to: {json_file}")


def main():
    parser = argparse.ArgumentParser(description="Process LLM OCR textbook output")
    parser.add_argument("input_file", help="Input markdown file from LLM OCR")
    parser.add_argument(
        "-o",
        "--output-prefix",
        default="textbook-llm",
        help="Output file prefix (default: textbook-llm)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file {input_path} does not exist")
        return 1

    processor = TextbookProcessor(args.output_prefix)
    processor.process_file(input_path)
    processor.write_outputs()

    print("Processing completed successfully!")
    return 0


if __name__ == "__main__":
    exit(main())
