#!/usr/bin/env python3

import argparse
import csv
import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# import re
import regex as re  # 'better' unicode support, allows for `\p{Script_Extensions=Arabic}`

from tex_utils import tex_cleanup_text, tex_remove_arabic_marks

# Quran data for validation (114 chapters/suras)
QURAN_CHAPTERS = {1: 7,  # Al-Fatihah
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

# @formatter:off # fmt: off
NUMBER_WORDS_TO_INTEGERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "twenty-one": 21,
    "twenty-two": 22,
    "twenty-three": 23,
    "twenty-four": 24,
    "twenty-five": 25,
    "twenty-six": 26,
    "twenty-seven": 27,
    "twenty-eight": 28,
    "twenty-nine": 29,
    "thirty": 30,
    "thirty-one": 31,
    "thirty-two": 32,
    "thirty-three": 33,
    "thirty-four": 34,
    "thirty-five": 35,
    "thirty-six": 36,
    "thirty-seven": 37,
    "thirty-eight": 38,
    "thirty-nine": 39,
    "forty": 40,
}
# @formatter:on # fmt: on

# CHARSET_ARABIC = r"[\u0600-\u06FF]"
# CHARSET_ARABIC_ALL = r"[\u0600–\u06ff\u0750–\u077f\u0870–\u089f\u08a0–\u08ff\ufb50–\ufdff\ufe70–\ufeff]"
# below did not work
# CHARSET_ARABIC_ALL = r"[\u0600–\u06ff\u0750–\u077f\u0870–\u089f\u08a0–\u08ff\ufb50–\ufdff\ufe70–\ufeff\u10e60–\u10e7F\u10ec0-\u10efF\u1ec70–\u1ecbF\u1ed00–\u1ed4F\u1ee00–\u1eefF]"

CHARSET_ARABIC = r"\p{Script=Arabic}"
CHARSET_ARABIC_ALL = r"\p{Script_Extensions=Arabic}"


def construct_section_match_pattern(section_type: str) -> str:
    """Construct a regex pattern to detect the start of a section (Vocabulary or Exercise)"""

    temp_pattern = r""
    for key in NUMBER_WORDS_TO_INTEGERS:
        temp_pattern += key.upper() + "|"

    if section_type == "vocabulary":
        return r"^VOCABULARY\s+(" + temp_pattern + r"\d+)$"
    elif section_type == "exercise":
        return r"^EXERCISE\s+(" + temp_pattern + r"\d+)$"
    else:
        logging.warning(f"Invalid section type: {section_type}")
        return r"FAILED TO DETECT SECTION TYPE"  # TODO make an actual error here...


def convert_written_number(word: str) -> int:
    """Convert written numbers to integers"""

    word_lower = word.lower()
    if word_lower in NUMBER_WORDS_TO_INTEGERS:
        return NUMBER_WORDS_TO_INTEGERS[word_lower]

    # Try to parse as integer
    try:
        return int(word)
    except ValueError:
        return 0


def contains_arabic_text(text: str) -> bool:
    """Check if text contains Arabic characters"""

    return bool(re.search(r"\p{Script_Extensions=Arabic}", text))


def validate_quran_reference(surah: int, ayah: int) -> Tuple[bool, str]:
    """Validate Quran reference and return validation status and warning message"""

    if surah < 1 or surah > 114:
        return False, f"Chapter {surah} is invalid (valid range: 1-114)"

    if ayah < 1 or ayah > QURAN_CHAPTERS[surah]:
        return False, f"Verse {ayah} is invalid for chapter {surah} (valid range: 1-{QURAN_CHAPTERS[surah]})",

    return True, ""


def write_tex_header() -> List[str]:
    """Generate LaTeX document header"""

    # @formatter:off # fmt: off
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
    # @formatter:on # fmt: on


