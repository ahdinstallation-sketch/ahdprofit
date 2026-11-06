"""Build the Excel workbook, figures, network diagram and rankings from outputs/results.pkl.

Usage:  python scripts/build_outputs.py
"""
import os
import pickle
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from muqattaat import OUT, transforms  # noqa: E402
from muqattaat.glosses import GLOSS  # noqa: E402
from muqattaat.openings import OPENINGS  # noqa: E402
from muqattaat.render import mpl, setup_matplotlib  # noqa: E402

setup_matplotlib()
import matplotlib.pyplot as plt  # noqa: E402

RES = Path(os.environ.get("RESULTS", OUT / "results.pkl"))
R = pickle.load(open(RES, "rb"))
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)
M = transforms.SCORED_METHODS + ["UNION"]
gloss = lambda r: GLOSS.get(r, "") if isinstance(r, str) else ""

# ------------------------------------------------------------------ rankings (Phase 9.5)
po = R["per_opening_method"]
xr = R["cross_reference"].set_index(["opening", "root"])
cand = R["candidates"]
method_consistency = (po[po.method != "UNION"].assign(hit=lambda d: d.p_vs_N2 < 0.05)
                      .groupby("method").hit.sum().to_dict())
rank_rows = []
for _, r in po[(po.method != "UNION") & (po.best_root != "")].iterrows():
    o, m, root = r.opening, r.method, r.best_root
    cs = cand[(cand.opening == o) & (cand.method == m) & (cand.quranic_root == root)]
    exact = bool(cs.uses_all_letters.any())
    math_grade = 3 if exact else 2  # 3 exact equality / all letters used; 2 subset (unused letters)
    ling = 3 if (cs.match_kind == "lemma").any() else 2
    x = xr.loc[(o, root)]
    rank_rows.append({
        "opening": o, "method": m, "root": root, "meaning": gloss(root),
        "matched_forms": ", ".join(sorted(set(cs.match))), "derivation": cs.derivation.iloc[0],
        "D1_mathematical_exactness": {3: "exact (all letters / equal value)", 2: "subset (letters left unused)"}[math_grade],
        "D1_grade": math_grade,
        "D2_linguistic_validity": "Qur'anic lemma" if ling == 3 else "Qur'anic root only", "D2_grade": ling,
        "D3_rule_consistency_openings_hit_of_14": method_consistency.get(m, 0),
        "D4_occurrences_in_target": int(x.count_target), "D4_verses": "",
        "D5_RR_vs_rest": x["B1_all_other_surahs|RR"], "D5_q_NB_GLM_global": x["NB_GLM|q_BH_global"],
        "D5_q_permutation_global": x["surah_permutation|q_BH_global"],
        "D6_p_vs_random_N2": r.p_vs_N2, "D6_q_vs_random_N2": r.q_vs_N2_BH,
    })
rk = pd.DataFrame(rank_rows).drop_duplicates(["opening", "root"])
# weight-free ranking: Pareto (non-dominated) fronts over the six dimensions
dims = np.column_stack([rk.D1_grade, rk.D2_grade, rk.D3_rule_consistency_openings_hit_of_14, rk.D4_occurrences_in_target,
                        -rk.D5_q_NB_GLM_global.fillna(1), -rk.D6_q_vs_random_N2])
front = np.zeros(len(rk), int)
remaining = set(range(len(rk)))
level = 1
while remaining:
    nd = {i for i in remaining if not any((dims[j] >= dims[i]).all() and (dims[j] > dims[i]).any() for j in remaining if j != i)}
    for i in nd:
        front[i] = level
    remaining -= nd
    level += 1
rk["pareto_front"] = front
rk["passes_all_statistical_bars"] = (rk.D5_q_NB_GLM_global < 0.05) & (rk.D5_q_permutation_global < 0.05) & (rk.D6_q_vs_random_N2 < 0.05)
rk = rk.sort_values(["pareto_front", "D6_p_vs_random_N2", "D5_q_NB_GLM_global"])
R["rankings"] = rk

