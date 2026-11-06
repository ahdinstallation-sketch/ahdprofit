"""Statistics for sparse root counts (Phase 6).

* token-level one-sided hypergeometric enrichment (primary score, fast, vectorized)
* exact conditional-binomial rate ratio with Clopper-Pearson 95% CI (robust to small counts)
* negative-binomial GLM with log(root-bearing tokens) offset across surahs, which absorbs
  over-dispersion ("burstiness") that the token-level test ignores
* surah-level permutation test (resampling target sets of the same size)
* Benjamini-Hochberg FDR and Holm corrections
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats as st


class Counts:
    def __init__(self, words: pd.DataFrame):
        rb = words[words.root.notna()]
        tab = pd.crosstab(rb.root, rb.surah)
        tab = tab.reindex(columns=range(1, 115), fill_value=0)
        self.roots = list(tab.index)
        self.idx = {r: i for i, r in enumerate(self.roots)}
        self.M = tab.values.astype(np.int64)            # roots x 114
        self.surah_tokens = self.M.sum(axis=0)          # root-bearing tokens per surah
        self.root_total = self.M.sum(axis=1)
        self.N = int(self.M.sum())

    def col(self, surahs):
        return np.asarray([s - 1 for s in surahs])

    def enrichment_p(self, surahs) -> np.ndarray:
        """-log10 one-sided hypergeometric p for every root in target set `surahs`."""
        c = self.col(surahs)
        k = self.M[:, c].sum(axis=1)
        n = int(self.surah_tokens[c].sum())
        p = st.hypergeom.sf(k - 1, self.N, self.root_total, n)
        p = np.where(k == 0, 1.0, p)
        return -np.log10(np.clip(p, 1e-300, 1.0))

    def rate(self, root, surahs):
        c = self.col(surahs)
        i = self.idx[root]
        return int(self.M[i, c].sum()), int(self.surah_tokens[c].sum())


def rate_ratio_exact(k1, n1, k0, n0, alpha=0.05):
    """RR = (k1/n1)/(k0/n0); exact CI via conditional binomial; one-sided p (enrichment)."""
    t = k1 + k0
    rr = (k1 / n1) / (k0 / n0) if k0 > 0 else np.inf if k1 > 0 else np.nan
    if t == 0:
        return rr, np.nan, np.nan, 1.0
    lo_pi = st.beta.ppf(alpha / 2, k1, t - k1 + 1) if k1 > 0 else 0.0
    hi_pi = st.beta.ppf(1 - alpha / 2, k1 + 1, t - k1) if k1 < t else 1.0
    conv = lambda pi: (pi / (1 - pi)) * (n0 / n1) if pi < 1 else np.inf
    p_null = n1 / (n1 + n0)
    p = st.binom.sf(k1 - 1, t, p_null)
    return rr, conv(lo_pi), conv(hi_pi), float(p)


NB_MIN_TOTAL = 20  # below this the dispersion parameter is not identifiable (degenerate fits, p ~ 0)
NB_MIN_ALPHA = 0.05


def nb_glm(counts: np.ndarray, exposure: np.ndarray, is_target: np.ndarray):
    """Negative-binomial regression log E[y] = b0 + b1*target + log(exposure).
    Returns (rate ratio, ci_lo, ci_hi, one-sided p for b1 > 0); NaNs when the root is too
    sparse (< NB_MIN_TOTAL tokens in the Qur'an) or the fit does not converge."""
    import statsmodels.api as sm
    if counts[is_target].sum() == 0:
        return np.nan, np.nan, np.nan, 1.0
    if counts.sum() < NB_MIN_TOTAL:
        return np.nan, np.nan, np.nan, np.nan
    X = sm.add_constant(is_target.astype(float))
    off = np.log(exposure)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Dispersion from the intercept-only model, floored: jointly estimating alpha lets it
            # collapse to the boundary (alpha ~ 0) and corrupts the Hessian-based SE of b1.
            m0 = sm.NegativeBinomial(counts, np.ones((len(counts), 1)), offset=off).fit(disp=0, maxiter=200)
            alpha = max(float(m0.params[-1]), NB_MIN_ALPHA)
            m = sm.GLM(counts, X, family=sm.families.NegativeBinomial(alpha=alpha), offset=off).fit()
        b, se = m.params[1], m.bse[1]
        if not m.converged or not np.isfinite(se) or se <= 0 or abs(b) > 10:
            raise ValueError
        z = b / se
        return float(np.exp(b)), float(np.exp(b - 1.96 * se)), float(np.exp(b + 1.96 * se)), float(st.norm.sf(z))
    except Exception:
        return np.nan, np.nan, np.nan, np.nan


def surah_permutation_p(C: Counts, root, surahs, pool, n_perm=10000, rng=None):
    """P(rate in random same-size surah set from `pool` >= observed rate)."""
    rng = rng or np.random.default_rng(0)
    i = C.idx[root]
    pool = np.asarray(pool) - 1
    tgt = C.col(surahs)
    obs = C.M[i, tgt].sum() / C.surah_tokens[tgt].sum()
    k = len(tgt)
    draws = np.array([rng.choice(pool, k, replace=False) for _ in range(n_perm)])
    rates = C.M[i, draws].sum(axis=1) / C.surah_tokens[draws].sum(axis=1)
    return float((1 + (rates >= obs - 1e-15).sum()) / (1 + n_perm))


def bh(p):
    p = np.asarray(p, float)
    q = np.full_like(p, np.nan)
    ok = np.isfinite(p)
    pv = p[ok]
    n = len(pv)
    if n == 0:
        return q
    order = np.argsort(pv)
    ranked = pv[order] * n / np.arange(1, n + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(ranked, 1)
    q[ok] = out
    return q


def holm(p):
    p = np.asarray(p, float)
    n = len(p)
    order = np.argsort(p)
    adj = np.empty(n)
    running = 0
    for rank, i in enumerate(order):
        running = max(running, (n - rank) * p[i])
        adj[i] = min(1, running)
    return adj


def js_divergence(a: np.ndarray, b: np.ndarray) -> float:
    a = a / a.sum()
    b = b / b.sum()
    m = (a + b) / 2
    with np.errstate(divide="ignore", invalid="ignore"):
        ka = np.nansum(np.where(a > 0, a * np.log2(a / m), 0))
        kb = np.nansum(np.where(b > 0, b * np.log2(b / m), 0))
    return float((ka + kb) / 2)
