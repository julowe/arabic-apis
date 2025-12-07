import re


def tex_escape_text(text: str) -> str:
    """Escape special LaTeX characters and remove footnote tags.

    Mirrors the existing behavior in scripts: strips `<sup foot_note=...>...</sup>`
    and escapes LaTeX meta characters.
    """
    # Remove footnotes like: <sup foot_note=12>12</sup>
    text = re.sub(r"<sup foot_note=(\d+)>(\d+)</sup>", r"", text)

    # Escape special characters
    # Important: escape literal backslashes FIRST so that backslashes we add
    # for other escapes (like \&) are not transformed.
    text = text.replace("\\", r"\textbackslash")
    text = text.replace("&", r"\&")
    text = text.replace("%", r"\%")
    text = text.replace("$", r"\$")
    text = text.replace("#", r"\#")
    text = text.replace("_", r"\_")
    text = text.replace("{", r"\{")
    text = text.replace("}", r"\}")
    text = text.replace("^", r"\textasciicircum")
    text = text.replace("~", r"\textasciitilde")
    return text


def tex_cleanup_text(text: str) -> str:
    """Apply small cleanups for LaTeX output and escape text.

    Current behavior: wrap ﷺ in Arabic macro and then escape LaTeX characters.
    """

    # First escape any LaTeX characters present in the original text
    text = tex_escape_text(text)
    # Then inject the Arabic ligature macro without escaping it
    text = re.sub(r"(ﷺ)", r"(\\ar{ﷺ})", text)
    return text


def tex_remove_arabic_marks(text: str) -> str:
    """Remove specific Arabic diacritical marks for cleaner display.

    The set of codepoints mirrors what the scripts currently remove.
    """

    # TODO check these are correct and all that we want to remove
    chars_to_remove = ["\u06D6", "\u06D7", "\u06D8", "\u06D9", "\u06DA", "\u06DB", "\u06DC", "\u06E0", "\u06E1",
                       "\u06E2", "\u06E3", "\u06E4", "\u06E5", "\u06E6", "\u06E7", "\u06E8", ]

    # Real characters
    chars = [c.encode("utf-8").decode("unicode_escape") for c in chars_to_remove]
    regex_pattern = "[" + re.escape("".join(chars)) + "]"
    text = re.sub(regex_pattern, "", text)
    return text