# discoveries summary
D = R["discoveries"]
disc = []
for label, prof, note in [
    ("A  طه → يد (hand)", D["A_profile"], "equal value 14; root ي د ي; place-value 10+4"),
    ("B  يس → سعي (striving)", D["B_profile"], "70→ع + original letters; Abjad(سعي)=140=2×70"),
    ("C  الم → علم (knowledge)", D["C_profiles"][0], "subset match: 71→ع+ا, two ا unused"),
    ("C  الم → عمل (deed)", D["C_profiles"][1], "subset match: 71→ع+ا, two ا unused"),
    ("D  حم → حمد (praise), 7 Ḥā-Mīm", D["D_profile"], "NOT equal value (52 vs 48); digits 4,8"),
    ("D  حم → حمد (praise), 6 surahs w/o 42", D["D_profile_6"], "sensitivity"),
    ("E  ص → ملك (sovereignty)", D["E_profiles"][0], "equal value 90"),
    ("E  ص → كلم (word)", D["E_profiles"][1], "equal value 90"),
]:
    disc.append({"discovery": label, "note": note, **prof})
R["discovery_table"] = pd.DataFrame(disc)

# ------------------------------------------------------------------ figures
# 1 null distributions (N2) per method
S_obs = R["S_obs"]
fig, axes = plt.subplots(3, 3, figsize=(12, 10))
for ax, (j, m) in zip(axes.flat, enumerate(M)):
    Tn = R["nulls"]["N2"]["S"][:, :, j].sum(1)
    ax.hist(Tn, bins=50, color="#9aa7b5")
    To = S_obs[:, j].sum()
    p = R["null_summary"].query("null=='N2' and method==@m").p_empirical.iat[0]
    ax.axvline(To, color="#b3412f", lw=2)
    ax.set_title(f"{m}: observed T = {To:.1f}, p = {p:.3f}", fontsize=11)
    ax.set_xlabel("T = Σ max −log10 p over 14 openings")
fig.suptitle("Real Muqaṭṭaʿāt (red line) vs 10,000 random letter sequences (N2)", fontsize=14)
fig.tight_layout()
fig.savefig(FIG / "null_distributions.png", dpi=150)
plt.close(fig)

# 2 heatmap opening x method (-log10 p vs N2)
H = po.pivot(index="opening", columns="method", values="p_vs_N2").loc[[o for o, _, _ in OPENINGS], M]
fig, ax = plt.subplots(figsize=(10, 7))
im = ax.imshow(-np.log10(H.values), cmap="viridis", vmin=0, vmax=3)
ax.set_xticks(range(len(M)), M)
ax.set_yticks(range(len(H)), [mpl(o) for o in H.index], fontsize=13)
for i in range(H.shape[0]):
    for j in range(H.shape[1]):
        ax.text(j, i, f"{H.values[i, j]:.2f}", ha="center", va="center", color="w" if H.values[i, j] > 0.05 else "k", fontsize=8)
plt.colorbar(im, label="−log10 empirical p vs random sequences (N2)")
ax.set_title("Does each method beat random letters for each opening? (uncorrected p)")
fig.tight_layout()
fig.savefig(FIG / "method_consistency_heatmap.png", dpi=150)
plt.close(fig)

# 3 forest plot for discoveries
dt = R["discovery_table"]
fig, ax = plt.subplots(figsize=(10, 5))
y = np.arange(len(dt))[::-1]
rr = dt.rate_ratio.replace(0, np.nan)
ax.errorbar(rr, y, xerr=[rr - dt.rr_ci_low.clip(lower=1e-2), dt.rr_ci_high - rr], fmt="o", color="#333", capsize=3)
ax.axvline(1, color="#b3412f", ls="--")
ax.set_xscale("log")
ax.set_yticks(y, [mpl(s) for s in dt.discovery])
ax.set_xlabel("rate ratio (target surahs vs rest of Qur'an), exact 95% CI")
for yi, (_, r) in zip(y, dt.iterrows()):
    ax.text(30, yi, f"n={r.count_target}  p={r.p_exact:.3f}", va="center", fontsize=9)
ax.set_xlim(0.05, 120)
ax.set_ylim(-0.7, len(dt) - 0.3)
ax.set_title("User discoveries A–E: root frequency in the corresponding surahs")
fig.tight_layout()
fig.savefig(FIG / "discoveries_forest.png", dpi=150)
plt.close(fig)

# ------------------------------------------------------------------ network (Phase 8)
G = nx.DiGraph()
op_val = {o: int(R["openings"].set_index("opening").loc[o, "abjad_computed"]) for o, _, _ in OPENINGS}
xrr = R["cross_reference"].set_index(["opening", "root"])
DISC = {("طه", "يدي"), ("يس", "سعي"), ("الم", "علم"), ("الم", "عمل"), ("حم", "حمد"), ("ص", "ملك"), ("ص", "كلم")}
links = {(r.opening, r.root): r.method for _, r in rk.iterrows() if r.D4_occurrences_in_target > 0}
for o, rt in DISC:
    links.setdefault((o, rt), "user discovery")
