# G3 generation batch: working notes (resume from here)

Spec: `../C4-audit/PREREG.md` section 12 (addendum 7, d060f21e), resting on sections 2, 3, 9 and 10. Template: G2
(`../G2/README.md`, `../G2/NOTES.md`). Times UTC. Scratch S =
`/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`, bulk under `S/g3/`.
GPU cap for G3 $15; stop if Vast credit < $15. Ledger session mesh-bold.

- 2026-11-03T01:52Z start. Read STATUS.md, CLAUDE.md, PREREG s2/s3/s9/s10/s12, G2 README/NOTES/scripts, gen/*, the
  29 Oct Pixal3D-MV probe (gen-probe README, work log ~4720-4830, S/gen/assemble_views.py, run_views*.sh).
  Vast credit $94.50; 3 other instances (20261103-pfS/pfT/pfU, not ours). Local: 4 cores idle, 3.4 GB free disk.
- Episodes with our tracks (data/sweep) and observed points (obs_all), GT-free inventory:
  dust pan 18/39/40; beige 11 only; lid 0/2; sweeper 18/31 only; boards 23/24 (ep24 only, per spec);
  rack 12/13/26/27/31 (G2 used 31/12/26 -> G3b uses 13/27); pot 0/2/26/27/41-45 (G2 used 41/43/44 -> G3b uses
  0/2/26/27/42/45, every non-G2 episode crops.py accepts). No hands.npz for ep18/24/27 (crops.py rest gate only there,
  as G2 did for ep12).
- 01:53-01:55Z crops (local CPU, GT-free): `bash scripts/make_crops.sh S/g3/inputs` = G2's make_crops.sh (crops.py as on
  29 Oct: every 3rd frame, --n 2, --hands where hands.npz exists, our sweep tracks, calib, library_v3 silhouette seed),
  G3 pairs, 4 in parallel. 18 pairs, all accepted, **36 crops**:
  dust pan ep18 (k108, k99), ep39 (k297, k315), ep40 (k12, k9); beige ep11 (k0, k6); lid ep0 (k0, k9), ep2 (k315, k321);
  sweeper ep18 (k162, k264), ep31 (k12, k270); board 1 ep24 (k3, k6); board 2 ep24 (k6, k9); rack ep13 (k66, k69),
  ep27 (k144, k147); pot ep0 (k285, k291), ep2 (k240, k258), ep26 (k33, k36), ep27 (k15, k6), ep42 (k237, k240),
  ep45 (k6, k9). Rankings `inputs/ep<E>_<obj>_crops.json`, hashes `inputs/inputs_crops_sha256.txt`.
  Visual check (S/g3/crops_montage.jpg), kept under the rule (crops.py's own ranking) but flagged:
  - **ep0 lid k0/k9 show the wooden table with a white strip, not the lid** (GrabCut failure; ep0's lid has only 2,104
    observed points in obs_all, i.e. it is barely seen). Expected to give junk meshes that stage 1 screens out.
  - hands in view: ep18 sweeper (both), ep18 dust pan (fingers in the ring), ep26 pot (hand on the handle), ep24
    board 1 (a finger at the edge); ep27 pot has GrabCut holes in the bowl. ep18/24/27 have no hands.npz.
  - ep39 dust pan k297 is the crop of the 13h dust pan's source (hy21 ep39 k297 s42); like G2's blue cup, a G3 hy21
    ep39 k297 s42 output would regenerate the shipped source (not byte-identical expected); kept and to be flagged.
- 01:55-01:57Z Pixal3D-MV view sets (local CPU, GT-free): `bash scripts/make_views.sh S/g3/inputs` = gen/mv_views.py with
  the 29 Oct per-object flags (S/gen/run_views2.sh): dust pan / lid `--skin 1 --held_speed_mm 8 --min_deg 15`; beige /
  sweeper / boards `--min_deg 8`; then `scripts/assemble_g3.py` = the 29 Oct assemble_views.py rule (skin-gated set unless
  its view-0 IoU < 0.75, then an at-rest set `--skin 1 --min_deg 15`; extra views with mask/silhouette IoU < 0.75
  dropped). ep18 / ep24 have no hands.npz; mv_views.py needs one (a_offset, hand gate), so a stub with a_offset 1 (the
  value in all 16 real hands.npz) and no valid hand is used (= rest/skin gates only).
  **9 view sets** (`inputs/views/selection.json`): dust pan ep18 (2 views), ep39 (3), ep40 (1); beige ep11 (1); lid ep2
  (1); sweeper ep18 (5), ep31 (1); board 1 ep24 (2); board 2 ep24 (1). **ep0 lid: no usable frame** in either set (the lid
  is barely visible in ep0), so no Pixal3D-MV for it. Hands are visible in the ep18 sweeper / dust pan and ep24 board 1
  views (no hand gate there); masks mostly exclude them (S/g3/views_montage.jpg).
- 01:57Z observed points for the box's Sim(3) fits: `scripts/obs_sub.py` (G2's, unchanged: 40k of S/obs_all/ep<E>_<obj>.npz,
  default_rng(0)); ep0 lid has only 2,104 points. Hashes `inputs/inputs_obs_sha256.txt`; view-set file hashes
  `inputs/inputs_views_sha256.txt`. Input tar S/g3/g3_inputs.tar (crops_flat, obs_sub, views_final) sha256 50b70285...
- Box queue `scripts/box_g3.sh` (G2's box_g2.sh + Pixal3D-MV): SAM 3D alongside Hunyuan3D-2.1; then Pixal3D-MV 1536
  (1024 fallback) after SAM 3D; then TRELLIS.2 1536 (1024 fallback); one large model at a time (Hunyuan small, alongside);
  Sim(3) of single-image outputs on the CPUs (xargs -r now); SHA256SUMS over every .ply; marker G3-GEN-DONE.
  Launcher `scripts/launch_box_g3.sh` (G2's S/g2/launch_box.sh): box_setup.sh unchanged + the hf-2.2 fix with the Python
  API for Hunyuan3D-2.1, TRELLIS.2-4B (incl. pipeline.json) and the Pixal3D files, after WEIGHTS-DONE.
  Screen: `scripts/screen_manifest.py` (G3 objects; Sim(3) copies + Pixal3D-MV object-frame outputs, not *_gen),
  `scripts/box_screen.sh` (G2's, G3 paths), `../C4-audit/scripts/screen6.py` unchanged. Screen package (kit + 8 public scans
  + 8 b4096 caches; scan/cache files cmp-identical to G2's for pot/rack) built locally, sha256 830b4848..., uploaded only
  after the freeze commit.
- Pixal3D-MV and placement: stage 1 screens the Pixal3D-MV output as generated in our object frame (29 Oct practice; no
  Sim(3)). Stage 2 places every pick with place.py, Pixal3D-MV included, as PREREG s12 step 2 says and as the C4 audit
  did for the 29 Oct Pixal3D-MV candidates (`candidates.json`: needs_place true); place.py includes the identity start.
- 01:58Z commit 2417282 pushed (inputs, scripts). Inputs uploaded to the store `runs/mesh-20261103-g3-2417282/inputs/g3_inputs.tar`
  (sha256 50b70285...). Credit $94.01 at 01:58Z (other sessions: pfS/pfT/pfU running).
- 01:59:12Z rental, run `mesh-20261103-g3-2417282`: ledger planned $11 (mesh-bold). On-demand offers (H200/H100 class,
  sm_90): Spain H200 NVL $3.68/h (37 cores, $20/TB), New York $3.81/h (64 cores, 855 Mbps), New Mexico $4.04/h (85 cores,
  6.7 Gbps, $2.67/TB: the G2 machine, which worked). Chose New Mexico 58415958 (proven, cores for Sim(3) + screen).
  `SETUP=none DISK=120 IMAGE=vastai/pytorch:2.7.1-cu128-cuda-12.9-mini-py310-2026-10-23 V2D_COMMIT=241728211a2d7b7a7aa95530c68474648398d10a
  ops/vast.sh create 58415958 mesh-20261103-g3-2417282 'IDLE_MIN=195 bash docs/research/mesh-2026-10-26/gen/box_job.sh'`
  -> **instance 58904222**. IDLE_MIN 195 keeps the worst case (idle limit + ~12 min pull) at ~$14 < $15 cap.
- 02:02:33Z (box clock) box 58904222 up within ~3 min (no long image pull this time): H200 NVL 143.8 GB, cgroup ~82 cores,
  repo at 2417282, RUN_ID / HF_STORE set. Launched through exec: `NP=64 bash .../G3/scripts/launch_box_g3.sh`
  (box_setup.sh; sam3d_setup.sh after UV-; hf-2.2 fix after WEIGHTS-DONE; then box_g3.sh).
- 02:02-02:06Z setup: all env markers OK; W-HY21-FAIL again (hf CLI 2.2 --include), fixed by the launcher's Python-API
  fetch (HYFIX-OK): Hunyuan3D-2.1 dit/vae, TRELLIS.2-4B pipeline.json + 4 ckpts, Pixal3D pipeline_mv.json + 5 ckpts all
  present (hyfix.log FILE lines). SAM 3D env C import OK. INPUTS-OK 50b70285 (36 crops, 9 view sets).
- 02:06:38Z generation started: SAM 3D alongside Hunyuan3D-2.1, 36 crops x 4 seeds each.
- 02:42:03Z SAM 3D done, 144/144 ok (~15 s each, alongside Hunyuan3D-2.1). Pixal3D-MV 1536 started 02:42:03 (9 view sets x
  4 seeds, one process) beside the small Hunyuan job (85/144 at 02:42); SAM 3D Sim(3) fits running on the CPUs.
- 02:47:55Z SAM 3D Sim(3): 144/144. 02:59:06Z Pixal3D-MV done: **36/36 ok at 1536** (median 18.8 s; the first 145 s
  incl. warm-up). TRELLIS.2 1536 started 02:59:06 (36 crops x 4 seeds, one process); Hunyuan 122/144 at 02:59.
- 03:00Z GT-free frame check of all 36 Pixal3D-MV outputs (`gen/mv_check.py` on the box, our view masks only, as on
  29 Oct; `results/mv_check.jsonl` after the fetch): silhouette IoU per view 0.84-0.99; mean per mesh 0.88-0.99 (lowest:
  ep18 sweeper 5-view sets 0.878-0.911 and dust pan multi-view sets 0.90-0.92; single-view sets 0.94-0.99). The outputs
  are in our object frame (no axis-convention error).
- 03:10:16Z Hunyuan3D-2.1 done 144/144 (~25-30 s each); Sim(3) 144/144 at 03:17. TRELLIS.2 1536: 141/144 ok; 3 CUDA OOM,
  all ep11 beige cup (k0 s123, k0 s2025, k6 s2025; two with Hunyuan's 8.6 GB still on the GPU), rerun at 1024
  (`trellis2_1024`, labelled, as G2): 3/3 ok; done 03:26:43. Sim(3) 141 + 3. No errors.log line (xargs -r).
- 03:34:44Z **G3-GEN-DONE**: SHA256SUMS over **936 .ply** = 432 raw single-image (SAM 3D 144, Hunyuan 144, TRELLIS.2
  141 + 3 at 1024) + 432 Sim(3) copies + 72 Pixal3D-MV (36 raw generator-cube `_gen` + 36 in our object frame). Per object
  (each model): dust pan 24, beige 8, lid 16, sweeper 16, board 1 8, board 2 8, rack 16, pot 48 (single-image); Pixal3D-MV
  dust pan 12, beige 4, lid 4, sweeper 8, board 1 4, board 2 4. **0 lost.**
- FREEZE: `results/SHA256SUMS` (sha256 below), `results/gen_logs/`, `results/sim3_fits/`, `results/mv_check.jsonl`,
  `results/box_logs/` (log tails) committed next, BEFORE any public-scan read of these meshes. No G3 mesh has been scored
  or compared with a scan.
  SHA256SUMS sha256 7bdb0a517e1b0517...
- 03:36Z after the freeze (56d4710 pushed): screen_pkg.tar (kit + 8 public scans + 8 b4096 caches, sha256 830b4848...)
  uploaded to runs/mesh-20261103-g3-2417282/screen/. The box's exec shell has no git credentials, so the fetch of the
  freeze commit used the onstart.sh pattern (GH_TOKEN from /etc/v2d_env as an http.extraheader, not printed). Box at
  56d4710; its SHA256SUMS == the committed one (cmp, SUMS-MATCH). 03:38:32Z `NP=64 box_screen.sh` started; PKG-OK 830b4848.
- 03:38:32-03:45:24Z stage-1 screen [D] on the box's CPUs (`box_screen.sh`, 64 workers; py3.13 venv pinned to the local
  versions numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0, pandas 3.1.0; manifest 468 meshes = 432 Sim(3) + 36 Pixal3D-MV
  object-frame, 0 hash mismatches). **468 records, 0 errors** (`results/screen/screen6.jsonl`, sha256 7906c429...).
  18 meshes logged "budget_mesh failed ... using raw" (mesh_metric's own fallback when the kit simplifier cannot meet the
  budget; same code as G2).
- 03:45:42-03:47:20Z final store push from the box (`ops/box/store.sh push-run`, PUSH-RC 0): runs/mesh-20261103-g3-2417282/
  holds 974 files incl. all 936 .ply (5.8 GB; results/gen, results/screen). Checked from here: 4 sample paths exist.
- 03:47:30Z instance record (`results/box_logs/vast_instance_58904222.txt`): start 01:59:26Z, $4.033/h, 71.8 GB down,
  3.6 GB up. **03:47:33Z box 58904222 destroyed**, confirmed absent in `ops/vast.sh show` (only pfU, not ours, remains).
  **Measured cost $7.47** = 1.802 h x $4.033/h ($7.27) + 71.8 GB down at $2.60/TB ($0.19) + 3.6 GB up ($0.01). Ledger
  actual $7.47 (mesh-bold).
- 03:48-03:50Z the 32 stage-2 sources (4 lowest stage-1 CD-O medians per object) downloaded from the store
  (S/g3/gendl/runs/mesh-20261103-g3-2417282/results/gen/); stage2.py checks each against the frozen SHA256SUMS.
- 03:47-03:55Z ledger: `ledger.py add actual` appended the same actual line 5 times (its retry loop re-appends when an
  upload raises after it has landed). Removed the 4 duplicates with one parent_commit-guarded rewrite (202 rows, only
  those 4 identical rows dropped); `ledger.py show` now lists one actual line, $7.47; its totals were never affected
  (they key by run).
- 03:51Z stage 2 local (`scripts/stage2.py`, 4 object groups in parallel with `--only`, nice, 1 thread each):
  place.py -> T3 fit.py (frozen cfg) -> trim.py (15 mm, obs union of the object's G3 episodes + 13h mesh).
  - fit.py ended with rc 1 on `wooden_piece_1 pixal_mv ep24 s7`: its final kit `budget_mesh(4096, 4096)` raised "mesh
    simplification cannot satisfy the budget" after the fit itself ran (stage_0 held tmean90 1.70 -> 1.55 mm). Treated as
    a failed T3 fit: no t3fit candidate (the copied fit.glb was removed). stage2.py first crashed on it (KeyError 'final')
    in two groups; patched (failed fit -> `fit_failed` in picks.json) and rerun; finished outputs are reused.
  - Added a GT-free info field: whether the kit's `budget_mesh(4096, 4096)` (the packer's simplifier) accepts each
    candidate file. Failures get a `note` in candidates_g3.json (mesh_metric scores such files raw, as the stage-1 screen
    did for 18 meshes). The two groups that had run with the earlier code are rerun to record it (outputs reused).
- 04:13Z stage 2 done: 32 picks, **94 candidates** (32 placed, 30 t3fit, 32 trim) -> `../C4-audit/candidates_g3.json`
  (merged with `stage2.py --merge`; candidates_g2.json key order; md5 check: none equals any of the 10 public scan files).
  - 2 failed T3 fits (rc 1, kit budget): `wooden_piece_1 pixal_mv ep24 s7`, `mini_sweeper pixal_mv ep18 s123`; their placed
    and trim copies also fail the kit `budget_mesh(4096, 4096)` (4 files with a `note`). All other candidates pass it.
  - Held-out tmean90 [M] improves on 29 of the 30 fits; worse on the pot pick 1 (trellis2 ep45 k9 s2025, 4.73 -> 5.23 mm).
  - Pixal3D-MV placements are near identity (0.6-9.8 deg, scale 0.93-1.04, <= 1 cm). Boards' placements are near-ties
    (second-distinct start within 0.01-0.08 mm).
  - Trim: 13 of 32 removed 0 faces (`note`: same geometry as the placed copy); others 35-10,242 faces, <= 2.4 % of area.
  - Stage-2 folder (260 files, 422 MB) uploaded to the store `runs/mesh-20261103-g3-2417282/stage2/`.
- README.md written. Stage 3 (50-seed audit, rules A/B/C, D1 vs the 13h meshes) is the coordinator's; not run here.
