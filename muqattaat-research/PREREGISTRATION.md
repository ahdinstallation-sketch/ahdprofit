# Pre-registration: primary hypothesis, method and metric

Written **before any root-enrichment statistic, null-model run or surah comparison
was computed.** At the time of writing, only the corpus had been parsed (word counts,
root/lemma inventory, cross-check agreement). Any deviation is listed at the end of
`outputs/REPORT.pdf` under "Deviations from pre-registration".

## Unit of analysis
* Frequency unit: the **Qurʾānic root** (QAC v0.4 `ROOT:` feature of the stem segment).
* Denominator: **root-bearing word tokens** of a surah (words whose stem carries a root).
  Muqaṭṭaʿāt tokens themselves carry no root in the QAC and are therefore excluded.
* A generated letter string is a **valid candidate** if its normalized letter multiset
  (or exact sequence, for ordered methods) equals a QAC root or a QAC lemma. Matches
  found only in the Arramooz general lexicon are reported (Phase 5) but do **not**
  enter the primary score, because they have no Qurʾānic frequency.

## Primary hypothesis (H1)
The real Muqaṭṭaʿāt, decoded with the full set of transformations the project uses,
yield candidate roots that are more strongly enriched in their own surahs than the
candidates produced by random letter sequences decoded with exactly the same freedom.

## Primary decoding method
`UNION` = all candidate roots from methods M1 (exact Abjad equivalence, roots and
lemmas), M2, M3, M5, M6 (≤ 4 letters), M7, M8A and M8B (subsets of ≥ 2 letters that
contain at least one original and one reconstructed letter). Letter limits are fixed
in `muqattaat/transforms.py` and are not tuned.

## Primary metric
For opening *o* with target surah set *S_o* and candidate root set *C_o*:

    p(r, o) = P(X ≥ k)  with X ~ Hypergeometric(N, K_r, n_S)    (token-level, one-sided)
    score(o) = max_{r ∈ C_o} −log10 p(r, o)      (0 if C_o is empty)
    T = Σ_o score(o)        over the 14 distinct openings

## Primary null model (N2)
10,000 trials. In each trial every opening is replaced by a random sequence of the same
length with **distinct** letters (all real openings have distinct letters), drawn
uniformly from the 14-letter Muqaṭṭaʿāt inventory {ا ل م ص ر ك ه ي ع ط س ح ق ن};
target surahs are unchanged. Empirical one-sided p = (1 + #{T_null ≥ T_obs}) / 10,001.
Significance threshold α = 0.05.

## Pre-registered secondary analyses (all corrected; Holm across methods)
1. Same test for each method separately (M1, M2, M3, M5, M6, M7, M8A, M8B).
2. Sensitivity nulls: N1 (uniform over 28 letters), N3 (28 letters, Abjad total within ±15 % of the real opening).
3. Label-permutation null: real openings, target surah sets replaced by random sets of
   the same size drawn from all 114 surahs (specificity test).
4. Nested method selection: 200 random 7/7 splits of the openings; choose the best
   method on the training half (by z-score vs null) and evaluate it on the held-out half.
5. Per-candidate surah-level tests (Phase 6): exact conditional-binomial rate ratios with
   95 % CIs against five baselines, negative-binomial GLM with log-length offset, and
   Benjamini–Hochberg FDR across all candidate × baseline tests.

## What would count as support
H1 is supported only if the primary empirical p < 0.05. Individual "striking" matches
(e.g. طه → يد) are evaluated descriptively and against equal-value alternatives, but
are not by themselves evidence for a system.
