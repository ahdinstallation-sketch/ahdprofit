"""Batch 4: do the letters predict the formula that follows? Do they encode the surah's names?"""
import sys
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from muqattaat import corpus
from muqattaat.arabic import normalize_letters
from muqattaat.openings import OPENINGS, MUQ_SURAHS, MUQ_LETTERS
rng = np.random.default_rng(4)
w, meta = corpus.load(); w = w[w.pos != "INL"].sort_values(["surah", "verse", "word"])
op = {s: o.replace(" ", "") for o, ss, _ in OPENINGS for s in ss}
head = {s: [normalize_letters(x) for x in w[w.surah == s].head(4).form_norm] for s in MUQ_SURAHS}
def formula(s):
    h = head[s]
    if h[0] in ("تلك", "ذلك", "كذلك"): return "demonstrative (تلك/ذلك…)"
    if h[0].startswith("و"): return "oath (و + Book/pen)"
    if h[0] in ("تنزيل", "كتب") or "انزل" in h[0] or h[0] == "ما": return "revelation statement (تنزيل/كتاب أنزل…)"
    return "other"
F = {s: formula(s) for s in MUQ_SURAHS}
print("=== H13 can the letters alone predict the formula that follows? (leave-one-out, nearest letter set) ===")
for s in MUQ_SURAHS: print(f"  {s:3d} {op[s]:6s} -> {F[s]}")
def loo(labels):
    hit = 0
    for s in MUQ_SURAHS:
        others = [t for t in MUQ_SURAHS if t != s]
        sim = {t: len(set(op[s]) & set(op[t])) / len(set(op[s]) | set(op[t])) for t in others}
        best = max(sim.values()); nn = [t for t in others if sim[t] == best]
        pred = Counter(labels[t] for t in nn).most_common(1)[0][0]
        hit += pred == labels[s]
    return hit
obs = loo(F)
null = np.array([loo(dict(zip(MUQ_SURAHS, rng.permutation([F[s] for s in MUQ_SURAHS])))) for _ in range(5000)])
base = Counter(F.values()).most_common(1)[0][1]
print(f"  correct predictions: {obs}/29 (always guessing the commonest class: {base}/29); shuffled-label mean {null.mean():.1f}; p = {(null >= obs).mean():.4f}")

print("\n=== H14 (your direction) do the letters encode the names in the surah's story? ===")
pn = w[w.pos == "PN"]
names = {s: Counter(normalize_letters(l) for l in pn[pn.surah == s].lemma_norm.dropna() if normalize_letters(l) != "الله") for s in range(1, 115)}
def score(assign):  # share of name letters (token-weighted) that belong to the assigned opening's letters
    v = []
    for s, o in assign.items():
        tot = sum(len(n) * k for n, k in names[s].items())
        if tot: v.append(sum(sum(c in set(o) for c in n) * k for n, k in names[s].items()) / tot)
    return np.mean(v)
obs = score(op)
ops = list(op.values()); null = []
for _ in range(20000):
    null.append(score(dict(zip(MUQ_SURAHS, rng.permutation(ops)))))
null = np.array(null)
print(f"  share of letters in each surah's proper names that come from its own opening: {obs:.3f}; shuffled openings {null.mean():.3f}; p = {(null >= obs).mean():.3f}")
for s in (19, 20, 38, 12, 36):
    print(f"   {s} {op[s]}: names {dict(names[s].most_common(5))}")
