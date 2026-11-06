"""Run Phases 2-8 and cache every table in outputs/results.pkl (+ CSVs).

Usage:  python scripts/run_analysis.py [--trials 10000] [--quick]
"""
import argparse
import pickle
import sys
import time
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from muqattaat import OUT, corpus, lexicon, nullmodel, transforms  # noqa: E402
from muqattaat import stats as S  # noqa: E402
from muqattaat.abjad import ABJAD, VALUE2LETTER, digital_root, value  # noqa: E402
from muqattaat.arabic import normalize_letters  # noqa: E402
from muqattaat.openings import HA_MIM_ALL, MUQ_SURAHS, OPENINGS  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=10000)
ap.add_argument("--perm", type=int, default=10000)
args = ap.parse_args()
OUT.mkdir(exist_ok=True)
T0 = time.time()
log = lambda *a: print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)

if not (OUT.parent / "data/processed/surah_meta.csv").exists():
    corpus.build()  # downloads the sources, verifies sha256, parses and caches
words, meta = corpus.load()
L = lexicon.build_lexicon(words)
C = S.Counts(words)
ALL = list(range(1, 115))
R = {"provenance": pd.read_csv(OUT.parent / "data/processed/provenance.csv"), "meta": meta}
log("corpus", len(words), "words;", C.N, "root-bearing tokens;", len(C.roots), "roots")

# verse references per root (for Phase 5)
rw = words[words.root.notna()]
ROOT_REFS = rw.assign(ref=rw.surah.astype(str) + ":" + rw.verse.astype(str)).groupby("root").ref.agg(
    lambda s: list(dict.fromkeys(s)))


def refs_in(root, surahs):
    if root not in ROOT_REFS.index:
        return []
    ss = {str(s) for s in surahs}
    return [r for r in ROOT_REFS[root] if r.split(":")[0] in ss]


# ------------------------------------------------------------------ Phase 2
rows = []
for o, ss, stated in OPENINGS:
    letters = o.replace(" ", "")
    v = value(letters)
    rec = transforms.reconstructions(v)
    rows.append({"opening": o, "surahs": ", ".join(map(str, ss)), "n_surahs": len(ss),
                 "letters": " + ".join(f"{c}={ABJAD[c]}" for c in letters), "n_letters": len(letters),
                 "abjad_computed": v, "abjad_stated": stated, "verified": v == stated,
                 "digital_root": digital_root(v), "M2_place_value": rec.get("M2", ""),
                 "M3_digits": rec["M3"], "M4_digital_root_letter": rec["M4"],
                 "n_partitions_le4": len(transforms.partitions(v))})
R["openings"] = pd.DataFrame(rows)
surah_rows = []
for o, ss, _ in OPENINGS:
    for s in ss:
        m = meta.set_index("surah").loc[s]
        surah_rows.append({"surah": s, "name": m["name"], "name_ar": m["name_ar"], "opening": o,
                           "abjad": value(o.replace(" ", "")), "verses": m["verses"], "place": m["place"],
                           "revelation_order": m["revelation_order"],
                           "root_tokens": int(C.surah_tokens[s - 1])})
R["surahs29"] = pd.DataFrame(surah_rows).sort_values("surah")
log("phase 2 ok; all verified:", R["openings"].verified.all())


# ------------------------------------------------------------------ helpers
def profile(root, surahs, n_perm=args.perm):
    k1, n1 = C.rate(root, surahs)
    rest = [s for s in ALL if s not in surahs]
    k0, n0 = C.rate(root, rest)
    rr, lo, hi, p = S.rate_ratio_exact(k1, n1, k0, n0)
    i = C.idx[root]
    tgt = np.isin(np.arange(1, 115), surahs)
    nb = S.nb_glm(C.M[i], C.surah_tokens, tgt)
    sv = C.enrichment_p(surahs)
    rank = int((sv > sv[i]).sum() + 1)
    perm = S.surah_permutation_p(C, root, surahs, ALL, n_perm)
    return {"root": root, "target_surahs": ",".join(map(str, surahs)), "count_target": k1,
            "tokens_target": n1, "per1000_target": 1000 * k1 / n1, "count_rest": k0,
            "per1000_rest": 1000 * k0 / n0, "rate_ratio": rr, "rr_ci_low": lo, "rr_ci_high": hi,
            "p_exact": p, "nb_rr": nb[0], "nb_ci_low": nb[1], "nb_ci_high": nb[2], "nb_p": nb[3],
            "p_surah_permutation": perm, "enrichment_rank_of_1642": rank,
            "verses_in_target": " ".join(refs_in(root, surahs))}


