"""Validation lexicons.

L1  QAC roots      (1,642 roots, frequency-bearing)
L2  QAC lemmas     (4,831 lemmas, mapped to their root)
L3  QAC surface forms (unvocalized; Uthmani spelling - see flags)
L4  Arramooz Alwaseet (Zerrouki; ~30k nouns + ~14k verbs with roots; GPL) - general
    Arabic validation outside the Qur'an.
"""
import glob
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field

import pandas as pd

from .abjad import ABJAD, value
from .arabic import letters_key, normalize_letters, strip_diacritics


@dataclass
class Lexicon:
    root_by_key: dict = field(default_factory=lambda: defaultdict(set))     # sorted letters -> roots
    root_by_seq: dict = field(default_factory=dict)                         # normalized root -> root
    lemma_by_key: dict = field(default_factory=lambda: defaultdict(set))    # sorted letters -> lemma_norm
    lemma_by_seq: dict = field(default_factory=lambda: defaultdict(set))    # normalized lemma -> lemma_norm
    lemma_root: dict = field(default_factory=dict)                          # lemma_norm -> root
    lemma_vocal: dict = field(default_factory=dict)
    form_set: set = field(default_factory=set)                              # normalized surface forms
    arr_by_key: dict = field(default_factory=lambda: defaultdict(set))      # sorted letters -> words
    arr_by_seq: dict = field(default_factory=lambda: defaultdict(set))
    arr_info: dict = field(default_factory=dict)                            # word -> (root, definition, type)
    roots_by_value: dict = field(default_factory=lambda: defaultdict(set))
    lemmas_by_value: dict = field(default_factory=lambda: defaultdict(set))
    arr_by_value: dict = field(default_factory=lambda: defaultdict(set))
    root_freq: dict = field(default_factory=dict)
    lemma_freq: dict = field(default_factory=dict)

    def roots_for_key(self, key):
        return self.root_by_key.get(key, set())

    def lemmas_for_key(self, key):
        return self.lemma_by_key.get(key, set())


def _safe_value(s):
    try:
        return value(s)
    except ValueError:
        return None


def build_lexicon(words: pd.DataFrame, with_arramooz=True) -> Lexicon:
    L = Lexicon()
    rb = words[words.root.notna()]
    L.root_freq = rb.root.value_counts().to_dict()
    for root in L.root_freq:
        n = normalize_letters(root)
        L.root_by_key["".join(sorted(n))].add(root)
        L.root_by_seq[n] = root
        v = _safe_value(root)
        if v is not None:
            L.roots_by_value[v].add(root)
    lw = words[words.lemma_norm.notna()]
    L.lemma_freq = lw.lemma_norm.value_counts().to_dict()
    lem_root = lw.groupby("lemma_norm").root.agg(lambda s: s.dropna().mode().iat[0] if s.notna().any() else None)
    lem_voc = lw.groupby("lemma_norm").lemma.first()
    for lem, root in lem_root.items():
        n = normalize_letters(lem)
        if not n or any(c not in ABJAD for c in n):
            continue
        L.lemma_by_key["".join(sorted(n))].add(lem)
        L.lemma_by_seq[n].add(lem)
        L.lemma_root[lem] = root if isinstance(root, str) else None
        L.lemma_vocal[lem] = lem_voc[lem]
        v = _safe_value(lem)
        if v is not None:
            L.lemmas_by_value[v].add(lem)
    L.form_set = set(words.form_norm.map(normalize_letters))
    if with_arramooz:
        _add_arramooz(L)
    return L


def _add_arramooz(L: Lexicon):
    import arramooz
    db = glob.glob(arramooz.__path__[0] + "/data/arabicdictionary.sqlite")[0]
    con = sqlite3.connect(db)
    rows = list(con.execute("select unvocalized, root, definition, wordtype from nouns"))
    rows += [(u, r, "", "فعل") for u, r in con.execute("select unvocalized, root from verbs")]
    for unv, root, definition, wtype in rows:
        w = strip_diacritics(unv or "").strip()
        n = normalize_letters(w)
        if not n or any(c not in ABJAD for c in n):
            continue
        L.arr_by_key["".join(sorted(n))].add(w)
        L.arr_by_seq[n].add(w)
        if w not in L.arr_info:
            d = (definition or "").strip().strip('"')
            L.arr_info[w] = (root or "", "" if d.startswith(":لا شرح") else d[:200], wtype or "")
        v = _safe_value(w)
        if v is not None:
            L.arr_by_value[v].add(w)
