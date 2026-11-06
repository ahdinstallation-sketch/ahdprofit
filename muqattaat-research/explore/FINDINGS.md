# Search loop: what do the Muqaṭṭaʿāt do? (batches 1–4)

Each hypothesis was tested against a chance baseline. Reproduce: `python explore/batchN.py`.

| # | Hypothesis | Result | Verdict |
|---|---|---|---|
| H5 | Letters are followed by a reference to the Book/revelation | 26/29 vs 24/85 surahs (p = 5e-9); holds for Meccan surahs only (p = 4e-8) and adjusted for length (OR 13.5, p = 3e-4) | **supported** |
| H10 | The next word is a demonstrative ("تلك/ذلك…") | 10/29 vs 0/85 (p = 3e-7). Of the 12 verses in the Qur'an starting "تلك/ذلك + آيات/الكتاب", 9 follow the letters directly | **supported** |
| H11 | The Book reference is local to the opening | 14.3% of the first 15 words vs 2.0% in the rest of the same surah (p = 3e-8); no such effect in other surahs | **supported** |
| H7 | Same-letter families share an opening formula | lemma overlap 0.19 vs 0.07 (p = 0.0001); not explained by adjacency | **supported** |
| H9 | Short openings (1–2 letters) are followed by an oath (و + القرآن/الكتاب/القلم) | 6/12 vs 0/17 (p = 0.002) | **supported** |
| H13 | Letters predict which formula follows | 10/29, same as the base rate (p = 0.24) | not supported |
| H1 | 14 letters are half of each phonetic class (al-Zamakhshari) | p = 0.02 with complementary classes, 0.29–0.40 with independent ones | not supported (artifact) |
| H2 | Opening letters are over-represented in their own surah | p = 0.19 (ق in Qaf, ن in Nun high; ص in Sad not) | not supported |
| H3 | Same-family surahs share a letter style | p = 0.03–0.10 per group | weak / suggestive |
| H4 | Letters encode the verse-end rhyme | 1/29, below chance | not supported |
| H6 | Code 19 | 2/14 totals divisible by 19 (p = 0.17) | not supported |
| H8 | Abjad total relates to surah position or verse count | explained by number of letters (p = 0.64) | not supported |
| H12 | Abjad of letters = Abjad of the following words | 1 hit (29:2 أحسب = 71), chance level | not supported |
| H14 | Letters encode the names in the surah's story | p = 0.70 | not supported |
| — | Abjad reconstruction (main study) | p = 0.29 vs random letters | not supported |

## Reading
The measurable regularity is positional and functional, not numerical. The letters open a block of
mostly Meccan surahs. They are immediately followed by a statement pointing to the Book: "these are the
verses of the Book", "the sending down of the Book", or an oath by the Qur'an. That wording is
specific to each letter family and to this position. This is consistent with the classical reading
(al-Farrāʾ, al-Zamakhsharī, Ibn Kathīr, Ibn Taymiyya). On that reading the letters present the raw
material of the revelation, the ordinary letters of Arabic speech, followed at once by "this is the
Book", as a challenge. It is also consistent with the letters acting as a heading for revelation
sections. The data support the function; they cannot decide the intended meaning.

## Batch 5: letter shapes and Arabic digit shapes

| # | Hypothesis | Result | Verdict |
|---|---|---|---|
| H15a | The 14 letters avoid dots | only ق ن ي are dotted (3/14, vs 15/28 in the alphabet); P = 9e-4; holds when letter frequency is controlled (p = 0.008) | **supported** |
| H15b | One letter per skeleton shape, always the undotted twin (ح not ج/خ, ر not ز, س not ش, ص not ض, ط not ظ, ع not غ) | 14 different shapes of 18 and no dotted twin; random P = 0.00028 | **supported** |
| H16 | Read each letter as the Arabic digit it looks like (glyph similarity computed from rendered fonts) | 0/14 numbers match surah number, verse count, Abjad or order; random mean 0.56 | not supported |
| H17 | Write the Abjad total in Arabic digits, read the digit shapes as letters | 5/14 give a real word, below random (7.2); p = 0.93 | not supported |

All 8 dotted twins (ج خ ذ ز ش ض ظ غ) are absent. The other 6 unused letters are ب ت ث ف و د.
So the set reads as a sample of the basic letter skeletons in their plain, undotted form. That fits
the "these are the letters the Book is made of" reading supported by H5/H10.