# ------------------------------------------------------------------ Phase 3: discoveries
D = {}
# A: طه -> يد
eq14 = []
for lem in sorted(L.lemmas_by_value[14]):
    r = L.lemma_root.get(lem)
    k20 = int(((words.surah == 20) & (words.lemma_norm == lem)).sum())
    ktot = int((words.lemma_norm == lem).sum())
    eq14.append({"lemma": lem, "vocalized": L.lemma_vocal.get(lem), "root": r, "lemma_count_surah20": k20,
                 "lemma_count_quran": ktot, "root_score_surah20": float(C.enrichment_p([20])[C.idx[r]]) if r in C.idx else 0.0})
for r in sorted(L.roots_by_value[14]):
    eq14.append({"lemma": "(root) " + r, "vocalized": "", "root": r, "lemma_count_surah20": C.rate(r, [20])[0],
                 "lemma_count_quran": L.root_freq[r], "root_score_surah20": float(C.enrichment_p([20])[C.idx[r]])})
D["A_equal14"] = pd.DataFrame(eq14).sort_values("root_score_surah20", ascending=False)
D["A_arramooz_equal14"] = len(L.arr_by_value[14])
D["A_yd_lemma_refs"] = words[(words.lemma_norm == "يد")].assign(ref=lambda d: d.surah.astype(str) + ":" + d.verse.astype(str))
D["A_yd_lemma_refs"] = D["A_yd_lemma_refs"][D["A_yd_lemma_refs"].surah == 20].ref.tolist()
D["A_profile"] = profile("يدي", [20])
D["B_profile"] = profile("سعي", [36])
D["C_profiles"] = [profile("علم", [2, 3, 29, 30, 31, 32]), profile("عمل", [2, 3, 29, 30, 31, 32])]
D["C_per_surah"] = pd.DataFrame([{"surah": s, "root": r, "count": C.rate(r, [s])[0], "tokens": C.rate(r, [s])[1],
                                  "per1000": 1000 * C.rate(r, [s])[0] / C.rate(r, [s])[1],
                                  "quran_per1000": 1000 * L.root_freq[r] / C.N}
                                 for r in ("علم", "عمل") for s in [2, 3, 29, 30, 31, 32]])
D["D_profile"] = profile("حمد", HA_MIM_ALL)
D["D_profile_6"] = profile("حمد", [40, 41, 43, 44, 45, 46])
D["E_profiles"] = [profile("ملك", [38]), profile("كلم", [38])]
eq90 = [profile(r, [38], n_perm=2000) for r in sorted(L.roots_by_value[90])]
D["E_equal90"] = pd.DataFrame(eq90).sort_values("enrichment_rank_of_1642")


# F: 26 / 27 / 28
def surah_struct(s):
    sw = words[words.surah == s]
    toks = sw.root.dropna().tolist()
    rng = np.random.default_rng(s)
    rare = np.mean([len(set(rng.choice(toks, 500, replace=False))) for _ in range(200)]) if len(toks) >= 500 else np.nan
    text = "".join(sw.form_norm.map(normalize_letters))
    lc = Counter(text)
    return {"surah": s, "verses": int(sw.verse.max()), "words": len(sw), "root_tokens": len(toks),
            "distinct_roots": len(set(toks)), "root_types_per_500_tokens": rare,
            "words_per_verse": len(sw) / sw.verse.max(),
            **{f"letter_{c}_per1000": 1000 * lc[c] / len(text) for c in "طسم"}}


F_struct = pd.DataFrame([surah_struct(s) for s in (26, 27, 28)])
qtext = "".join(words.form_norm.map(normalize_letters))
qlc = Counter(qtext)
F_struct.loc[len(F_struct)] = {"surah": "Qur'an", **{f"letter_{c}_per1000": 1000 * qlc[c] / len(qtext) for c in "طسم"}}
D["F_structure"] = F_struct
P = C.M.astype(float)
JSD = lambda a, b: S.js_divergence(P[:, a - 1], P[:, b - 1])
trip = []
for a in range(1, 113):
    b, c = a + 1, a + 2
    if min(C.surah_tokens[[a - 1, b - 1, c - 1]]) < 500:
        continue
    d = (JSD(a, b) + JSD(b, c)) / 2 - JSD(a, c)
    trip.append({"triple": f"{a}-{b}-{c}", "middle_distinctness": d, "jsd_ab": JSD(a, b), "jsd_bc": JSD(b, c), "jsd_ac": JSD(a, c)})
