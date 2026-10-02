# Company Creature

A company drawn as a living creature. Its organs are scored from the company's
numbers, and the picture (colour, posture, heartbeat, breathing, belly, body
width, eyelids, fever, twitching, rash) follows those scores. Change any number
and the change runs through the whole chain in front of you.

`index.html` is the complete first version. Open it in a browser; nothing else
is needed. It is seeded with AHD Group figures read from AHD Costing on
1 Oct 2026 and reproduces that dashboard's material-method margins within half
a percentage point (see the "Check against AHD Costing" table in the page).

## Data model

The structure mirrors the AHD Costing database, where imports feed facts, rules
turn facts into derived figures, and a recalculation runs after every change.

| Layer | In AHD Costing | Here |
|---|---|---|
| Sources | Imports with fingerprint, row counts, date | `SOURCES` (named only, in v1) |
| Numbers | Components, items, POs, ledger, each with evidence | `INPUTS`: value, unit, group, source text |
| Derived | Price rule, material cost, overhead rate, margins | `DERIVED`: `fn(values, derived)` with declared `deps` |
| Rules | Rules & settings page, logged | Organ formulas and thresholds in `ORGANS` |
| Scores | Audit checks, loss verdicts | `ORGANS[i].score` → 0–100, weighted into health |
| Output | Pages, exports | The SVG creature and the vitals |
| Recalculate | Button after any change | `update()` on every input event |

Every derived figure and every organ declares what it depends on, so the page
can show, for any organ, the exact inputs and intermediate figures that feed it,
and after any edit it can list what moved and light the path through the flow
strip.

## Organs and what drives them

| Organ | Business meaning | Drives | Weight |
|---|---|---|---|
| Heart | Margin on revenue | Heartbeat speed, pulse, size | 20% |
| Fat | Overhead as a share of what customers paid | Body width | 15% |
| Temperature | Discount above the break-even discount | Red glow, sweat | 15% |
| Blood | Items that make money at list | Heart colour | 10% |
| Stomach | Late open orders | Belly size | 10% |
| Nerves | Audit findings, unconfirmed matches, undecided prices | Twitching | 10% |
| Lungs | Open orders without a factory plan | Breathing depth and rate | 5% |
| Muscles | Plans past start date, not released | Arm thickness | 5% |
| Eyes | Share of sales value with a known cost | Eyelids | 5% |
| Immune system | Purchase price inflation, FX gap | Rash spots | 5% |

Thresholds are first guesses to tune with management.

## Next steps

1. Feed it live: a daily pull from AHD Costing (its home page figures, or the
   Odoo/Excel exports) into `INPUTS`, keeping the date and source per number.
2. History: store a snapshot per day so the creature can be scrubbed through
   time and the pulse line becomes the real trend.
3. Backend: the same tables as above in Django, next to the costing app, with
   the rules page editable and logged like the costing Rules page.
