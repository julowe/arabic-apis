from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pandas as pd

import re


def read_csv(filepath: str | Path) -> list[dict[str, Any]]:
    """Read a CSV file into a list of dict rows.

    The CSV is assumed to have a header row.
    """

    # Hacky 'just make it work'
    bool_found_exercise_only_headers = False
    # mapping_exercise_columns_dict = {
    #     "Page Number": "Page Number",
    #     "Lesson Number": "Lesson #",
    #     "Exercise Number": "Exercise #",
    #     "Arabic Text": "Sing. / Perf.",
    #     "Quran Chapter/Surah": "Sura",
    #     "Quran Verse/Ayah": "Verse",
    #     "Warning": "Warning",
    # }
    bool_found_vocab_only_headers = False
    # mapping_vocab_columns_dict = {
    #     "Page Number": "Page Number",
    #     "Lesson Number": "Lesson #",
    #     "Exercise Number": "Exercise #",
    #     "Arabic Text": "Sing. / Perf.",
    #     "Quran Chapter/Surah": "Sura",
    #     "Quran Verse/Ayah": "Verse",
    #     "Warning": "Warning",
    # }
    bool_found_all_only_headers = False
    mapping_all_columns_dict = {
        "Page Number": "Page Number",
        "Lesson Number": "Lesson #",
        # "Ex/Voc": "Ex/Voc",
        # "Column 1": "Sing. / Perf.",
        # "Column 2": "Dual / Imperf.",
        # "Column 3": "Plural / Verbal N.",
        "English Translations": "English",
        # "Verb Form": "Verb Form",
        # "Part of Speech": "Part of Speech",
        "Exercise Number": "Exercise #",
        # "Arabic Text": "Arabic Text",
        "Quran Chapter/Surah": "Sura",
        "Quran Verse/Ayah": "Verse",
        # "Warning": "Warning",
    }

    rows: list[dict[str, Any]] = []
    with open(filepath, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)

        if reader.fieldnames[3] == "Sing. / Perf.":
            if reader.fieldnames[9] == "Exercise Number":
                bool_found_all_only_headers = True
            else:
                bool_found_vocab_only_headers = True
        elif reader.fieldnames[2] == "Exercise Number":
            bool_found_exercise_only_headers = True
            # row_type = "exercise"

        # see if we have column headers we expect
        for i in range(len(reader.fieldnames)):
            if bool_found_exercise_only_headers or bool_found_vocab_only_headers or bool_found_all_only_headers:
                if reader.fieldnames[i] in mapping_all_columns_dict:
                    reader.fieldnames[i] = mapping_all_columns_dict[reader.fieldnames[i]]
            else:
                print("ERROR: unexpected header in CSV: {}".format(reader.fieldnames[i]))
                exit(1)

        for row in reader:
            # Skip completely empty rows
            if not any(v for v in row.values()):
                continue

            if bool_found_exercise_only_headers:
                row.update({"Ex/Voc": "Exercise"})
            if bool_found_vocab_only_headers:
                row.update({"Ex/Voc": "Vocabulary"})

            rows.append(row)
            # FIXME: correlate data with headers
    return rows


