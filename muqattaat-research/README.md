# Muqaṭṭaʿāt: an Abjad / linguistic / statistical investigation

This package tests whether the Qur'an's disjoined opening letters (الحروف المقطعة) carry a reproducible
numerical-linguistic structure: does converting them to Abjad numbers and back into letters produce
Arabic words tied to their surahs **more often than chance**?

**Result:** no. Under the pre-registered primary test the real openings score T = 36.0, against
32.3 ± 7.5 for random sequences drawn from the same 14 letters (empirical p = 0.29, 10,000 trials).
No method survives correction, held-out validation fails, and no candidate root is robustly enriched
in its surahs. Full details are in `outputs/REPORT.pdf`.

## Outputs

| file | contents |
|---|---|
| `outputs/REPORT.pdf` | 14-page report: methods, the user's discoveries A–F, statistics, controls, limitations, conclusions |
| `outputs/muqattaat_research.xlsx` | 22 sheets: all 29 surahs, 14 openings, every candidate word, validation, root frequencies, all statistical comparisons, null models, rankings |
| `outputs/csv/` | every workbook sheet as CSV |
| `outputs/figures/network_diagram.png/.svg`, `outputs/network.graphml` | opening → value → root → surah network |
| `outputs/figures/*.png` | null distributions, method × opening heatmap, discovery forest plot |
| `PREREGISTRATION.md` | primary method/metric/null, committed before any statistic was computed |

## Reproduce

```bash
pip install -r requirements.txt
python scripts/run_analysis.py      # downloads + verifies data, Phases 2–8, 10,000 trials (~5 min on 4 cores)
python scripts/build_outputs.py     # workbook, figures, network
python scripts/build_report.py      # REPORT.pdf
```

Seeds are fixed, so a rerun gives identical numbers. Use `--trials 200 --perm 500` for a quick check.

## Package layout

| module | role |
|---|---|
| `muqattaat/corpus.py` | download (with sha256), parse QAC morphology, cross-check, surah metadata |
| `muqattaat/arabic.py` | Buckwalter → Arabic, diacritic stripping, hamza/ة/ى normalization with flags |
| `muqattaat/abjad.py` | Eastern Abjad values, digital root |
| `muqattaat/lexicon.py` | QAC roots/lemmas/forms + Arramooz general-Arabic lexicon, indexed by value and letter multiset |
| `muqattaat/transforms.py` | decoding methods M1–M8 (M9 numeric relations are in `run_analysis.py`) |
| `muqattaat/stats.py` | hypergeometric enrichment, exact rate ratios + CIs, NB GLM, permutation, BH/Holm |
| `muqattaat/nullmodel.py` | random-sequence controls (N1/N2/N3), parallelized |
| `muqattaat/render.py`, `glosses.py` | Arabic rendering for figures; analyst-supplied English root glosses |

## Data provenance

| source | used as | obtained from | licence |
|---|---|---|---|
| Quranic Arabic Corpus v0.4 (Dukes; Tanzil text 1.0.2) | primary corpus | GitHub mirror `cltk/arabic_morphology_quranic-corpus` (corpus.quran.com unreachable) | GPL / CC BY-ND (verbatim) |
| `mustafa0x/quran-morphology` | root cross-check (98.5% agreement) | GitHub | GPL (QAC derivative) |
| Arramooz Alwaseet (Zerrouki) | general Arabic validation | PyPI `arramooz-pysqlite` | GPL |
| quran.com chapters, fawazahmed0/quran-api | Meccan/Medinan, names | GitHub | MIT / Unlicense |
| Egyptian standard revelation order (Tanzil) | chronology baseline | transcribed in `corpus.py` (tanzil.net unreachable), asserted to be a permutation | — |
| Amiri font | Arabic in figures/PDF | google/fonts | OFL |

**Not obtained:** Birzeit Quran Corpus, MASAQ (Mendeley), the Buckwalter analyzer, and classical
dictionaries. These hosts were blocked from the build environment, or no machine-readable copy
was available. Raw files are not committed; `run_analysis.py` re-downloads them and checks their sha256.

## Normalization (applied identically to real and random sequences)

ا أ إ آ ٱ ء = 1; ؤ = و = 6; ئ = ي = 10; ى = ي = 10; ة = ه = 5. Harakat and Qur'anic marks are
removed. A root containing a hamza that is matched through an alif is flagged.
