#!/usr/bin/env python3

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm
from quran_api import (
    get_access_token as api_get_access_token,
    get_verse as api_get_verse,
)
from tex_utils import (
    tex_escape_text,
    tex_cleanup_text,
    tex_remove_arabic_marks,
)
from textbook_data import read_csv as tb_read_csv, read_ods as tb_read_ods, build_json_from_rows
from textbook_enrich import enrich_with_quran_api, write_json as save_json, read_json as load_json

# # Load environment variables
# load_dotenv()


def export_ods_to_csv(ods_file_path, output_csv_path, filter_string=None):
    """
    Export ODS file to CSV, optionally filtering sheets by name.

    Args:
        ods_file_path: Path to the input ODS file
        output_csv_path: Path to the output CSV file
        filter_string: Optional string to filter sheet names (only sheets containing this string will be exported)
    """
    import csv

    # Read ODS file
    sheets = tb_read_ods(Path(ods_file_path))

    # Filter sheets if filter_string is provided
    if filter_string:
        filtered_sheets = {name: rows for name, rows in sheets.items() if filter_string in name}
        if not filtered_sheets:
            print(f"Warning: No sheets found matching filter '{filter_string}'")
            print(f"Available sheets: {', '.join(sheets.keys())}")
            sys.exit(1)
        sheets_to_export = filtered_sheets
        print(f"Exporting {len(filtered_sheets)} sheet(s) matching filter '{filter_string}': {', '.join(filtered_sheets.keys())}")
    else:
        sheets_to_export = sheets
        print(f"Exporting all {len(sheets)} sheet(s): {', '.join(sheets.keys())}")

    # Write to CSV
    with open(output_csv_path, 'w', encoding='utf-8', newline='') as csvfile:
        writer = csv.writer(csvfile)

        for sheet_name, rows in sheets_to_export.items():
            # Write sheet name as a header row
            writer.writerow([f"=== Sheet: {sheet_name} ==="])

            # Get all unique column headers preserving original order
            if rows:
                # Use first row to establish column order, then add any additional columns from other rows
                headers = list(rows[0].keys()) if rows else []

                # Add any additional columns that appear in subsequent rows (preserve discovery order)
                seen = set(headers)
                for row in rows[1:]:
                    for key in row.keys():
                        if key not in seen:
                            headers.append(key)
                            seen.add(key)

                # Write header row
                writer.writerow(headers)

                # Write data rows
                for row in rows:
                    writer.writerow([row.get(h, '') for h in headers])

            # Add blank row between sheets
            writer.writerow([])

    print(f"Successfully exported to: {output_csv_path}")


def get_access_token(url_base, client_id, client_secret):
    """Get an access token for Quran.com API via the shared quran_api module"""
    logging.debug(
        f"Getting access token for client_id: {client_id} from url: {url_base}/oauth2/token"
    )
    return api_get_access_token(url_base, client_id, client_secret)

def get_verse_with_translations(url_base, access_token, client_id, chapter_number, verse_number):
    """Get verse with Arabic text, transliteration, and English translations using quran_api"""
    # Use the shared API layer and request the same fields/translations as before
    data = api_get_verse(
        url_base,
        access_token,
        client_id,
        chapter_number,
        verse_number,
        fields=["text_indopak", "text_uthmani", "text_imlaei"],
        translations=[19, 20, 57],  # Pickthall, Saheeh International, Transliteration
    )
    return data

