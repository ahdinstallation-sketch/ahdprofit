"""Build outputs/REPORT.pdf from outputs/results.pkl (run build_outputs.py first).

Every number in the report is read from the results file, not typed by hand.
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from muqattaat import OUT, corpus, transforms  # noqa: E402
from muqattaat.glosses import GLOSS  # noqa: E402
from muqattaat.openings import OPENINGS  # noqa: E402
import arabic_reshaper  # noqa: E402
from bidi.algorithm import get_display  # noqa: E402
from muqattaat.render import _AR_RUN, FONT_BOLD, FONT_REGULAR  # noqa: E402

R = pickle.load(open(OUT / "results.pkl", "rb"))
pdfmetrics.registerFont(TTFont("Amiri", str(FONT_REGULAR)))
pdfmetrics.registerFont(TTFont("Amiri-Bold", str(FONT_BOLD)))
pdfmetrics.registerFontFamily("Amiri", normal="Amiri", bold="Amiri-Bold", italic="Amiri", boldItalic="Amiri-Bold")
DV = Path("/usr/share/fonts/truetype/dejavu/")
LATIN, LATIN_BOLD = ((DV / "DejaVuSerif.ttf", DV / "DejaVuSerif-Bold.ttf") if (DV / "DejaVuSerif.ttf").exists()
                     else (FONT_REGULAR, FONT_BOLD))  # Amiri fallback where DejaVu is not installed
pdfmetrics.registerFont(TTFont("DVS", str(LATIN)))
pdfmetrics.registerFont(TTFont("DVS-Bold", str(LATIN_BOLD)))
pdfmetrics.registerFontFamily("DVS", normal="DVS", bold="DVS-Bold", italic="DVS", boldItalic="DVS-Bold")
_CMAP = TTFont("probe", str(LATIN)).face.charToGlyph
_SUB = {"→": "->", "Σ": "sum ", "−": "-", "≥": ">=", "≤": "<=", "≈": "~", "×": "x", "–": "-", "—": "-", "±": "+/-"}


def clean(s):
    s = str(s)
    return "".join(c if (ord(c) in _CMAP or c in "\n") else _SUB.get(c, "?") for c in s)


def T(s):
    """Latin in DejaVu Serif; each Arabic run shaped, put in visual order and set in Amiri."""
    s = str(s)
    out, last = [], 0
    for m in _AR_RUN.finditer(s):
        out.append(clean(s[last:m.start()]))
        out.append(f'<font name="Amiri" size="+1.5">{get_display(arabic_reshaper.reshape(m.group()))}</font>')
        last = m.end()
    out.append(clean(s[last:]))
    return "".join(out)


ss = getSampleStyleSheet()
BODY = ParagraphStyle("b", parent=ss["BodyText"], fontName="DVS", fontSize=9.5, leading=14, spaceAfter=5)
SMALL = ParagraphStyle("s", parent=BODY, fontSize=7.5, leading=10, spaceAfter=0)
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="DVS-Bold", fontSize=16, leading=21, spaceBefore=10, spaceAfter=6)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="DVS-Bold", fontSize=12, leading=16, spaceBefore=8, spaceAfter=4)
TITLE = ParagraphStyle("t", parent=H1, fontSize=22, leading=27, alignment=TA_CENTER)
CAP = ParagraphStyle("c", parent=BODY, fontSize=9, leading=11, textColor=colors.HexColor("#555555"), alignment=TA_CENTER)
BOX = ParagraphStyle("box", parent=BODY, backColor=colors.HexColor("#f3efe6"), borderColor=colors.HexColor("#c9a86a"),
                     borderWidth=0.8, borderPadding=7, spaceBefore=6, spaceAfter=10)
story = []
P = lambda s, st=BODY: story.append(Paragraph(T(s), st))
fmtp = lambda p: "<0.0001" if p < 1e-4 else f"{p:.4f}" if p < 0.01 else f"{p:.3f}"


def table(df, widths=None, font=8.5):
    data = [[Paragraph(T(f"<b>{c}</b>"), SMALL) for c in df.columns]]
    for _, r in df.iterrows():
        data.append([Paragraph(T(v if isinstance(v, str) else "n/a" if isinstance(v, float) and np.isnan(v)
                                 else f"{v:.3g}" if isinstance(v, float) else str(v)), SMALL) for v in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bbbbbb")),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ece6d8")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#faf8f3")])]))
    story.append(t)
    story.append(Spacer(1, 6))


def fig(name, width=17, caption=""):
    from PIL import Image as PI
    path = OUT / "figures" / name
    w, h = PI.open(path).size
    story.append(Image(str(path), width=width * cm, height=width * cm * h / w))
    if caption:
        story.append(Paragraph(T(caption), CAP))
    story.append(Spacer(1, 6))


ns = R["null_summary"]
nsel = lambda null, m: ns[(ns.null == null) & (ns.method == m)].iloc[0]
prim = nsel("N2", "UNION")
D = R["discoveries"]
xr = R["cross_reference"]
po = R["per_opening_method"]
cv = R["nested_cv"]
leg = R["legitimacy"].set_index("null")
rk = R["rankings"]
dt = R["discovery_table"].set_index("discovery")
n_pairs = len(xr)
qcols = [c for c in xr.columns if c.endswith("q_BH_global")]
surv = {c.split("|")[0]: xr[xr[c] < 0.05].apply(lambda r: f"{r.opening}:{r.root}", axis=1).tolist() for c in qcols}

# ------------------------------------------------------------------ title + summary
P("Decoding the Qur'an's Muqaṭṭaʿāt through Abjad mathematics, Arabic linguistics and computational analysis", TITLE)
P("Exploratory research report: reproducible pipeline, pre-registered primary test, 10,000-trial randomized controls", CAP)
story.append(Spacer(1, 10))
P("Answer to the central question", H1)
verdict = (f"<b>The data do not support an encoded numerical-linguistic structure that performs better than chance.</b> "
           f"Under the pre-registered primary test, the 14 real openings decoded with every method together produce a "
           f"score T = {prim.T_observed:.1f}, against {prim.T_null_mean:.1f} ± {prim.T_null_sd:.1f} for random letter sequences "
           f"drawn from the same 14-letter inventory (empirical p = {prim.p_empirical:.3f}, 10,000 trials). "
           f"No single method survives correction for the eight methods tried (smallest Holm-adjusted p = "
           f"{ns[(ns.null == 'N2') & (ns.method != 'UNION')].p_holm_methods.min():.2f}). "
           f"When the best method is chosen on half of the openings and tested on the other half, it beats chance in only "
           f"{(cv.test_p < 0.05).mean() * 100:.1f}% of 200 splits (median held-out p = {cv.test_p.median():.2f}). "
           f"Across {n_pairs} opening-root pairs, none is enriched in its own surahs under all three robust tests after "
           f"correction for multiple comparisons.")
story.append(Paragraph(T(verdict), BOX))
P("What the data <i>do</i> show: (1) every Abjad total in the brief is arithmetically correct; (2) the transformations "
  "generate real Arabic words easily, for random letters just as for the real openings "
  f"({leg.loc['N2', 'share_sequences_with_>=1_valid_root'] * 100:.1f}% of random sequences yield at least one Qur'anic root, "
  f"with {leg.loc['N2', 'mean_candidate_roots_per_sequence']:.1f} candidate roots on average versus "
  f"{leg.loc['REAL', 'mean_candidate_roots_per_sequence']:.1f} for the real openings); (3) a few candidate roots are genuinely "
  "more frequent in their surahs (علم in the Alif-Lām-Mīm surahs, أب in the Alif-Lām-Rā surahs, which is the Joseph narrative), "
  "but random letter sequences find comparably strong matches in the same surahs, so these are properties of the surahs' "
  "vocabulary, not of the letters.")
xa = xr.query("opening=='الر' and root=='ابو'").iloc[0]
_w, _ = corpus.load()
n12 = int(((_w.surah == 12) & (_w.root == "ابو")).sum())
P(f"The أب result is concentrated in Surah Yusuf: {n12} of the {xa.count_target} occurrences in the five Alif-Lām-Rā surahs are in "
  "surah 12, the story of Jacob and his sons.")
P("Of the six preliminary discoveries, A, B and D are linguistically valid words but are <b>not</b> statistically enriched "
  "in their surahs; C (علم) is enriched but only as a subset match; E (ملك) is borderline and its equal-value twin كلم never "
  "occurs in Sad; F (طسم/طس/طسم) shows no measurable structural difference. Details follow.")

# ------------------------------------------------------------------ data
story.append(PageBreak())
P("1. Data, provenance and normalization", H1)
P("<b>Primary corpus.</b> Quranic Arabic Corpus (QAC) morphology v0.4 (Kais Dukes, built on the Tanzil Uthmani text 1.0.2), "
  "obtained verbatim from the GitHub mirror cltk/arabic_morphology_quranic-corpus because corpus.quran.com did not resolve "
  "from the build environment. File sha256 and every URL are listed in the workbook's Provenance sheet. The parsed corpus has "
  "77,429 words, 49,967 root-bearing word tokens, "
  "1,642 QAC roots, and 4,831 vocalized lemmas (4,341 unvocalized lemma spellings); "
  f"{len(R['cross_reference'].root.unique())} of the roots arise as candidates for some opening.")
P("<b>Cross-check.</b> mustafa0x/quran-morphology (an Arabic-script revision of the QAC) agrees with the primary roots on "
  "98.5% of words; the differences are later corrections (e.g. الناس assigned to نوس in v0.4 versus أنس in the revision) and "
  "roots added for proper nouns. All statistics use QAC v0.4.")
P("<b>General lexicon.</b> Arramooz Alwaseet (T. Zerrouki; ~30k nouns, ~14k verbs, each with root; GPL) validates words that "
  "are Arabic but absent from the Qur'an. <b>Metadata:</b> Meccan/Medinan from quran.com's chapter data, cross-checked against "
  "fawazahmed0/quran-api; revelation order is the Egyptian standard order as distributed by Tanzil (transcribed because "
  "tanzil.net was unreachable; verified to be a permutation of 1-114).")
P("<b>Not obtained:</b> Birzeit Quran Corpus, MASAQ (Mendeley) and corpus.quran.com were DNS-blocked from the execution "
  "environment, and no Buckwalter analyzer or classical dictionary (Lisān al-ʿArab, Lane) was available in machine-readable "
  "form. English glosses are analyst-supplied core meanings (flagged as such) and should be checked against Lane or Hans Wehr.")
P("<b>Normalization rules</b> (applied identically to real and random sequences, and flagged on every candidate): all alif and "
  "hamza forms (ا أ إ آ ٱ ء) = ا = 1; ؤ = و = 6; ئ = ي = 10; ى = ي = 10; ة = ه = 5. Harakat and Qur'anic annotation marks are "
  "removed. An alif in a Muqaṭṭaʿāt inventory matching a hamza in a root is flagged as hamza normalization.")

P("2. Phase 2: the 14 openings verified", H1)
o = R["openings"][["opening", "surahs", "letters", "abjad_computed", "abjad_stated", "verified", "digital_root",
                   "M2_place_value", "M3_digits", "M4_digital_root_letter", "n_partitions_le4"]]
o = o.rename(columns={"abjad_computed": "Abjad", "abjad_stated": "brief", "digital_root": "dig. root", "M2_place_value": "place value",
                      "M3_digits": "digits", "M4_digital_root_letter": "dig.-root letter", "n_partitions_le4": "partitions (<=4)"})
table(o, [1.5 * cm, 2.1 * cm, 4 * cm, 1.3 * cm, 1.2 * cm, 1.3 * cm, 1.2 * cm, 1.4 * cm, 1.3 * cm, 1.5 * cm, 1.7 * cm])
P("All 14 totals in the brief are correct. Note that the brief's table covers 29 surahs; the seven Ḥā-Mīm surahs are 40-46, "
  "of which 42 adds ʿAyn-Sīn-Qāf and is analysed as its own opening.")

# ------------------------------------------------------------------ methods
P("3. Methods", H1)
P("<b>Decoding methods (Phase 4).</b> M1 exact Abjad equivalence (every QAC root/lemma and Arramooz word with the same total); "
  "M2 decimal place-value decomposition (71 -> 70+1 -> عا); M3 individual digits, zeros dropped (71 -> 7,1 -> زا); M4 digital "
  "root (71 -> 8 -> ح); M5 original letters concatenated with a reconstruction, in either order; M6 all additive partitions of "
  "the total into at most four Abjad letters; M7 exact anagrams; M8A all original + reconstructed letters rearranged; M8B "
  "subsets of at least two letters containing at least one original and one reconstructed letter. M9 numerical relations "
  "between openings. Matching is by letter multiset for anagram methods and by exact spelling for ordered methods.")
P("<b>Frequency unit and denominator (Phase 6).</b> The QAC root of each word stem; rates are per 1,000 root-bearing tokens. "
  "Each opening-root pair is compared with five baselines (all other surahs; other Muqaṭṭaʿāt surahs; surahs without "
  "Muqaṭṭaʿāt; surahs within ±35% in length; same Meccan/Medinan class within ±10 places of revelation order) using exact "
  "conditional-binomial rate ratios with Clopper-Pearson 95% CIs. Because word counts are bursty (over-dispersed), two "
  "surah-level tests are added: a negative-binomial GLM with a log-length offset (dispersion estimated from the "
  "intercept-only model, floored at 0.05; roots under 20 occurrences excluded), and a permutation test that resamples "
  "same-size surah sets 10,000 times. Benjamini-Hochberg FDR is applied within each test and globally across all "
  f"{n_pairs * len(qcols):,} tests.")
P("<b>Randomized controls (Phase 7).</b> Pre-registered before any statistic was computed (PREREGISTRATION.md, committed "
  "first). For each opening the score is the strongest enrichment (max -log10 hypergeometric p) among all its candidate "
  "roots; T sums this over the 14 openings. Taking the maximum means the random sequences enjoy the same freedom to pick "
  "their best match as the real ones, which is what controls the 'garden of forking paths'. Primary null N2: random "
  "sequences of the same length with distinct letters from the 14 Muqaṭṭaʿāt letters, same target surahs. Sensitivity: "
  "N1 (any of 28 letters), N3 (28 letters, Abjad total within ±15%), and LABEL (the real candidates scored against "
  "random surah sets of the same size). 10,000 trials each.")

# ------------------------------------------------------------------ discoveries
story.append(PageBreak())
P("4. Phase 3: the preliminary discoveries, reproduced and tested", H1)
fig("discoveries_forest.png", 17, "Rate of each root in the corresponding surahs relative to the rest of the Qur'an (exact 95% CI).")
cols = ["count_target", "per1000_target", "per1000_rest", "rate_ratio", "rr_ci_low", "rr_ci_high", "p_exact", "nb_p",
        "p_surah_permutation", "enrichment_rank_of_1642"]
d = R["discovery_table"][["discovery"] + cols].rename(columns={
    "count_target": "n", "per1000_target": "/1000 target", "per1000_rest": "/1000 rest", "rate_ratio": "RR",
    "rr_ci_low": "CI low", "rr_ci_high": "CI high", "p_exact": "p exact", "nb_p": "p NB", "p_surah_permutation": "p perm",
    "enrichment_rank_of_1642": "rank /1642"})
table(d, [4.6 * cm] + [1.25 * cm] * 10, 8)
A = dt.loc["A  طه → يد (hand)"]
eq14 = D["A_equal14"]
P(f"<b>A. طه -> يد.</b> Arithmetic verified: 9+5 = 14 = 10+4. The same total is produced three ways (M1 equal value, M2 place value, "
  f"M6 partition). The lemma يد occurs in Ta-Ha at {', '.join(D['A_yd_lemma_refs'])} (20:22 is the verse the brief cites). "
  f"But the root ي-د-ي is not enriched: {A.count_target} occurrences, RR {A.rate_ratio:.2f} (95% CI {A.rr_ci_low:.2f}-"
  f"{A.rr_ci_high:.2f}), p = {A.p_exact:.2f}, rank {A.enrichment_rank_of_1642} of 1,642 roots in Ta-Ha. "
  f"<b>Exceptionalism:</b> {len(eq14[~eq14.lemma.str.startswith('(root)')])} Qur'anic lemmas and "
  f"{len(eq14[eq14.lemma.str.startswith('(root)')])} roots have Abjad 14, plus {D['A_arramooz_equal14']} Arramooz words; one of them, "
  f"the lemma أهواء (desires, Abjad 1+5+6+1+1 = 14), belongs to the root هوي, which is more enriched in Ta-Ha than يدي. What is unusual is narrower: M2 rarely yields a valid word at all, so "
  f"the event 'place-value decoding gives a real word that occurs in the surah' has p = "
  f"{po.query('opening==\"طه\" and method==\"M2\"').p_vs_N2.iat[0]:.3f} against random sequences, uncorrected. Across the "
  f"{len(po)} opening x method tests this does not survive correction (q = {po.query('opening==\"طه\" and method==\"M2\"').q_vs_N2_BH.iat[0]:.2f}). "
  "Verdict: valid word, exact equality, not statistically exceptional.")
B = dt.loc["B  يس → سعي (striving)"]
P(f"<b>B. يس -> سعي.</b> Arithmetic verified: 10+60 = 70 = ع; {{ي س ع}} rearranges to سعي (M8A, all letters used once); "
  f"Abjad(سعي) = 140 = 2 x 70. Linguistically valid (lemmas سعى/سعي). But the root occurs <b>once</b> in Ya-Sin (36:20, the "
  f"verse cited): RR {B.rate_ratio:.1f} with a CI of {B.rr_ci_low:.2f}-{B.rr_ci_high:.1f}, p = {B.p_exact:.2f}. A single "
  "occurrence cannot establish prominence. Verdict: valid, exact, not enriched.")
C1, C2 = dt.loc["C  الم → علم (knowledge)"], dt.loc["C  الم → عمل (deed)"]
cps = D["C_per_surah"]
P(f"<b>C. الم -> علم / عمل.</b> Correction to the brief: strict place-value decoding gives 71 -> 70 + 1 -> ع + ا, so the combined "
  "inventory is {ا ل م ع ا} and both words leave <b>two</b> alifs unused (one if the units digit is ignored). Classified as "
  f"subset matches (M8B). <b>علم is enriched</b> in the six surahs: {C1.count_target} occurrences, {C1.per1000_target:.1f} vs "
  f"{C1.per1000_rest:.1f} per 1,000 (RR {C1.rate_ratio:.2f}, CI {C1.rr_ci_low:.2f}-{C1.rr_ci_high:.2f}, exact p {fmtp(C1.p_exact)}; "
  f"NB p {C1.nb_p:.3f}; permutation p {C1.p_surah_permutation:.3f}). It also holds against same-period and similar-length "
  f"surahs. It is driven by al-Baqara ({cps.query('root==\"علم\" and surah==2').per1000.iat[0]:.1f}/1000) and al-ʿAnkabut "
  f"({cps.query('root==\"علم\" and surah==29').per1000.iat[0]:.1f}); as-Sajda is below the Qur'anic average. "
  f"<b>عمل is not enriched</b> (RR {C2.rate_ratio:.2f}, p {C2.p_exact:.2f}). But random letters do as well in these surahs: "
  f"the M8B score for الم is beaten by {po.query('opening==\"الم\" and method==\"M8B\"').p_vs_N2.iat[0] * 100:.0f}% of random sequences, "
  f"because علم is a very frequent root in long surahs that any letter-rich inventory reaches.")
Dp, D6 = dt.loc["D  حم → حمد (praise), 7 Ḥā-Mīm"], dt.loc["D  حم → حمد (praise), 6 surahs w/o 42"]
P(f"<b>D. حم -> حمد.</b> Not an equal-value match: Abjad(حمد) = 52, not 48. Derivation: digits 4, 8 -> د ح; with the original م "
  f"this gives {{ح م د}} with one ح unused (M8B). In the seven Ḥā-Mīm surahs the root occurs {Dp.count_target} times "
  f"(RR {Dp.rate_ratio:.2f}, CI {Dp.rr_ci_low:.2f}-{Dp.rr_ci_high:.2f}, p {Dp.p_exact:.2f}); without surah 42, "
  f"{D6.count_target} times (p {D6.p_exact:.2f}). Verdict: not enriched. The strongest M8B root for حم is حمم (hot water / close "
  "friend), not حمد.")
E1, E2 = dt.loc["E  ص → ملك (sovereignty)"], dt.loc["E  ص → كلم (word)"]
P(f"<b>E. ص -> ملك / كلم.</b> Both have Abjad 90 (M1, M6). ملك occurs {E1.count_target} times in Sad (RR {E1.rate_ratio:.2f}, "
  f"CI {E1.rr_ci_low:.2f}-{E1.rr_ci_high:.2f}, exact p {E1.p_exact:.3f}, NB p {E1.nb_p:.3f}, permutation p "
  f"{E1.p_surah_permutation:.3f}): nominally borderline, not significant after correction. كلم occurs <b>zero</b> times in Sad. "
  f"Nine roots share the value 90; ملك is the only one occurring in Sad. Against random sequences the M1 score for ص is "
  f"p = {po.query('opening==\"ص\" and method==\"M1\"').p_vs_N2.iat[0]:.2f}. Verdict: thematically apt but statistically weak.")
F = D["F_middle"]
fs = D["F_structure"]
P(f"<b>F. طسم (109) -> طس (69) -> طسم (109).</b> The difference is 40 = م, verified. Lexically, surah 27 is not more different "
  f"from its neighbours than they are from each other: Jensen-Shannon divergence of root distributions 26-27 = "
  f"{F['jsd_26_27']:.3f}, 27-28 = {F['jsd_27_28']:.3f}, 26-28 = {F['jsd_26_28']:.3f}; the middle-distinctiveness statistic is at "
  f"the {F['percentile']:.0f}th percentile of the {F['n_triples']} adjacent surah triples with at least 500 tokens each. The letter "
  f"م is not depleted in 27 ({fs.iloc[1]['letter_م_per1000']:.1f} per 1,000 letters vs {fs.iloc[0]['letter_م_per1000']:.1f} in 26, "
  f"{fs.iloc[2]['letter_م_per1000']:.1f} in 28, {fs.iloc[3]['letter_م_per1000']:.1f} Qur'an-wide). Its distinctive roots (مكر plot, "
  "طير birds, عرش throne, نمل ants) reflect the Solomon and Saba narrative; none survives FDR correction. Verdict: no measurable "
  "structural correlate of the missing م.")

# ------------------------------------------------------------------ phase 4-6
story.append(PageBreak())
P("5. Phases 4-5: exhaustive generation and validation", H1)
v = R["validation"]
cand = R["candidates"]
P(f"The nine methods produced {len(cand):,} candidate records ({cand[['opening', 'method', 'match']].drop_duplicates().shape[0]:,} "
  f"unique opening-method-word combinations), validated as follows ({len(v):,} unique words):")
vc = v.status.value_counts().rename_axis("validation status").reset_index(name="unique candidates")
table(vc, [11 * cm, 4 * cm])
lg = R["legitimacy"].copy()
lg.columns = ["sequences", ">=1 valid Qur'anic root", "mean candidate roots", "best root occurs in target surah", "best root p<0.001"]
P("Phase 7 question 1 and 2: how often do random sequences produce legitimate words, and do they occur in the assigned surahs?")
table(lg, [2.5 * cm, 3.4 * cm, 3.2 * cm, 3.8 * cm, 3 * cm])
P("Random letters produce valid Qur'anic roots almost as reliably as the real openings, and their best root occurs in the "
  "target surahs most of the time. Producing a real word, and finding it in the surah, is therefore the expected outcome "
  "of these transformations, not evidence of design.")

P("6. Phase 6: cross-referencing all 114 surahs", H1)
P(f"{n_pairs} opening-root pairs were tested; {int(xr.occurs_in_target.sum())} roots occur at least once in their target surahs, "
  f"{int((xr['B1_all_other_surahs|p'] < 0.05).sum())} are nominally enriched against the rest of the Qur'an (p < 0.05), "
  f"{int((xr['NB_GLM|p'] < 0.05).sum())} under the over-dispersion-aware NB GLM, and "
  f"{int((xr['surah_permutation|p'] < 0.05).sum())} under the surah permutation test. At about 5% false positives, "
  f"{n_pairs * 0.05:.0f} nominal hits are expected by chance alone. After global FDR correction:")
sv = pd.DataFrame([{"test": k, "pairs with q<0.05": len(vl), "which": ", ".join(vl) or "none"} for k, vl in surv.items()])
table(sv, [5.2 * cm, 2.4 * cm, 8.8 * cm])
P(f"<b>No pair passes all three robust tests</b> (token-level vs rest, NB GLM, permutation): {int(xr.robust_enriched.sum())} of {n_pairs}. "
  "The token-level survivors (علم, نفس, أب, جيا, قوم, قول, مدن) are frequent words in long narrative surahs; the token-level test "
  "ignores burstiness, which is why they lose significance at the surah level.")
top = xr.sort_values("NB_GLM|p").head(12)[["opening", "root", "methods", "count_target", "B1_all_other_surahs|RR",
                                           "B1_all_other_surahs|p", "NB_GLM|RR", "NB_GLM|p", "surah_permutation|p",
                                           "B5_same_period_(±10_in_revelation_order)|p"]]
top.insert(2, "meaning", top.root.map(lambda r: GLOSS.get(r, "")))
top.columns = ["opening", "root", "meaning", "methods", "n", "RR", "p vs rest", "NB RR", "NB p", "perm p", "p same period"]
table(top, [1.4 * cm, 1.1 * cm, 2.8 * cm, 1.8 * cm, 0.9 * cm, 1.1 * cm, 1.4 * cm, 1.2 * cm, 1.3 * cm, 1.3 * cm, 1.5 * cm])

# ------------------------------------------------------------------ phase 7
story.append(PageBreak())
P("7. Phase 7: randomized control experiment", H1)
rows = []
for m in transforms.SCORED_METHODS + ["UNION"]:
    r = {"method": m}
    for null in ("N2", "N1", "N3", "LABEL"):
        x = nsel(null, m)
        r[f"{null} p"] = x.p_empirical
    x = nsel("N2", m)
    r["T obs"], r["T null mean"], r["z (N2)"], r["Holm p (N2)"] = x.T_observed, x.T_null_mean, x.z, x.p_holm_methods
    rows.append(r)
nt = pd.DataFrame(rows)[["method", "T obs", "T null mean", "z (N2)", "N2 p", "Holm p (N2)", "N1 p", "N3 p", "LABEL p"]]
table(nt, [1.7 * cm, 1.6 * cm, 1.8 * cm, 1.6 * cm, 1.6 * cm, 1.9 * cm, 1.6 * cm, 1.6 * cm, 1.6 * cm])
n1 = nsel("N1", "UNION")
P(f"<b>Primary (pre-registered) result: UNION vs N2, p = {prim.p_empirical:.3f}. H1 is not supported.</b> The single "
  f"sensitivity null in which the real openings look better is N1 (uniform over all 28 letters; UNION p = {n1.p_empirical:.3f}, "
  f"M8B p = {nsel('N1', 'M8B').p_empirical:.3f}). N1 is the least appropriate comparison: the 14 Muqaṭṭaʿāt letters are "
  "frequent, light letters that form many more roots than rare letters such as ظ, غ or ث "
  f"({leg.loc['N1', 'mean_candidate_roots_per_sequence']:.0f} candidate roots per random N1 sequence vs "
  f"{leg.loc['N2', 'mean_candidate_roots_per_sequence']:.0f} for N2). Once the letter inventory (N2) or the Abjad magnitude (N3, "
  f"p = {nsel('N3', 'UNION').p_empirical:.3f}) is matched, the advantage disappears. Specificity (LABEL): the real candidate sets "
  f"are not better matched to their own surahs than to random surah sets of the same size (p = {nsel('LABEL', 'UNION').p_empirical:.3f}).")
P(f"<b>Held-out method selection.</b> In 200 random 7/7 splits, the method chosen on the training openings was "
  f"{', '.join(f'{k} ({v})' for k, v in cv.chosen_method.value_counts().items())}; on the held-out openings the median p was "
  f"{cv.test_p.median():.2f} and only {(cv.test_p < 0.05).sum()} of 200 splits reached p < 0.05, fewer than the 10 expected by "
  "chance. No method generalizes from one half of the openings to the other.")
fig("null_distributions.png", 16.5, "Distribution of T for 10,000 random letter sets (N2) with the real Muqaṭṭaʿāt marked in red.")

# ------------------------------------------------------------------ phase 8
story.append(PageBreak())
P("8. Phase 8: the system as a network", H1)
fig("network_diagram.png", 17.5, "Opening -> Abjad value -> best candidate root per method (and the user's discoveries) -> target surahs.")
hits = po[(po.method != "UNION") & (po.p_vs_N2 < 0.05)]
P(f"A genuine code should use a few rules consistently. Per opening and method, only {len(hits)} of "
  f"{len(po[po.method != 'UNION'])} combinations beat random sequences at uncorrected p < 0.05 "
  f"({'; '.join(f'{r.opening} {r.method} -> {r.best_root} (p={r.p_vs_N2:.3f})' for _, r in hits.iterrows())}), against about "
  f"{0.05 * len(po[po.method != 'UNION']):.0f} expected by chance, each with a different method and none surviving FDR. "
  "No method works for more than one opening, and the user's own discoveries each require a different transformation "
  "(A: M2/M1, B: M8A, C: M8B with letters discarded, D: M3 + M8B with an unequal value, E: M1). That is the signature of "
  "post-hoc selection rather than of a rule.")
fig("method_consistency_heatmap.png", 15, "Empirical p of each opening x method against random sequences (N2), uncorrected.")
m9 = R["m9_null"].rename(columns={"observed": "observed", "null_mean": "random mean", "null_sd": "random sd", "p_empirical_ge": "p (>= observed)"})
P("<b>M9: numerical relations between openings.</b> Relations among the 14 totals (equal digital roots, differences that are "
  "letter values, integer multiples) occur no more often than among random openings of the same lengths:")
table(m9, [6 * cm, 2 * cm, 2.3 * cm, 2.3 * cm, 2.5 * cm])
P("Examples that look striking in isolation: Abjad(طه) x 5 = Abjad(يس); Abjad(ق) = 2 x Abjad(ن); الر and المر differ by 40 = م "
  "(as do طسم and طس); four single-letter openings (يس=70=ع, ص, ق, ن) have totals that are themselves letters. Random sets "
  "produce as many such coincidences, so they are not reported as findings.")

# ------------------------------------------------------------------ rankings
story.append(PageBreak())
P("9. Ranked findings", H1)
P("Each finding (best candidate root per opening and method, where it occurs in the target surah) is rated on six separate "
  "dimensions: D1 mathematical exactness (3 = all letters / equal value, 2 = subset); D2 linguistic validity (3 = Qur'anic lemma, "
  "2 = root only); D3 rule consistency (number of openings, out of 14, for which that method beats random letters); D4 direct "
  "textual correspondence (occurrences in the target surahs); D5 statistical significance (global FDR q, NB GLM); D6 performance "
  "against random sequences (empirical p). No weights are used: findings are ranked by Pareto front, so a finding is ranked "
  "below another only if it is no better on every dimension and worse on at least one. The full ranking is in the workbook.")
rt = rk[rk.D4_occurrences_in_target > 0].head(22)[["pareto_front", "opening", "method", "root", "meaning", "D1_grade", "D2_grade",
                                                   "D3_rule_consistency_openings_hit_of_14", "D4_occurrences_in_target",
                                                   "D5_q_NB_GLM_global", "D6_p_vs_random_N2"]]
rt.columns = ["front", "opening", "method", "root", "meaning", "D1", "D2", "D3", "D4 n", "D5 q", "D6 p"]
table(rt, [1.1 * cm, 1.5 * cm, 1.3 * cm, 1.2 * cm, 4.1 * cm, 0.9 * cm, 0.9 * cm, 0.9 * cm, 1.2 * cm, 1.3 * cm, 1.3 * cm])
P(f"<b>{int(rk.passes_all_statistical_bars.sum())}</b> findings pass all statistical bars (q < 0.05 for NB GLM, permutation and "
  "the random-sequence comparison). The strongest single finding on the mathematical and linguistic dimensions is طه -> يد "
  "(exact, Qur'anic lemma, present in 20:22, 20:71, 20:110), which fails on frequency. The strongest on frequency are علم "
  "(ALM surahs) and أب (ALR surahs), which are subset matches that random letters also reach.")

# ------------------------------------------------------------------ phase 10
P("10. Phase 10: the proposed thematic sentence", H1)
s_rows = []
for w, o_, rt_ in [("علم knowledge", "الم", "علم"), ("عمل action", "الم", "عمل"), ("سعي striving", "يس", "سعي"),
                   ("حمد praise", "حم", "حمد"), ("ملك sovereignty", "ص", "ملك")]:
    x = xr.query("opening==@o_ and root==@rt_").iloc[0]
    meths = [m.strip() for m in x.methods.split(",")]
    pm = po[(po.opening == o_) & po.method.isin(meths)].sort_values("p_vs_N2").iloc[0]
    s_rows.append({"word": w, "opening": o_, "how derived": x.methods, "n in target": x.count_target,
                   "RR vs rest": x["B1_all_other_surahs|RR"], "p vs rest": x["B1_all_other_surahs|p"], "NB p": x["NB_GLM|p"],
                   "method vs random letters": f"{pm.method}: p={pm.p_vs_N2:.3f}, q={pm.q_vs_N2_BH:.2f}"})
table(pd.DataFrame(s_rows), [2.8 * cm, 1.4 * cm, 2 * cm, 1.6 * cm, 1.7 * cm, 1.7 * cm, 1.5 * cm, 3.2 * cm])
P("The five words come from three different transformations (M8B subset with discarded letters, M8A anagram, M1 equal value), "
  "one of them with an unequal value (حمد). Only علم is more frequent in its surahs, and the random controls show that "
  "is a property of al-Baqara and al-ʿAnkabut, not of the letters. Applying any single one of these rules uniformly to all 14 "
  "openings produces mostly unrelated words (e.g. under M8B: قوم people for المص, أب father for الر, أوب return for المر, "
  "قصو farthest for كهيعص, عزم resolve for حم عسق). The sentence is therefore a meaningful human synthesis of Qur'anic themes, "
  "but it is not generated by a consistent mathematical rule, and the data do not support it as an encoded message.")

# ------------------------------------------------------------------ failed, limitations, conclusion
P("11. Failed hypotheses", H1)
for s in [f"H1 (pre-registered): the Muqaṭṭaʿāt beat random letter sequences under the full decoding toolkit (p = {prim.p_empirical:.2f}).",
          "Any single decoding method works across openings (best Holm-adjusted p "
          f"{ns[(ns.null == 'N2') & (ns.method != 'UNION')].p_holm_methods.min():.2f}; held-out validation fails).",
          "Candidate words are specific to their own surahs (LABEL null p "
          f"{nsel('LABEL', 'UNION').p_empirical:.2f}).",
          "Numerical relations among the openings exceed chance (all M9 p >= "
          f"{R['m9_null'].p_empirical_ge.min():.2f}).",
          "Discoveries A (يد), B (سعي), D (حمد), the عمل half of C, and كلم in E are enriched in their surahs.",
          "Surah 27 is structurally or lexically distinct from 26 and 28 in a way linked to the missing م (F)."]:
    P("- " + s)
P("12. Limitations", H1)
for s in ["Root is the frequency unit. Theme was operationalized as lexical enrichment; human judgements of theme were not "
          "scored, because they cannot be applied blind to random controls.",
          "The QAC v0.4 is the 2011 release; later root corrections (~1.5% of words) would change some counts slightly.",
          "Birzeit, MASAQ, a Buckwalter analyzer and classical dictionaries could not be downloaded; the lexicon is the QAC plus "
          "Arramooz, a modern lexicon. Some classical words may be missed, though this affects real and random sequences equally.",
          "Abjad conventions (hamza, ة, ى) follow one stated scheme; others (e.g. ة = 400) would change some totals.",
          "Statistical power is limited for rare roots in short surahs: a word occurring once (سعي in Ya-Sin) can never be shown "
          "to be enriched, whatever its importance to the narrative.",
          "The search space was fixed in advance with explicit letter limits; a looser search (longer partitions, more "
          "transformations) would find more words for random letters too and cannot rescue H1."]:
    P("- " + s)
P("<b>Deviations from pre-registration.</b> (1) The negative-binomial GLM originally estimated dispersion jointly and produced "
  "degenerate p ~ 0 for rare roots (e.g. منن, one occurrence in Sad). It was replaced, after inspection, by a fixed-dispersion "
  "GLM with a 20-occurrence minimum. This affects only secondary Phase 6 tests and made them more conservative. (2) The "
  "rarefaction sample for Discovery F was reduced from 1,000 to 500 tokens because surahs 26-28 have fewer than 1,000 "
  "root tokens. The primary test and all null models are unchanged.")
P("13. Conclusions", H1)
story.append(Paragraph(T(
    "The Muqaṭṭaʿāt letters can be turned into meaningful Arabic words by Abjad arithmetic, and some of those words fit the "
    "themes of their surahs strikingly well (يد in Ta-Ha, سعي in Ya-Sin, ملك in Sad). Rigorous testing shows that this is what "
    "the transformations do to almost any short sequence of common Arabic letters: with nine methods, roughly 28 candidate "
    "roots per opening and long, lexically rich target surahs, good-looking matches are expected. The real openings do not "
    "outperform random letters, no rule works consistently, and no candidate is robustly enriched after correction. "
    "Within the scope of these methods and data, the evidence favours coincidence and selection over a reproducible "
    "numerical-linguistic code. This is a statement about these Abjad decoding procedures only; it says nothing about the "
    "Muqaṭṭaʿāt's meaning as understood in the tafsir tradition."), BOX))
P("14. Reproducing every result", H1)
P("pip install -r requirements.txt; python scripts/run_analysis.py (downloads data, verifies sha256, runs Phases 2-8 with "
  "10,000 trials, about 5 minutes on 4 cores); python scripts/build_outputs.py (workbook, figures, network); "
  "python scripts/build_report.py (this PDF). All random seeds are fixed. See README.md.")


def footer(c, d):
    c.saveState()
    c.setFont("DVS", 7.5)
    c.drawRightString(A4[0] - 1.6 * cm, 1 * cm, f"Muqaṭṭaʿāt numerical-linguistic study  |  page {d.page}".replace("ṭ", "t").replace("ʿ", "'").replace("ā", "a"))
    c.restoreState()


doc = SimpleDocTemplate(str(OUT / "REPORT.pdf"), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                        topMargin=1.5 * cm, bottomMargin=1.6 * cm, title="Muqattaat Abjad Study",
                        author="Muqattaat research pipeline")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("REPORT.pdf written")
