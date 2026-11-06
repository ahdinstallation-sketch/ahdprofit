"""Arabic orthography helpers: Buckwalter conversion and normalization."""
import re

# Extended Buckwalter as used by the Quranic Arabic Corpus (corpus.quran.com/java/buckwalter.jsp)
BW2AR = {
    "'": "ء", "|": "آ", ">": "أ", "&": "ؤ", "<": "إ", "}": "ئ", "A": "ا", "b": "ب",
    "p": "ة", "t": "ت", "v": "ث", "j": "ج", "H": "ح", "x": "خ", "d": "د", "*": "ذ",
    "r": "ر", "z": "ز", "s": "س", "$": "ش", "S": "ص", "D": "ض", "T": "ط", "Z": "ظ",
    "E": "ع", "g": "غ", "_": "ـ", "f": "ف", "q": "ق", "k": "ك", "l": "ل", "m": "م",
    "n": "ن", "h": "ه", "w": "و", "Y": "ى", "y": "ي", "F": "ً", "N": "ٌ", "K": "ٍ",
    "a": "َ", "u": "ُ", "i": "ِ", "~": "ّ", "o": "ْ", "^": "ٓ", "#": "ٔ", "`": "ٰ",
    "{": "ٱ", ":": "ۜ", "@": "۟", '"': "۠", "[": "ۢ", ";": "ۣ", ",": "ۥ", ".": "ۦ",
    "!": "ۨ", "-": "۪", "+": "۫", "%": "۬", "]": "ۭ",
}


def bw_to_ar(s: str) -> str:
    return "".join(BW2AR.get(c, c) for c in s)


# Harakat, Quranic annotation marks, tatweel, superscript/subscript alif etc.
_DIACRITICS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")

HAMZA_FORMS = set("أإآءؤئٱ")
ALIF_LIKE = set("اأإآٱء")


def strip_diacritics(s: str) -> str:
    return _DIACRITICS.sub("", s)


def normalize_surface(s: str) -> str:
    """Unvocalized surface form. Keeps hamza carriers, ة and ى (they matter for
    Abjad); only wasla alif is mapped to bare alif."""
    s = strip_diacritics(s)
    return s.replace("ٱ", "ا")


def normalize_letters(s: str) -> str:
    """Aggressive normalization used for letter-inventory (anagram) matching:
    all hamza/alif forms -> ا, ؤ -> و, ئ -> ي, ى -> ي, ة -> ه.
    Every one of these is recorded as a flag by `normalization_flags`."""
    s = normalize_surface(s)
    table = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ء": "ا", "ؤ": "و",
                           "ئ": "ي", "ى": "ي", "ة": "ه"})
    return s.translate(table)


def normalization_flags(s: str) -> list[str]:
    s = normalize_surface(s)
    flags = []
    if any(c in "أإآء" for c in s):
        flags.append("hamza/alif normalized to ا")
    if "ؤ" in s:
        flags.append("ؤ normalized to و")
    if "ئ" in s:
        flags.append("ئ normalized to ي")
    if "ى" in s:
        flags.append("alif maqsura ى normalized to ي")
    if "ة" in s:
        flags.append("taʾ marbuta ة normalized to ه")
    return flags


def letters_key(s: str) -> str:
    """Sorted normalized letters: the multiset key for anagram lookup."""
    return "".join(sorted(normalize_letters(s)))
