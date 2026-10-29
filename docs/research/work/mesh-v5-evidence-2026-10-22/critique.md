**Verdict:** the spec should not be ported as written. Its main risk is the per-episode chain, which is what actually gets submitted. On ep18 along our own tracks, the fallback mesher F4 is much worse than v2. The frozen gates would ship an F4 sweeper that flips on all 6 seeds. Repo unmodified, CPU only, $0, no depth fetched, about 14 GB of disk free.

## New measurements from this review
All runs are single-episode, on existing grids or local depth. Cells are CD-O cm / ADD mm at the eval seeds / scan flips out of 6 [D]. X flips (registered against our own reference) and C (chamfer to the seed) use v2 or lib5 as reference. lib5 here is the all-episode observation-first (O) nobc mesh. Both are [M] given that reference.

| Mesh | Score [D] | X flips v2 / lib5 | C v2 / lib5 |
|---|---|---|---|
| sweeper O def, scan-templated tracks | 0.446 / 5.4 / 0 | 0 / 0 | 0.352 / 0.311 |
| sweeper O def, own tracks | 0.477 / 4.2 / 0 | 0 / 0 | 0.385 / 0.359 |
| sweeper O nobc, scan-templated | 0.413 / 25.0 / **1** (seed 30000090) | **0 / 0** | 0.334 / 0.311 |
| sweeper O nobc, own tracks | 0.428 / 23.9 / **2** | **0 / 0** | 0.377 / 0.338 |
| **sweeper F4, own tracks** | **0.510 / 71.1 / 6** | **0** / 3 | **0.468** / 0.479 |
| dust pan O def / nobc, own tracks | 0.261 / 5.1 / 0 and 0.317 / 7.9 / 0 | 0 | 0.23 |
| **dust pan F4, own tracks** | **0.642 / 15.2 / 0** | 0 / 5 | 0.547 / 0.609 |
| board 2 def / nobc, ep24 own tracks | **0.367 / 127.8 / 6** and 0.193 / 4.6 / 0 | 1 / 2 and 0 | 0.472 / 0.476 |

For reference, v2 is sweeper 0.316 and dust pan 0.331.

E0 re-weighted from existing results [D]:
- **nobc, all-seed means:** −0.0153 cm / −0.80 mm.
- **nobc, score-share weights:** −0.0144 / −1.14.
- **nobc without the sweeper:** +0.40 mm at eval seeds, +0.33 mm over all seeds. The ADD gain is entirely v2's sweeper flips.
- **def, all-seed means:** +1.73 mm, so def also fails clause 2.

## Riskiest assumption and cheapest test
**Assumption:** per-episode re-fusion with the frozen gates never ships a mesh worse than the seed, and F4 is a safe fallback. F4 is the branch for pot, blue cup, rack and pitcher, which is 42.5% of the final AUC, plus the sweeper whenever O fails G2. On ep18 it is falsified [D].

**Test (about 1.5 h CPU, $0, 1–1.5 GB of depth fetched and then deleted, before porting the selection logic or any GPU spend):** run M0, F4 and O plus all gates on ep12 and ep27 (blue cup, rack, pot) along their existing own-mesh tracks.
- **Pre-registered rule:** if F4 is worse than v2 by more than 0.10 cm CD-O, or flips, on at least 2 of the 4 object-episodes, F4 is dropped as a submission branch.
- **Then:** owner decision O2 (submit the library mesh) or the library-plus-episode fusion in #13 decides instead.

