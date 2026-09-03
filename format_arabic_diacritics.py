#!/usr/bin/env python3
"""
format_arabic_diacritics.py - Arabic Diacritics Linter and Formatter.

Enforces Canonical Project Order: Base Letter -> Shadda (U+0651) -> Harakah.
Reorders instances of inverted diacritics (Harakah followed by Shadda) to Shadda followed by Harakah.
See docs/adr/0001-shadda-first-diacritic-order.md and CONTEXT.md for rationale and domain definitions.
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Unicode constants
SHADDA = "\u0651"
# Harakat: Fathatan (U+064B), Dammatan (U+064C), Kasratan (U+064D),
#          Fatha (U+064E), Damma (U+064F), Kasra (U+0650), Superscript/Dagger Alef (U+0670)
HARAKAT_CHARS = "\u064b\u064c\u064d\u064e\u064f\u0650\u0670"
HARAKAT_CLASS = f"[{HARAKAT_CHARS}]"

# Inverted pattern: Harakah followed immediately by Shadda
INVERTED_PATTERN = re.compile(f"({HARAKAT_CLASS})({re.escape(SHADDA)})")

# Word pattern to extract surrounding context for reporting
ARABIC_WORD_PATTERN = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+")

DEFAULT_EXTENSIONS = [".csv"]
IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    ".agents",
    "backup",
    ".gemini",
}


def reorder_diacritics(text: str) -> tuple[str, int]:
    """
    Replaces all occurrences of Harakah + Shadda with Shadda + Harakah.
    Returns (new_text, count_of_replacements).
    """
    new_text, count = INVERTED_PATTERN.subn(r"\2\1", text)
    return new_text, count


def find_violations(text: str) -> list[dict]:
    """
    Scans text line-by-line and identifies all inverted diacritic occurrences with context.
    """
    violations = []
    lines = text.splitlines(keepends=True)

    for line_idx, line in enumerate(lines, start=1):
        for match in INVERTED_PATTERN.finditer(line):
            start, end = match.span()
            # Find surrounding word if available
            word_match = None
            for wm in ARABIC_WORD_PATTERN.finditer(line):
                if wm.start() <= start and wm.end() >= end:
                    word_match = wm
                    break

            if word_match:
                token = word_match.group(0)
                corrected_token, _ = reorder_diacritics(token)
            else:
                token = line[max(0, start - 3) : min(len(line), end + 3)]
                corrected_token, _ = reorder_diacritics(token)

            violations.append(
                {
                    "line_num": line_idx,
                    "col_num": start + 1,
                    "inverted_sequence": match.group(0),
                    "inverted_token": token,
                    "corrected_token": corrected_token,
                }
            )

    return violations


def format_diff(violation: dict) -> str:
    """
    Formats a single violation for terminal display.
    """
    token_old = violation["inverted_token"]
    token_new = violation["corrected_token"]
    codepoints_old = " ".join(f"U+{ord(c):04X}" for c in token_old)
    codepoints_new = " ".join(f"U+{ord(c):04X}" for c in token_new)
    return (
        f"  Line {violation['line_num']}:{violation['col_num']}: {token_old} -> {token_new}\n"
        f"    Old: {codepoints_old}\n"
        f"    New: {codepoints_new}"
    )


def scan_files(paths: list[str], extensions: list[str]) -> list[Path]:
    """
    Resolves a list of files or directories into a sorted list of unique file paths matching extensions.
    """
    collected = set()

    for p_str in paths:
        p = Path(p_str)
        if not p.exists():
            continue
        if p.is_file():
            if any(p.name.endswith(ext) for ext in extensions) or len(paths) == 1:
                collected.add(p)
        elif p.is_dir():
            for root, dirs, files in os.walk(p):
                dirs[:] = [
                    d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")
                ]
                for file in files:
                    if any(file.endswith(ext) for ext in extensions):
                        collected.add(Path(root) / file)

    return sorted(collected)


def main(argv: list[str] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check and reorder Arabic diacritics to enforce Canonical Project Order (Base -> Shadda -> Harakah)."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=[],
        help="Files or directories to scan. Defaults to all *.csv files in the repository.",
    )
    parser.add_argument(
        "-c",
        "--check",
        action="store_true",
        help="Check mode (default): exits 0 if all clean, 1 if violations are found.",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Print detailed diffs of what would be changed without modifying any files.",
    )
    parser.add_argument(
        "-w",
        "--write",
        "--fix",
        dest="write",
        action="store_true",
        help="Modify files in-place to correct diacritic ordering.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Minimal output. Only report overall status.",
    )

    args = parser.parse_args(argv)

    # Determine files to process
    target_paths = args.paths if args.paths else ["."]
    files = scan_files(target_paths, DEFAULT_EXTENSIONS)

    if not files:
        if not args.quiet:
            print("No matching files found to check.")
        return 0

    total_violations = 0
    total_files_with_violations = 0

    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            continue

        violations = find_violations(content)
        if violations:
            total_files_with_violations += 1
            total_violations += len(violations)

            if not args.quiet:
                print(f"{file_path}: {len(violations)} violation(s)")
                if args.dry_run:
                    for v in violations:
                        print(format_diff(v))

            if args.write:
                new_content, count = reorder_diacritics(content)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                if not args.quiet:
                    print(f"  Fixed {count} diacritic order issue(s) in {file_path}")

    if not args.quiet:
        print("\n--- Summary ---")
        print(f"Files scanned: {len(files)}")
        print(f"Files with violations: {total_files_with_violations}")
        print(f"Total violations: {total_violations}")

    if args.write:
        return 0

    # In check mode or dry-run mode, exit 1 if violations were found
    return 1 if total_violations > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
