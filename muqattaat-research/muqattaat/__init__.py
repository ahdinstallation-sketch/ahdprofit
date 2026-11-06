"""Muqattaʿat numerical-linguistic research package.

Modules
-------
corpus      download + parse the Quranic Arabic Corpus (QAC) morphology file
arabic      orthographic normalization, Buckwalter transliteration
abjad       Eastern Abjad values with explicit normalization flags
lexicon     validation lexicons (QAC roots/lemmas/forms, Arramooz)
transforms  the nine decoding methods of the study protocol
stats       enrichment tests, rate ratios, confidence intervals, FDR
nullmodel   randomized control experiments
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
OUT = ROOT / "outputs"
