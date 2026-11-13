# Pre-registration: frame-0 depth-ICP polish (rule F0-ICP), 20-episode public CPU test

Written 30 Oct 2026 23:00 UTC, BEFORE the 20-episode run, after developing the rule on ep31 only
(`f0icp.json`: ep31 P_o sweeper f0 rotation error 9.2° → 3.7°; lib 0.7998 → 0.9514). Labels [M]/[E]/[H].

**Rule F0-ICP (GT-free; inputs: our frame-0 depth `depth0.npy`, our frame-0 masks `det_f0.npz` (chosen proposals),
our library_v3 meshes, our tracks).** For each object, at frame 0:
1. back-project the valid depth inside the object's chosen mask (half-res rectified camera, K/2);
2. point-to-plane ICP of the camera-facing surface samples (150k; rack 400k) of our mesh onto those points, starting at
   the tracker's frame-0 pose; per iteration keep the 80 % closest pairs; ≤ 60 iterations;
3. accept only if ≥ 200 points, the pose change is ≤ 15° and ≤ 3 cm, and the trimmed mean point-to-plane residual drops;
4. apply the accepted change as a constant body-frame correction B = T0⁻¹·T_icp to the object's frames before its
   perceived onset (first frame > 1 cm or > 5° from its frame-0 pose); later frames unchanged.
Variants: **A** = slot 0 only (the scorer's scene anchor); **B** = every object.

**Data.** Primary: the refine-input tracks P_r (`refine/in`, 25 Oct; the masks in `det_f0.npz` were made in the same
run). Beside: Phase-1 P_o with the same 25 Oct masks (mask/track mismatch possible; reported, not decisive).
Scoring after inference: kit chain, lib (library_v3 at X_kit, leaderboard convention) primary, \* beside.

**Pre-set reading (per variant, on P_r lib):**
- PASS (worth a GPU perception test): mean ΔR_lib ≥ +0.005 over 20 episodes, ≥ 12/20 non-negative (|Δ| < 0.0005
  counts as 0), no episode < −0.010, and ep31 ΔR_lib ≥ +0.05.
- FALSIFIED: anything else. A variant that passes only because of ep31 (mean without ep31 < 0) is reported as
  "ep31-only", not as a pass.

## Outcome (added after the run, 23:26 UTC)
Both variants FALSIFIED by the harm guard (`f0icp_all_Pr.json`, P_r lib):
- A: mean +0.0107 (w/o ep31 +0.0036), 13/20 non-negative, min −0.0154 (ep12), ep40 −0.0108, ep31 +0.1474.
- B: mean +0.0110, min −0.0852 (ep12), ep13 −0.0255.

A gated variant (rotation anchor with mask coverage < 0.70) was formulated after reading these results. It is a
hypothesis, not a pass (DIAG.md §4).