def read_ods(filepath: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Read an ODS file into a mapping of sheet_name -> a list of dict rows.

    Uses pandas with the 'odf' engine.
    """
    xls = pd.ExcelFile(filepath, engine="odf")
    result: dict[str, list[dict[str, Any]]] = {}
    for sheet in xls.sheet_names:
        # only parse sheets with names that start with "lesson", so we don't get duplicates
        if sheet.strip().lower().startswith("lesson"):
        # if sheet.strip().lower().startswith("lesson 16"): # quick process only one sheet for debugging
            df = xls.parse(sheet)

            # Convert NaN to empty string and rows to dicts
            result[sheet] = [
                {k: ("" if pd.isna(v) else v) for k, v in rec.items()}
                for rec in df.to_dict(orient="records")
                if any(v not in (None, "") for v in rec.values())
            ]

    return result


def guess_sort_letter_arabic(arabic_string: str) -> tuple[str, int]:
    # TODO change to accept all three (possible) word forms given?
    # TODO logic to ignore... leading alif?
    if arabic_string:
        return arabic_string[0], 0
    else:
        return "", -1


def guess_sort_letter_part_of_speech_english(eng_str: str, pos: (str | None) = None) -> tuple[str, int, str]:
    """
    Infers the sort letter, the starting index for sorting, and the part of speech
    for an English string. Attempts to process and adjust the input string based
    on its structure and optionally provided part of speech (pos).

    :param eng_str: The English string to process. Must not be empty.
    :type eng_str: str
    :param pos: The part of speech of the input string, if known. Can be None if
        the part of speech is not specified.
    :type pos: str or None
    :return: A tuple containing:
        - The initial letter for sorting the input string.
        - The starting index for sorting based on structural removal.
        - The inferred or provided part of speech (e.g., "verb", "noun").
    :rtype: tuple[str, int, str]
    """

    if not eng_str:
        print("Warning: guess_sort_letter_english() called with empty string")
        return "", -1, "empty_string"

    result = "" # default to empty, don't need to guess if we are told
    test_str = eng_str.strip().lower()

    # Get rid of any starting complications
    test_str = remove_leading_parens(test_str)

    # Pattern to check if the string starts with `to` then one or more whitespaces characters and then a word character
    # i.e. don't catch `to (motion)`
    pattern = r'^to\s+\w'

    sort_start_index = 0 # default for noun or simple strings
    match = re.search(pattern, test_str)
    if match:
        result = "verb"
        sort_start_index = match.end() - 1
    else:
        result = "noun"

        # TODO do all at once and get index, or split up?
        pattern_noun = r'^(a)?(the)?(an)?\s+\w'

    sort_letter = test_str[sort_start_index]

    # many verb entries will have a second meaning that doesn't look like a verb itself
    # e.g. `to co-operate, help one another`
    if pos is not None:
        if pos == "verb" and result == "noun":
            result = pos # as this is prob a `to walk, run` king of entry
        elif pos == "noun" and result == "verb":
            print("Warning: guess_sort_letter_english() called with guess of noun, but string looks like a verb: {}, {}".format(eng_str, test_str))
            # probably drop this results from function anway

    return sort_letter, sort_start_index, result

# # def guess_sort_letter_english(english_string_array: list[str], pos_guess: str) -> list[dict[str, str]]:
# def guess_sort_letter_english(eng_str: str, pos_guess: str) -> str:
#     print(eng_str)
#     if pos_guess == "noun":
#         sort_letter_eng = eng_str[0]
#     elif pos_guess == "verb":
#         # Get rid of any starting complications
#         test_string = remove_leading_parens(test_string)
#
#
#
#         if index_close_paren != -1: #example: "(+ bi-) to see, observe"
#             eng_str = eng_str[index_close_paren+1:].strip()
#
#         if eng_str.startswith("to "): # the overall string could be "(+ bi-) to see, (+XY-) observe" ??
#             sort_letter_eng = eng_str[3]
#         else:
#             print(eng_str)
#             sort_letter_eng = eng_str[0]
#     else:
#         print("ERROR: sort_letter_english() called with unknown part of speech: {}".format(pos_guess))
#         sort_letter_eng = ""
#
#     return sort_letter_eng


def remove_leading_parens(english_string: str) -> str:
    # Get rid of any starting complications, if they exist, otherwise return same string
    # check for parentheses at start of string
    if english_string.startswith("("):  # so we don't catch `to (motion)` etc.
        index_close_paren = english_string.find(")")
        english_string = english_string[index_close_paren + 1:].strip()  # example: "(+ bi-) to see, observe"
    elif english_string.startswith("["):  # so we don't catch `to (motion)` etc.
        index_close_bracket = english_string.find("]")
        english_string = english_string[1:].strip()
        # TODO see if this is enough or can do better

    return english_string


# def verb_or_noun(english_string: str) -> tuple[str, str]:
#     """Guess if a string is a verb or noun."""
#
#     result = "" # fallback
#     index_word_start = 0
#
#     test_string = english_string.strip().lower()
#
#     # Get rid of any starting complications
#     test_string = remove_leading_parens(test_string)
#
#     # Pattern to check if the string starts with `to` then one or more whitespaces characters and then a word character
#     # i.e. don't catch `to (motion)`
#     pattern = r'^to\s+\w'
#
#     match = re.search(pattern, test_string)
#
#     if match: # whoops remember to keep that space after `to` so it doesn't catch `towards` etc.
#         result = "verb"
#
#         # # remove the start helper words from verb
#         # test_string = test_string[match.end()+1:].strip()
#         # sort_letter = test_string[0]
#     else:
#         result = "noun"
#
#     # also get the main English sort letter for the whole string/entry
#     sort_letter = guess_sort_letter_english(test_string, result)
#
#     return result, sort_letter


def build_json_from_rows(rows: list[dict[str, Any]], lesson_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a standardized JSON structure from raw textbook rows.

    Minimal schema produced:
    {
      "lesson": {...optional meta...},
      "vocabulary": [
         {"sing_perf": str, "dual_imperf": str, "plural_vn": str, "english": str}
      ],
      "exercises": []
    }
    """

    print("Info: Building JSON from rows...")

    vocab: list[dict[str, Any]] = []
    exercises: list[dict[str, Any]] = []

    part_of_speech_guessed_previous = ""
    for row in rows:
        # Get Lesson/textbook chapter number
        try:
            chapter_number = int(row.get("Lesson #"))
        except ValueError:
            print("Warning: invalid Lesson number: {}, {}".format(row.get('Lesson #'),row.get("English")))
            chapter_number = 0
        # chapter_number = str(row.get("Lesson #") or "")

        if row.get("Ex/Voc").lower() == "exercise":
            # Get Exercise number
            try:
                exercise_number = int(row.get("Exercise #"))
            except ValueError:
                print("Warning: invalid Exercise number: {}, {}".format(row.get('Exercise #'), row.get("English")))
                exercise_number = 0
                # exercise_number = str(row.get("Exercise #") or "")
                try:
                    if row.get("Exercise #") == "B": #handle special case of Lesson 3
                        exercise_number = 21
                        exercises.append(
                            {
                                "exercise_text": "{}: {}".format(str(row.get("Sing. / Perf.", "") or ""),str(row.get("Plural / Verbal N.", "") or "")),
                                "exercise_chapter": chapter_number,
                                "exercise_number": exercise_number,
                                "quranic_reference": "",
                                "surah": 0,
                                "ayah": 0,
                            }
                        )
                        continue
                except:
                    print("ERROR: Really could not parse this Exercise...")


            if row.get("Sura"):
                sura = int(row.get("Sura"))
            else:
                sura = 0
                # TODO some fallback?? or at least logging/print complain?

            if row.get("Verse"):
                verse = int(row.get("Verse"))
            else:
                verse = 0
                # TODO some fallback?? or at least logging/print complain?

            try:
                qref = f"{int(sura)}:{int(verse)}" if sura and verse else ""
            except (TypeError, ValueError):
                qref = ""

            exercise_string = ""
            if "Arabic Text" in row:
                exercise_string = str(row.get("Arabic Text"))
            elif "Sing. / Perf." in row:
                exercise_string = str(row.get("Sing. / Perf.", ""))
            else:
                print("ERROR: Could not find Arabic Text or Sing. / Perf. in row: {}".format(row))

            exercises.append(
                {
                    "exercise_text": exercise_string,
                    "exercise_chapter": chapter_number,
                    "exercise_number": exercise_number,
                    "quranic_reference": qref,
                    "surah": sura,
                    "ayah": verse,
                    "quranic_sources": []
                }
            )
        elif row.get("Ex/Voc").lower() == "vocabulary":
            english_meanings = row.get("English") or ""

            ## Get sort letter of main string and guess if noun or verb
            english_meanings_sort_letter_guessed, english_meanings_sort_index_guessed, part_of_speech_guessed = guess_sort_letter_part_of_speech_english(english_meanings)

            if part_of_speech_guessed == "noun" and row.get("Sing. / Perf.") and row.get("Dual / Imperf.") and row.get("Plural / Verbal N."):
                print("Warning: row was guessed as a noun, but has all three forms filled out for Lesson {}: {}".format(
                    chapter_number, english_meanings))
                # TODO maybe we'll get this more often now? or maybe just delete this "check"?
                if part_of_speech_guessed_previous == "verb":
                    print("Warning: ...and the previous row was guessed as a verb, so let's just change this to a verb too")
                    part_of_speech_guessed = part_of_speech_guessed_previous

            part_of_speech_guessed_previous = part_of_speech_guessed

            string_col_1 = str(row.get("Sing. / Perf.", "") or "").strip()
            string_col_2 = str(row.get("Dual / Imperf.", "") or "").strip()
            string_col_3 = str(row.get("Plural / Verbal N.", "") or "").strip()

            # TODO: search for and split out any gender in strings here? i.e. remove (f.) and such variations to their own field?? or just leave and always parse out as needed?
            ## Guess the sort letter for arabic word
            # TODO have more than one sort letter?? or just more confusing
            if string_col_1:
                string_to_guess = string_col_1
            elif string_col_2:
                string_to_guess = string_col_2
            elif string_col_3:
                string_to_guess = string_col_3
            else:
                string_to_guess = ""

            sort_letter_arabic_guessed, sort_index_arabic_guessed = guess_sort_letter_arabic(string_to_guess)

            # Split English meanings into a list and then get sort letters for each meaning
            english_meanings_list = english_meanings.split(",")

            definitions_list = []
            # # debug
            # print(english_meanings_list)
            for english_string in english_meanings_list:
                english_string = english_string.strip()
                english_definition_sort_letter_guessed, english_definition_sort_index_guessed, _ = guess_sort_letter_part_of_speech_english(english_string, part_of_speech_guessed) # drop the part of speech result

                definitions_list.append(
                    {
                        "english_definition": english_string,
                        "source_name": "textbook_jones",
                        "english_sort_letter": english_definition_sort_letter_guessed,
                        "english_sort_start_index": english_definition_sort_index_guessed
                    }
                )

            if not string_col_1 and not string_col_2 and not string_col_3:
                print("ERROR: Vocabulary row has no arabic entries for Lesson {}: {}".format(chapter_number, english_meanings))
                # TODO maybe continue-skip this row if this happens?

            # definitions_dict = {}
            # for meaning in english_meanings_array:
            #     definitions_dict = {"english_meanings_string": meaning, "source_name": "textbook_jones"}

            if part_of_speech_guessed == "verb":
                vocab.append(
                    {
                        "chapter_vocab": chapter_number,
                        "part_of_speech": "verb",
                        "verb_form": str(row.get("Verb Form", "") or "").strip(),
                        "arabic_words": {
                            "perfect": string_col_1,
                            "imperfect": string_col_2,
                            "verbal-noun": string_col_3,
                        },
                        "arabic_sort_letter": sort_letter_arabic_guessed,
                        "arabic_sort_start_index": sort_index_arabic_guessed,
                        "english_meanings": english_meanings,
                        "english_meanings_sort_letter": english_meanings_sort_letter_guessed,
                        "english_meanings_sort_start_index": english_meanings_sort_index_guessed,
                        "source_name": "textbook_jones",
                        "definitions": definitions_list,
                    }
                )
            elif part_of_speech_guessed == "noun":

                vocab.append(
                    {
                        "chapter_vocab": chapter_number,
                        "part_of_speech": "noun",
                        "arabic_words": {
                            "singular": string_col_1,
                            "dual": string_col_2,
                            "plural": string_col_3,
                        },
                        "arabic_sort_letter": sort_letter_arabic_guessed,
                        "english_meanings": english_meanings,
                        "english_meanings_sort_letter": english_meanings_sort_letter_guessed,
                        "english_meanings_sort_start_index": english_meanings_sort_index_guessed,
                        "source_name": "textbook_jones",
                        "definitions": definitions_list,
                    }
                )
                # TODO get python library to do transliteration?
            else:
                print("Warning: row was guessed as neither a verb nor a noun: {}".format(english_meanings))
        else:
            # Unknown row type; skip or log
            continue
            # TODO print error??

    data: dict[str, Any] = {
        "lesson": lesson_meta or {},
        "vocabulary": vocab,
        "exercises": exercises,
    }
    return data