# TODO print arabic/english letters along the outside edge of glossary pages, highlighting letters on that page??
def write_tex_header(fh):
    """Write LaTeX document header"""

    header = r"""\documentclass[a4paper, notitlepage, DIV = 14]{scrbook}
\usepackage[x11names]{xcolor}
\usepackage{hyperref}
\hypersetup{
    colorlinks=true,
    linktoc=all,
    linkcolor=Blue4,
}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{array}

\usepackage{polyglossia}
\setmainlanguage{english}
\setotherlanguage{arabic}
\setmainfont{Charis}
\newfontfamily\arabicfont[Script=Arabic]{Noto Naskh Arabic}
\newfontfamily\arabicfonttt[Script=Arabic]{Noto Kufi Arabic}
\newfontfamily\symbolfont{Symbola}
\newcommand{\ar}[1]{{\textarabic{#1}}}
\newcommand{\arl}[1]{{{\large \textarabic{#1}}}}
\newcommand{\arL}[1]{{{\Large \textarabic{#1}}}}
\newcommand{\arLA}[1]{{{\LARGE \textarabic{#1}}}}
\newcommand{\arpar}[1]{
\begin{Arabic}{\Large #1}
\end{Arabic}}

\setcounter{secnumdepth}{2}

\title{Arabic Textbook Exercises and Vocabulary}
\author{Generated from textbook data}

\begin{document}
\maketitle
\tableofcontents
\clearpage

"""
    fh.write(header)

# TODO handle unicode in roman charset, e.g. ch 3 ex 14
def write_exercises_by_chapter(fh, data_json):
    """Write exercises grouped by chapter and sorted by exercise number"""
    exercises = data_json.get('exercises', [])
    if not exercises:
        return

    # Group exercises by chapter
    chapters = {}
    for exercise in exercises:
        chapter = exercise.get('exercise_chapter')
        if chapter:
            if chapter not in chapters:
                chapters[chapter] = []
            chapters[chapter].append(exercise)

    # Process each chapter
    for chapter in sorted(chapters.keys()):
        chapter_exercises = sorted(chapters[chapter], key=lambda x: x.get('exercise_number', 0))

        # TODO new page for each chapter? does it do that automatically for chapters?
        #fh.write(f"\\section{{Chapter {chapter} Exercises}}\n\n")
        fh.write(f"\\chapter{{Chapter {chapter} Exercises}}\n\n")
        fh.write("\\begin{enumerate}\n")

        for exercise in chapter_exercises:
            # Write exercise item
            exercise_text = exercise.get('exercise_text', '')
            quranic_ref = exercise.get('quranic_reference', '')

            # Only write item if there's actual content
            if not exercise_text.strip() and not quranic_ref:
                continue

            # TODO handle no exercises of ch 14? otherwise the number is off and it annoys me.
            #  hmm or just remove numbering form front of sectio ha.
            fh.write("\\item ")
            if exercise_text.strip():
                fh.write(f"\\arL{{\n{tex_cleanup_text(exercise_text)}\n}}")

            # Add Quran reference with hyperlink
            if quranic_ref and ':' in quranic_ref:
                try:
                    sura, ayah = quranic_ref.split(':', 1)
                    sura_int = int(sura)
                    ayah_int = int(ayah)
                    fh.write(f"\n\\textbf{{[{sura_int}:{ayah_int}]}}")
                    fh.write(f"\n\\href{{https://quran.com/{sura_int}?startingVerse={ayah_int}}}{{Quran.com}}")
                    fh.write(f"\n\\href{{https://quranwbw.com/morphology?word={sura_int}:{ayah_int}}}{{QuranWBW.com}}\n\n")
                except (ValueError, TypeError):
                    fh.write(f"({quranic_ref})\n\n")

            # Write Quranic sources
            quranic_sources = exercise.get('quranic_sources', [])

            # First write imlaei text
            for source in quranic_sources:
                if source.get('text_type') == 'imlaei':
                    arabic_text = source.get('text', '')
                    if arabic_text.strip():
                        fh.write("\\arpar{\n")
                        fh.write(tex_remove_arabic_marks(arabic_text))
                        fh.write("\n}\n\n")
                    break

            # print_context = "" # empty string means don't print context
            print_context = "M. Pickthall"
            print_transliteration = False

            # Then write all translations
            translation_string = f""
            for source in quranic_sources:
                if source.get('text_type') == 'translation':
                    translation_text = source.get('text', '')
                    resource_name = source.get('translation_resource_name', '')
                    if translation_text.strip():
                        if resource_name == "Transliteration":
                            if print_transliteration:
                                translation_string = f"\\textit{{{resource_name}}}: {tex_cleanup_text(translation_text)}\n\n" + translation_string
                        else:
                            # fh.write(f"\\textit{{{resource_name}}}: {tex_cleanup_text(translation_text)}\n\n")
                            if resource_name == print_context:
                                context_string = f"\\textbf{{Context:}} "
                                for context_line in exercise["context_lines"]:
                                    if "quranic_sources" in context_line: # FIXME this is a hack for msitaken 0 index entries
                                        for line in context_line["quranic_sources"]:
                                            if "translation_resource_name" in line:
                                                if line["translation_resource_name"] == print_context:
                                                    context_string += f"\\textbf{{[{str(context_line["ayah"])}]:}} {tex_cleanup_text(line['text'])} "

                                translation_string += f"\\textit{{{resource_name}}}: {context_string}\n\n"
                            else:
                                translation_string += f"\\textit{{{resource_name}}}: {tex_cleanup_text(translation_text)}\n\n"

            if translation_string:
                fh.write(f"{translation_string}")


        fh.write("\\end{enumerate}\n\n")

