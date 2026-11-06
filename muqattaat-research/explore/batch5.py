"""Batch 5: letter shapes (rasm, dots) and Eastern-Arabic digit shapes."""
import sys, itertools
from math import comb
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import stats as st
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from muqattaat import corpus, lexicon
from muqattaat.abjad import LETTERS, value
from muqattaat.openings import OPENINGS, MUQ_LETTERS
from muqattaat.render import FONT_REGULAR
rng = np.random.default_rng(5)
MUQ = set(MUQ_LETTERS); ALL = LETTERS
print("=== H15 letter shapes: dots and shared skeletons ===")
DOTTED = set("بتثجخذزشضظغفقني")
print(f"  dotted letters in the alphabet: {len(DOTTED)}/28; in the muqatta'at set: {sorted(MUQ & DOTTED)} = {len(MUQ & DOTTED)}/14")
p = st.hypergeom.cdf(len(MUQ & DOTTED), 28, len(DOTTED), 14)
print(f"  P(random 14 letters contain <= {len(MUQ & DOTTED)} dotted) = {p:.2e}")
# skeleton (rasm) groups: letters that differ only by dots, isolated forms
GROUPS = {"Naskh isolated forms": ["ا", "بتث", "جحخ", "دذ", "رز", "سش", "صض", "طظ", "عغ", "ف", "ق", "ك", "ل", "م", "ن", "ه", "و", "ي"],
          "early Hijazi/Kufic rasm (ف=ق, ن ي join ب)": ["ا", "بتثني", "جحخ", "دذ", "رز", "سش", "صض", "طظ", "عغ", "فق", "ك", "ل", "م", "ه", "و"]}
def base(g):  # undotted member of a skeleton group, if any
    u = [c for c in g if c not in DOTTED]; return u[0] if u else None
for name, G in GROUPS.items():
    gof = {c: i for i, g in enumerate(G) for c in g}
    used = [gof[c] for c in MUQ]; distinct = len(set(used)) == len(used)
    twin_groups = [g for g in G if len(g) > 1]
    picks = {g: sorted(set(g) & MUQ) for g in twin_groups}
    def props(S):
        S = set(S); u = [gof[c] for c in S]
        one_per_shape = len(set(u)) == len(u)
        undotted_choice = all((set(g) & S) <= {base(g)} for g in twin_groups if base(g))
        return one_per_shape, undotted_choice
    o1, o2 = props(MUQ)
    R = [props(rng.choice(ALL, 14, replace=False)) for _ in range(200000)]
    r1 = np.mean([a for a, b in R]); r2 = np.mean([b for a, b in R]); r12 = np.mean([a and b for a, b in R])
    print(f"  [{name}] {len(G)} skeleton shapes; muqatta'at use {len(set(used))} different shapes")
    print(f"    letters taken from each multi-letter shape group: { {g: v for g, v in picks.items()} }")
    print(f"    one letter per shape: {o1} (random P = {r1:.4f});  never the dotted twin of an undotted letter: {o2} (random P = {r2:.4f});  both: P = {r12:.5f}")
excluded = sorted(set(ALL) - MUQ)
print(f"  the 14 letters NOT used: {excluded}")

print("\n=== glyph similarity: render letters and Eastern-Arabic digits, compare shapes ===")
DIG = "٠١٢٣٤٥٦٧٨٩"
fonts = [str(FONT_REGULAR), "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
def glyph(ch, font, S=64):
    f = ImageFont.truetype(font, 120); im = Image.new("L", (240, 240), 0); d = ImageDraw.Draw(im)
    d.text((60, 30), ch, fill=255, font=f); a = np.array(im) > 80
    ys, xs = np.nonzero(a)
    if len(xs) == 0: return None
    a = a[ys.min():ys.max()+1, xs.min():xs.max()+1]
    h, w = a.shape; side = max(h, w); pad = np.zeros((side, side), bool)
    pad[(side-h)//2:(side-h)//2+h, (side-w)//2:(side-w)//2+w] = a
    return np.array(Image.fromarray(pad.astype(np.uint8)*255).resize((S, S))) / 255.0
def sim(a, b):  # best IoU-like overlap over small shifts
    best = 0
    for dy in range(-4, 5, 2):
        for dx in range(-4, 5, 2):
            bb = np.roll(np.roll(b, dy, 0), dx, 1)
            best = max(best, (np.minimum(a, bb).sum()) / (np.maximum(a, bb).sum() + 1e-9))
    return best
SIM = np.zeros((28, 10))
for f in fonts:
    G = {c: glyph(c, f) for c in ALL + list(DIG)}
    for i, c in enumerate(ALL):
        for j, d in enumerate(DIG):
            if G[c] is not None and G[d] is not None: SIM[i, j] += sim(G[c], G[d]) / len(fonts)
for j, d in enumerate(DIG):
    top = np.argsort(-SIM[:, j])[:3]
    print(f"  digit {d} ({j}) looks most like: " + ", ".join(f"{ALL[i]} {SIM[i, j]:.2f}" for i in top))
L2D = {c: int(np.argmax(SIM[i])) for i, c in enumerate(ALL)}
D2L = {j: ALL[int(np.argmax(SIM[:, j]))] for j in range(10)}

print("\n=== H16 read each opening letter as the digit it looks like ===")
words, meta = corpus.load(); M = meta.set_index("surah")
def decode(o): return int("".join(str(L2D[c]) for c in o))
def hits(o, ss):
    n = decode(o); h = []
    for s in ss:
        for k, v in (("surah no.", s), ("verses", M.loc[s, "verses"]), ("abjad", value(o)), ("rev. order", M.loc[s, "revelation_order"])):
            if n == v: h.append(k)
    return n, h
tot = 0
for o, ss, _ in OPENINGS:
    o = o.replace(" ", ""); n, h = hits(o, ss); tot += bool(h)
    print(f"  {o:6s} -> {''.join(DIG[L2D[c]] for c in o)} = {n:>6d}   surahs {ss}  matches: {h or '-'}")
null = []
for _ in range(20000):
    k = 0
    for o, ss, _ in OPENINGS:
        r = "".join(rng.choice(MUQ_LETTERS, len(o.replace(' ', '')), replace=False)); k += bool(hits(r, ss)[1])
    null.append(k)
null = np.array(null)
print(f"  openings matching a surah property: {tot}/14; random letter sets mean {null.mean():.2f}; p = {(null >= tot).mean():.3f}")

print("\n=== H17 write the Abjad total in Arabic digits, read the digit shapes as letters ===")
L = lexicon.build_lexicon(words)
from muqattaat.transforms import match_multiset, match_sequence
def shape_word(n): return "".join(D2L[int(c)] for c in str(n))
def valid(s): return [m for k, m, r in match_sequence(L, s) + match_multiset(L, s) if k in ("root", "lemma")]
vh = 0
for o, ss, _ in OPENINGS:
    v = value(o.replace(" ", "")); s = shape_word(v); ok = sorted(set(valid(s))); vh += bool(ok)
    print(f"  {o:7s} {v:4d} = {''.join(DIG[int(c)] for c in str(v))} -> shapes {s:4s} -> Qur'anic words: {ok or '-'}")
nv = []
for _ in range(5000):
    k = 0
    for o, ss, _ in OPENINGS:
        r = "".join(rng.choice(MUQ_LETTERS, len(o.replace(' ', '')), replace=False)); k += bool(valid(shape_word(value(r))))
    nv.append(k)
nv = np.array(nv)
print(f"  openings yielding a real word: {vh}/14; random letter sets mean {nv.mean():.2f}; p = {(nv >= vh).mean():.3f}")
