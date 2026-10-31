# Robot side: jitter in the robot's own targets, and finger synergies (31 Oct 2026, CPU, $0)

Owner: "can't the filter help the robot follow the trajectory better? … also try the solver-synergy idea."

Inputs: training plans of public ep2/12/18/24 from store run `20261030-psolverl-04301a2/refs`:
- `perc2mc(k)`: human-retargeted base;
- `glockt_input`: grasp lock + ILC;
- `glockt`: physics-solved, G2 for ep2/12 and G1 for ep18/24.

No ground truth is read. Command: `refjit_syn.py <refs> refjit_syn.json`. Labels: [M] measured, [H] hypothesis.

## 1. The robot's targets are jerky, much more than the object path [M]
High-frequency part = the residual from a 9-frame Savitzky–Golay fit. Acceleration = the second difference at
20 fps, raw against smoothed.

| | wrist position jitter | wrist acceleration, raw / smooth | wrist rotation jitter | angular acceleration, raw / smooth | finger jitter |
|---|---|---|---|---|---|
| human-retargeted base | 0.22–0.74 cm | 2.0–8.2 / 0.9–2.5 m/s² | 1.9–10.1° | 28–173 / 12–39 rad/s² | 18–38° |
| grasp lock + ILC (ep2, ep12) | 0.30–0.82 cm | 3.1–7.3 / 1.0–2.3 m/s² | 1.7–7.0° | 23–104 / 10–30 rad/s² | 7–10° |
| physics-solved | 0.32–1.09 cm | 3.3–11.7 / 1.1–2.4 m/s² | 1.5–7.2° | 23–126 / 10–31 rad/s² | 4–12° |
| object path (for comparison) | 0.09–0.20 cm | 1.1–2.0 / 0.2–1.0 m/s² | – | – | – |

**Reading:**
- Jitter multiplies the commanded wrist acceleration by 2–5×, up to 11.7 m/s², more than gravity. On a stiff wrist
  (kp 400) that jerks the holding hand, and contact moments are exactly where draws split.
- The solver's own plans are among the jerkiest (ep18 left wrist 1.09 cm, 11.7 m/s²): sampling noise in the committed
  plan.

**[H-cmdsmooth]:**
- Fix: a zero-lag (forward–backward) Kalman smoother on the robot's wrist and finger targets. During holds, recompute
  the locked hand from the smoothed object path so the grasp stays consistent.
- Claim: this raises executability.
- Falsified unless the jittered zero-action sim_vs_ref gains ≥ +0.03 on ≥ 2 of 4 episodes, with none ≤ −0.03.
- CPU test, $0.

## 2. Finger synergies [M]
PCA of the 22 finger joints:

| set | frames | components for 80 / 90 / 95 % | RMS error with 3 / 6 components (of total) |
|---|---|---|---|
| all plans (poses) | 5,656 | 7 / 10 / 13 | 21.6° / 15.1° (of 33.7°) |
| **the solver's edits** (solved − input, ep2/ep12, edited frames) | 804 | **3 / 6 / 10** | 4.3° / 3.0° (of 9.8°) |

**Reading:**
- Whole grasp poses are not low-dimensional.
- What the solver changes is: two directions carry 74 % of its edits.

**[H-syn]:**
- Fix: the solver samples in the first 3–6 edit synergies (basis in `refjit_syn.json`, `synergy.solver_edits._basis`
  and `_mean`), plus small full-joint noise.
- Claim: this finds plans at least as good at the same budget.
- Test: ep18 and ep24, which are held out from the basis, plus ep2 and ep12; standard vs synergy sampling at an equal
  sample budget; jittered zero-action score.
- Falsified if synergy sampling is not ≥ the standard on ≥ 3 of 4 episodes.
- CPU prototype, then a G1-scale box ≈ $1.5–3 [E].
