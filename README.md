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

There are some tests. Much of this was written or at least started by LLMs,
mainly because I really should be reading these Lessons instead of coding...
