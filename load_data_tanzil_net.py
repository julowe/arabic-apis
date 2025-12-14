#!/usr/bin/env python3
"""
This module provides functionality to retrieve Quranic text and translations from
various XML files, allowing access to specific chapters, verses, and entire translations
such as Uthmani, Arberry, Pickthall, and Sahih International versions.

All files were downloaded from https://tanzil.net/trans/ on 2025-12-13.

Functions:
- get_chapter_count: Retrieve the total number of chapters in the Quran.
- get_verse_count: Retrieve the total number of verses in a specified chapter.
- check_chapter_verse_exists: Check if a specific verse exists in a specified chapter.
- get_quran_uthmani_text: Retrieve the Uthmani text for a specified chapter and verse.
- get_quran_arberry_text: Retrieve Arberry English translation for a chapter and verse.
- get_quran_pickthall_text: Retrieve Pickthall English translation for a chapter and verse.
- get_quran_sahih_text: Retrieve Sahih International English translation for a chapter and verse.
"""

import xml.etree.ElementTree as ElmTree
from pathlib import Path
from typing import Dict


def _get_quran_text_from_xml(
    chapter_number: int,
    xml_path: str,
    source_name: str,
    verse_number: int | None = None
) -> str | Dict[int, str]:
    """Generic function to retrieve Quran text from any XML file.

    Args:
        chapter_number: The chapter (sura) number (1-114). Required.
        xml_path: Path to the XML file
        source_name: Name of the source for error messages
        verse_number: The verse (aya) number within the chapter. If None, returns all verses.

    Returns:
        If verse_number is specified: Returns the text of that specific verse as a string.
        If verse_number is None: Returns a dictionary mapping verse numbers to their text.

    Raises:
        ValueError: If chapter_number is not provided or is invalid.
        FileNotFoundError: If the XML file doesn't exist.
        TypeError: If parameters are not the correct type.
    """
    # Validate that chapter_number is provided
    if chapter_number is None:
        raise ValueError("chapter_number is required")

    if not isinstance(chapter_number, int):
        raise TypeError("chapter_number must be an integer")

    # Validate chapter number
    if chapter_number < 1 or chapter_number > 114:
        raise ValueError(f"Invalid chapter number: {chapter_number}. Must be between 1 and 114.")

    # Check XML file exists
    xml_file = Path(xml_path)
    if not xml_file.exists():
        raise FileNotFoundError(f"{source_name} XML file not found: {xml_path}")

    # Parse the XML file
    tree = ElmTree.parse(xml_path)
    root = tree.getroot()

    # Find the specific sura (chapter)
    sura = root.find(f".//sura[@index='{chapter_number}']")

    if sura is None:
        raise ValueError(f"Chapter {chapter_number} not found in {source_name} XML file")

    # If verse_number is specified, get that specific verse
    if verse_number is not None:
        if not isinstance(verse_number, int):
            raise TypeError("verse_number must be an integer")

        # Validate verse number against known chapter data
        if chapter_number in QURAN_CHAPTERS:
            max_verses = QURAN_CHAPTERS[chapter_number]
            if verse_number < 1 or verse_number > max_verses:
                raise ValueError(
                    f"Invalid verse number: {verse_number}. "
                    f"Chapter {chapter_number} has {max_verses} verses (valid range: 1-{max_verses})"
                )

        # Find the specific aya (verse)
        aya = sura.find(f".//aya[@index='{verse_number}']")

        if aya is None:
            raise ValueError(f"Verse {verse_number} not found in chapter {chapter_number} ({source_name})")

        # Return the text - it might be in 'text' attribute or as element text
        text = aya.get('text')
        if text is None:
            text = aya.text

        if text is None:
            raise ValueError(f"No text found for chapter {chapter_number}, verse {verse_number} ({source_name})")

        return text.strip()

    else:
        # Get all verses for the chapter
        ayas = sura.findall('.//aya')

        if not ayas:
            raise ValueError(f"No verses found in chapter {chapter_number} ({source_name})")

        # Build a dictionary of verse_number -> text
        verses_dict = {}
        for aya in ayas:
            aya_index = int(aya.get('index'))
            text = aya.get('text')
            if text is None:
                text = aya.text
            if text:
                verses_dict[aya_index] = text.strip()

        return verses_dict


def get_quran_uthmani_text(
    chapter_number: int,
    verse_number: int | None = None,
    xml_path: str = "tanzil_net/quran-uthmani.xml"
) -> str | Dict[int, str]:
    """Retrieve the Uthmani text for a specified chapter and optionally a specific verse.

    Args:
        chapter_number: The chapter (sura) number (1-114). Required.
        verse_number: The verse (aya) number within the chapter. If None, returns all verses.
        xml_path: Path to the quran-uthmani.xml file

    Returns:
        If verse_number is specified: Returns the text of that specific verse as a string.
        If verse_number is None: Returns a dictionary mapping verse numbers to their text.

    Raises:
        ValueError: If chapter_number is not provided or is invalid.
        FileNotFoundError: If the XML file doesn't exist.
        ValueError: If the verse_number is invalid for the specified chapter.

    Example:
        >>> # Get a specific verse
        >>> text = get_quran_uthmani_text(1, 1) # Al-Fatihah, verse 1
        >>> # Get all verses of a chapter
        >>> verses = get_quran_uthmani_text(1) # All verses of Al-Fatihah
        >>> verses[1]  # First verse
    """
    return _get_quran_text_from_xml(chapter_number, xml_path, "Uthmani", verse_number)