## Corrections
**Evidence**
1. **D4 (fallback F4) is falsified where measured** (table above). Earlier single-episode classic builds from the 2026-10-21 log were also worse than v2: pot 0.65–0.70, blue cup 0.85, pitcher 1.15. Selection becomes O → seed (O2) or O → #13. Keep F4 only as M0, the region and other-object source.
2. **The gates do not stop flips.**
   - X misses both nobc sweepers (0/6 against both references while the scan shows 1–2 flips).
   - C passes the F4 sweeper (0.468) and the def board 2 (0.472), and both flip 6/6.
   - The F4 branch skips G2.
   - E0c tested only O meshes and only CD-O.
   - **Fixes:**
     - Raise X to at least 24 seeds and register against both the seed and the leave-one-out library mesh.
     - Make F4 pass a G2-type gate if it is kept.
     - Objects whose seed has scan-free ambiguity under 4 mm (sweeper, boards, lid, spoon) keep the seed unless the twin rehearsal (E8) shows per-episode meshes add no flips. That is a ground-truth-free class rule, so it is allowed.
3. **D2 (nobc) was decided on library meshes only.**
   - Per episode, nobc makes the sweeper flip at eval seed 30000090, and def makes board 2 flip 6/6 on own tracks.
   - E1 must judge library and per-episode twin meshes; the ep18 and ep24 grids already exist.
   - Fix the E0 bookkeeping:
     - `gate_pass` is hard-coded from the def grids in `e0_global.py`;
     - the lid has no nobc grid;
     - 66% of the CD-O gain is the beige cup.