for o, ss, _ in OPENINGS:
    G.add_node(o, kind="opening", label=f"{o}  ({','.join(map(str, ss))})")
    G.add_node(f"v{op_val[o]}", kind="value", label=str(op_val[o]))
    G.add_edge(o, f"v{op_val[o]}", kind="abjad")
root_order = []
for (o, rt), m in links.items():
    x = xrr.loc[(o, rt)]
    nominal = x["B1_all_other_surahs|p"] < 0.05
    if rt not in G:
        G.add_node(rt, kind="root", label=f"{rt}  {gloss(rt).split(',')[0]}")
        root_order.append(rt)
    G.add_edge(f"v{op_val[o]}", rt, kind=m)
    G.add_edge(rt, f"S:{o}", kind="enriched" if nominal else "occurs",
               label=f"RR {x['B1_all_other_surahs|RR']:.1f}, p={x['B1_all_other_surahs|p']:.3f}")
    G.add_node(f"S:{o}", kind="surah", label="surah " + ",".join(x.surahs.split(",")))
nx.write_graphml(G, OUT / "network.graphml")
cols = {"opening": 0, "value": 1, "root": 2, "surah": 3}
pos = {}
order = {"opening": [o for o, _, _ in OPENINGS], "value": [f"v{op_val[o]}" for o, _, _ in OPENINGS],
         "root": root_order, "surah": [f"S:{o}" for o, _, _ in OPENINGS if f"S:{o}" in G]}
for kind, nodes in order.items():
    for i, n in enumerate(nodes):
        pos[n] = (cols[kind] * 3.0, -i * (len(root_order) / max(1, len(nodes))))
mcol = {"M1": "#7BA7C9", "M2": "#8E6CB8", "M3": "#B86C9A", "M5": "#C98A3A", "M6": "#5B8DB8", "M7": "#888",
        "M8A": "#3E9E6B", "M8B": "#74B27F", "user discovery": "#000", "abjad": "#C9A86A", "occurs": "#ccc", "enriched": "#b3412f"}
fig, ax = plt.subplots(figsize=(17, 0.42 * len(root_order) + 3))
for u, v, d in G.edges(data=True):
    ax.annotate("", xy=pos[v], xytext=pos[u], arrowprops=dict(arrowstyle="-", color=mcol.get(d["kind"], "#999"),
                lw=2.2 if d["kind"] in ("enriched", "user discovery") else 1.1, alpha=0.85))
style = {"opening": ("#C9A86A", 15), "value": ("#7BA7C9", 12), "root": ("#e8f3ea", 12), "surah": ("#eee", 11)}
for n, d in G.nodes(data=True):
    c, fs = style[d["kind"]]
    ax.text(*pos[n], mpl(d["label"]), ha="center", va="center", fontsize=fs,
            bbox=dict(boxstyle="round,pad=0.3", fc=c, ec="#555", lw=0.6))
for i, (lab, key) in enumerate([("opening (surahs)", None), ("Abjad value", None), ("candidate root (best per method)", None), ("target surahs", None)]):
    ax.text(i * 3.0, 1.6, lab, ha="center", fontsize=13, weight="bold")
handles = [plt.Line2D([], [], color=c, lw=2, label=k) for k, c in mcol.items() if k not in ("abjad",)]
ax.legend(handles=handles, loc="lower center", ncol=6, fontsize=9, bbox_to_anchor=(0.5, -0.06), frameon=False)
ax.set_xlim(-1.5, 10.5)
ax.set_ylim(-len(root_order) - 1, 2.3)
ax.axis("off")
ax.set_title("Muqaṭṭaʿāt network. Value-to-root edges are coloured by decoding method; root-to-surah edges are red when the root is "
             "nominally enriched there (p<0.05 vs rest, uncorrected). No link survives the corrected tests.", fontsize=12)
fig.tight_layout()
fig.savefig(FIG / "network_diagram.png", dpi=150)
fig.savefig(FIG / "network_diagram.svg")
plt.close(fig)

# ------------------------------------------------------------------ Excel workbook
def gl(df, col="root"):
    if col in df:
        df = df.copy()
        df.insert(df.columns.get_loc(col) + 1, "meaning_en", df[col].map(gloss))
    return df