def get_quran_arberry_text(
    chapter_number: int,
    verse_number: int | None = None,
    xml_path: str = "tanzil_net/en.arberry.xml"
) -> str | Dict[int, str]:
    """Retrieve the Arberry English translation for a specified chapter and optionally a specific verse.

    Args:
        chapter_number: The chapter (sura) number (1-114). Required.
        verse_number: The verse (aya) number within the chapter. If None, returns all verses.
        xml_path: Path to the en.arberry.xml file

    Returns:
        If verse_number is specified: Returns the text of that specific verse as a string.
        If verse_number is None: Returns a dictionary mapping verse numbers to their text.

    Raises:
        ValueError: If chapter_number is not provided or is invalid.
        FileNotFoundError: If the XML file doesn't exist.
        TypeError: If parameters are not the correct type.

    Example:
        >>> # Get a specific verse
        >>> text = get_quran_arberry_text(1, 1) # Al-Fatihah, verse 1 (Arberry)
        >>> # Get all verses of a chapter
        >>> verses = get_quran_arberry_text(1) # All verses of Al-Fatihah (Arberry)
    """
    return _get_quran_text_from_xml(chapter_number, xml_path, "Arberry", verse_number)


def get_quran_pickthall_text(
    chapter_number: int,
    verse_number: int | None = None,
    xml_path: str = "tanzil_net/en.pickthall.xml"
) -> str | Dict[int, str]:
    """Retrieve the Pickthall English translation for a specified chapter and optionally a specific verse.

    Args:
        chapter_number: The chapter (sura) number (1-114). Required.
        verse_number: The verse (aya) number within the chapter. If None, returns all verses.
        xml_path: Path to the en.pickthall.xml file

    Returns:
        If verse_number is specified: Returns the text of that specific verse as a string.
        If verse_number is None: Returns a dictionary mapping verse numbers to their text.

    Raises:
        ValueError: If chapter_number is not provided or is invalid.
        FileNotFoundError: If the XML file doesn't exist.
        TypeError: If parameters are not the correct type.

    Example:
        >>> # Get a specific verse
        >>> text = get_quran_pickthall_text(1, 1) # Al-Fatihah, verse 1 (Pickthall)
        >>> # Get all verses of a chapter
        >>> verses = get_quran_pickthall_text(1) # All verses of Al-Fatihah (Pickthall)
    """
    return _get_quran_text_from_xml(chapter_number, xml_path, "Pickthall", verse_number)


def get_quran_sahih_text(
    chapter_number: int,
    verse_number: int | None = None,
    xml_path: str = "tanzil_net/en.sahih.xml"
) -> str | Dict[int, str]:
    """Retrieve the Sahih International English translation for a specified chapter and optionally a specific verse.

    Args:
        chapter_number: The chapter (sura) number (1-114). Required.
        verse_number: The verse (aya) number within the chapter. If None, returns all verses.
        xml_path: Path to the en.sahih.xml file

    Returns:
        If verse_number is specified: Returns the text of that specific verse as a string.
        If verse_number is None: Returns a dictionary mapping verse numbers to their text.

    Raises:
        ValueError: If chapter_number is not provided or is invalid.
        FileNotFoundError: If the XML file doesn't exist.
        TypeError: If parameters are not the correct type.

    Example:
        >>> # Get a specific verse
        >>> text = get_quran_sahih_text(1, 1) # Al-Fatihah, verse 1 (Sahih International)
        >>> # Get all verses of a chapter
        >>> verses = get_quran_sahih_text(1) # All verses of Al-Fatihah (Sahih International)
    """
    return _get_quran_text_from_xml(chapter_number, xml_path, "Sahih International", verse_number)


def load_quran_chapters(xml_path: str = "tanzil_net/quran-data.xml") -> Dict[int, int]:
    """Load Quran chapter data from an XML file.

    Args:
        xml_path: Path to the quran-data.xml file (relative or absolute)

    Returns:
        Dictionary mapping chapter index (1-114) to number of verses (ayas)

    Raises:
        FileNotFoundError: If the XML file doesn't exist.
        ET.ParseError: If the XML file is malformed.

    Example:
        >>> loaded_metadata_chapters = load_quran_chapters()
        >>> loaded_metadata_chapters[1] # Al-Fatihah
        7
        >>> loaded_metadata_chapters[2] # Al-Baqarah
        286
    """
    xml_file = Path(xml_path)
    if not xml_file.exists():
        raise FileNotFoundError(f"Quran data XML file not found: {xml_path}")

    tree = ElmTree.parse(xml_path)
    root = tree.getroot()

    xml_chapters = {}
    for sura in root.findall('.//sura'):
        index = int(sura.get('index'))
        ayas = int(sura.get('ayas'))
        xml_chapters[index] = ayas

    return xml_chapters


