"""Batch 1: six alternative hypotheses, each against a chance baseline."""
import sys, itertools
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats as st
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from muqattaat import corpus
from muqattaat.arabic import normalize_letters
from muqattaat.abjad import LETTERS
from muqattaat.openings import OPENINGS, MUQ_SURAHS, MUQ_LETTERS
rng = np.random.default_rng(1)
w, meta = corpus.load()
w = w[w.pos != "INL"]  # drop the muqatta'at tokens themselves
MUQ = set(MUQ_LETTERS)
print("=== H1 Zamakhshari: 14 letters = half of each phonetic class ===")
CLASSES = {  # classical tajwid sifat (Sibawayh / Ibn al-Jazari)
 "hams (whispered)": "فحثهشخصسكت", "jahr (voiced)": None,
 "shidda (plosive)": "اجدقطبكت", "rakhawa+tawassut": None,
 "itbaq (emphatic)": "صضطظ", "infitah": None,
 "istiʿla (elevated)": "خصضغطقظ", "istifal": None,
 "qalqala": "قطبجد", "dhalaqa (fluent)": "فرملنب",
 "safir (whistling)": "صزس", "lin-capable/weak (و ي ا)": "اوي"}
allL = set(LETTERS)
for k in list(CLASSES):
    if CLASSES[k] is None:
        prev = list(CLASSES)[list(CLASSES).index(k) - 1]
        CLASSES[k] = "".join(sorted(allL - set(CLASSES[prev])))
def score(sub):
    sub = set(sub); dev = 0; rows = []
    for k, cl in CLASSES.items():
        n, m = len(cl), len(sub & set(cl)); rows.append((k, n, m)); dev += abs(m - n / 2)
    return dev, rows
d_obs, rows = score(MUQ)
for k, n, m in rows: print(f"  {k:28s} class size {n:2d}  in muqatta'at {m:2d}  (half = {n/2})")
null = np.array([score(rng.choice(LETTERS, 14, replace=False))[0] for _ in range(100000)])
print(f"  total |deviation from half| = {d_obs}; random 14-letter sets: mean {null.mean():.2f}; P(<= observed) = {(null <= d_obs).mean():.4f}")
# exact: number of classes hit exactly or within 0.5
exact = sum(abs(m - n/2) <= 0.5 for _, n, m in rows)
nulle = np.array([sum(abs(m - n/2) <= 0.5 for _, n, m in score(rng.choice(LETTERS, 14, replace=False))[1]) for _ in range(100000)])
print(f"  classes split as evenly as possible: {exact}/{len(rows)}; P(random >= that) = {(nulle >= exact).mean():.4f}")

print("\n=== H2 self-reference: opening letters over-represented in own surah text ===")
text = {s: "".join(w[w.surah == s].form_norm.map(normalize_letters)) for s in range(1, 115)}
cnt = {s: Counter(t) for s, t in text.items()}; ln = {s: len(t) for s, t in text.items()}
F = np.array([[cnt[s][c] / ln[s] for c in LETTERS] for s in range(1, 115)])  # 114 x 28
Z = (F - F.mean(0)) / F.std(0)
LI = {c: i for i, c in enumerate(LETTERS)}
def self_score(assign):  # mean z of opening letters in their surahs
    v = [Z[s - 1, LI[c]] for o, ss in assign for s in ss for c in set(o.replace(" ", ""))]
    return np.mean(v)
real = [(o, ss) for o, ss, _ in OPENINGS]
obs = self_score(real)
per = []
for o, ss, _ in OPENINGS:
    for c in sorted(set(o.replace(" ", ""))):
        per.append((o, c, ",".join(map(str, ss)), np.mean([Z[s-1, LI[c]] for s in ss])))
perm = []
for _ in range(20000):
    pool = rng.permutation(np.arange(1, 115)); i = 0; a = []
    for o, ss in real: a.append((o, list(pool[i:i+len(ss)]))); i += len(ss)
    perm.append(self_score(a))
perm = np.array(perm)
print(f"  mean z-score of each opening's letters in its own surahs = {obs:.3f}; random surah assignment mean {perm.mean():.3f}; p = {(perm >= obs).mean():.4f}")
for o, c, ss, z in sorted(per, key=lambda x: -x[3])[:12]: print(f"   {o:7s} letter {c}  surahs {ss:18s} z = {z:+.2f}")
print("   weakest:", [(o, c, round(z, 2)) for o, c, ss, z in sorted(per, key=lambda x: x[3])[:6]])

