# Arabic APIs and other Data Processing Scripts

This repository contains code to obtain and/or parse and reformat data to help
teach Arabic.

- `quran_api.py`: will read in your API token from a `.env` file and output the
  requested data
- `quran-interlinear.py`: Will download the specified interpretations and/or
  script styles for specified verses from Quran.com
  (and other APIs, when coded up in the future...)
- `textbook_data.py`: reads in textbook Vocabulary and Exercise data from
  spreadsheets and outputs them as structured .json files
- `textbook_enrich.py`: reads in the above .json files and adds data from the
  specified APIs
- `arabic-textbook-to-tex-file.py`: Converts either a CSV/TSV or ODS spreadsheet
  or a structured .json file into a formatted XeLaTeX document
  (Work In Progress)
- `process_textbook_llm_output.py`: Converts the markdown formatted text from
  the Optical Character Recognition (OCR) of textbook pages into CSV with " as
  the string delimiter, structured json file and a XeLaTeX document.
  (Work In Progress)
- `arabic-textbook-to-flashcards.py`: Converts textbook vocabulary and exercises
  into flashcard formats (Anki .apkg or two-column CSV) for language learning

There are some tests. Much of this was written or at least started by LLMs,
mainly because I really should be reading these Lessons instead of coding...

## Automated Flashcard Generation

This repository includes a GitHub Action that automatically generates flashcard
files whenever the source CSV files are updated on the main branch.

Currently, the action only generates flashcards for the vocabulary file, as
the exercises file is not proofread at all. Yet...

### How It Works

When either `textbook-jones-vocabulary.csv` or `textbook-jones-exercises.csv` is
updated on the main branch, the workflow:

1. Runs `arabic-textbook-to-flashcards.py` with multiple output formats
    specified by `--format`:
   - `anki`: to generate `attq-vocab-deck.apkg`
   - `csv_min`: to generate `attq-vocab-deck-min.csv`
   - `csv_med`: to generate `attq-vocab-deck-med.csv`
   - `csv_max`: to generate `attq-vocab-deck-max.csv`
2. Creates a new GitHub release with a timestamp tag (e.g., `flashcards-20231218-120000`)
3. Uploads all generated files as release assets
4. Includes permalinks to the exact commits of the input CSV files used

### Downloading Flashcards

To get the latest vocabulary flashcards:

