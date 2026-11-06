"""Randomized control experiments (Phase 7)."""
import multiprocessing as mp
from functools import lru_cache

import numpy as np

from .abjad import ABJAD, LETTERS
from .openings import MUQ_LETTERS
from . import transforms

_L = None


def _init(L):
    global _L
    _L = L


@lru_cache(maxsize=500_000)
def roots_by_method(seq: str) -> tuple:
    """For one letter sequence: tuple (method -> frozenset of Qur'anic roots)."""
    out = {m: set() for m in transforms.SCORED_METHODS}
    for c in transforms.generate(seq, _L, include_arramooz=False, methods=transforms.SCORED_METHODS):
        if c.root and c.match_kind in ("root", "lemma"):
            out[c.method].add(c.root)
    return tuple((m, frozenset(out[m])) for m in transforms.SCORED_METHODS)


def sample_sequence(rng, length, scheme, target_value=None):
    if scheme == "N2":      # distinct letters from the 14-letter Muqatta'at inventory
        return "".join(rng.choice(MUQ_LETTERS, length, replace=False))
    if scheme == "N1":      # distinct letters, uniform over all 28
        return "".join(rng.choice(LETTERS, length, replace=False))
    if scheme == "N3":      # distinct letters from 28, Abjad total within +-15% of the real one
        lo, hi = 0.85 * target_value, 1.15 * target_value
        for _ in range(100_000):
            s = rng.choice(LETTERS, length, replace=False)
            v = sum(ABJAD[c] for c in s)
            if lo <= v <= hi:
                return "".join(s)
        raise RuntimeError("N3 rejection sampling failed")
    raise ValueError(scheme)


def _worker(args):
    scheme, seed, n, lengths, values = args
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        trial = []
        for ln, v in zip(lengths, values):
            seq = sample_sequence(rng, ln, scheme, v)
            trial.append((seq, roots_by_method(seq)))
        out.append(trial)
    return out


def simulate(L, scheme, n_trials, lengths, values, seed=2026, processes=4):
    chunks = processes * 8
    per = [n_trials // chunks + (1 if i < n_trials % chunks else 0) for i in range(chunks)]
    args = [(scheme, seed + i, k, lengths, values) for i, k in enumerate(per)]
    with mp.get_context("fork").Pool(processes, initializer=_init, initargs=(L,)) as pool:
        parts = pool.map(_worker, args)
    return [t for p in parts for t in p]


def score_trials(trials, score_vectors, root_idx):
    """Return array [n_trials, n_openings, n_methods + 1(union)] of max -log10 p,
    and array of candidate counts [n_trials, n_openings, n_methods + 1]."""
    M = transforms.SCORED_METHODS
    n, k = len(trials), len(score_vectors)
    S = np.zeros((n, k, len(M) + 1))
    NC = np.zeros((n, k, len(M) + 1), dtype=np.int32)
    for t, trial in enumerate(trials):
        for o, (seq, by_m) in enumerate(trial):
            sv = score_vectors[o]
            union = set()
            for j, (m, roots) in enumerate(by_m):
                if roots:
                    ix = [root_idx[r] for r in roots]
                    S[t, o, j] = sv[ix].max()
                    NC[t, o, j] = len(ix)
                    union |= roots
            if union:
                ix = [root_idx[r] for r in union]
                S[t, o, -1] = sv[ix].max()
                NC[t, o, -1] = len(ix)
    return S, NC
