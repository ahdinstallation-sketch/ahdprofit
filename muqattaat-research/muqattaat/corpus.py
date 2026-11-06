"""Download and parse the Quranic Arabic Corpus morphology (v0.4).

Primary source  : corpus.quran.com/download (not reachable from the build
                  environment) -> GitHub mirror cltk/arabic_morphology_quranic-corpus
Cross-check     : mustafa0x/quran-morphology (Arabic-script derivative of the QAC)
Metadata        : quran.com-frontend-next chapters (Meccan/Medinan), fawazahmed0/quran-api
"""
import hashlib
import json
import re
import urllib.request
from collections import defaultdict

import pandas as pd

from . import RAW, PROCESSED
from .arabic import bw_to_ar, normalize_surface, normalize_letters

SOURCES = {
    "qac": ("qac/quranic-corpus-morphology-0.4.txt",
            "https://raw.githubusercontent.com/cltk/arabic_morphology_quranic-corpus/master/quranic-corpus-morphology-0.4.txt",
            "a1d12923815341face765083805d2148ed2d9f5cc3f7d6665219d887675d8c46"),
    "qac_crosscheck": ("qac_crosscheck/quran-morphology.txt",
                       "https://raw.githubusercontent.com/mustafa0x/quran-morphology/master/quran-morphology.txt",
                       "742bfac59941b2cb09736d5b7aae694af50792261fb8450cbf6afafcc340645f"),
    "meta_qcom": ("meta_qcom/chapters_en.json",
                  "https://raw.githubusercontent.com/quran/quran.com-frontend-next/production/data/chapters/en.json",
                  "a85fdfbda9e005e134dfcf1b642c197ca65ebbdf4d0da74f59e59497ff5c3716"),
    "meta_fawaz": ("meta_fawaz/info.json",
                   "https://raw.githubusercontent.com/fawazahmed0/quran-api/1/info.json",
                   "99c654caeea7c63bf9634703167ea0f806d90c55f98d23e2e82d3e3d1b74075c"),
    "font_amiri": ("fonts/Amiri-Regular.ttf",
                   "https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Regular.ttf", None),
    "font_amiri_bold": ("fonts/Amiri-Bold.ttf",
                        "https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Bold.ttf", None),
}

# Egyptian standard (Al-Azhar 1924) revelation order, as distributed in Tanzil's
# quran-data.js. tanzil.net was unreachable from the build environment, so this
# list was transcribed; `load_metadata` asserts it is a permutation of 1..114.
REVELATION_ORDER = [
    5, 87, 89, 92, 112, 55, 39, 88, 113, 51, 52, 53, 96, 72, 54, 70, 50, 69, 44, 45,
    73, 103, 74, 102, 42, 47, 48, 49, 85, 84, 57, 75, 90, 58, 43, 41, 56, 38, 59, 60,
    61, 62, 63, 64, 65, 66, 95, 111, 106, 34, 67, 76, 23, 37, 97, 46, 94, 105, 101, 91,
    109, 110, 104, 108, 99, 107, 77, 2, 78, 79, 71, 40, 3, 4, 31, 98, 33, 80, 81, 24,
    7, 82, 86, 83, 27, 36, 8, 68, 10, 35, 26, 9, 11, 12, 28, 1, 25, 100, 93, 14,
    30, 16, 13, 32, 19, 29, 17, 15, 18, 114, 6, 22, 20, 21,
]


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_all(force=False) -> list[dict]:
    rows = []
    for key, (rel, url, expected) in SOURCES.items():
        path = RAW / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if force or not path.exists():
            urllib.request.urlretrieve(url, path)
        digest = sha256(path)
        if expected and digest != expected:
            raise RuntimeError(f"{key}: sha256 mismatch ({digest})")
        rows.append({"key": key, "file": rel, "url": url, "sha256": digest,
                     "bytes": path.stat().st_size})
    return rows


_LOC = re.compile(r"\((\d+):(\d+):(\d+):(\d+)\)")