1. Visit the [Releases page](https://github.com/julowe/arabic-apis/releases)
2. Download the latest release:
   - **attq-vocab-deck.apkg** - Import into Anki for full featured flashcard experience
   - **attq-vocab-deck-min.csv**, **attq-vocab-deck-med.csv**, **attq-vocab-deck-max.csv** - Import into other flashcard applications

### Manual Generation

You can also generate flashcards manually:

```bash
# Generate Anki deck
python3 arabic-textbook-to-flashcards.py \
  --format anki \
  --output my-deck.apkg \
  textbook-jones-vocabulary.csv \
  textbook-jones-exercises.csv

# Generate two-column CSV
python3 arabic-textbook-to-flashcards.py \
  --format csv_max \
  --output my-cards.csv \
  textbook-jones-vocabulary.csv \
  textbook-jones-exercises.csv
```

See `python3 arabic-textbook-to-flashcards.py --help` for more options.

## Arabic Textbook to LaTeX Converter

This Python script converts CSV/TSV or ODS files containing Arabic textbook data
(vocabulary and exercises) into a formatted LaTeX document with both Arabic
and English text.

### Features

- **Multi-format support**: Reads both CSV/TSV and ODS files
- **Quran integration**: Fetches verses from Quran.com API with Arabic text,
  transliteration, and interpretations
- **Hyperlinks**: Creates clickable links to Quran.com for verse references
- **Vocabulary tables**: Formats vocabulary entries in clean LaTeX tables
- **Numbered exercises**: Creates ordered exercise lists

### Installation

0. Probably set up a python virtual environment first (optional but recommended)
1. Install required Python packages:

```bash
pip install -r requirements.txt
```

2. (Optional) Set up Quran.com API credentials:
   - Request API credentials from here: [https://api-docs.quran.foundation/request-access/]
   - Copy `.env.example` to `.env`
   - Fill in your credentials in the `.env` file

### Usage

#### Basic usage with CSV/TSV file

```bash
python arabic-textbook-to-tex-file.py input.csv
```

#### With ODS file and custom output

```bash
python arabic-textbook-to-tex-file.py input.ods -o output.tex
```

#### Without API (no verse details)

```bash
python arabic-textbook-to-tex-file.py input.csv --no-api
```

#### With verbose output

```bash
python arabic-textbook-to-tex-file.py input.csv -v
```

### Input File Format

This script can read in either CSV/TSV/ODS formatted files.
It parses them by column name (not number),
so the file should have the following column names:

- **Sing. / Perf.**: Arabic text (singular/perfect form)
- **Dual / Imperf.**: Arabic text (dual/imperfect form)
- **Plural / Verbal N.**: Arabic text (plural/verbal noun form)
- **English**: English translation/meaning
- **Sura**: Quran chapter number (for exercises)
- **Verse**: Quran verse number (for exercises)
- **Lesson #**: Number of the Lesson/Chapter
- **Ex/Voc**: Type indicator ("Exercise" or "Vocabulary")
- **Exercise #**: Exercise number (for ordering)

#### Example CSV/TSV structure

```csv
Sing. / Perf., Dual / Imperf., Plural / Verbal N., English, Sura, Verse, Ex/Voc, Lesson #, Exercise #
أَبْصَرَ,يُبْصِرُ,إِبْصَارٌ,(+ bi-) to see observe,,,Vocabulary,16,,
نَبْعَثُ مِنْ كُلِّ أُمَّةٍ شَهِيدًا,,,We shall raise up in every community a witness,16,89,Exercise,16,1
```

**Note**: Yes, in a web browser it might look like the Perfect and Verbal Noun
columns are swapped, but in the CSV/TSV (and in this text file) they are in the
correct order. So it is probably easiest for people to edit this data if it is
kept in an ODS file.
And this is how I learned you can save a 180kb ODF file as a 4.2mb
'Flat XML ODF Spreadsheet' .fods file, which at least might make it easier to
commit to git and track changes??

### Output

The script generates an XeLaTeX file with:

1. **Document header**: Proper XeLaTeX setup for Arabic and English characters
2. **Vocabulary section**: Tables with Arabic forms and English meanings
3. **Exercises section**: Numbered list with:
   - Arabic text
   - English translation
   - Hyperlinked Quran reference
   - Full verse in Arabic (if API enabled)
   - Transliteration (if API enabled)
   - Saheeh International translation (if API enabled)
   - Pickthall translation (if API enabled)

### LaTeX Compilation

To compile the generated LaTeX file (run twice, to generate references/ToC):

```bash
xelatex your-output.tex
```

**Requirements:**

- XeLaTeX engine
- Fonts: Charis SIL, Noto Naskh Arabic, Noto Kufi Arabic
- LaTeX packages: polyglossia, xcolor, hyperref, longtable, booktabs, array

### API Integration

When API credentials are provided, the script fetches additional verse information:

- **Arabic text**: Full verse in Arabic script
- **Transliteration**: Romanized transliteration in Quran.com's style
- **English translations**:
  - Saheeh International
  - Pickthall

Verses are linked to quran.com with format: `https://quran.com/CHAPTER?startingVerse=VERSE`

### Command Line Options

- `input_file`: Input CSV/TSV or ODS file (required)
- `-o, --output`: Output LaTeX file (default: arabic-textbook.tex)
- `--no-api`: Skip Quran API calls
- `-v, --verbose`: Enable verbose logging

### Examples

#### CSV/TSV with API integration

```bash
python arabic-textbook-to-tex-file.py lesson-16.csv -o lesson-16.tex
```

#### ODS file without API

```bash
python arabic-textbook-to-tex-file.py all-lessons.ods --no-api -o complete-textbook.tex
```

### Troubleshooting

1. **Encoding issues**: Ensure input files are saved in UTF-8 encoding
2. **API timeout**: Use `--no-api` flag if network is slow
3. **LaTeX compilation**: Install required fonts and packages
4. **Missing data**: Check column names match the format specified above exactly
