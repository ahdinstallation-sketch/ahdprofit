# Company Creature

A company drawn as a person who walks, or runs, on their own. A healthy company runs; a sick one shuffles. Each department is the
body system that does the same job in a person (biomimicry), the department's
numbers set that system's score, and the score is visible in the walk: speed,
stride, cadence, posture, gaze, breathing, pulse, stumbles, limp, tremor,
complexion.

`index.html` is the complete first version. Open it in a browser; nothing else
is needed. It is seeded with AHD Group figures read from AHD Costing on
1 Oct 2026 and reproduces that dashboard's material-method margins within half
a percentage point (see the "Check against AHD Costing" table in the page).

## Departments and body systems

| Department | Body system | Why | Numbers | Seen in the walk as |
|---|---|---|---|---|
| Finance | Heart & blood | Margin pushes cash round the company as the heart pushes blood | margin on revenue | heart rate, stride length, posture, arm swing |
| Administration | Fat | Overhead is cost carried on every sale | overhead ÷ what customers paid | build, foot clearance |
| Sales | Mouth & temperature | Orders are the intake; selling below break-even is a fever | discount vs break-even discount | cadence, open-mouth breathing, flushed face, sweat |
| Costing (Asmaa) | Eyes | Costing sees what a sale really costs | cost coverage, items profitable at list | eyelids |
| Purchasing (Yahya) | Lungs | Material intake is the air the factory runs on; rising prices are thin air | items up ≥10% in a year, FX gap | breathing rate and depth, shoulder rise |
| Planning | Balance | Planning places each order before it is due, as the inner ear places each foot | open orders with no plan | stumbles, uneven rhythm |
| Factory | Stomach | Undelivered orders are undigested food | late orders | belly, cadence |
| Factory | Muscles | Plans stuck before release are muscle that will not fire | plans past start date | foot clearance, knee lift, limb bulk |
| Delivery & invoicing | Legs | Late deliveries weaken the left leg; delivered-not-invoiced weakens the right | late ≤30 days, late >30 days | limp, foot drag |
| Data & IT | Nerves | Bad data is a noisy nerve | audit findings, unconfirmed matches | hand tremor |
| Management | Brain | Decisions left waiting slow every reaction | links to confirm, price decisions, approvals | reaction time to any change, gaze |

Thresholds, weights and the motion mapping are first settings to tune with
management. The formulas are shown on each system's card in the page.

## How the walk is generated

The person is drawn procedurally on a canvas every frame at human scale
(1 unit = 1 cm, 175 cm tall).

- Gait cycle: steps per minute from the Finance and Sales/Factory scores,
  stride in metres from Finance, speed in km/h from the two; the gait name
  (shuffle, walk, brisk walk, jog, run) follows the speed. A strong heart in
  a sound body (Finance high and overall health above the middle) breaks into
  a run: higher cadence and stride, a flight phase, bent arms, high knees, a
  heel kick and a forward athletic lean.
- Legs: two-bone inverse kinematics from hip to ankle; the stance foot moves
  back at ground speed with heel strike, flat foot and toe-off rotation; the
  swing foot arcs forward with a clearance set by Muscles and Fat. A weak leg
  shortens its stance, clears less and drops the hip; under 25 strength the
  foot drags.
- Arms: counter-swing to the legs with elbow bend, amplitude from Finance,
  tremor on the hands from Nerves.
- Torso and head: pelvis bob at twice the step rate, forward lean and rounded
  shoulders from Finance and overall health, ribcage and shoulder rise with
  each breath (Lungs), carotid pulse (Heart), gaze from Brain, eyelids from
  Eyes, flush, open mouth and sweat from Sales.
- Stumbles: decided once per step with a probability from Planning; the torso
  pitches forward, the arms fly up and the hip drops.
- Reaction time: a changed number is approached with a time constant set by
  the Brain score, so a company with many open decisions visibly takes longer
  to respond.
- Status glow: a vignette around the scene whose hue runs from red (critical)
  through amber to green (thriving) with overall health, and whose strength
  pulses with each heartbeat.
- Monitor: live ECG and breathing traces at the current heart and breath rate.
- Layout: the walker stays pinned at the top while the sliders beside it
  scroll, so a change and its effect are visible together.

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
| Output | Pages, exports | The walker, the monitor, the department map |
| Recalculate | Button after any change | `update()` on every input event |

Every derived figure and every system declares what it depends on, so the page
can show, for any system, the exact inputs that feed it, and after any edit it
lists what moved and lights the path through the flow strip.

## Next steps

1. Feed it live: a daily pull from AHD Costing into `INPUTS`, keeping the date
   and source per number.
2. History: a snapshot per day so the walk can be scrubbed through time.
3. Backend: the same tables in Django next to the costing app, with the rules
   page editable and logged like the costing Rules page.

## Company as a Human (multi-company app)

`app/index.html` is the general version of the walker: anyone enters their own company's numbers
(money in any currency plus percentages of orders, items and records), names the company, and watches it walk.
Published at https://claude.ai/artifact/32aR8yJzoqce4b7WBbeD2C with the artifact database enabled:

- **Save** keeps companies per signed-in user under `data/users/<id>/profile/companies/<slug>` (private).
- **Share link** writes one public record per user to `shared/<user id>` and gives a `#c-<slug>` link.
- **Companies people shared** lists `shared` newest first.
- Presets: "Typical company" and "Demo: AHD Group, Oct 2026".

Version 2 replaces the 2D stick figure with a rigged, skinned character (three.js Soldier model, Mixamo rig, CC-BY,
shipped base64-encoded in `app/models/soldier.glb.txt` because artifacts do not serve binary .glb) in a night street scene,
and restyles the page as a tactical HUD (dark panels with corner brackets, orange accents, segmented bars, scanlines).
The eleven scores still drive everything: walk/run clips blended by fitness, cadence from the heart, spine and head pitch
for posture and gaze, chest scale for breathing, hand jitter for data quality, stumbles from planning, a hip drop over the
weak leg for delivery/invoicing, and the orange wrist light pulsing with the heartbeat. `app/build.py` regenerates the page.