trip = pd.DataFrame(trip)
obs = trip[trip.triple == "26-27-28"].iloc[0]
D["F_triples"] = trip
D["F_middle"] = {"middle_distinctness": obs.middle_distinctness,
                 "percentile": float((trip.middle_distinctness < obs.middle_distinctness).mean() * 100),
                 "n_triples": len(trip), "jsd_26_27": obs.jsd_ab, "jsd_27_28": obs.jsd_bc, "jsd_26_28": obs.jsd_ac}
dist = []
for r in C.roots:
    k1, n1 = C.rate(r, [27])
    k0, n0 = C.rate(r, [26, 28])
    if k1 + k0 < 3:
        continue
    rr, lo, hi, p = S.rate_ratio_exact(k1, n1, k0, n0)
    rr2, lo2, hi2, p2 = S.rate_ratio_exact(k0, n0, k1, n1)
    dist.append({"root": r, "count_27": k1, "count_26_28": k0, "rr_27_vs_26_28": rr, "ci_low": lo, "ci_high": hi,
                 "p_more_in_27": p, "p_more_in_26_28": p2})
dist = pd.DataFrame(dist)
dist["q_more_in_27"] = S.bh(dist.p_more_in_27)
dist["q_more_in_26_28"] = S.bh(dist.p_more_in_26_28)
D["F_distinctive"] = dist.sort_values("p_more_in_27")
R["discoveries"] = D
log("phase 3 ok")

# ------------------------------------------------------------------ Phase 4/5: candidates + validation
cands = []
for o, ss, _ in OPENINGS:
    for c in transforms.generate(o, L, include_arramooz=True):
        cands.append({**c.__dict__, "flags": "; ".join(c.flags), "target_surahs": ss})
cand = pd.DataFrame(cands)
cand["quranic_root"] = cand.root.where(cand.root.isin(C.idx.keys()))
R["candidates"] = cand
log("phase 4 candidates:", len(cand), "rows;", cand[["opening", "method", "match"]].drop_duplicates().shape[0], "unique")

val = []
for (kind, item), g in cand.groupby(["match_kind", "match"]):
    root = g.root.iloc[0]
    in_q_root = root in C.idx
    item_n = normalize_letters(item)
    as_lemma = item in L.lemma_root
    as_form = item_n in L.form_set
    arr = L.arr_info.get(item, ("", "", ""))
    val.append({"match_kind": kind, "item": item, "abjad": value(item), "root": root, "root_in_quran": in_q_root,
                "lemma_vocalized": L.lemma_vocal.get(item, ""), "is_quranic_lemma": as_lemma,
                "exact_surface_form_in_quran": as_form,
                "status": ("exact Qur'anic lemma" if as_lemma else "exact Qur'anic surface form" if as_form
                           else "Qur'anic root (bare root letters)" if kind == "root"
                           else "Arabic word (Arramooz) whose root occurs in the Qur'an" if in_q_root
                           else "Arabic word (Arramooz), root not in the Qur'an" if root else "Arramooz word, no root"),
                "root_quran_freq": L.root_freq.get(root, 0), "lemma_quran_freq": L.lemma_freq.get(item, 0),
                "arramooz_definition_ar": arr[1], "arramooz_type": arr[2],
                "openings": ", ".join(sorted(set(g.opening))), "methods": ", ".join(sorted(set(g.method))),
                "flags": "; ".join(sorted({f for f in g["flags"] if f}))})
R["validation"] = pd.DataFrame(val)
log("phase 5 validation rows", len(val))

# M9 numeric relationships
vals = {o: value(o.replace(" ", "")) for o, _, _ in OPENINGS}


def numeric_relations(vs):
    items = list(vs.items())
    rel = []
    for (a, va), (b, vb) in combinations(items, 2):
        if va == vb:
            rel.append(("equal total", a, b, va))
        if digital_root(va) == digital_root(vb):
            rel.append(("equal digital root", a, b, digital_root(va)))
        d = abs(va - vb)
        if d in VALUE2LETTER:
            rel.append(("difference is a letter value", a, b, f"{d} = {VALUE2LETTER[d]}"))
        hi_, lo_ = max(va, vb), min(va, vb)
        if lo_ and hi_ % lo_ == 0 and hi_ != lo_:
            rel.append(("integer multiple", a, b, f"x{hi_ // lo_}"))
    for a, va in items:
        if va in VALUE2LETTER:
            rel.append(("total is itself a letter value", a, "", f"{va} = {VALUE2LETTER[va]}"))
    return rel


