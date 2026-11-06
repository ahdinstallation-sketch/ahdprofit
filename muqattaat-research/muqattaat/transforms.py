"""The decoding methods of the study protocol (Phase 4).

Every generator returns Candidate records with a human-readable derivation.
Fixed limits (pre-registered, not tuned):
  * M6 partitions: at most 4 letters (parts), repetition allowed
  * M8B subsets: size >= 2, at least one original AND one reconstructed letter
  * zero digits are dropped (no letter has value 0)
"""
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import combinations, permutations

from .abjad import ABJAD, VALUE2LETTER, digital_root
from .arabic import normalize_letters

ORDERED_VALUES = sorted(ABJAD.values())
MAX_PARTITION_LETTERS = 4
METHODS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8A", "M8B"]
SCORED_METHODS = ["M1", "M2", "M3", "M5", "M6", "M7", "M8A", "M8B"]  # M4 yields one letter


@dataclass
class Candidate:
    opening: str
    method: str
    reconstruction: str          # e.g. "M2:عا"
    letters: str                 # generated letters (ordered as generated)
    match_kind: str              # root | lemma | arramooz
    match: str                   # matched root / lemma / word
    root: str | None             # Qur'anic root used for frequency analysis
    uses_all_letters: bool
    unused_letters: str
    derivation: str
    flags: list = field(default_factory=list)


def abjad_sum(letters: str) -> int:
    return sum(ABJAD[c] for c in normalize_letters(letters))


# ---------- numeric reconstructions -------------------------------------------------

def place_value_letters(n: int) -> str | None:
    """71 -> 70 + 1 -> 'عا'. Thousands digit only representable when it is 1 (غ)."""
    out, place = [], 1
    while n:
        d = n % 10
        if d:
            v = d * place
            if v not in VALUE2LETTER:
                return None
            out.append(VALUE2LETTER[v])
        n //= 10
        place *= 10
    return "".join(reversed(out))


def digit_letters(n: int) -> str:
    """71 -> 7, 1 -> 'زا' (zeros dropped)."""
    return "".join(VALUE2LETTER[int(d)] for d in str(n) if d != "0")


def digital_root_letter(n: int) -> str:
    return VALUE2LETTER[digital_root(n)]


def reconstructions(n: int) -> dict:
    out = {}
    pv = place_value_letters(n)
    if pv:
        out["M2"] = pv
    out["M3"] = digit_letters(n)
    out["M4"] = digital_root_letter(n)
    return out


@lru_cache(maxsize=None)
def partitions(n: int, max_parts: int = MAX_PARTITION_LETTERS, min_val: int = 1) -> tuple:
    """Multisets of Abjad values (non-decreasing) summing to n, at most max_parts parts."""
    res = []
    if n == 0:
        return ((),)
    if max_parts == 0:
        return ()
    for v in ORDERED_VALUES:
        if v < min_val:
            continue
        if v > n:
            break
        for rest in partitions(n - v, max_parts - 1, v):
            res.append((v,) + rest)
    return tuple(res)


# ---------- lexicon matching -------------------------------------------------------

def _key(s):
    return "".join(sorted(normalize_letters(s)))


def match_multiset(L, letters, include_arramooz=True):
    """All lexicon items whose letter multiset equals `letters` (any order)."""
    k = _key(letters)
    out = [("root", r, r) for r in L.roots_for_key(k)]
    out += [("lemma", m, L.lemma_root.get(m)) for m in L.lemmas_for_key(k)]
    if include_arramooz:
        out += [("arramooz", w, L.arr_info[w][0] or None) for w in L.arr_by_key.get(k, ())]
    return out


def match_sequence(L, letters, include_arramooz=True):
    """Lexicon items spelled exactly `letters` in this order (after normalization)."""
    n = normalize_letters(letters)
    out = []
    if n in L.root_by_seq:
        out.append(("root", L.root_by_seq[n], L.root_by_seq[n]))
    out += [("lemma", m, L.lemma_root.get(m)) for m in L.lemma_by_seq.get(n, ())]
    if include_arramooz:
        out += [("arramooz", w, L.arr_info[w][0] or None) for w in L.arr_by_seq.get(n, ())]
    return out


def _flags(original, letters, match):
    fl = []
    if "ا" in normalize_letters(letters) and any(c in "ءأإآؤئ" for c in match):
        fl.append("alif in inventory matched a hamza (hamza normalization)")
    if any(c in "ىة" for c in match):
        fl.append("ى/ة normalization")
    return fl


