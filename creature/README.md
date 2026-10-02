# Company Creature

A company drawn as a living animal that walks on its own. Each department is
the body system that does the same job in an animal (biomimicry), the
department's numbers set that system's score, and the score is visible in how
the animal moves: stride, cadence, gait, heartbeat, breathing, stumbles, limp,
posture, coat.

`index.html` is the complete first version. Open it in a browser; nothing else
is needed. It is seeded with AHD Group figures read from AHD Costing on
1 Oct 2026 and reproduces that dashboard's material-method margins within half
a percentage point (see the "Check against AHD Costing" table in the page).

## Departments and body systems

| Department | Body system | Why | Numbers | Seen as |
|---|---|---|---|---|
| Finance | Heart & blood | Margin pushes cash round the company as the heart pushes blood | margin on revenue | heart rate, stride length, head carriage |
| Administration | Fat | Overhead is cost carried on every sale | overhead ÷ what customers paid | girth, foot lift |
| Sales | Mouth & temperature | Orders are the intake; selling below break-even is a fever | discount vs break-even discount | cadence, panting, sweat |
| Costing (Asmaa) | Eyes | Costing sees what a sale really costs | cost coverage, items profitable at list | eyelids |
| Purchasing (Yahya) | Lungs | Material intake is the air the factory runs on; rising prices are thin air | items up ≥10% in a year, FX gap | breathing rate and depth |
| Planning | Balance | Planning places each order before it is due, as the inner ear places each foot | open orders with no plan | stumbles, uneven rhythm |
| Factory | Stomach | Undelivered orders are undigested food | late orders | belly size, cadence |
| Factory | Muscles | Plans stuck before release are muscle that will not fire | plans past start date | foot lift, leg bulk |
| Delivery & invoicing | Legs | Late deliveries limp in front; delivered-not-invoiced drags behind | late ≤30 days, late >30 days | limp |
| Data & IT | Nerves | Bad data is a noisy nerve | audit findings, unconfirmed matches | tremor |
| Management | Brain | Decisions left waiting slow every reaction | links to confirm, price decisions, approvals | reaction time to any change, ears |

Thresholds, weights and the motion mapping are first settings to tune with
management. The formulas are shown on each system's card in the page.

## How the motion is generated

The animal is drawn procedurally on a canvas every frame.

- Gait cycle: strides per minute from the Finance and Sales/Factory scores; a
  duty factor and per-leg phase offsets for walk, trot and canter, chosen by the
  speed the numbers allow.
- Legs: two-bone inverse kinematics from hip or shoulder to the foot; stance
  feet move back at ground speed, swing feet arc forward. A weak leg shortens
  its stance, lifts less and makes the body dip when it bears weight.
- Body: vertical bob at twice the stride rate, breathing on the ribcage,
  heartbeat on the chest, belly sag, girth, tremor, stumbles, head and tail.
- Reaction time: when a number changes, the new target motion is approached
  with a time constant set by the Brain score, so a company with many open
  decisions visibly takes longer to respond.

## Data model

The structure mirrors the AHD Costing database: sources feed numbers, numbers
feed derived figures, rules turn figures into scores, and a recalculation runs
through the whole chain after any change.

| Layer | In AHD Costing | Here |
|---|---|---|
| Sources | Imports with fingerprint, row counts, date | `SOURCES` (named only, in v1) |
| Numbers | Components, items, POs, ledger, each with evidence | `INPUTS`: value, unit, department group, source text |
| Derived | Price rule, material cost, overhead rate, margins | `DERIVED`: `fn(values, derived)` with declared `deps` |
| Rules | Rules & settings page, logged | System formulas and thresholds in `ORGANS` |
| Scores | Audit checks, loss verdicts | `ORGANS[i].score` → 0–100, weighted into health |
| Output | Pages, exports | The animal, the readouts, the department map |
| Recalculate | Button after any change | `update()` on every input event |

Every derived figure and every system declares what it depends on, so the page
can show, for any system, the exact inputs that feed it, and after any edit it
lists what moved and lights the path through the flow strip.

## Next steps

1. Feed it live: a daily pull from AHD Costing into `INPUTS`, keeping the date
   and source per number.
2. History: a snapshot per day so the animal can be scrubbed through time.
3. Backend: the same tables in Django next to the costing app, with the rules
   page editable and logged like the costing Rules page.
