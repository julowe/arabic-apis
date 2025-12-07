from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

from tqdm import tqdm

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

    token = get_access_token(url_oauth_base, client_id, client_secret)

    # Collect unique verse references (chapter, verse)
    verse_keys: set[Tuple[int, int]] = set()

    def add_ref(qref: str | None):
        if not qref:
            return
        if ":" not in qref:
            return
        try:
            ch, vs = qref.split(":", 1)
            key = (int(ch), int(vs))
            verse_keys.add(key)
        except (ValueError, TypeError):
            return

    def add_ref2(ch: int, vs: int):
        if ch and vs:
            verse_keys.add(
                (ch, vs)
            )

    for item in data.get("vocabulary", []) or []:
        # add_ref(item.get("quranic_reference"))
        add_ref2(item.get("surah", 0), item.get("ayah", 0))
    for item in data.get("exercises", []) or []:
        # add_ref(item.get("quranic_reference"))
        add_ref2(item.get("surah", 0), item.get("ayah", 0))

    # Fetch verses once each
    cache: dict[Tuple[int, int], Dict[str, Any]] = {}

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
            if verse_json["verse"].get("text_indopak"):
                qs.append(
                    {
                        "source_name": "quran.com",
                        "source_url": f"https://quran.com/{ch}?startingVerse={vs}",
                        "text_type": "indopak",
                        "language": "arabic",
                        "text": verse_json["verse"].get("text_indopak") or "",
                    }
                )

            if verse_json["verse"].get("text_uthmani"):
                qs.append(
                    {
                        "source_name": "quran.com",
                        "source_url": f"https://quran.com/{ch}?startingVerse={vs}",
                        "text_type": "uthmani",
                        "language": "arabic",
                        "text": verse_json["verse"].get("text_uthmani") or ""
                    }
                )
            if verse_json["verse"].get("text_imlaei"):
                qs.append(
                    {
                        "source_name": "quran.com",
                        "source_url": f"https://quran.com/{ch}?startingVerse={vs}",
                        "text_type": "imlaei",
                        "language": "arabic",
                        "text": verse_json["verse"].get("text_imlaei") or ""
                    }
                )

            for translation in verse_json["verse"].get("translations") or []:
                qs.append(
                    {
                        "source_name": "quran.com",
                        "source_url": f"https://quran.com/{ch}?startingVerse={vs}",
                        "text_type": "translation",
                        "translation_resource_id": translation.get("resource_id") or "",
                        "translation_resource_name": translations_english.get(str(translation.get("resource_id"))) or "",
                        "language": "english",
                        "text": translation.get("text") or ""
                    }
                )

            item["quranic_sources"] = qs

            # this has hizb_number, manzil_number, page_number, rub_el_hizb_number, sajdah_number, juz_number, ruku_number
            # qa = item.get("quran_api") or {}
            # qa["verse"] = verse_json
            # item["quran_api"] = qa

    for item in data.get("vocabulary", []) or []:
        attach(item)
    for item in data.get("exercises", []) or []:
        attach(item)

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