def parse_qac(path=None) -> pd.DataFrame:
    """One row per word (surah, verse, word) with form, root, lemma, POS of stem."""
    path = path or RAW / SOURCES["qac"][0]
    words = defaultdict(lambda: {"form_bw": "", "root_bw": None, "lemma_bw": None, "pos": None})
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("("):
                continue
            loc, form, tag, feats = line.rstrip("\n").split("\t")
            s, v, w, _ = map(int, _LOC.match(loc).groups())
            rec = words[(s, v, w)]
            rec["form_bw"] += form
            fs = feats.split("|")
            if "STEM" in fs:
                rec["pos"] = tag
                for ft in fs:
                    if ft.startswith("ROOT:"):
                        rec["root_bw"] = ft[5:]
                    elif ft.startswith("LEM:"):
                        rec["lemma_bw"] = ft[4:]
    rows = []
    for (s, v, w), r in words.items():
        form = bw_to_ar(r["form_bw"])
        root = bw_to_ar(r["root_bw"]) if r["root_bw"] else None
        lemma = bw_to_ar(r["lemma_bw"]) if r["lemma_bw"] else None
        rows.append({
            "surah": s, "verse": v, "word": w,
            "form": form, "form_norm": normalize_surface(form),
            "root": root, "root_norm": normalize_letters(root) if root else None,
            "lemma": lemma, "lemma_norm": normalize_surface(re.sub(r"\d", "", lemma)) if lemma else None,
            "pos": r["pos"], "root_bw": r["root_bw"], "lemma_bw": r["lemma_bw"],
        })
    df = pd.DataFrame(rows).sort_values(["surah", "verse", "word"]).reset_index(drop=True)
    return df


def parse_crosscheck(path=None) -> pd.DataFrame:
    path = path or RAW / SOURCES["qac_crosscheck"][0]
    roots = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            s, v, w, _ = map(int, parts[0].split(":"))
            m = re.search(r"ROOT:([^|]+)", parts[3])
            if m:
                roots[(s, v, w)] = m.group(1)
    return pd.Series(roots, name="root_cc")


def load_metadata() -> pd.DataFrame:
    assert sorted(REVELATION_ORDER) == list(range(1, 115)), "revelation order is not a permutation"
    qcom = json.load(open(RAW / SOURCES["meta_qcom"][0], encoding="utf-8"))
    fz = json.load(open(RAW / SOURCES["meta_fawaz"][0], encoding="utf-8"))
    rows = []
    for ch in fz["chapters"]:
        n = ch["chapter"]
        q = qcom[str(n)]
        rows.append({"surah": n, "name": q["transliteratedName"], "name_en": q["translatedName"],
                     "name_ar": normalize_surface(ch["arabicname"]).replace("سورة ", ""),
                     "verses": q["versesCount"], "place": q["revelationPlace"],
                     "place_fawaz": ch["revelation"], "revelation_order": REVELATION_ORDER[n - 1]})
    return pd.DataFrame(rows)


def build(force=False):
    """Download, parse, cross-check and cache processed tables."""
    PROCESSED.mkdir(parents=True, exist_ok=True)
    prov = download_all(force=force)
    words = parse_qac()
    cc = parse_crosscheck()
    words = words.join(cc, on=["surah", "verse", "word"])
    meta = load_metadata()
    words.to_parquet(PROCESSED / "words.parquet") if _has_parquet() else words.to_pickle(PROCESSED / "words.pkl")
    meta.to_csv(PROCESSED / "surah_meta.csv", index=False)
    pd.DataFrame(prov).to_csv(PROCESSED / "provenance.csv", index=False)
    return words, meta, prov


def _has_parquet():
    try:
        import pyarrow  # noqa: F401
        return True
    except ImportError:
        return False


def load():
    p = PROCESSED / "words.parquet"
    words = pd.read_parquet(p) if p.exists() else pd.read_pickle(PROCESSED / "words.pkl")
    meta = pd.read_csv(PROCESSED / "surah_meta.csv")
    return words, meta
