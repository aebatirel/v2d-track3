# Eval 10: why no learner stacks the cups (CPU investigation, 26 Oct 2026; GT-free, our reference only)

Owner: "Check and fix" (the hypothesis that the fingers close on air because of the 8 mm collision shrink).

## Findings (measured)

1. **Hypothesis rejected.** `grasp_lock.py` plans the grip on the simulator's own collision pieces, so with the carve it
   already plans on the shrunk surface: 1.3 mm gap, 4 fingers on.
2. **In every trained rollout neither cup moves** (0.4 cm in total; grasp lock A/B and the standard learner alike).
   The reference lifts the beige cup 21 cm and stacks it into the blue cup. (The curve's "blue_cup: lift 0" label
   only tracks the blue cup.)
3. **Playing the plan open loop (no policy) does carry the cup.** The zero-action replay on the GPU box scored 0.579
   (A) and 0.663 (B), against 0.454 and 0.438 for the trained policies. Training learns to avoid the cup.
4. **Why the replay fails**, reproduced on CPU with contact forces (`tools/trace_rollout.py` CONTACTS=1):
   - frames 32–72: the cup is carried well (2–4 cm);
   - from frame 60 the beige cup hits the **blue cup's rim**, with up to 9,650 N; the wrist stalls up to 14 cm behind;
   - the hand opens in mid-air (≈ f120) and the cup is flung off the table (80–120 cm).
   - Training terminates on such failures, so the policies learn not to touch the cup.
5. **The reference path itself is feasible.** Kinematic overlap of the carved pieces along the reference is
   ≤ 2.4 mm (`nest_pen.py`). The failure is misalignment in the simulation: before the insertion, the beige cup is
   6–7 cm off relative to the blue cup, made of 3–6 cm in-hand offset (low in the grip) plus a 2–5 cm offset of the
   blue cup.

## Fix attempts (CPU, zero-action replays; scored with qa.py's metric, `obj_score.py` per object)

**New options (both off by default):**
- `grasp_lock.py --rest_below_cm X`: objects that move less than X in our reference rest; a hand with no hold parks.
- `wrist_ilc.py --hold <grasp_lock json>`: during a carry, feed back the HELD OBJECT's position and orientation
  error, and keep the best-scoring iteration.

| Variant | Zero-action sim_vs_ref | Blue cup | Beige cup |
|---|---|---|---|
| Today's reference (CPU) | 0.517 | 0.609 | 0.426 (flung) |
| Blue at rest, left hand parked | 0.454 | — | still blocked at the rim |
| Both hands + object ILC, position (iter 6) | 0.515 | 0.315 (knocked over, 86°) | 0.715 (nested) |
| **Blue at rest + object ILC, position + orientation (best, iter 4)** | **0.632** | 0.604 | 0.659 |
| Same, wrist targets jittered ±3–6 mm (6 replays) | 0.42–0.54 (mean ≈ 0.48) | | beige tips 80–180° |
| Beige collision shrink 15 mm instead of 8 | ≤ 0.517 (best is iter 0) | | weaker grip |

**Conclusion:** the 0.632 is a knife-edge. Small perturbations tip the beige cup at the rim, so a GPU rerun is not
justified on this evidence. Nesting with ≈ 8 mm clearance needs alignment the open-loop plan does not reach.

## Zero action vs trained, all stored grasp-lock runs (`zero_vs_trained.md`)

- 64 distinct results: training beats zero action by +0.175 on average.
- Trained is below zero action by > 0.02 in 15 results.
- For the current submission, only **eval 10** is worth acting on: zero action (frozen variant) 0.663 vs submitted
  0.447.
- Evals 14 and 16 also have zero > trained, but their packed rollouts (0.909, 0.908) are above their zero action.
- Submitting a zero-residual policy is an owner decision. The 22 Oct floor-guard rule says "the submission must stay
  a learned policy".