def format_arabic_for_tex(text: str) -> str:
    """Format Arabic text appropriately for LaTeX"""

    if not contains_arabic_text(text):
        return tex_cleanup_text(text)

    # If it's a short phrase (< 50 chars), use inline Arabic
    if len(text) < 50:
        return f"\\ar{{{tex_cleanup_text(text)}}}"
    else:
        # For longer text, use paragraph Arabic
        return f"\\arpar{{\n{tex_remove_arabic_marks(text)}\n}}"


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

    def extract_arabic_words(self, text: str, page_num: int):
        """Extract individual Arabic words from the text and track them"""

        # Find all Arabic words (sequences of Arabic characters)
        arabic_words = re.findall(r"\p{Script_Extensions=Arabic}+", text)

        for word in arabic_words:
            # Clean up the word (remove diacritics for counting)
            clean_word = tex_remove_arabic_marks(word)
            if clean_word:
                self.arabic_words[clean_word]["count"] += 1
                self.arabic_words[clean_word]["pages"].add(page_num)

    def parse_metadata_line(self, line: str) -> Optional[int]:
        """Parse metadata line to extract page number"""

        # Pattern: ### START FILE 10, Extracted Page 112
        match = re.match(r"### START FILE \d+, Extracted Page (\d+)", line)
        if match:
            return int(match.group(1))

        # Alternative pattern without page number
        match = re.match(r"### START FILE \d+, Extracted Page\s*$", line)
        if match:
            return self.current_page + 1  # Increment from the last-known page

        return None

    def detect_lesson_start(self, line: str) -> Optional[Tuple[int, str]]:
        """Detect lesson start and extract lesson number and header"""

        # Pattern: ## CHAPTER 12
        match = re.match(r"## CHAPTER (\d{1,2})", line)
        if match:
            return int(match.group(1)), line.strip()
        return None

    def detect_vocabulary_section(self, line: str) -> Optional[int]:
        """Detect vocabulary section start and return lesson number"""

        match = re.match(construct_section_match_pattern("vocabulary"), line, re.IGNORECASE, )
        if match:
            return convert_written_number(match.group(1))
        return None

    def detect_exercise_section(self, line: str) -> Optional[int]:
        """Detect exercise section start and return lesson number"""

        match = re.match(construct_section_match_pattern("exercise"), line, re.IGNORECASE, )
        if match:
            return convert_written_number(match.group(1))
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
        elif re.search(r"SINGULAR", line, re.IGNORECASE):
            return ["SINGULAR"]

        if re.search(r"Idioms", line, re.IGNORECASE):
            return ["Idioms"]

        return None

    def parse_vocabulary_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a vocabulary line that contains Arabic words and English translations"""

        line = line.strip()
        if not line or not contains_arabic_text(line):
            return None

        # Pattern for early chapter's vocabulary: Arabic transliteration [Arabic transliteration] English
        # Example: "اَللهُ Allāhu God" or "إِلٰهٌ ilāhun آلِهَةٌ ālihatun a god"

        ## Split into parts and identify Arabic vs. transliteration vs. English
        verb_form_number = ""  # to fill in column as empty for nouns, or for verbs without the verb form number specified


        ## Parse out verb form (number) if present, should always be enclosed by braces after editing the output file
        # hmm though I guess could just assume any number in a vocab row is a verb form??
        if self.current_vocab_type == "verb":
            # Remove verb form number if present, can be anywhere in line
            verb_form_number = ""
            pattern_verb_form = r"\s*\{(\d{1,2})\}\s*"  # e.g. `{2}` or `{10}`
            verb_form_match = re.search(pattern_verb_form, line)
            if verb_form_match:
                verb_form_number = verb_form_match.group(1)
                line = re.sub(pattern_verb_form, " ", line)

        # oooof there are so many odd variations, just split on spaces and then deal with
        # find things that change how we process
        index_line_sng = line.find("(s.)")
        pattern_plural = r"\(.*\s?pl\.\s?.*\)"
        match_plural = re.search(pattern_plural, line)
        # index_line_pl = line.find("(pl.)")

        # Keep words separate by slash together
        # Remove spaces around slash and replace them later
        pattern_slash_spaces = r"\s*\/\s*"
        line = re.sub(pattern_slash_spaces, "/", line)

        parts = line.split()
        if len(parts) < 2:  # there should be at least on arabic word and one english word
            return None

        arabic_words = []
        transliterations = []
        english_parts = []

        # go throught split parts of line, use while loop so I can process successive elements when needed (e.g. transliterations)
        i = 0
        while i < len(parts):
            part = parts[i]
            part_with_slash_spaces = re.sub(pattern_slash_spaces, " / ", part)  # does nothing if no slashses

            if contains_arabic_text(part):
                # ok so it contains arabic text
                if not english_parts:
                    # haven't hit any english words yet, so should be one fo the main 3 columns of vocab
                    arabic_words.append(part)
                else:
                    # ok we already hit some english, but that could include the random gender parentheticals
                    if len(english_parts) < 2:
                        # only one english part, let's call it fine
                        arabic_words.append(part)
                    elif self.current_vocab_type == "idiom":
                        arabic_words.append(part)
                    else:
                        # maybe it is some note "from this word..." or e.g. vocab 11: نَظَرَ يَنْظُرُ نَظَرٌ to look at (إِلَىٰ), into (فِي)
                        english_parts.append(part)

                i += 1
                # we just had some arabic, the next part might be a transliteration (lowercase, non-Arabic charset)
                if self.current_lesson <= 5:  # the textbook only has transliterations for lesson 1 through 5
                    if i < len(parts) and not contains_arabic_text(parts[i]) and parts[i][0].islower():
                        transliterations.append(parts[i])
                        i += 1
            else:
                english_parts.append(part)
                i += 1

        if english_parts:
            english_text = " ".join(english_parts)
        else:
            english_text = ""
            logging.warning(f"No English text found in vocabulary line: {line}")

        if not arabic_words:
            return None

        # Now we assign parts to columns based on count
        # Col1: Sing. / Perf.
        # Col2: Dual / Imperf.
        # Col3: Plural / Verbal N.

        if len(arabic_words) > 3:
            # ugh what happened with this then?
            logging.warning(f"More than 3 Arabic words in vocabulary line: {line}")
            # shunt to english part?
            english_text += ";; " + " ".join(arabic_words[3:])  # remember zero indexed ha

        # Assign default guesses
        col1 = arabic_words[0] if len(arabic_words) > 0 else ""
        col2 = ""  # fallback
        col3 = ""  # fallback
        if self.current_vocab_type == "verb":
            # Verb forms are always 3 columns
            col1 = arabic_words[0] if len(arabic_words) > 0 else ""
            col2 = arabic_words[1] if len(arabic_words) > 1 else ""
            col3 = arabic_words[2] if len(arabic_words) > 2 else ""
        elif self.current_vocab_type == "noun":
            if len(self.vocabulary_headers) == 1:  # Vocabulary for 25 switches to just one header 'singular' on page 160, ugh
                if self.vocabulary_headers[0] == "SINGULAR":
                    col1 = arabic_words[0] if len(arabic_words) > 0 else ""
                    col2 = ""  # fallback
                    col3 = ""  # fallback
                elif self.vocabulary_headers[0] == "DUAL":
                    col1 = ""  # fallback
                    col2 = arabic_words[0] if len(arabic_words) > 0 else ""
                    col3 = ""  # fallback
                elif self.vocabulary_headers[0] == "PLURAL":
                    col1 = ""  # fallback
                    col2 = ""  # fallback
                    col3 = arabic_words[0] if len(arabic_words) > 0 else ""
                else:
                    logging.warning(f"Unexpected vocabulary header: {self.vocabulary_headers[0]}")
                    col1 = ""  # fallback
                    col2 = ""  # fallback
                    col3 = ""  # fallback
            elif len(self.vocabulary_headers) == 2:
                # handle the occasional vocab line that only has the plural form
                if len(arabic_words) == 1:
                    # Check if (pl.) was on the line, (s.) was NOT, and only one column of arabic text,
                    # then assign to the plural column
                    if index_line_sng == -1 and match_plural:
                        logging.debug(
                            f"Plural abbreviation found on line without singular abbreviation, moving it to Plural columng: {line}")
                        col1 = ""
                        col3 = arabic_words[0]  # the `else` was already done above as a default.
                elif len(arabic_words) > 1:
                    col3 = arabic_words[1]
                    if len(arabic_words) > 2:
                        logging.warning(
                            f"We have 2 Column headers, but the vocabulary line has more than 2 Arabic words: {line}")
                        logging.warning("Shunting {} to English part.".format(" ".join(arabic_words[2:])))
                        english_text += ";; " + " ".join(arabic_words[2:])
            elif len(self.vocabulary_headers) == 3:
                if len(arabic_words) == 1:
                    # Check if (pl.) was on the line, (s.) was NOT, and only one column of arabic text,
                    # then assign to the plural column
                    if index_line_sng == -1 and match_plural:
                        logging.debug(
                            f"Plural abbreviation found on line without singular abbreviation, moving it to Plural columng: {line}")
                        col1 = ""
                        col3 = arabic_words[0]  # the `else` was already done above as a default.
                if len(arabic_words) > 1:
                    col2 = arabic_words[1]
                if len(arabic_words) > 2:
                    col3 = arabic_words[2]
        elif self.current_vocab_type == "idiom":
            col1 = " ".join(arabic_words) if len(arabic_words) > 0 else ""
            col2 = ""  # fallback
            col3 = ""  # fallback
        else:
            logging.warning(f"Unexpected vocabulary type ({self.current_vocab_type}) for line: {line}")
            return None

        return {"page_number": self.current_page, "lesson_number": self.current_lesson, "column1": col1,
                "column2": col2, "column3": col3, "english_translations": english_text, "verb_form": verb_form_number,
                "part_of_speech": self.current_vocab_type, "transliterations": " ".join(transliterations),
                "raw_line": line,  # Keep original for debugging
                }

    def parse_exercise_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse an exercise line to extract number, Arabic text, and Quran reference"""

        line = line.strip()

        # Look for exercise number at start
        # exercise_match = re.match(r"^(\d+)\.?\s*(.*)", line)
        exercise_match = re.match(r"^(\d+)\.\s*(.*" + CHARSET_ARABIC_ALL + r".*)", line)
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
            is_valid, validation_msg = validate_quran_reference(surah, ayah)
            if not is_valid:
                warning = validation_msg

            # Remove reference from text
            remaining_text = re.sub(r"\[\d+:\d+\]", "", remaining_text).strip()

        return {"page_number": self.current_page, "lesson_number": self.current_lesson, "exercise_number": exercise_num,
                "arabic_text": remaining_text, "surah": surah, "ayah": ayah, "quranic_reference": quran_ref,
                "validation_warning": warning, }

    def convert_markdown_to_tex(self, line: str) -> str:
        """Convert Markdown formatting to LaTeX"""

        # Bold: **text** or __text__ -> \textbf{text}
        line = re.sub(r"\*\*(.*?)\*\*", r"\\textbf{\1}", line)
        line = re.sub(r"__(.*?)__", r"\\textbf{\1}", line)

        # Italic: *text* or _text_ -> \textit{text}
        line = re.sub(r"\*(.*?)\*", r"\\textit{\1}", line)
        line = re.sub(r"_(.*?)_", r"\\textit{\1}", line)

        # Code: `text` -> \texttt{text}
        line = re.sub(r"`(.*?)`", r"\\texttt{\1}", line)

        return line

    def process_file(self, input_file: Path):
        """Main file processing logic"""

        with open(input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Start with the LaTeX header
        self.tex_content = write_tex_header()

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
                self.tex_content.append(f"\\chapter{{{tex_cleanup_text(self.lesson_header)}}}")
                self.tex_content.append("")

                # Reset section states
                self.in_vocabulary_section = False
                self.in_exercise_section = False

                i += 1
                continue

            # Check for the start of the vocabulary section
            if not self.in_vocabulary_section and not self.in_exercise_section:
                vocab_lesson = self.detect_vocabulary_section(line)
                if vocab_lesson:
                    self.in_vocabulary_section = True
                    self.in_exercise_section = False
                    self.pending_vocabulary_entry = None  # Reset
                    if vocab_lesson != self.current_lesson:
                        logging.warning("Vocab section number does not match Lesson number.")
                    self.tex_content.append(f"\\section{{Vocabulary}}")
                    self.tex_content.append("")
                    i += 1
                    continue

            # Check for the start of the exercise section (which is always after the vocabulary section)
            if self.in_vocabulary_section:
                exercise_lesson = self.detect_exercise_section(line)
                if exercise_lesson:
                    self.in_exercise_section = True
                    self.in_vocabulary_section = False
                    self.pending_vocabulary_entry = None  # Reset
                    if exercise_lesson != self.current_lesson:
                        logging.warning("Exercise section number does not match Lesson number.")
                    self.tex_content.append(f"\\section{{Exercises}}")
                    self.tex_content.append("\\begin{{enumerate}}")
                    i += 1
                    continue

            # Process vocabulary headers
            if self.in_vocabulary_section:
                if "Idioms" in line:
                    logging.debug(f"Idioms section on page {self.current_page}")
                headers = self.parse_vocabulary_headers(line)
                if headers:
                    self.vocabulary_headers = headers
                    if "PERFECT" in headers:
                        self.current_vocab_type = "verb"
                    elif "SINGULAR" in headers:
                        self.current_vocab_type = "noun"
                    elif "Idioms" in headers:
                        self.current_vocab_type = "idiom"
                    else:
                        logging.warning(f"Unrecognized vocabulary headers: {headers}")
                        self.current_vocab_type = "other"
                    i += 1
                    continue

                # Parse vocabulary lines (lines with Arabic text)
                vocab_entry = self.parse_vocabulary_line(line)
                if vocab_entry:
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
                        warning_comment = f" % WARNING: {exercise_data['validation_warning']}"

                    # TODO fix this overcomplication
                    self.tex_content.append(f"\\item {format_arabic_for_tex(exercise_data['arabic_text'])}"
                                            f" [{exercise_data['quranic_reference']}]{warning_comment}")
                    i += 1
                    continue

                # Check if we're leaving the exercise section
                if (line.strip() and not re.match(r"^\d+\.", line.strip()) and not line.startswith(
                        "###") and not contains_arabic_text(line) and len(line.strip()) > 10):  # Probably a new section
                    self.tex_content.append("\\end{enumerate}")
                    self.in_exercise_section = False

            # Regular content processing
            if line.strip() and not line.startswith("###"):
                # Extract Arabic words for tracking
                self.extract_arabic_words(line, self.current_page)

                # Convert Markdown to TeX
                tex_line = self.convert_markdown_to_tex(line)

                # Handle Arabic text
                # FIXME: check what in line is actually Arabic text and wrap the word(s)
                if contains_arabic_text(line):
                    tex_line = format_arabic_for_tex(line)
                else:
                    tex_line = tex_cleanup_text(tex_line)

                # TODO fix this up
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
                        tex_line = f"\\subsubsection{{{tex_cleanup_text(heading_text)}}}"

                self.tex_content.append(tex_line)
                if not tex_line.startswith("\\"):
                    self.tex_content.append("")

            i += 1

        # Close document
        self.tex_content.append("\\end{document}")

    def write_outputs(self):
        """Write all output files"""

        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")

        # # Write TeX file
        # tex_file = f"{self.output_prefix}.tex"
        # with open(tex_file, "w", encoding="utf-8") as f:
        #     f.write("\n".join(self.tex_content))
        # logging.info(f"TeX file written to: {tex_file}")

        # Write Arabic words CSV
        words_csv = f"{self.output_prefix}-arabic-words.csv"
        with open(words_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Arabic Word", "Count", "Pages"])

            for word, data in sorted(self.arabic_words.items()):
                pages = ", ".join(map(str, sorted(data["pages"])))
                writer.writerow([word, data["count"], pages])
        logging.info(f"Arabic words CSV written to: {words_csv} ({len(self.arabic_words)} words)")

        # Write vocabulary CSV
        vocab_csv = f"{self.output_prefix}-vocabulary.csv"
        with open(vocab_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Page Number", "Lesson Number", "Column 1", "Column 2", "Column 3", "English Translations",
                             "Verb Form", "Part of Speech", ])

            for entry in self.vocabulary_data:
                writer.writerow(
                    [entry["page_number"], entry["lesson_number"], entry["column1"], entry["column2"], entry["column3"],
                     entry["english_translations"], entry["verb_form"], entry["part_of_speech"], ])
        logging.info(f"Vocabulary CSV written to: {vocab_csv}")

        # Write exercises CSV
        exercises_csv = f"{self.output_prefix}-exercises.csv"
        with open(exercises_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Page Number", "Lesson Number", "Exercise Number", "Arabic Text", "Quran Chapter/Surah",
                             "Quran Verse/Ayah", "Warning", ])

            for entry in self.exercises_data:
                writer.writerow(
                    [entry["page_number"], entry["lesson_number"], entry["exercise_number"], entry["arabic_text"],
                     entry["surah"], entry["ayah"], entry["validation_warning"], ])
        logging.info(f"Exercises CSV written to: {exercises_csv}")

        # Write the JSON file compatible with arabic-textbook-to-tex-file.py
        self.write_json_output(timestamp)

    def write_json_output(self, timestamp: str):
        """Write JSON output compatible with the existing textbook processor"""

        # Convert vocabulary data to the expected format
        vocabulary_json = []
        for entry in self.vocabulary_data:
            if entry["part_of_speech"] == "verb":
                arabic_words = {"perfect": entry["column1"], "imperfect": entry["column2"],
                                "verbal-noun": entry["column3"], }
            else:
                arabic_words = {"singular": entry["column1"], "dual": entry["column2"], "plural": entry["column3"], }

            # Extract sort letter from the first non-empty Arabic word
            sort_word = entry["column1"] or entry["column2"] or entry["column3"]
            sort_letter = sort_word[0] if sort_word else ""

            # Parse English meanings for definitions
            english_meanings = entry["english_translations"]
            definitions = []
            if english_meanings:
                for meaning in english_meanings.split(","):
                    meaning = meaning.strip()
                    if meaning:
                        definitions.append({"english_definition": meaning, "source_name": "textbook_llm_ocr",
                                            "english_sort_letter": (meaning[0].upper() if meaning else ""),
                                            "english_sort_start_index": 0, })

            vocab_entry = {"chapter_vocab": entry["lesson_number"], "part_of_speech": entry["part_of_speech"],
                           "arabic_words": arabic_words, "arabic_sort_letter": sort_letter,
                           "arabic_sort_start_index": 0, "english_meanings": english_meanings,
                           "english_meanings_sort_letter": (english_meanings[0].upper() if english_meanings else ""),
                           "english_meanings_sort_start_index": 0, "source_name": "textbook_llm_ocr",
                           "definitions": definitions, }

            vocabulary_json.append(vocab_entry)

        # Convert exercises data to expected format
        exercises_json = []
        for entry in self.exercises_data:
            exercise_entry = {"exercise_text": entry["arabic_text"], "exercise_chapter": entry["lesson_number"],
                              "exercise_number": entry["exercise_number"],
                              "quranic_reference": entry["quranic_reference"], "surah": entry["surah"],
                              "ayah": entry["ayah"], "quranic_sources": [],
                              "validation_warning": entry["validation_warning"], }

            exercises_json.append(exercise_entry)

        # Create a complete JSON structure
        json_data = {"lesson": {"source": f"LLM OCR processed on {timestamp}", "processing_date": timestamp, },
                     "vocabulary": vocabulary_json, "exercises": exercises_json, }

        # Write JSON file
        json_file = f"arabic-textbook-llm-{timestamp.replace(':', '')}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        logging.info(f"JSON file written to: {json_file}")


def main():
    parser = argparse.ArgumentParser(description="Process LLM OCR textbook output")
    parser.add_argument("input_file", help="Input markdown file from LLM OCR")
    parser.add_argument("-o", "--output-prefix", default="textbook-llm",
                        help="Output file prefix (default: textbook-llm)", )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    input_path = Path(args.input_file)
    if not input_path.exists():
        logging.critical(f"Input file {input_path} does not exist. EXITING.")
        return 1

    processor = TextbookProcessor(args.output_prefix)
    processor.process_file(input_path)
    processor.write_outputs()

    logging.info("Processing completed successfully!")
    return 0


if __name__ == "__main__":
    exit(main())