rel = numeric_relations(vals)
R["m9_relations"] = pd.DataFrame(rel, columns=["relation", "opening_a", "opening_b", "detail"])
# adjacency in surah order
seq = sorted((s, o) for o, ss, _ in OPENINGS for s in ss)
adj = [{"surah_a": s1, "opening_a": o1, "surah_b": s2, "opening_b": o2, "consecutive_surahs": s2 == s1 + 1,
        "difference": vals[o2] - vals[o1],
        "difference_letter": VALUE2LETTER.get(abs(vals[o2] - vals[o1]), "")} for (s1, o1), (s2, o2) in zip(seq, seq[1:])]
R["m9_adjacent"] = pd.DataFrame(adj)
rng = np.random.default_rng(9)
lengths = [len(o.replace(" ", "")) for o, _, _ in OPENINGS]
null_counts = []
for _ in range(args.trials):
    vs = {i: sum(ABJAD[c] for c in nullmodel.sample_sequence(rng, ln, "N2")) for i, ln in enumerate(lengths)}
    null_counts.append(Counter(r[0] for r in numeric_relations(vs)))
obs_c = Counter(r[0] for r in rel)
m9 = []
for kind in ["equal total", "equal digital root", "difference is a letter value", "integer multiple",
             "total is itself a letter value"]:
    nc = np.array([c[kind] for c in null_counts])
    m9.append({"relation": kind, "observed": obs_c[kind], "null_mean": nc.mean(), "null_sd": nc.std(),
               "p_empirical_ge": (1 + (nc >= obs_c[kind]).sum()) / (1 + len(nc))})
R["m9_null"] = pd.DataFrame(m9)
log("M9 ok")

# ------------------------------------------------------------------ Phase 6: cross-reference
groups = {o: ss for o, ss, _ in OPENINGS}
non_muq = [s for s in ALL if s not in MUQ_SURAHS]


def baselines(ss):
    out = {"B1_all_other_surahs": [s for s in ALL if s not in ss],
           "B2_other_muqattaat_surahs": [s for s in MUQ_SURAHS if s not in ss],
           "B3_surahs_without_muqattaat": non_muq}
    sim = set()
    for s in ss:
        n = C.surah_tokens[s - 1]
        sim |= {t for t in ALL if t not in ss and 0.65 * n <= C.surah_tokens[t - 1] <= 1.35 * n}
    out["B4_similar_length_(±35%)"] = sorted(sim)
    m = meta.set_index("surah")
    chron = set()
    for s in ss:
        o, pl = m.loc[s, "revelation_order"], m.loc[s, "place"]
        chron |= {t for t in ALL if t not in ss and m.loc[t, "place"] == pl and abs(m.loc[t, "revelation_order"] - o) <= 10}
    out["B5_same_period_(±10_in_revelation_order)"] = sorted(chron)
    return out


R["baseline_sets"] = {o: {k: v for k, v in baselines(ss).items()} for o, ss in groups.items()}
xr = []
qc = cand[cand.quranic_root.notna()]
pairs = qc.groupby(["opening", "quranic_root"]).agg(methods=("method", lambda s: ", ".join(sorted(set(s)))),
                                                    matches=("match", lambda s: ", ".join(sorted(set(s))))).reset_index()
rng = np.random.default_rng(6)
perm_draws = {o: np.array([rng.choice(114, len(ss), replace=False) for _ in range(args.perm)]) for o, ss in groups.items()}
for _, row in pairs.iterrows():
    o, r = row.opening, row.quranic_root
    ss = groups[o]
    i = C.idx[r]
    k1, n1 = C.rate(r, ss)
    rec = {"opening": o, "root": r, "methods": row.methods, "matches": row.matches, "surahs": ",".join(map(str, ss)),
           "count_target": k1, "tokens_target": n1, "per1000_target": 1000 * k1 / n1,
           "root_quran_total": int(C.root_total[i]), "occurs_in_target": k1 > 0}
    for bname, bs in baselines(ss).items():
        k0, n0 = C.rate(r, bs)
        rr, lo, hi, p = S.rate_ratio_exact(k1, n1, k0, n0)
        rec.update({f"{bname}|n_surahs": len(bs), f"{bname}|per1000": 1000 * k0 / n0 if n0 else np.nan,
                    f"{bname}|RR": rr, f"{bname}|CI_low": lo, f"{bname}|CI_high": hi, f"{bname}|p": p})
    tgt = np.isin(np.arange(1, 115), ss)
    nb = S.nb_glm(C.M[i], C.surah_tokens, tgt)
    rec.update({"NB_GLM|RR": nb[0], "NB_GLM|CI_low": nb[1], "NB_GLM|CI_high": nb[2], "NB_GLM|p": nb[3]})
    d = perm_draws[o]
    obs_rate = k1 / n1
    rates = C.M[i, d].sum(axis=1) / C.surah_tokens[d].sum(axis=1)
    rec["surah_permutation|p"] = (1 + (rates >= obs_rate - 1e-15).sum()) / (1 + len(d))
    xr.append(rec)
