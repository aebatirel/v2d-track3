# Rack round R: working notes (resume from here)

Spec: `../C4-audit/PREREG.md` section 14 (addendum 9, f471f18a), with sections 2, 9, 12 and 13 for the copy types.
Template: G3 (`../G3/README.md`, `../G3/NOTES.md`, `../G3/scripts/`). Times UTC. Scratch S =
`/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`, bulk under `S/r/`.
GPU cap for R $10; stop and destroy if Vast credit < $15. Ledger session mesh-bold. Stage 3 (50-seed audit) is the
coordinator's; not run here.

- 2026-11-03T07:36Z start. Read CLAUDE.md, STATUS.md (head), PREREG s2/s7-s14, G3 README / NOTES / scripts, G2 NOTES,
  crops.py, prim_rack.py header, results/prim/rack/*, C2/R-rack/PREREG.md. Local: 4 cores, 2.3 GB free disk.
  Vast credit $73.73; two instances of other sessions (20261103-ptrkH, 20261103-ipose; not ours, not touched).
- Rack episodes: pipeline/mesh_v5.json lists exactly 12 / 13 / 26 / 27 / 31 as the rack's public episodes, and those are
  the five with our tracks (data/sweep) and observed points (obs_all). No other public rack episode exists for crops.py.
- 07:37-07:39Z crops (local CPU, GT-free): `bash scripts/make_crops.sh S/r/inputs` = G3 make_crops.sh with `--n 6` and
  the five rack episodes; only crops.py's ranks 3-6 (`chosen[2:6]`) go to crops_flat. Ranks 1-2 reproduce the G2 / G3
  crops exactly (ep12 k24 / k21, ep13 k66 / k69, ep26 k144 / k138, ep27 k144 / k147; ep31 below), so the R crops are
  disjoint from G2 / G3. ep12 / ep27 have no hands.npz (rest gate only, as G2 / G3).
  **20 crops** (ranks 3-6 x 5 episodes): ep12 k18 / k27 / k15 / k12; ep13 k87 / k96 / k15 / k12; ep26 k132 / k150 /
  k96 / k126; ep27 k129 / k132 / k84 / k87; ep31 k279 / k0 / k3 / k6. Rankings `inputs/ep<E>_plastic_dish_rack_crops.json`,
  hashes `inputs/inputs_crops_sha256.txt`. Visual check (S/r/crops_montage.jpg), kept under the rule but flagged:
  - **ep31 ranks 4-6 (k0, k3, k6) have crops.py score 0**: MediaPipe hand joints (3-6) inside the rack's box, so the
    hand gate zeroes them; ep31 has only 3 frames with score > 0 (of 97). They are still crops.py's ranks 4-6 and show
    the whole rack with a notch where the hand is. Kept (PREREG s14 says ranks 3-6); stage 1 decides.
  - a hand on the cup holder in ep26 k96; skin / table at the right end of ep13 k96; GrabCut notches in the peg area of
    ep12 k12 / k15 / k27, ep13 k12 / k15 / k87, ep26 k126 / k150.
- 07:37-07:39Z Pixal3D-MV view sets (local CPU, GT-free): `bash scripts/make_views.sh S/r/inputs` = G3 make_views.sh for
  the rack only, with the rack's 29 Oct flags (`--skin 1 --held_speed_mm 8 --min_deg 15 --occl 0.15`, from
  S/gen/run_views2.sh); at-rest fallback `--skin 1 --min_deg 15 --occl 0.15` when view 0's mask / silhouette IoU < 0.75;
  then G3 `scripts/assemble_g3.py` unchanged. Every skin-gated set had view-0 IoU 0.51-0.69 (the lattice defeats GrabCut),
  so all 5 use the at-rest set, **one view each** (`inputs/views/selection.json`): ep12 k24 (IoU 0.68), ep13 k66 (0.66),
  ep26 k98 (0.51), ep27 k146 (0.69), ep31 k286 (0.65). ep12 / ep27 use the stub hands file (a_offset 1, no valid hand).
  The 29 Oct probe ran Pixal3D-MV on ep26 (view k138, seeds 42 / 7); R's ep26 set uses k98, so no R output repeats it.
- 07:40Z observed points for the box's Sim(3) fits: G3 `scripts/obs_sub.py` unchanged (40k of S/obs_all/ep<E>_plastic_dish_rack.npz,
  default_rng(0)); all five are cmp-identical to the G2 (ep12 / 26 / 31) and G3 (ep13 / 27) files. Hashes
  `inputs/inputs_obs_sha256.txt`, view files `inputs/inputs_views_sha256.txt`. Input tar S/r/r_inputs.tar (crops_flat,
  obs_sub, views_final) sha256 9ff31e5e3f989cfb...
- Box queue `scripts/box_r.sh` = G3 box_g3.sh with the R tar, seeds 42 / 7 / 123 / 2025 / 31337 / 777, marker R-GEN-DONE and
  an HF-download retry. Launcher `scripts/launch_box_r.sh` = G3's (hf-2.2 Python-API fetch), queue path changed. Screen:
  `scripts/screen_manifest_r.py` (G3's, rack only, label r/...), `scripts/box_screen_r.sh` (G3's, R paths),
  `../C4-audit/scripts/screen6.py` unchanged.
