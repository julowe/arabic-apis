from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

from tqdm import tqdm

from load_data_tanzil_net import QURAN_CHAPTERS
from quran_api import get_access_token, get_verse


translations_english = {
    "85": "M.A.S. Abdel Haleem",
    "84": "T. Usmani",
    "95": "A. Maududi (Tafhim commentary)",
    "22": "A. Yusuf Ali",
    "203": "Al-Hilali & Khan",
    "19": "M. Pickthall",
    "20": "Saheeh Intl.",
    "57": "Transliteration",
}

def enrich_with_quran_api(
    data: Dict[str, Any],
    url_oauth_base: str,
    url_api_base: str,
    client_id: str,
    client_secret: str,
) -> Dict[str, Any]:
    """Attach raw Quran.com API responses to items that reference verses.

    - Obtains a single access token.
    - Deduplicates verse fetches across all items.
    - Adds raw verse JSON under item["quran_api"]["verse"]
    """

    if not data:
        return data


    def add_ref(qref: str | None):
        if not qref:
            return
        if ":" not in qref:
            return
        try:
            ch_qref, vs_qref = qref.split(":", 1)
            key = (int(ch_qref), int(vs_qref))
            verse_keys.add(key)
        except (ValueError, TypeError):
            return


    def add_ref2(ch_ref: int, vs_ref: int):
        if ch_ref and vs_ref:
            verse_keys.add((ch_ref, vs_ref))


    def construct_context_lines_index_list(
            current_ch: int,
            current_vs: int,
            num_context_lines_before: int = 1,
            num_context_lines_after: int = 1
    ) -> list[dict[str, int]]:

        ## Make an ordered context lines list
        context_lines_list = []

        # Define how many # TODO make var somewhere
        # num_context_lines_before = 1
        # num_context_lines_after = 1

        # Make the list of verses to get
        for i in range(-num_context_lines_before, num_context_lines_after + 1):
            # if i: # skip zero, we already have the current verse # TODO or maybe don't skip and then we have a full context to print??
            context_ch, context_vs = get_sequential_ayah(current_ch, current_vs, i, False)

            # only add if it returns a valid chapter and verse
            if context_ch and context_vs:
                # @formatter:off # fmt: off
                context_lines_list.append(
                    {
                        "surah": context_ch,
                        "ayah": context_vs,
                    }
                )
                # @formatter:on # fmt: on

        return context_lines_list
        # qs.append({"context_lines_list": context_lines_list})
        # context_lines_list = item.get("context_lines", [])
        # if context_lines_list:
        #     for context_line in context_lines_list:
        #         add_ref2(context_line.get("surah", 0), context_line.get("ayah", 0))


    def get_sequential_ayah(
            ch_current: int,
            vs_current: int,
            vs_to_get: int,
            other_ch: bool = True
    ) -> tuple[int, int]:
        # TODO do we want to go into other chapters?? is it really context, or not connected??

        # get the number of ayahs in the chapter
        ayahs_in_current_surah = QURAN_CHAPTERS.get(ch_current) or 0
        vs_to_get_calc = vs_current + vs_to_get

        # how many prev or later context indexes are we looking for
        if vs_to_get < 0:
            # Getting lines before, so make sure we don't try to get a line before the first line
            if vs_to_get_calc <= 0: # getting previous context line
                if other_ch:
                    # would be before first line, so get number of ayahs in previous surah
                    ch_to_get = ch_current - 1
                    ayahs_in_previous_surah = QURAN_CHAPTERS.get(ch_to_get) or 0
                    vs_to_get_previous_ch_calc = ayahs_in_previous_surah + vs_to_get_calc

                    # just make sure we aren't trying to get, e.g., 10 lines from a 5-line surah
                    if vs_to_get_previous_ch_calc < 0:
                        # TODO don't fail but keep looping on a separate function to get to context lines start we need
                        # for now just error and return start of this surah
                        print(
                            f"ERROR: Negative verse index {vs_to_get_calc} to get from previous surah {ch_to_get} ayah {vs_current}")
                        return ch_to_get, 1
                    else:
                        return ch_to_get, vs_to_get_previous_ch_calc
                else: # don't get other chapters, so return index of 1
                    # return ch_current, 1
                    return 0, 0

                return ch_to_get, ayahs_in_previous_surah - vs_to_get_calc
            else:
                return ch_current, vs_to_get_calc
        else:  # getting later context line, but check it isn't over the number of ayahs in the surah
            if vs_to_get_calc > ayahs_in_current_surah:
                if other_ch:
                    # Would be beyond current surah, so get number of ayahs in next surah
                    ch_to_get = ch_current + 1
                    ayahs_in_next_surah = QURAN_CHAPTERS.get(ch_to_get) or 0
                    vs_to_get_next_ch_calc = vs_to_get_calc - ayahs_in_current_surah
                    # just make sure we aren't trying to get, e.g., 10 lines from a 5-line surah
                    if vs_to_get_next_ch_calc > ayahs_in_next_surah:
                        # TODO don't fail but keep looping on a separate function to get to context lines start we need
                        # for now just error and return end of this surah
                        print(f"ERROR: Too large verse index {vs_to_get_calc} to get from next "
                              f"surah {ch_to_get} ayah {vs_current}, returning last ayah from next surah")
                        return ch_to_get, ayahs_in_next_surah
                    else:
                        return ch_to_get, vs_to_get_next_ch_calc
                else: # not going into next chapter, so return end index of this surah
                    # return ch_current, ayahs_in_current_surah
                    return 0, 0
            else:
                return ch_current, vs_to_get_calc


    # Attach to items
    def attach(item: Dict[str, Any]):
        # qref = item.get("quranic_reference")
        # if not qref or ":" not in qref:
        #     return
        # try:
        #     ch, vs = (int(x) for x in qref.split(":", 1))
        # except (ValueError, TypeError):
        #     return
        # verse_json = cache.get((ch, vs))

        item_ch = item.get("surah", 0)
        item_vs = item.get("ayah", 0)

        if item_ch == 0 or item_vs == 0:
            return

        verse_json = cache.get((item_ch, item_vs))

        if verse_json is not None:
            # qs = item.get("quran_sources") or []
            qs = item.get("quranic_sources") or []
            # TODO this wil duplicate entries, fix that. check by lang then text_type/resource_id
            if verse_json["verse"].get("text_indopak"):
                # @formatter:off # fmt: off
                qs.append(
                    {
                        "source_name": "quran.com",
                        "source_url": f"https://quran.com/{ch}?startingVerse={vs}",
                        "text_type": "indopak",
                        "language": "arabic",
                        "text": verse_json["verse"].get("text_indopak") or "",
                    }
                )
                # @formatter:on # fmt: on

            if verse_json["verse"].get("text_uthmani"):
                # @formatter:off # fmt: off
                qs.append(
                    {
                        "source_name": "quran.com",
                        "source_url": f"https://quran.com/{ch}?startingVerse={vs}",
                        "text_type": "uthmani",
                        "language": "arabic",
                        "text": verse_json["verse"].get("text_uthmani") or ""
                    }
                )
                # @formatter:on # fmt: on
            if verse_json["verse"].get("text_imlaei"):
                # @formatter:off # fmt: off
                qs.append(
                    {
                        "source_name": "quran.com",
                        "source_url": f"https://quran.com/{ch}?startingVerse={vs}",
                        "text_type": "imlaei",
                        "language": "arabic",
                        "text": verse_json["verse"].get("text_imlaei") or ""
                    }
                )
                # @formatter:on # fmt: on
                # TODO check length vs exercise length, always get context, only TeX print if short line??
                # if len(qs.get("exercise_text") or "") > len(verse_json["verse"].get("text_imlaei") or "") * 0.70:
                #     print("yay")


            for translation in verse_json["verse"].get("translations") or []:
                # @formatter:off # fmt: off
                qs.append(
                    {
                        "source_name": "quran.com",
                        "source_url": f"https://quran.com/{ch}?startingVerse={vs}",
                        "text_type": "translation",
                        "translation_resource_id": translation.get("resource_id") or "",
                        "translation_resource_name": translations_english.get(
                                str(translation.get("resource_id"))
                            ) or "",
                        "language": "english",
                        "text": translation.get("text") or "",
                    }
                )
                # @formatter:on # fmt: on

            item["quranic_sources"] = qs

            # this has hizb_number, manzil_number, page_number, rub_el_hizb_number, sajdah_number, juz_number, ruku_number
            # qa = item.get("quran_api") or {}
            # qa["verse"] = verse_json
            # item["quran_api"] = qa

    token = get_access_token(url_oauth_base, client_id, client_secret)

    # Collect unique verse references (chapter, verse)
    verse_keys: set[Tuple[int, int]] = set()

    # go through and build up the list of ayahs to get
    for vocab in data.get("vocabulary", []) or []:
        # add_ref(vocab.get("quranic_reference"))
        add_ref2(vocab.get("surah", 0), vocab.get("ayah", 0))
    for exercise in data.get("exercises", []) or []:
        # add_ref(exercise.get("quranic_reference"))
        exercise_surah = exercise.get("surah", 0)
        exercise_ayah = exercise.get("ayah", 0)
        add_ref2(exercise_surah, exercise_ayah)
        # TODO add context refs here...
        if exercise_surah and exercise_ayah:
            context_lines = construct_context_lines_index_list(exercise_surah, exercise_ayah)
            for line in context_lines:
                add_ref2(line.get("surah", 0), line.get("ayah", 0))

            exercise.update({"context_lines": context_lines})

    # Fetch verses once each
    cache: dict[Tuple[int, int], Dict[str, Any]] = {}

    # TODO also get audio files and... note in json file the local path?? save locally at least and name them well
    # maybe name them surah verse, but also symlink them by exercise ch and number?
    # TODO make "api" for corpus.quran.com
    # TODO make api? for quran wbw? or just link, nothing new I can easily get from that website? api or monolith or beautifulsoup?
    pbar_verse_keys = tqdm(verse_keys, desc="Processing Verses", position=0)
    for (ch, vs) in pbar_verse_keys:
        cache[(ch, vs)] = get_verse(
            url_api_base,
            token,
            client_id,
            ch,
            vs,
            fields=["text_indopak", "text_uthmani", "text_imlaei"],
            translations=[19, 20, 57],
        )

    # now go through items in data source and add quran data
    for vocab in data.get("vocabulary", []) or []:
        attach(vocab)
    for exercise in data.get("exercises", []) or []:
        attach(exercise)
        if "context_lines" in exercise:
            for context_lines in exercise["context_lines"]:
                attach(context_lines)

    return data


def write_json(filepath: str | Path, data: Dict[str, Any]) -> None:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def read_json(filepath: str | Path) -> Dict[str, Any]:
    with open(filepath, "r", encoding="utf-8") as fh:
        return json.load(fh)
