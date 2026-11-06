"""The 14 distinct Muqaṭṭaʿāt combinations and their 29 surahs (as given in the brief)."""

OPENINGS = [
    # (opening, surahs, abjad total stated in the brief)
    ("الم", [2, 3, 29, 30, 31, 32], 71),
    ("المص", [7], 161),
    ("الر", [10, 11, 12, 14, 15], 231),
    ("المر", [13], 271),
    ("كهيعص", [19], 195),
    ("طه", [20], 14),
    ("طسم", [26, 28], 109),
    ("طس", [27], 69),
    ("يس", [36], 70),
    ("ص", [38], 90),
    ("حم", [40, 41, 43, 44, 45, 46], 48),
    ("حم عسق", [42], 278),
    ("ق", [50], 100),
    ("ن", [68], 50),
]

MUQ_SURAHS = sorted(s for _, ss, _ in OPENINGS for s in ss)
MUQ_LETTERS = sorted(set("".join(o.replace(" ", "") for o, _, _ in OPENINGS)))
HA_MIM_ALL = [40, 41, 42, 43, 44, 45, 46]  # the seven Ḥā-Mīm surahs (42 adds ʿAyn-Sīn-Qāf)