print("\n=== H3 family style: same-opening surahs share letter profiles beyond adjacency ===")
groups = [ss for _, ss, _ in OPENINGS if len(ss) > 1] + [[26, 27, 28], [40,41,42,43,44,45,46]]
groups = [[2,3,29,30,31,32],[10,11,12,14,15],[26,27,28],[40,41,42,43,44,45,46]]
from scipy.spatial.distance import pdist, squareform
D = squareform(pdist(Z, "euclidean"))
def within(g): return np.mean([D[a-1, b-1] for a, b in itertools.combinations(g, 2)])
for g in groups:
    o = within(g)
    # null: blocks with the same internal surah-number spacing, shifted, plus random same-size sets of similar length
    offs = [s - g[0] for s in g]; shifts = [x for x in range(1, 115 - offs[-1]) if not set(x + np.array(offs)) & set(g)]
    nb = np.array([within(list(x + np.array(offs))) for x in shifts])
    L_ = np.array([ln[s] for s in g]); cand = [s for s in range(1, 115) if s not in g]
    nr = []
    for _ in range(5000):
        pick = [min(cand, key=lambda t: abs(np.log(ln[t]) - np.log(L)) + rng.random()*0.6) for L in L_]
        if len(set(pick)) == len(pick): nr.append(within(pick))
    nr = np.array(nr)
    print(f"  group {g}: within-distance {o:.2f} | same-spacing blocks elsewhere: mean {nb.mean():.2f}, P(<=) = {(nb <= o).mean():.3f} (n={len(nb)}) | length-matched random sets: mean {nr.mean():.2f}, P(<=) = {(nr <= o).mean():.3f}")

print("\n=== H4 rhyme: opening letters vs verse-final (fasila) letter ===")
last = w.sort_values(["surah", "verse", "word"]).groupby(["surah", "verse"]).form_norm.last().map(lambda f: normalize_letters(f)[-1:] if f else "")
rhyme = last.groupby(level=0).agg(lambda s: Counter(s).most_common(1)[0][0])
share = last.groupby(level=0).agg(lambda s: Counter(s).most_common(1)[0][1] / len(s))
hits = []
for o, ss, _ in OPENINGS:
    for s in ss:
        r = rhyme[s]; hits.append((o, s, r, round(share[s], 2), r in o, o.replace(" ", "")[-1] == r))
hdf = pd.DataFrame(hits, columns=["opening", "surah", "dominant_rhyme_letter", "share", "rhyme_in_opening", "last_letter_is_rhyme"])
print(hdf.to_string(index=False))
obs_in = hdf.rhyme_in_opening.sum()
nulls = []
allr = rhyme.to_dict()
for _ in range(20000):
    sh = rng.permutation(list(allr.values()))
    m = dict(zip(allr.keys(), sh))
    nulls.append(sum(m[s] in o for o, ss, _ in OPENINGS for s in ss))
nulls = np.array(nulls)
print(f"  surahs whose dominant rhyme letter is in their opening: {obs_in}/29; shuffled rhymes mean {nulls.mean():.1f}; p = {(nulls >= obs_in).mean():.4f}")

print("\n=== H5 the letters announce the Book: verses right after the opening mention scripture ===")
BOOK = {"كتب", "قرا", "نزل", "ايي", "وحي", "ذكر", "تنزيل"}
first = {}
for s in range(1, 115):
    sw = w[(w.surah == s) & (w.verse <= 3)]
    first[s] = bool(set(sw.root_norm.dropna()) & BOOK)
a = sum(first[s] for s in MUQ_SURAHS); b = sum(first[s] for s in range(1, 115) if s not in MUQ_SURAHS)
tab = [[a, 29 - a], [b, 85 - b]]
print(f"  muqatta'at surahs with Book/revelation roots in verses 1-3: {a}/29; other surahs: {b}/85; Fisher p = {st.fisher_exact(tab, 'greater')[1]:.2e}, odds ratio {st.fisher_exact(tab)[0]:.1f}")
print("   muqatta'at surahs lacking it:", [s for s in MUQ_SURAHS if not first[s]])
print("   non-muqatta'at surahs having it:", [s for s in range(1, 115) if s not in MUQ_SURAHS and first[s]])

print("\n=== H6 Code 19: counts of the opening's letters in their surahs ===")
c19 = []
for o, ss, _ in OPENINGS:
    tot = sum(cnt[s][c] for s in ss for c in o.replace(" ", ""))
    c19.append((o, ss, tot, tot % 19 == 0))
for r in c19: print(f"  {r[0]:7s} {str(r[1]):25s} letter total {r[2]:6d}  divisible by 19: {r[3]}")
k = sum(r[3] for r in c19)
print(f"  {k}/14 divisible by 19 (expected by chance {14/19:.2f}); binomial p = {st.binom.sf(k-1, 14, 1/19):.3f}")