4. **The gate freeze breaks binding critique 12.** §4.5 freezes the gates "now", but they were calibrated on scan-templated tracks. Own tracks already change outcomes (board 2 def goes from 0 to 6/6 flips; O CD-O rises 0.012–0.031 cm). Freeze after E4 on the 4 own-track episodes (possible now) and the G1 episodes, with the adjustment rule written down first.
5. **Rule A uses eval-seed means,** which is one registration for the lid, pitcher and boards.
   - Use means over all of at least 12 seeds, with eval seeds as ordinary members, and treat flips as a rate. The same applies to `--reg_seeds eval`.
   - Reason one, noise: the 10-21 log says Kaggle's scan samples differ.
   - Reason two, rules: scan diagnostics at eval-episode seeds approximate eval results.
   - The E0 verdicts do not change (#3 numbers).
6. **Weights.** CD-O is the kit mean over 36 pairs, so pair weights are right for CD-O. ADD-AUC is a per-episode mean with objects equal within an episode, so the registration clause should use score shares (dust pan 3 units of 27).

**Rules, provenance and owner**

7. **The spec drifts from the owner's 11:20 decision.**
   - The owner said re-fuse and then re-track with the new mesh; the spec drops re-tracking for known objects. Add it (perception is about 4 min per episode, about $0.1 [E]) or flag the change to the owner.
   - O2 contradicts "library mesh only as a tracking seed". Ask O2 now with these numbers (10 of 19 single-episode O meshes are more than 0.1 cm worse than v2; F4 is worse still), not after E8.
8. **O7 does not need the owner.** Re-derive the spoon frame from the template's principal axes and map the ep3/ep35 tracks by that fixed transform. This is score-neutral because the kit registers our mesh before scoring.
9. **Hands tier.** Hands refined or depenetrated against object meshes inherit those meshes' tier, and the prototypes used `loc/refs` hands. `provenance.check` must accept only unrefined hands in stage 2m.
10. **Port tests must not open scans.** Use a ground-truth-free chamfer to the prototype mesh ≤ 0.2 mm; the scan check stays in `tools/mesh_diag.py`.

**Design**

11. **Our convex pieces should be off by default in v5.0.** Their physics results are mixed (ep24 swings 4× between track sources; the lid is helped by neither), host memory per world doubles, and the pot needs 64 pieces. Use default CoACD on the full-resolution watertight mesh instead (13.5 → 6.7 cm³ on ep24 [M]). Use pieces only where the rest replay tilts more than 5° with default CoACD.
12. **Spoon.**
    - The fit's gain is synthetic (about 0.005 cm on the 36-pair mean), so port it last; the unfitted template serves meanwhile.
    - The template's ambiguity excess is 2.0 mm, which puts it in the flip-prone class, and X is blind to shape-driven flips. So the spoon's flip risk is [H] high, not low.
    - Not addressed: 7 of 10 spoon episodes put the spoon inside a pot, rack or blue cup that may have a false floor. Add to E9: per-frame overlap of the posed template with the container's mesh on eval ep3 (ground-truth-free).
13. **[H] Library-plus-episode fusion instead of F4.** Sum the eval episode's grid with the v5 library grids; they share a frame. This is re-fused from the episode's own video and keeps library-level evidence. Falsified if leave-one-out-plus-twin fails Rule A against leave-one-out alone on the twins.
14. **E3 (one global edge filter) has a known per-object conflict.** The 0.02 setting strips the dust pan (registered AUC 0.953 → 0.880) but fixes board flips (0.12 → 0). Add an adaptive arm [H]. E3 also needs a full re-fusion pass, not a post-pass.

**GPU and feasibility**

15. **The G2 base for ep18 must be kfi (0.715), not kri.** The base kri (0.368) is a different flag set; using it adds about 0.11 to the mean clause from flags alone and masks regressions on ep12/ep27.
16. **A single-seed "fail" has a high false-alarm rate:** about 11–19% per episode, 30–45% for at least one of three [E]. A fail should trigger a second seed for that episode (about $3–4) before stopping.
17. **The spec has no schedule.**
    - Estimate: 3–4 days of porting plus 2–3 CPU days of runs [E]; classic fusion measured here at 4.3 min per object-episode.
    - Proposed dates: G1 go-ahead today (credit $6.28); ports P1–P8 by Oct 25; E-runs by Oct 28; G2 on Oct 29; last safe G3 start Oct 31.
    - Degraded path to decide now, if E2/E8 are not green by Oct 29: O2 or #13, open3d decimation, default CoACD, unfitted spoon template, support rule only if E5 passes.
    - No eval submission exists yet, so name an insurance trigger date.

## Port order, corrected
- **P1:** `STOP_AFTER=hands` in `pipeline_ep.sh` (one line; unblocks G1 today).
- **P2:** `provenance.py`, the deny-list, G0 checks in perc2/mkref/recon_mesh, and `test_provenance` (E10), including the hands-refinement tier.
- **P3:** `recon_mesh.py`: thin SVD, `--save_grid`, observation-first accumulators with NB/NBR/NVR.
- **P4:** `mesh_decimate.py` plus the `setup.sh` dependencies (open3d 0.20.0 works on Python 3.13 here).
- **P5:** `mesh_post.py` (O@lc25; nobc, def and clip modes; G1/G2/G5 report-only until E4).
- **P6:** `tools/mesh_diag.py` (all-seed means, score-share weights, ≥ 12 seeds) and `score_registered --reg_seeds`.
- **P7:** `build_library.sh` with `--loo` and grid summing (needed for #13 and E8).
- **P8:** `ep_mesh` plus stage 2m, per-episode `ASSETS`, and `make_assets` collision from `_full.glb` with default CoACD. Selection is O → (#13 | seed per O2).
- **P9:** `mesh_gates.py`: X at ≥ 24 seeds against both references, the ambiguity class, and C report-only.
- **P10:** `rest_support.py` and `replay_rest.py`, after E5.
- **P11:** `ops/jobs` default to library_v5.
- **Deferred:** `collision_decomp` / `--pieces` / `hullovl`, `spoon_mesh` (fit), and F4 as a submission branch unless the ep12/ep27 test passes.

Files are in `/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/v5/review_spec/`:
- COMMANDS.txt (run record with all commands and results)
- e0_sens.py
- e0_sens.json
- build_p2m.py
- f4_ep18.sh
- gate_c.py
- results_p2m.jsonl
- xreg_v2.jsonl
- xreg_lib5.jsonl
- gate_c.jsonl
- meshes/ (12 O meshes and their manifest)
- f4/ (M0 and F4 meshes and logs)