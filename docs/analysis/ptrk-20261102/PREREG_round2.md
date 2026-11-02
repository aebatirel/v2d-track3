# Pre-registration: pose-board CV round 2 (2 Nov 2026, ~22:45 UTC)

Coordinator's ask (keen-heisenberg, 21:55 UTC, after pack 13p transferred: AUC 0.88257, +0.0103). Written and pushed
before any round-2 score. Same scorer, tracks and seeds as PREREG_posemesh.md:
- tracks: C with ep23 after identity_fix;
- scorer: `score_registered.py --reg_seeds 10`.

**Baseline "13p":** the 13f payloads, except
- wooden_piece_2 → library_v3 (13f1, as focused-pascal shipped);
- white_pot → X (`white_pot_potlid_tsdf_ep43`);
- plastic_dish_rack → library_c0.

## (a) Wider pool, nested leave-one-episode-out
- **Candidates per object:**
  - every mesh of bold-albattani's C4-audit candidates.json, as delivered placed in the library_v3 frame, plus G2
    generations as they land;
  - meshes identical (md5) to the 13p choice are skipped.
- **gain_k(e)** = seed-mean AUC (13p with o ← k) − seed-mean AUC (13p).
- **For each held-out e:**
  - k̂ = argmax over {13p (gain 0)} ∪ pool of the mean gain on E_o \ {e};
  - g(e) = gain_k̂(e).

  The selection runs inside the loop, so the held-out estimate pays for the pool size.
- **o passes** if mean g ≥ +0.005, min g ≥ −0.01 and |E_o| ≥ 2.
- **For a passing o:** k* = argmax of the mean gain over all of E_o, which must not be 13p; then D1 (< 20° at every
  eval seed of o's eval slots); then focused-pascal's d1gate.

## (b) Placement from depth on top of the 13p mesh
- **Objects:** white_pot (X), plastic_dish_rack (library_c0), blue_cup (13f), mini_sweeper (13f).
- **Fit:** `scripts/place_fit.py` with `--sub` = the 13p mesh; otherwise as in test A (rest segments, masks, trimmed
  ICP, guards).
- **Candidate:** o placed per episode, everything else 13p.
- **Rule:** the binary leave-one-episode-out rule of PREREG_posemesh Part 2, with the same thresholds.
- If (a) also passes for o, the two are not combined (untested); the larger held-out mean wins.

## (c) Pitcher placement on eval 20 (Part 2 pass of round 1)
- **Fit:** place_fit on the packed eval-20 reference body poses (rebuilt as inv(W)·inv(T_table)·reference, see work
  log 22:10), the eval-20 depth cache and SAM2 video masks (`ops/jobs/eval_vos.sh`).
- **Submitted mesh:** Δ · (pitcher payload of 13p).
- No public score exists for this step; the public CV of round 1 is its evidence.

## Cost
CPU here ($0) for scoring and fits. Eval depth / masks for objects that pass (b): ≤ $10, pre-approved. Stop below $15
credit.
