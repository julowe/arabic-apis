# Misc Notes for these scripts/files

## `jq` Helpers

To get the first exercise of each chapter:
`jq '.exercises.[] | select(.exercise_number == 1)'  arabic-textbook.json > arabic-textbook.sample.exercises.json`

To get the first vocabulary item of each chapter:
`jq '[.vocabulary | group_by(.chapter_vocab) | map(.[0]) | sort_by(.chapter_vocab)]' arabic-textbook.json > arabic-textbook.sample.vocab.json`

## Arabic Unicode Ranges

From [Wikipedia's page on Arabic script in Unicode](https://en.wikipedia.org/wiki/Arabic_script_in_Unicode):

- Arabic (0600–06FF, 256 characters)
- Arabic Supplement (0750–077F, 48 characters)
- Arabic Extended-B (0870–089F, 43 characters)
- Arabic Extended-A (08A0–08FF, 96 characters)
- Arabic Presentation Forms-A (FB50–FDFF, 656 characters)
- Arabic Presentation Forms-B (FE70–FEFF, 141 characters)
- Rumi Numeral Symbols (10E60–10E7F, 31 characters)
- Arabic Extended-C (10EC0-10EFF, 21 characters)
- Indic Siyaq Numbers (1EC70–1ECBF, 68 characters)
- Ottoman Siyaq Numbers (1ED00–1ED4F, 61 characters)
- Arabic Mathematical Alphabetic Symbols (1EE00–1EEFF, 143 characters)

Python Regex pattern to match any Arabic character:
`[\u0600–\u06FF\u0750–\u077F\u0870–\u089F\u08A0–\u08FF\uFB50–\uFDFF\uFE70–\uFEFF\u10E60–\u10E7F\u10EC0-\u10EFF\u1EC70–\u1ECBF\u1ED00–\u1ED4F\u1EE00–\u1EEFF]`
