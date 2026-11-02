# Pre-registration: per-object pose-board mesh choice and per-object placement, by public cross-validation (2 Nov 2026)

Coordinator's task (keen-heisenberg, 20:24 UTC; owner's "go crazy, let's win this"). Written and pushed before any
candidate score of this test. Public development only; mocap is read only by the scorer. The decision uses public
pose scores, which is legitimate development. No eval result is read.

## Inputs
- **Tracks T:** today's control C (ptrkA / ptrkB C; ep23 = ptrkD Cr after `pipeline/identity_fix.py`, the GT-free
  board knob rule the eval pipeline applies to board episodes).
- **Mesh sets** (the 9a+ files are budgeted by the scorer as the packer does):
  - **13f:** the pack-13f payloads, the baseline (`meshes/m13f_payload`).
  - **12c:** the pack-12c payloads.
  - **9a+:** the posefix mesh9a set.
- **Scorer:** `pipeline/score_registered.py --reg_seeds 10`. This is the mean over 10 registration seeds
  (1_000_003·ep + 101·slot + 7919·k, k = 0..9), so no single public seed decides.

## Part 1: mesh per object
- For each object o with episodes E_o in the public set:
  - **candidate (o, k), k ∈ {12c, 9a+}:** every object 13f except o, which takes k's mesh;
  - **gain_k(e)** = seed-mean AUC(candidate) − seed-mean AUC(all 13f), for e ∈ E_o.
- **Leave-one-episode-out:** for each held-out e ∈ E_o, k̂ = argmax over {13f (gain 0), 12c, 9a+} of the mean gain on
  E_o \ {e}; the held-out gain is g(e) = gain_k̂(e).
- **o passes** if mean_e g(e) ≥ +0.005 and min_e g(e) ≥ −0.01. Objects with one public episode (beige cup) are not
  eligible.
- **For a passing o:** k* = argmax over k of the mean gain on all of E_o, and it must be non-13f.
- **D1 no-flip check:** k*'s mesh registered (public scan as the stand-in) at every eval seed it would face
  (1_000_003·ep + 101·slot, eval episodes / slots of o in the kit roster) must turn by < 20°. Otherwise o keeps 13f.

## Part 2: test A's placement per object
- For each object o:
  - **candidate:** o's 13f mesh re-placed by its per-episode Δ_e from test A (`placeA/episode_*/o.glb`, fitted
    GT-free on that episode's depth); every other object 13f;
  - **gain(e)** = seed-mean AUC(candidate) − seed-mean AUC(all 13f).
- **Leave-one-episode-out:** "placed" is chosen for the held-out e if the mean gain on E_o \ {e} > 0; then g(e) is
  that gain, else 0.
- **o passes** with the same rule as Part 1 (mean g ≥ +0.005, min g ≥ −0.01, ≥ 2 episodes).
- **On eval:** a passing o needs eval depth and the same GT-free fit (≈ $5, pre-approved) before any hand-over.

## Hand-over
Passing objects go to focused-pascal as a "pose pack" on 13f2, with its checklist: branch@commit, paths, md5,
object → eval (slot), transform, disclosure (public-CV selection; Tier B / 12c provenance as in their READMEs).
Objects that fail keep 13f.

## Cost
CPU here, $0 (≈ 120 multi-seed scorer runs at ≈ 65 s, 4 cores).

## Addendum 1 (21:25 UTC, pushed before any score of these candidates)
Two more candidates, from the coordinator via bold-albattani (branch claude/bold-albattani-6qmxsv, commit 30186bb,
library_v3 body frame, transform none, not adopted by the CD-O rules; GT-informed: best existing by scan-registration
ADD):
- **white_pot "X":** `docs/research/mesh-2026-10-26/cdo-sprint/C4-audit/meshes/white_pot_potlid_tsdf_ep43.glb`,
  md5 3591440e2dbf2029be908d46b29bfc96. Eval 1, 3, 5, 6 (slot 0); 8, 28 (slot 1).
- **mini_dust_pan "X":** `.../C4-audit/meshes/mini_dust_pan_pixal_mv_ep39_s7_lib.glb`,
  md5 35de47337b6385a1effdbc23257bded7. Eval 19 (slot 1); 38 (slot 0).

They join k ∈ {12c, 9a+, X} for these two objects. The rule is unchanged:
- leave-one-episode-out over {13f, 12c, 9a+, X};
- mean held-out gain ≥ +0.005, no held-out episode below −0.01;
- 10-seed means;
- D1 at the eval seeds of the listed eval slots (plus focused-pascal's d1gate.py before any pack).

Caveat: the X dust pan was generated from public ep39 frames, and ep39 is also one of its CV episodes.
