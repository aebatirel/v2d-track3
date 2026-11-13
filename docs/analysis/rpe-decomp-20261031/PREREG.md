# Pre-registration: GT-free fix candidates for RPE / MPPE / AUC (public episodes)

Each block below was written BEFORE its candidate was scored against mocap. Times are UTC, from `date -u` on this
machine. Scoring = `cand.py` (kit chain, lib convention: library_v3 submitted, kit registration to the public scan),
20 public episodes, Phase-1 P_o tracks (`20261030-orcP1{a,b,c}-87fc869`), base = the same tracks unchanged.
No eval episode is run. Nothing is tuned on scores: the parameters below are fixed now and not changed after scoring.

## Block 1 — written 2026-10-31 15:46:46 UTC (cand.py md5 4432bda471d3cc32a5e8ea6e345ac63b)

Evidence that motivated it (oracle diagnostics, README tables): holding every object at the truth in the frames where
mocap says it is still (`c_rest_k`, kit world) gives ΔRPE −0.117 cm, ΔMPPE −0.87 cm, ΔAUC +0.055 (15/20 better, 0
worse). The GT-free version can only remove our own jitter/creep in rest phases, not the rest-pose bias, so a smaller
gain is expected [H]. The 26 Oct timing review proposed exactly this rule as H3 (no hand within 2 cm and no moving
support → hold), never tested.

Transform inputs (inference side only): our P_o track, our perceived hands (`hands_refined.npz`, md5 checked against
phase1/inputs.tsv: 0 mismatches), library_v3 meshes, object names/slot order. A dry run of the transform (no scoring,
no ground truth) was used only to check that it runs and what it holds.

Fixed parameters: HAND_CM 4.0 (no perceived hand joint within 4 cm of the object surface), SUPPORT_CM 2.0 (an object
within 2 cm of another object that is not free is not free), RUN_MIN 10 frames, CARRY 10 frames (an invalid hand side
keeps its last valid joints for 10 frames, then is absent), DEV_CM 5.0 / DEV_DEG 25.0 (a run is held only if the
track stays within 5 cm and 25° of the run's mean; cups: tilt of the axis only), NPTS 300 surface samples. Hold value:
median translation, chordal-mean rotation over the run.

- **K1 rest_hold:** every qualifying run held.
- **K2 initial_hold:** only the run that starts at frame 0 (a multi-frame frame-0 estimate, held until first contact).
  Differs from the rejected A-f0 test (spoon README: rest-averaged ANCHOR orientation only, +0.001): K2 holds every
  object's full pose over its whole initial free run, not only the anchor's frame-0 orientation.

**Pass rule (each candidate on its own; all must hold):**
1. mean ΔAUC over the 20 episodes ≥ +0.005;
2. mean ΔRPE over the 20 episodes (kit convention: single-object episodes count 0) ≤ −0.10 cm;
3. ≥ 12 of 20 episodes improved, improved = ΔAUC > 0 (an untouched episode, Δ = 0, does not count as improved);
4. no episode with ΔAUC < −0.02;
5. mean ΔMPPE over the 20 episodes ≤ 0.
Reported beside it, not part of the rule: the same numbers without ep23 (identity swap), per-object deltas, the frames
held. Two candidates are tested, so a pass is read with that multiplicity in mind (no correction applied to a
deterministic CPU reading; stated, not hidden).
Eval episodes they would touch: every eval episode has objects at rest at the start, so both would change all 20 eval
references at a retrain (frames unknown until run there; nothing is run on eval here).