def write_glossary_arabic_sorted(fh, vocabulary):
    """Write vocabulary glossary sorted by Arabic characters"""

    # TODO consolidate english and arabic glossary writing functions?

    # TODO make compact, multicolumn footnotes?

    if not vocabulary:
        return

    fh.write("\\section{Glossary - Arabic Alphabetical Order}\n\n")

    # Group by Arabic sort letter
    grouped = {}
    for entry in vocabulary:
        sort_letter = entry.get('arabic_sort_letter', '')
        # Skip entries with invalid or empty sort letters (non-Arabic characters)
        if not sort_letter or sort_letter in ['(', ')', ' ', ''] or len(sort_letter) == 0:
            # Try to extract first Arabic letter from the word itself
            arabic_words = entry.get('arabic_words', {})
            part_of_speech = entry.get('part_of_speech', '')
            if part_of_speech == 'verb':
                word = arabic_words.get('imperfect', '') or arabic_words.get('perfect', '')
            else:
                word = arabic_words.get('singular', '')

            # Extract first Arabic character from word
            if word:
                # Remove prefix markers like "(f.)"
                clean_word = word
                if clean_word.startswith('('):
                    # Find closing paren and skip it
                    close_paren = clean_word.find(')')
                    if close_paren > 0:
                        clean_word = clean_word[close_paren + 1:].strip()

                # Get first Arabic character
                for char in clean_word:
                    if '\u0600' <= char <= '\u06FF':  # Arabic Unicode range
                        sort_letter = char
                        break

            if not sort_letter or sort_letter in ['(', ')', ' ', '']:
                continue

        if sort_letter not in grouped:
            grouped[sort_letter] = []
        grouped[sort_letter].append(entry)

    # Sort each group by the sorting substring
    for letter in grouped:
        grouped[letter].sort(key=lambda x: get_arabic_sort_key(x))

    # Write longtable
    write_glossary_table_start(fh)

    # Define Arabic alphabetical order
    arabic_order = ['ا', 'إ', 'آ', 'أ', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'س', 'ش', 'ص', 'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'ه', 'و', 'ي']

    # Sort letters by Arabic alphabetical order
    sorted_letters = []
    for letter in arabic_order:
        if letter in grouped:
            sorted_letters.append(letter)

    # Add any remaining letters not in our standard order
    for letter in sorted(grouped.keys()):
        if letter not in sorted_letters:
            sorted_letters.append(letter)

    # Write entries grouped by letter
    for letter in sorted_letters:
        if letter in grouped and len(grouped[letter]) > 0:
            write_glossary_header(fh,letter, "arabic")
            # # Huge header row spanning all columns, no vertical lines
            # fh.write(f"\\multicolumn{{5}}{{c}}{{}} \\\\\n")
            # fh.write(f"\\multicolumn{{5}}{{c}}{{\\Huge \\textbf{{--- \\ar{{{letter}}} ---}}}} \\\\\n")
            # fh.write(f"\\multicolumn{{5}}{{c}}{{}} \\\\\n")
            # fh.write("\\hline\n")

            for entry in grouped[letter]:
                write_vocabulary_row(fh, entry)

    fh.write("\\end{longtable}\n\n")


def write_glossary_table_start(fh):
    fh.write("\\renewcommand{\\arraystretch}{1.3} % Default value: 1\n")
    fh.write("\\begin{longtable}{p{2.75cm}p{2.75cm}p{2.75cm}p{5.25cm}p{0.5cm}}\n")
    fh.write("\\textbf{Sing./Perf.} & \\textbf{Dual/Imperf.} & \\textbf{Pl./Verbal N.} & \\textbf{English} & \\textbf{Ch \\#} \\\\\n")
    fh.write("\\hline\n")
    fh.write("\\endhead\n")

def write_glossary_header(fh, header_letter, language):
    # Huge header row spanning all columns, no vertical lines
    fh.write(f"\\multicolumn{{5}}{{c}}{{}} \\\\\n")
    if language == 'arabic':
        fh.write(f"\\multicolumn{{5}}{{c}}{{\\Huge \\textbf{{--- \\ar{{{header_letter}}} ---}}}} \\\\\n")
    else:
        fh.write(f"\\multicolumn{{5}}{{c}}{{\\Huge \\textbf{{--- {header_letter} ---}}}} \\\\\n")

    fh.write(f"\\multicolumn{{5}}{{c}}{{}} \\\\\n")
    # fh.write("\\hline\n")

def write_glossary_english_sorted(fh, vocabulary):
    """Write vocabulary glossary sorted by English definitions"""
    if not vocabulary:
        return

    fh.write("\\section{Glossary - English Alphabetical Order}\n\n")

    # Create entries for each definition
    all_entries = []
    for entry in vocabulary:
        definitions = entry.get('definitions', [])
        if definitions:
            for definition in definitions:
                all_entries.append((entry, definition))
        else:
            # Fallback to english_meanings
            all_entries.append((entry, None))

    # Group by English sort letter
    grouped = {}
    for entry, definition in all_entries:
        if definition:
            sort_letter = definition.get('english_sort_letter', '').upper()
            sort_start = definition.get('english_sort_start_index', 0)
            english_def = definition.get('english_definition', '')
            sort_key = english_def[sort_start:] if sort_start < len(english_def) else english_def
        else:
            english_meanings = entry.get('english_meanings', '')
            sort_letter = entry.get('english_meanings_sort_letter', '').upper()
            sort_start = entry.get('english_meanings_sort_start_index', 0)
            sort_key = english_meanings[sort_start:] if sort_start < len(english_meanings) else english_meanings

        if sort_letter:
            if sort_letter not in grouped:
                grouped[sort_letter] = []
            grouped[sort_letter].append((entry, definition, sort_key))

    # Sort each group by sort key
    for letter in grouped:
        grouped[letter].sort(key=lambda x: x[2].lower())

    # Write longtable
    write_glossary_table_start(fh)

    # Write entries grouped by letter
    for letter in sorted(grouped.keys()):
        write_glossary_header(fh, letter, "english")
        # # Large header row spanning all columns
        # fh.write(f"\\multicolumn{{5}}{{|c|}}{{\\Large \\textbf{{{letter}}}}} \\\\\n")
        # fh.write("\\hline\n")

        for entry, definition, _ in grouped[letter]:
            write_vocabulary_row(fh, entry, definition)

    fh.write("\\end{longtable}\n\n")

def get_arabic_sort_key(entry):
    """Get sorting key for Arabic vocabulary entry"""
    arabic_words = entry.get('arabic_words', {})
    sort_start = entry.get('arabic_sort_start_index', 0)

    # Get the word to sort by based on part of speech
    part_of_speech = entry.get('part_of_speech', '')
    if part_of_speech == 'verb':
        sort_word = arabic_words.get('imperfect', '')
    else:
        sort_word = arabic_words.get('singular', '')

    # Return substring for sorting
    if sort_start < len(sort_word):
        return sort_word[sort_start:]
    return sort_word

def write_vocabulary_row(fh, entry, specific_definition=None):
    """Write a single vocabulary row to the longtable"""
    arabic_words = entry.get('arabic_words', {})
    part_of_speech = entry.get('part_of_speech', '')
    chapter_vocab = entry.get('chapter_vocab', '')

    # Determine column values based on part of speech
    if part_of_speech == 'verb':
        col1 = arabic_words.get('perfect', '')
        col2 = arabic_words.get('imperfect', '')
        col3 = arabic_words.get('verbal-noun', '')
        verb_form = ""
        if "verb_form" in entry:
            verb_form = entry.get('verb_form','')
    else:  # noun
        col1 = arabic_words.get('singular', '')
        col2 = arabic_words.get('dual', '')
        col3 = arabic_words.get('plural', '')

    # Format Arabic text
    col1_tex = f"\\arL{{{tex_cleanup_text(col1)}}}" if col1.strip() else ""
    col2_tex = f"\\arL{{{tex_cleanup_text(col2)}}}" if col2.strip() else ""
    col3_tex = f"\\arL{{{tex_cleanup_text(col3)}}}" if col3.strip() else ""

    # English column
    if specific_definition:
        english_text = specific_definition.get('english_definition', '')
        english_escaped = tex_cleanup_text(english_text)

        # TODO: footnotes look bad. instead maybe just use the `english_meanings` value for all and people can figure it out?
        # Add footnote for multiple definitions
        definitions = entry.get('definitions', [])
        if len(definitions) > 1:
            other_defs = [d.get('english_definition', '') for d in definitions
                         if d != specific_definition and d.get('english_definition', '')]
            if other_defs:
                see_also = ', '.join(other_defs)
                see_also_escaped = tex_cleanup_text(see_also)
                # Build footnote manually to avoid double-escaping
                english_tex = english_escaped + "\\footnote{see also: " + see_also_escaped + "}"
            else:
                english_tex = english_escaped
        else:
            english_tex = english_escaped
    else:
        english_tex = tex_cleanup_text(entry.get('english_meanings', ''))

    # Get verb form if verb and has it
    if part_of_speech == 'verb' and verb_form:
        english_tex += f" ({tex_cleanup_text(verb_form)})"

    # FIXME sometimes english has arabic letters, go through and find them and \arL them. maybe \arl ?

    chapter_tex = str(chapter_vocab) if chapter_vocab else ""

    fh.write(f"{col1_tex} & {col2_tex} & {col3_tex} & {english_tex} & {chapter_tex} \\\\\n")
    # fh.write("\\hline\n")


def main():
    parser = argparse.ArgumentParser(description='Convert Arabic textbook data to LaTeX')
    parser.add_argument('input_file', nargs='?', help='Input CSV or ODS file (ignored if --json-input is used)')
    parser.add_argument('-o', '--output', help='Output TEX file', default='arabic-textbook.tex')
    parser.add_argument('--no-api', action='store_true', help='Skip Quran API calls')
    parser.add_argument('--json-input', help='Existing JSON file to render (bypass ingestion and API)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--output-csv', action='store_true', help='Export ODS to CSV and exit (requires input_file to be an ODS file)')
    parser.add_argument('--filter-sheetnames', type=str, help='Filter ODS sheets by name (only sheets containing this string will be exported)')

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')

    # Handle CSV export mode
    if args.output_csv:
        if not args.input_file:
            print("Error: input_file is required when using --output-csv")
            sys.exit(1)

        input_path = Path(args.input_file)
        if not input_path.exists():
            print(f"Error: Input file {input_path} does not exist")
            sys.exit(1)

        if input_path.suffix.lower() != '.ods':
            print(f"Error: --output-csv requires an ODS input file, got {input_path.suffix}")
            sys.exit(1)

        # Generate output CSV filename
        output_csv = input_path.with_suffix('.csv')

        # Export and exit
        export_ods_to_csv(input_path, output_csv, args.filter_sheetnames)
        sys.exit(0)

    # Check some existent file was passed in
    input_path = Path(args.input_file) if args.input_file else None
    if args.json_input:
        json_input_path = Path(args.json_input)
        if not json_input_path.exists():
            print(f"Error: JSON input file {json_input_path} does not exist")
            sys.exit(1)
    else:
        if input_path is None or not input_path.exists():
            print("Error: Provide an input CSV/ODS or --json-input JSON file")
            sys.exit(1)

    # Setup API info
    api_token = None
    client_id = None
    client_secret = None
    url_oauth_base = None
    url_api_base = None

    # Load CLIENT_ID and CLIENT_SECRET from a dot env file
    load_dotenv(dotenv_path=".env")

    # TODO: make this an argument and make it actually work?
    test_api = False

    if not args.no_api:
        try:
            if test_api:
                client_id = os.getenv("CLIENT_ID_TEST")
                client_secret = os.getenv("CLIENT_SECRET_TEST")
                url_oauth_base = os.getenv("END_POINT_TEST")
                url_api_base = os.getenv("URL_API_TEST")
            else:
                client_id = os.getenv("CLIENT_ID_LIVE")
                client_secret = os.getenv("CLIENT_SECRET_LIVE")
                url_oauth_base = os.getenv("END_POINT_LIVE")
                url_api_base = os.getenv("URL_API_LIVE")

            if client_id and client_secret and url_oauth_base:
                api_token = get_access_token(url_oauth_base, client_id, client_secret)
                if api_token:
                    logging.info("Successfully connected to Quran.com API")
                else:
                    logging.warning("Failed to get API token")
            else:
                logging.warning("API credentials not found in environment")
        except Exception as e:
            logging.error(f"Error setting up API: {e}")

    # Decide data source
    if args.json_input:
        data_json = load_json(args.json_input)
        enriched_json = data_json  # Do not call API when using existing JSON
    else:
        # Ingest CSV/ODS then build JSON then enrich via Quran API
        if input_path.suffix.lower() == '.ods':
            # sheets = tb_read_ods(str(input_path))
            # TODO print message to terminal? but logging info vs print vs...?
            sheets = tb_read_ods(input_path)
            # Merge sheets into a single rows list for minimal implementation
            all_rows = []
            for _, rows in sheets.items():
                all_rows.extend(rows)
            rows = all_rows
            lesson_meta = {"source": input_path.name}
        else:
            rows = tb_read_csv(input_path)
            lesson_meta = {"source": input_path.name}

        data_json = build_json_from_rows(rows, lesson_meta)

        if not args.no_api:
            # Load env and endpoints (already above)
            if not (client_id and url_api_base):
                logging.warning("Missing API configuration; proceeding without enrichment")
                enriched_json = data_json
            else:
                enriched_json = enrich_with_quran_api(
                    data_json,
                    url_oauth_base,
                    url_api_base,
                    client_id,
                    client_secret,
                )
        else:
            enriched_json = data_json

        # Save JSON next to TeX output
        out_tex_path = Path(args.output)
        out_json_path = out_tex_path.with_suffix('.json')
        try:
            save_json(out_json_path, enriched_json)
            logging.info(f"Saved JSON to {out_json_path}")
        except Exception as e:
            logging.error(f"Failed to save JSON: {e}")

    # Write TeX file from JSON data
    with open(args.output, 'w', encoding='utf-8') as fh:
        write_tex_header(fh)

        # Write lesson title if available
        lesson = enriched_json.get('lesson', {})
        if lesson.get('name'):
            fh.write(f"\\section{{{tex_cleanup_text(str(lesson['name']))}}}\n\n")

        # Write exercises grouped by chapter
        write_exercises_by_chapter(fh, enriched_json)

        # TODO add tex code for appendix or backmatter?
        # \backmatter
        #
        # %Epilogue
        # \chapter
        # {Epilogue}
        #\appendix
        # \chapter{Glossary - Arabic Alphabetical Order}

        # Write vocabulary glossaries
        vocabulary = enriched_json.get('vocabulary', [])
        if vocabulary:
            write_glossary_arabic_sorted(fh, vocabulary)
            write_glossary_english_sorted(fh, vocabulary)

        fh.write("\\end{document}\n")


    print(f"LaTeX file written to: {args.output}")

if __name__ == "__main__":
    main()
