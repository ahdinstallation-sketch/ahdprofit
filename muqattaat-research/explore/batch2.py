"""Batch 2: stress-test the survivors (H1, H5) and new angles."""
import sys, itertools
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats as st
import statsmodels.api as sm
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from muqattaat import corpus
from muqattaat.arabic import normalize_letters
from muqattaat.abjad import LETTERS, value
from muqattaat.openings import OPENINGS, MUQ_SURAHS, MUQ_LETTERS
rng = np.random.default_rng(2)
w, meta = corpus.load(); w = w[w.pos != "INL"]
MUQ = set(MUQ_LETTERS); allL = set(LETTERS)

print("=== H1 robustness: independent classical sifat only (no complements) ===")
SIFAT = {  # Ibn al-Jazari's Muqaddima list of characteristics with opposites, plus the single ones
 "hams": "فحثهشخصسكت", "shidda": "اجدقطبكت", "tawassut (lin ʿumar)": "لنعمر", "istiʿla": "خصضغطقظ",
 "itbaq": "صضطظ", "idhlaq": "فرملنب", "safir": "صزس", "qalqala": "قطبجد", "lin": "وي",
 "inhiraf": "لر", "takrir": "ر", "tafashshi": "ش", "istitala": "ض", "ghunna": "نم"}
def dev(sub, classes):
    s = set(sub); return sum(abs(len(s & set(c)) - len(c) / 2) for c in classes.values())
def evenly(sub, classes):
    s = set(sub); return sum(abs(len(s & set(c)) - len(c) / 2) <= 0.5 for c in classes.values())
for name, cl in [("8 core classes with an opposite", {k: SIFAT[k] for k in ["hams","shidda","istiʿla","itbaq","idhlaq","safir","qalqala","tawassut (lin ʿumar)"]}),
                 ("all 14 sifat", SIFAT)]:
    rows = [(k, len(c), len(MUQ & set(c))) for k, c in cl.items()]
    R = [rng.choice(LETTERS, 14, replace=False) for _ in range(100000)]
    nd = np.array([dev(r, cl) for r in R]); ne = np.array([evenly(r, cl) for r in R])
    print(f" {name}: " + "; ".join(f"{k} {m}/{n}" for k, n, m in rows))
    print(f"   deviation {dev(MUQ, cl)} vs random mean {nd.mean():.2f}, P(<=) = {(nd <= dev(MUQ, cl)).mean():.4f}; "
          f"evenly split {evenly(MUQ, cl)}/{len(cl)}, P(>=) = {(ne >= evenly(MUQ, cl)).mean():.4f}")
# also: the 14 letters vs the 14 most frequent letters of the Qur'an (is it just 'frequent letters'?)
alltext = "".join(w.form_norm.map(normalize_letters)); fc = Counter(c for c in alltext if c in allL)
top14 = {c for c, _ in fc.most_common(14)}
print(f"  overlap of muqatta'at letters with the 14 most frequent Qur'anic letters: {len(MUQ & top14)}/14; missing frequent: {sorted(top14 - MUQ)}; included rare: {sorted(MUQ - top14)}")
print(f"  top-14-by-frequency set deviation = {dev(top14, SIFAT)} (vs muqatta'at {dev(MUQ, SIFAT)})")

print("\n=== H5 stress test: control for Meccan/Medinan and amount of text ===")
BOOK = {"كتب", "قرا", "نزل", "ايي", "وحي", "ذكر"}
place = meta.set_index("surah").place
rows = []
for s in range(1, 115):
    sw = w[w.surah == s].sort_values(["verse", "word"])
    for N in (15, 30):
        first = sw.head(N)
        rows.append({"surah": s, "N": N, "book": bool(set(first.root_norm.dropna()) & BOOK), "muq": s in MUQ_SURAHS,
                     "meccan": place[s] == "makkah", "words": len(sw)})
