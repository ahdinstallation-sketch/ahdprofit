"""Eastern (Mashriqi) Abjad numerals.

Conventions (documented, applied identically everywhere):
  * all alif/hamza forms (ا أ إ آ ٱ ء) = 1
  * ؤ counts as its carrier و = 6, ئ as its carrier ي = 10   (flagged)
  * ى (alif maqsura) = 10 as ي                                (flagged)
  * ة (taʾ marbuta) = 5 as ه; the alternative 400 is reported (flagged)
"""
from .arabic import normalize_letters, normalization_flags

ABJAD = {
    "ا": 1, "ب": 2, "ج": 3, "د": 4, "ه": 5, "و": 6, "ز": 7, "ح": 8, "ط": 9,
    "ي": 10, "ك": 20, "ل": 30, "م": 40, "ن": 50, "س": 60, "ع": 70, "ف": 80,
    "ص": 90, "ق": 100, "ر": 200, "ش": 300, "ت": 400, "ث": 500, "خ": 600,
    "ذ": 700, "ض": 800, "ظ": 900, "غ": 1000,
}
VALUE2LETTER = {v: k for k, v in ABJAD.items()}
LETTERS = list(ABJAD)  # the 28 letters


def value(word: str) -> int:
    s = normalize_letters(word)
    missing = [c for c in s if c not in ABJAD]
    if missing:
        raise ValueError(f"non-Abjad characters in {word!r}: {missing}")
    return sum(ABJAD[c] for c in s)


def value_with_flags(word: str) -> tuple[int, list[str]]:
    return value(word), normalization_flags(word)


def letter_for(v: int) -> str | None:
    return VALUE2LETTER.get(v)


def digital_root(n: int) -> int:
    return 0 if n == 0 else 1 + (n - 1) % 9