readme = pd.DataFrame({"sheet": [
    "Provenance", "Openings", "Surahs_29", "Discoveries", "A_equal_value_14", "E_equal_value_90", "C_per_surah",
    "F_structure", "F_triples", "F_distinctive_roots", "Candidates_all", "Validation", "Cross_reference",
    "Null_summary", "Per_opening_method", "Legitimacy", "Nested_CV", "M9_relations", "M9_vs_null", "M9_adjacent", "Rankings"],
    "contents": [
    "Data sources, URLs, sha256, licences", "14 openings: Abjad verification and numeric reconstructions",
    "The 29 surahs with metadata", "User discoveries A–E with rate ratios, exact CIs, NB-GLM, permutation p",
    "All Qur'anic lemmas/roots with Abjad 14, ranked by enrichment in Ta-Ha", "All roots with Abjad 90 in Sad",
    "علم / عمل per ALM surah", "Discovery F structure of 26/27/28", "Middle-surah distinctiveness for all adjacent triples",
    "Roots distinguishing 27 from 26+28", "Every candidate produced by every method (incl. Arramooz)",
    "Phase 5 validation of each unique candidate", "Phase 6: candidate roots x 5 baselines + NB GLM + permutation, BH",
    "Phase 7 primary + secondary null tests", "Each opening x method vs random sequences",
    "How often random sequences produce valid roots", "Held-out method selection (200 splits)",
    "Numeric relations between openings", "Those relations vs random openings", "Adjacent-surah differences",
    "Ranked findings on six separate dimensions (Pareto fronts, no weights)"]})
prov = R["provenance"].copy()
prov["licence"] = prov.key.map({"qac": "GPL (QAC) / CC BY-ND 3.0 (Tanzil text); verbatim copy",
                               "qac_crosscheck": "derivative of QAC (GPL)", "meta_qcom": "quran.com (MIT repo)",
                               "meta_fawaz": "Unlicense", "font_amiri": "SIL OFL", "font_amiri_bold": "SIL OFL"})
extra = pd.DataFrame([{"key": "arramooz", "file": "pip arramooz-pysqlite", "url": "https://github.com/linuxscout/arramooz",
                       "sha256": "", "bytes": "", "licence": "GPL"},
                      {"key": "corpus.quran.com / Birzeit / MASAQ / tanzil.net", "file": "NOT DOWNLOADED",
                       "url": "DNS blocked in the build environment", "sha256": "", "bytes": "",
                       "licence": "see report: secondary sources not used"}])
prov = pd.concat([prov, extra])
cand_x = cand.drop(columns=["target_surahs"]).copy()
cand_x["meaning_en"] = cand_x.root.map(gloss)
sheets = {
    "README": readme, "Provenance": prov, "Openings": R["openings"], "Surahs_29": R["surahs29"],
    "Discoveries": gl(R["discovery_table"]), "A_equal_value_14": gl(D["A_equal14"]), "E_equal_value_90": gl(D["E_equal90"]),
    "C_per_surah": D["C_per_surah"], "F_structure": D["F_structure"], "F_triples": D["F_triples"],
    "F_distinctive_roots": gl(D["F_distinctive"]), "Candidates_all": cand_x, "Validation": gl(R["validation"]),
    "Cross_reference": gl(R["cross_reference"]), "Null_summary": R["null_summary"],
    "Per_opening_method": gl(po, "best_root"), "Legitimacy": R["legitimacy"], "Nested_CV": R["nested_cv"],
    "M9_relations": R["m9_relations"], "M9_vs_null": R["m9_null"], "M9_adjacent": R["m9_adjacent"], "Rankings": rk,
}
with pd.ExcelWriter(OUT / "muqattaat_research.xlsx", engine="openpyxl") as xw:
    for name, df in sheets.items():
        df.to_excel(xw, sheet_name=name[:31], index=False)
        ws = xw.sheets[name[:31]]
        ws.freeze_panes = "A2"
        for col in ws.columns:
            width = min(60, max(10, *(len(str(c.value)) if c.value is not None else 0 for c in col[:200])))
            ws.column_dimensions[col[0].column_letter].width = width
for name, df in sheets.items():
    df.to_csv(OUT / "csv" / f"{name}.csv", index=False) if (OUT / "csv").mkdir(exist_ok=True) is None else None
with open(RES, "wb") as f:
    pickle.dump(R, f)
print("workbook, figures, network written")