def _sub_multisets(letters, min_size=2):
    seen = set()
    for size in range(min_size, len(letters) + 1):
        for combo in combinations(range(len(letters)), size):
            s = "".join(sorted(letters[i] for i in combo))
            if s not in seen:
                seen.add(s)
                yield s, combo


# ---------- the methods ------------------------------------------------------------

def generate(opening: str, L, include_arramooz=True, methods=None) -> list[Candidate]:
    methods = set(methods or METHODS)
    orig = normalize_letters(opening.replace(" ", ""))
    V = abjad_sum(orig)
    rec = reconstructions(V)
    C = []

    def add(method, recon, letters, hits, all_used, unused, derivation):
        for kind, item, root in hits:
            C.append(Candidate(opening, method, recon, letters, kind, item, root, all_used, unused,
                               derivation, _flags(orig, letters, item)))

    if "M1" in methods:  # exact Abjad equivalence
        hits = [("root", r, r) for r in L.roots_by_value.get(V, ())]
        hits += [("lemma", m, L.lemma_root.get(m)) for m in L.lemmas_by_value.get(V, ())]
        if include_arramooz:
            hits += [("arramooz", w, L.arr_info[w][0] or None) for w in L.arr_by_value.get(V, ())]
        for kind, item, root in hits:
            C.append(Candidate(opening, "M1", f"value={V}", item, kind, item, root, True, "",
                               f"Abjad({opening}) = {V} = Abjad({item})", _flags(orig, item, item)))

    for m in ("M2", "M3"):
        if m in methods and m in rec:
            r = rec[m]
            add(m, f"{m}:{r}", r, match_sequence(L, r, include_arramooz), True, "",
                f"{V} -> {'place values' if m == 'M2' else 'digits'} -> {' + '.join(r)} = {r}")

    if "M5" in methods:  # original + reconstruction, concatenated in order
        for m, r in rec.items():
            for seq, how in ((orig + r, "original+recon"), (r + orig, "recon+original")):
                add("M5", f"{m}:{r}", seq, match_sequence(L, seq, include_arramooz), True, "",
                    f"{opening} ({V}) -> {m} {r}; {how} = {seq}")

    if "M6" in methods:  # alternative additive partitions
        for parts in partitions(V):
            letters = "".join(VALUE2LETTER[p] for p in parts)
            add("M6", f"partition:{'+'.join(map(str, parts))}", letters,
                match_multiset(L, letters, include_arramooz), True, "",
                f"{V} = {' + '.join(map(str, parts))} -> {{{' '.join(letters)}}} (any order)")

    if "M7" in methods and len(orig) >= 2:  # exact anagram of the original letters
        add("M7", "anagram", orig, match_multiset(L, orig, include_arramooz), True, "",
            f"rearrange {' '.join(orig)}")

    if "M8A" in methods or "M8B" in methods:
        for m, r in rec.items():
            combined = orig + r
            if "M8A" in methods:
                add("M8A", f"{m}:{r}", combined, match_multiset(L, combined, include_arramooz), True, "",
                    f"{opening} ({V}) -> {m} {r}; all of {{{' '.join(combined)}}} rearranged")
            if "M8B" in methods:
                n_orig = len(orig)
                for sub, combo in _sub_multisets(combined):
                    if len(sub) == len(combined):
                        continue
                    if not any(i < n_orig for i in combo) or not any(i >= n_orig for i in combo):
                        continue
                    unused = Counter(combined) - Counter(sub)
                    add("M8B", f"{m}:{r}", sub, match_multiset(L, sub, include_arramooz), False,
                        "".join(unused.elements()),
                        f"{opening} ({V}) -> {m} {r}; subset {{{' '.join(sub)}}} of {{{' '.join(combined)}}}, "
                        f"unused {{{' '.join(unused.elements())}}}")
    return C


def candidate_roots(opening_letters: str, L, methods) -> set:
    """Fast path for the null model: Qur'anic roots only (no Arramooz)."""
    return {c.root for c in generate(opening_letters, L, include_arramooz=False, methods=methods)
            if c.root and c.match_kind in ("root", "lemma")}


def all_permutations_words(L, letters):
    """Ordered permutations that are lemmas or roots (used for reporting M7 spellings)."""
    out = set()
    for p in set(permutations(letters)):
        for kind, item, root in match_sequence(L, "".join(p), include_arramooz=False):
            out.add((kind, item, root))
    return out