xr = pd.DataFrame(xr)
pcols = [c for c in xr.columns if c.endswith("|p")]
for c in pcols:
    xr[c.replace("|p", "|q_BH")] = S.bh(xr[c])
allp = np.concatenate([xr[c].values for c in pcols])
allq = S.bh(allp).reshape(len(pcols), -1)
for j, c in enumerate(pcols):
    xr[c.replace("|p", "|q_BH_global")] = allq[j]
xr["robust_enriched"] = ((xr["B1_all_other_surahs|q_BH_global"] < 0.05) & (xr["NB_GLM|q_BH_global"] < 0.05)
                         & (xr["surah_permutation|q_BH_global"] < 0.05))
R["cross_reference"] = xr
log("phase 6 pairs", len(xr), "robustly enriched:", int(xr.robust_enriched.sum()))

# ------------------------------------------------------------------ Phase 7: null models
score_vec = [C.enrichment_p(ss) for _, ss, _ in OPENINGS]
M = transforms.SCORED_METHODS
S_obs = np.zeros((14, len(M) + 1))
NC_obs = np.zeros((14, len(M) + 1), dtype=int)
best_obs = {}
for o_i, (o, ss, _) in enumerate(OPENINGS):
    by_m = {m: set() for m in M}
    for c in transforms.generate(o, L, include_arramooz=False, methods=M):
        if c.root and c.match_kind in ("root", "lemma"):
            by_m[c.method].add(c.root)
    union = set().union(*by_m.values())
    for j, m in enumerate(M + ["UNION"]):
        rs = union if m == "UNION" else by_m[m]
        if rs:
            ix = [C.idx[r] for r in rs]
            k = int(np.argmax(score_vec[o_i][ix]))
            S_obs[o_i, j] = score_vec[o_i][ix][k]
            NC_obs[o_i, j] = len(ix)
            best_obs[(o, m)] = list(rs)[k]
R["S_obs"], R["NC_obs"], R["best_obs"] = S_obs, NC_obs, best_obs
lengths = [len(o.replace(" ", "")) for o, _, _ in OPENINGS]
values = [value(o.replace(" ", "")) for o, _, _ in OPENINGS]
nulls = {}
for scheme in ("N2", "N1", "N3"):
    trials = nullmodel.simulate(L, scheme, args.trials, lengths, values, seed={"N2": 1, "N1": 2, "N3": 3}[scheme])
    Sn, NCn = nullmodel.score_trials(trials, score_vec, C.idx)
    nulls[scheme] = {"S": Sn, "NC": NCn, "examples": [t[0][0] for t in trials[:20]]}
    log("null", scheme, "done")
# label permutation: real candidate sets, random target surah sets of equal size
rng = np.random.default_rng(77)
cand_ix = []
for o_i, (o, ss, _) in enumerate(OPENINGS):
    by_m = {m: set() for m in M}
    for c in transforms.generate(o, L, include_arramooz=False, methods=M):
        if c.root and c.match_kind in ("root", "lemma"):
            by_m[c.method].add(C.idx[c.root])
    by_m["UNION"] = set().union(*by_m.values())
    cand_ix.append({m: np.array(sorted(v)) for m, v in by_m.items()})
