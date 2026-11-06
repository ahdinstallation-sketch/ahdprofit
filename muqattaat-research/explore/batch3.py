"""Batch 3: what grammatical role do the letters play? + H8 confound + local Book effect."""
import sys, itertools
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats as st
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from muqattaat import corpus
from muqattaat.arabic import normalize_letters
from muqattaat.abjad import value
from muqattaat.openings import OPENINGS, MUQ_SURAHS
rng = np.random.default_rng(3)
w, meta = corpus.load(); w = w[w.pos != "INL"].sort_values(["surah", "verse", "word"])
op = {s: o for o, ss, _ in OPENINGS for s in ss}
first = {s: list(w[w.surah == s].head(4).form_norm.map(normalize_letters)) for s in range(1, 115)}

print("=== H9 short openings are followed by an oath (wa- + noun) ===")
oath = {s: first[s][0].startswith("و") and len(first[s][0]) > 3 for s in range(1, 115)}
rows = [(s, op[s], len(op[s].replace(" ", "")), oath[s]) for s in MUQ_SURAHS]
short = [r for r in rows if r[2] <= 2]; long_ = [r for r in rows if r[2] >= 3]
t = [[sum(r[3] for r in short), sum(not r[3] for r in short)], [sum(r[3] for r in long_), sum(not r[3] for r in long_)]]
print(f"  1-2 letter openings followed by oath: {t[0][0]}/{len(short)} {[r[:2] for r in short if r[3]]}; 3-5 letters: {t[1][0]}/{len(long_)}; Fisher p = {st.fisher_exact(t, 'greater')[1]:.4f}")
print(f"  non-muqatta'at surahs opening with an oath: {sum(oath[s] for s in range(1,115) if s not in MUQ_SURAHS)}/85 ->",
      [s for s in range(1, 115) if s not in MUQ_SURAHS and oath[s]])

print("\n=== H10 the next word points back at the letters (demonstrative / 'the Book') ===")
DEM = {"ذلك", "تلك", "كذلك"}
dem = {s: bool(set(first[s][:2]) & DEM) for s in range(1, 115)}
a = sum(dem[s] for s in MUQ_SURAHS); b = sum(dem[s] for s in range(1, 115) if s not in MUQ_SURAHS)
print(f"  demonstrative in first 2 words: muqatta'at {a}/29 {[s for s in MUQ_SURAHS if dem[s]]}; others {b}/85; Fisher p = {st.fisher_exact([[a,29-a],[b,85-b]], 'greater')[1]:.1e}")
# in the whole Qur'an, how often does a verse START with تلك/ذلك + (آيات|الكتاب)?
vs = w.groupby(["surah", "verse"]).form_norm.apply(lambda s: [normalize_letters(x) for x in s])
pat = [(k, v[:3]) for k, v in vs.items() if v[0] in ("تلك", "ذلك") and len(v) > 1 and (v[1].endswith("ايت") or "الكتب" in v[1])]
print(f"  verses anywhere in the Qur'an beginning 'تلك/ذلك + آيات/الكتاب': {len(pat)} ->", [k for k, _ in pat])

print("\n=== H11 is the Book reference local to the opening? ===")
BOOK = {"كتب", "قرا", "نزل", "ايي", "وحي", "ذكر"}
loc = []
for s in range(1, 115):
    sw = w[w.surah == s]; r = sw.root_norm
    head = r.head(15).isin(BOOK).mean(); rest = r.iloc[15:].isin(BOOK).mean() if len(r) > 30 else np.nan
    loc.append({"surah": s, "muq": s in MUQ_SURAHS, "hd": head, "rs": rest})
loc = pd.DataFrame(loc).dropna()
for g, d in loc.groupby("muq"):
    print(f"  {'muqatta`at' if g else 'other':10s}: Book-root share in first 15 words {d["hd"].mean():.3f} vs rest of surah {d["rs"].mean():.3f}; paired Wilcoxon p = {st.wilcoxon(d["hd"], d["rs"], alternative='greater').pvalue:.1e}")
dm = loc[loc.muq]; do = loc[~loc.muq]
print(f"  head-minus-rest: muqatta'at {np.mean(dm["hd"] - dm["rs"]):.3f} vs others {np.mean(do["hd"] - do["rs"]):.3f}; Mann-Whitney p = {st.mannwhitneyu(dm["hd"] - dm["rs"], do["hd"] - do["rs"], alternative='greater').pvalue:.1e}")

print("\n=== H8 confound check: Abjad total vs surah position, controlling for number of letters ===")
d = pd.DataFrame([{"opening": o, "mean_surah": np.mean(ss), "abjad": value(o.replace(' ', '')), "n_letters": len(o.replace(' ', ''))} for o, ss, _ in OPENINGS])
print("  opening level (n=14): Spearman abjad~surah", [round(x, 3) for x in st.spearmanr(d.abjad, d.mean_surah)],
      "| n_letters~surah", [round(x, 3) for x in st.spearmanr(d.n_letters, d.mean_surah)])
import statsmodels.api as sm
m = sm.OLS(d.mean_surah, sm.add_constant(np.column_stack([np.log(d.abjad), d.n_letters]))).fit()
print(f"  OLS mean_surah ~ log(abjad) + n_letters: log(abjad) coef {m.params.iloc[1]:.1f} p = {m.pvalues.iloc[1]:.2f}; n_letters coef {m.params.iloc[2]:.1f} p = {m.pvalues.iloc[2]:.2f}")

print("\n=== H12 (your direction) Abjad(letters) vs Abjad of the words that follow ===")
for s in MUQ_SURAHS:
    v = value(op[s].replace(" ", "")); fw = first[s][:4]
    vals = []
    for i in range(len(fw)):
        try: vals.append(value(fw[i]))
        except ValueError: vals.append(None)
    cum = [sum(x for x in vals[:k+1] if x) for k in range(len(vals))]
    hit = [fw[i] for i in range(len(fw)) if vals[i] == v] + [("+".join(fw[:k+1])) for k in range(len(cum)) if cum[k] == v]
    if hit: print(f"  {s} {op[s]} ({v}): equal-value following words: {hit}")
print("  (no other surah had a following word or word-prefix with the same Abjad total)")