def get_chapter_count() -> int:
    """Get the total number of chapters in the Quran.

    Returns:
        114 (the number of chapters/suras in the Quran)
    """

    return len(QURAN_CHAPTERS)


def get_verse_count(chapter_number: int) -> int:
    """
    Retrieve the total number of verses in a specified chapter.

    This function retrieves the verse count for a given chapter of the Quran.
    It ensures that the input chapter number is an integer and checks its validity
    against a predefined list of chapters. An error is raised if the input is
    invalid.

    :param chapter_number: The chapter number for which to retrieve the verse count.
    :type chapter_number: int
    :return: The number of verses in the specified chapter.
    :rtype: int
    :raises TypeError: If the chapter_number is not an integer.
    :raises ValueError: If the chapter_number is not valid or does not exist.
    """

    # Check that chapter_number is an integer
    if not isinstance(chapter_number, int):
        raise TypeError("Chapter number must be an integer")

    # Check that the chapter number is valid
    if chapter_number not in QURAN_CHAPTERS:
        raise ValueError(f"Invalid chapter number: {chapter_number}")

    return QURAN_CHAPTERS[chapter_number]


def check_chapter_verse_exists(chapter_number: int, verse_number: int) -> bool:
    """Check if a specific verse exists in a specified chapter."""

    # Check that chapter_number is an integer
    if not isinstance(chapter_number, int):
        raise TypeError("Chapter/Sura number must be an integer")

    # Check that verse_number is an integer
    if not isinstance(verse_number, int):
        raise TypeError("Verse/Aya number must be an integer")

    # Check that the chapter number is valid
    if chapter_number not in QURAN_CHAPTERS:
        return False
    elif verse_number > QURAN_CHAPTERS[chapter_number]:
        return False
    else:
        return True



# Singleton instance - loaded once on module import
QURAN_CHAPTERS: Dict[int, int] = load_quran_chapters()


if __name__ == "__main__":
    # Simple test when run directly
    print("=" * 70)
    print("LOAD DATA TANZIL.NET - MODULE TEST")
    print("=" * 70)
    print()
    print("Please note: this file was made to be called from other scripts.")
    print("Executing this file directly runs the following tests and then quits.")
    print()

    # Test 1: Load chapter metadata
    print("1. Loading chapter metadata...")
    chapters = load_quran_chapters()
    print(f"   ✓ Loaded {len(chapters)} chapters from Tanzil.net XML")
    print(f"   Chapter 1 (Al-Fatihah): {chapters[1]} verses")
    print(f"   Chapter 2 (Al-Baqarah): {chapters[2]} verses")
    print(f"   Chapter 114 (An-Nas): {chapters[114]} verses")
    print()

    # Test 2: Get Uthmani text
    print("2. Getting Uthmani text (Chapter 1, Verse 1)...")
    try:
        uthmani_text = get_quran_uthmani_text(1, 1)
        print(f"   ✓ Uthmani: {uthmani_text}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    print()

    # Test 3: Get English translations for the same verse
    print("3. Getting English translations (Chapter 1, Verse 1)...")

    try:
        arberry_text = get_quran_arberry_text(1, 1)
        print(f"   ✓ Arberry: {arberry_text}")
    except Exception as e:
        print(f"   ✗ Arberry Error: {e}")

    try:
        pickthall_text = get_quran_pickthall_text(1, 1)
        print(f"   ✓ Pickthall: {pickthall_text}")
    except Exception as e:
        print(f"   ✗ Pickthall Error: {e}")

    try:
        sahih_text = get_quran_sahih_text(1, 1)
        print(f"   ✓ Sahih: {sahih_text}")
    except Exception as e:
        print(f"   ✗ Sahih Error: {e}")
    print()

    # Test 4: Get all verses of a chapter (showing first 3)
    print("4. Getting all verses of Chapter 112 (Al-Ikhlas) in Arberry translation...")
    try:
        all_verses = get_quran_arberry_text(112)
        print(f"   ✓ Retrieved {len(all_verses)} verses:")
        for verse_num in sorted(all_verses.keys()):
            print(f"      {verse_num}. {all_verses[verse_num]}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    print()

    print("=" * 70)
    print("Available functions:")
    print("  • get_quran_uthmani_text(ch, v?)  - Arabic Uthmani script")
    print("  • get_quran_arberry_text(ch, v?)  - Arberry English translation")
    print("  • get_quran_pickthall_text(ch, v?) - Pickthall English translation")
    print("  • get_quran_sahih_text(ch, v?)    - Sahih International translation")
    print("=" * 70)