df = pd.DataFrame(rows)
for N in (15, 30):
    d = df[df.N == N]
    a = d[d.muq].book.mean(); b = d[~d.muq].book.mean()
    X = sm.add_constant(np.column_stack([d.muq.astype(float), d.meccan.astype(float), np.log(d.words)]))
    m = sm.Logit(d.book.astype(float).values, X).fit(disp=0)
    mec = d[d.meccan]
    t = [[mec[mec.muq].book.sum(), (~mec[mec.muq].book).sum()], [mec[~mec.muq].book.sum(), (~mec[~mec.muq].book).sum()]]
    print(f"  first {N} words: muqatta'at {a:.2f} vs others {b:.2f}; logistic OR (adj. Meccan, log length) = {np.exp(m.params[1]):.1f}, p = {m.pvalues[1]:.1e}; "
          f"Meccan-only Fisher {t}, p = {st.fisher_exact(t, 'greater')[1]:.1e}")
# what exactly follows the letters?
print("  text immediately after the letters (first 6 words of verse 1 or 2):")
FOLLOW = {}
for o, ss, _ in OPENINGS:
    for s in ss:
        sw = w[(w.surah == s)].sort_values(["verse", "word"]).head(6)
        FOLLOW[s] = list(sw.form_norm.map(normalize_letters))
        print(f"   {s:3d} {o:7s} " + " ".join(sw.form_norm))

print("\n=== H7 each letter family has its own fixed formula ===")
fam = {s: o for o, ss, _ in OPENINGS for s in ss}
fam[27] = "طسم/طس"; fam[26] = fam[28] = "طسم/طس"
for s in (40,41,42,43,44,45,46): fam[s] = "حم*"
for s in (10,11,12,13,14,15): fam[s] = "الر*"
lem = {s: set(w[(w.surah == s) & (w.verse <= 2)].lemma_norm.dropna()) for s in MUQ_SURAHS}
def jac(a, b): return len(lem[a] & lem[b]) / len(lem[a] | lem[b])
pairs = list(itertools.combinations(MUQ_SURAHS, 2))
same = [jac(a, b) for a, b in pairs if fam[a] == fam[b]]; diff = [jac(a, b) for a, b in pairs if fam[a] != fam[b]]
obs = np.mean(same) - np.mean(diff)
labels = [fam[s] for s in MUQ_SURAHS]; null = []
for _ in range(20000):
    pl = dict(zip(MUQ_SURAHS, rng.permutation(labels)))
    sm_ = [jac(a, b) for a, b in pairs if pl[a] == pl[b]]; df_ = [jac(a, b) for a, b in pairs if pl[a] != pl[b]]
    null.append(np.mean(sm_) - np.mean(df_))
null = np.array(null)
print(f"  opening-verse lemma overlap: same family {np.mean(same):.3f} vs different {np.mean(diff):.3f}; permutation p = {(null >= obs).mean():.4f}")
# adjacency control: same family pairs are adjacent; compare adjacent different-family muq pairs
adj_diff = [jac(a, b) for a, b in pairs if fam[a] != fam[b] and abs(a - b) <= 2]
print(f"  control: adjacent (<=2 apart) different-family pairs overlap {np.mean(adj_diff):.3f} (n={len(adj_diff)})")
for f in sorted(set(fam.values())):
    ss = [s for s in MUQ_SURAHS if fam[s] == f]
    if len(ss) > 1:
        common = set.intersection(*[lem[s] for s in ss])
        print(f"   {f:8s} {ss}: lemmas shared by all = {sorted(common)}")

print("\n=== H8 Abjad totals vs surah numbers / verse counts / order (your direction, new angle) ===")
rows = []
for o, ss, _ in OPENINGS:
    for s in ss:
        m = meta.set_index("surah").loc[s]
        rows.append({"opening": o, "surah": s, "abjad": value(o.replace(" ", "")), "verses": m.verses, "order": m.revelation_order,
                     "letters": len(o.replace(" ", ""))})
d = pd.DataFrame(rows)
for col in ("surah", "verses", "order"):
    r, p = st.spearmanr(d.abjad, d[col]); print(f"  Spearman abjad vs {col}: rho = {r:+.2f}, p = {p:.3f}")
# exact arithmetic links: abjad == verses, == surah, abjad mod verses etc.
links = d[(d.abjad == d.verses) | (d.abjad == d.surah) | (d.abjad % d.verses == 0) | (d.verses % d.abjad == 0)]
print("  exact equalities/divisibility between total and verses or surah number:", links[["opening","surah","abjad","verses"]].to_dict("records"))