from scipy.stats import hypergeom  # noqa: E402
SL = np.zeros((args.trials, 14, len(M) + 1))
for t in range(args.trials):
    for o_i, (o, ss, _) in enumerate(OPENINGS):
        cols = rng.choice(114, len(ss), replace=False)
        U = cand_ix[o_i]["UNION"]
        if len(U) == 0:
            continue
        k = C.M[U][:, cols].sum(axis=1)
        n = C.surah_tokens[cols].sum()
        p = np.where(k == 0, 1.0, hypergeom.sf(k - 1, C.N, C.root_total[U], n))
        sc = dict(zip(U, -np.log10(np.clip(p, 1e-300, 1))))
        for j, m in enumerate(M + ["UNION"]):
            ix = cand_ix[o_i][m]
            if len(ix):
                SL[t, o_i, j] = max(sc[x] for x in ix)
nulls["LABEL"] = {"S": SL}
R["nulls"] = nulls
log("label permutation done")

summ = []
for scheme, nd in nulls.items():
    Sn = nd["S"]
    for j, m in enumerate(M + ["UNION"]):
        Tn = Sn[:, :, j].sum(axis=1)
        To = S_obs[:, j].sum()
        p = (1 + (Tn >= To).sum()) / (1 + len(Tn))
        summ.append({"null": scheme, "method": m, "T_observed": To, "T_null_mean": Tn.mean(), "T_null_sd": Tn.std(),
                     "z": (To - Tn.mean()) / Tn.std() if Tn.std() > 0 else np.nan, "p_empirical": p,
                     "null_95th": np.percentile(Tn, 95)})
summ = pd.DataFrame(summ)
for scheme in nulls:
    msk = (summ.null == scheme) & (summ.method != "UNION")
    summ.loc[msk, "p_holm_methods"] = S.holm(summ.loc[msk, "p_empirical"].values)
R["null_summary"] = summ
# per opening x method empirical p (N2)
po = []
for o_i, (o, ss, _) in enumerate(OPENINGS):
    for j, m in enumerate(M + ["UNION"]):
        Sn = nulls["N2"]["S"][:, o_i, j]
        po.append({"opening": o, "method": m, "best_root": best_obs.get((o, m), ""), "score_obs": S_obs[o_i, j],
                   "n_candidate_roots": NC_obs[o_i, j], "null_mean": Sn.mean(),
                   "p_vs_N2": (1 + (Sn >= S_obs[o_i, j]).sum()) / (1 + len(Sn)),
                   "p_vs_LABEL": (1 + (nulls["LABEL"]["S"][:, o_i, j] >= S_obs[o_i, j]).sum()) / (1 + args.trials)})
po = pd.DataFrame(po)
po["q_vs_N2_BH"] = S.bh(po.p_vs_N2)
R["per_opening_method"] = po
# how often random sequences give legitimate words / occur in target surah
leg = []
for scheme in ("N2", "N1", "N3"):
    NCn, Sn = nulls[scheme]["NC"][:, :, -1], nulls[scheme]["S"][:, :, -1]
    leg.append({"null": scheme, "share_sequences_with_>=1_valid_root": (NCn > 0).mean(),
                "mean_candidate_roots_per_sequence": NCn.mean(),
                "share_best_root_occurs_in_target": (Sn > 0).mean(),
                "share_best_root_p<0.001": (Sn > 3).mean()})
leg.append({"null": "REAL", "share_sequences_with_>=1_valid_root": (NC_obs[:, -1] > 0).mean(),
            "mean_candidate_roots_per_sequence": NC_obs[:, -1].mean(),
            "share_best_root_occurs_in_target": (S_obs[:, -1] > 0).mean(),
            "share_best_root_p<0.001": (S_obs[:, -1] > 3).mean()})
R["legitimacy"] = pd.DataFrame(leg)
# nested method selection (held-out)
rng = np.random.default_rng(42)
Sn = nulls["N2"]["S"]
cv = []
for rep in range(200):
    perm = rng.permutation(14)
    tr, te = perm[:7], perm[7:]
    zs = []
    for j in range(len(M) + 1):
        tn = Sn[:, tr, j].sum(1)
        zs.append((S_obs[tr, j].sum() - tn.mean()) / (tn.std() or np.inf))
    j = int(np.nanargmax(zs))
    tn = Sn[:, te, j].sum(1)
    cv.append({"rep": rep, "chosen_method": (M + ["UNION"])[j], "train_z": zs[j],
               "test_p": (1 + (tn >= S_obs[te, j].sum()).sum()) / (1 + len(tn))})
R["nested_cv"] = pd.DataFrame(cv)
log("phase 7 summary:\n", summ[summ.null == "N2"].to_string())

with open(OUT / "results.pkl", "wb") as f:
    pickle.dump(R, f)
log("saved results.pkl")
