# G2 generation batch: working notes (resume from here)

Spec: `../C4-audit/PREREG.md` section 7 (addendum 2, e573235), sections 2-3. Times UTC. Scratch S =
`/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`, bulk under `S/g2/`.

- 2026-11-02T20:17Z start. Read STATUS.md, CLAUDE.md, PREREG s2/s3/s7, gen-probe README, the 29 Oct log (work log
  ~4707-4830), gen/*.sh|py, crops.py, sim3_fit.py, audit_multiseed.py, mesh_metric.evaluate, C1 T2 place.py, C1 T3 fit.py.
  Vast credit $127.84; one other instance (20261102-ptrkF-58a0f37, not ours).
- 20:22-20:25Z crops (local CPU, GT-free): `bash scripts/make_crops.sh S/g2/inputs` = crops.py as on 29 Oct (every 3rd
  frame, --n 2, --hands where hands.npz exists, our sweep tracks, calib, library_v3 silhouette seed). 11 pairs, all
  accepted, 22 crops: pot ep41 (k279, k285), ep43 (k300, k303), ep44 (k0, k3); blue cup ep22 (k156, k159), ep21 (k15,
  k18), ep12 (k156, k159; no hands.npz for ep12, so no hand gate there, rest gate only); rack ep31 (k285, k282), ep12
  (k24, k21), ep26 (k144, k138); pitcher ep22 (k33, k174), ep21 (k171, k33). crops.py's rankings in
  `inputs/ep<E>_<obj>_crops.json`, hashes in `inputs/inputs_crops_sha256.txt`.
  vs 29 Oct: same picks for ep41 pot and ep22 blue cup; ep22 pitcher now k33 + k174 (was k174 + k171), ep26 rack
  k144 + k138 (was k144 + k96). Scores differ by < 0.2 % with unchanged tracks and library_v3 (likely the local
  trimesh/OpenCV versions); the current ranking is used as pre-registered.
  Visual check of the montage (S/g2/crops_montage.jpg): all 22 show the right object; GrabCut cut notches into some
  masks (ep12 blue cup base, ep31 rack, pot floor) and ep21 pitcher k33 has skin-coloured pixels at its base.
- 20:25Z observed points for the box's Sim(3) fits: `scripts/obs_sub.py` (40k points of S/obs_all/ep<E>_<obj>.npz,
  default_rng(0)), hashes `inputs/inputs_obs_sha256.txt`. Input tar S/g2/g2_inputs.tar sha256 de9fc1c9...
- Box queue: `../../gen/box_g2.sh` (SAM 3D alongside Hunyuan3D-2.1, then TRELLIS.2 1536 alone, 1024 fallback; Sim(3)
  on the CPUs; SHA256SUMS at the end). Screen: `../C4-audit/scripts/screen6.py` (6 seeds 3001-3006, roster emptied).
- 20:26:51Z rental: commit ff63482 pushed; inputs uploaded to the store `runs/mesh-20261102-g2-ff63482/inputs/g2_inputs.tar`;
  ledger planned $7 (mesh-bold); credit $127.37 (other sessions now run 5 boxes, ~$7/h). Launch:
  `SETUP=none DISK=120 IMAGE=vastai/pytorch:2.7.1-cu128-cuda-12.9-mini-py310-2026-10-23 V2D_COMMIT=ff63482f72a339cf8469780b760986a16409ebc4
  ops/vast.sh create 31183486 mesh-20261102-g2-ff63482 'IDLE_MIN=300 bash docs/research/mesh-2026-10-26/gen/box_job.sh' 1.30`
  -> instance 58873650 (H100 NVL, Czechia, interruptible bid $1.30/h GPU).
- 20:28Z box: H100 NVL 95.8 GB, nproc 224 (host) but 28 effective cores (offer), so the queue runs with NP=24. Started
  through exec: box_setup.sh, sam3d_setup.sh (after UV-OK), `NP=24 box_g2.sh` (INPUTS-OK de9fc1c9..., 22 crops).
- Stage-1 location decided: the box's CPUs after the freeze commit (28 cores, ~264 x ~65 s / 24 workers ~ 12 min,
  ~$0.3 [E]) instead of local (4 cores already at load 4.3 from another job; 2 workers ~ 4 h). The kit, the 4 public
  scans and the 4 reference caches go to the box only after the freeze commit (`S/g2/screen_pkg`, 54 MB). Screen env:
  a fresh py3.13 venv pinned to the local versions (numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0, pandas 3.1.0).
- 20:30Z setup fix: W-HY21-FAIL. The box's hf CLI is now 2.2.0; `hf download REPO --include A B` takes B as a file
  name ("Ignoring --include since filenames have been explicitly set"), so Hunyuan3D-2.1 got no weights and
  TRELLIS.2-4B got its ckpts but no pipeline.json. Fixed by hand through exec with the Python API
  (snapshot_download allow_patterns hunyuan3d-dit-v2-1/*, hunyuan3d-vae-v2-1/*: 7.5 GB; hf_hub_download pipeline.json).
  box_setup.sh is unchanged in git; the fix is logged here.
- 20:32Z PREEMPTED: instance 58873650 went exited/stopped ~4 min into generation; the whole 8-GPU machine was rented
  on-demand (its 1-GPU min bid jumped to $2.69). Destroyed 20:33:53Z (nothing kept; no output was hashed or pushed).
  Instance record: 70.4 GB downloaded at $37.33/TB + ~6 min at $1.398/h, ~$2.80 [estimate from the record]; ledger actual.
- 20:35:21Z replacement, on-demand to avoid another preemption: run `mesh-20261102-g2b-ff63482` (same commit ff63482,
  inputs re-uploaded under runs/mesh-20261102-g2b-ff63482/inputs/, same sha256). Offer 58415958 -> instance 58874418,
  H200 NVL 141 GB (Hopper sm_90 like the H100, so the compute_90 wheels apply; the memory also avoids TRELLIS.2's
  1536 OOM), New Mexico, $4.033/h, 85 cores, $2.67/TB. Ledger planned $12. Credit $123.65 at 20:34Z.
  Same launch line with `create 58415958 mesh-20261102-g2b-ff63482 ...` and no bid.
- 20:47:17Z (box clock) box 58874418 up after a ~10 min image pull: H200 NVL 143.8 GB, cgroup quota ~82 cores.
  Launched through exec `S/g2/launch_box.sh` (box_setup.sh; sam3d_setup.sh after UV-; the Hunyuan / TRELLIS.2
  pipeline.json fetch with the Python API after UV-OK (hyfix.log); then `NP=64 box_g2.sh`).
- 20:51:59Z generation started (box clock): SAM 3D alongside Hunyuan3D-2.1 (GPU memory ~16.5 GB and ~9.5 GB).
  21:13:50Z SAM 3D done, 88/88 ok (~15 s each). 21:13:58Z operator step: touched `.hy21_gen_done` so TRELLIS.2
  (large) starts beside the small Hunyuan job instead of after it: one large model at a time still holds, and the
  H200 has 143 GB (Hunyuan ~10 GB, TRELLIS.2 needed <= ~85 GB on 29 Oct). Logged in g2_queue.log. TRELLIS.2 1536
  started 21:14:00Z, all 22 crops x 4 seeds in one process.
- ~21:18Z coordinator update (PREREG s10 at 63e2c39, before any G2 scoring): stage 2 also takes, per object, the 2
  lowest stage-1 ADD medians (median of the 6 seeds' add_mm = screen summary add_med) among G2 meshes with stage-1
  CD-O median <= shipped 50-seed median + 0.005 (pot 0.3157, blue cup 0.2696, rack 0.4232, pitcher 0.3763), when not
  already among the 4 by CD-O; field why = "cdo_top4" | "add_ext". Read literally: the 2 lowest are taken first and any
  already in the top 4 is not replaced. `scripts/stage2.py` updated before any score exists.
- 21:30:49Z Hunyuan done 88/88 (~25 s each). 21:40:12Z TRELLIS.2 done: 82/88 at 1536; the 6 failures are all ep22
  blue cup (k156 s42/s7/s2025, k159 s42/s7/s123), CUDA OOM even on 140 GB (two failed with the TRELLIS process alone at
  138.7 GB; four while Hunyuan held 8.6 GB), rerun at 1024 (`trellis2_1024`, labelled): 6/6 ok.
  Sim(3) fits: 264/264 (sam3d 88, hy21 88, trellis2 82, trellis2_1024 6). The 2-line errors.log in sam3d_sim3/hy21_sim3 is
  xargs running sim3_fit.py once with no arguments in the final gap-fill pass (GNU xargs without -r on empty input);
  no fit is missing.
- 21:46:34Z G2-GEN-DONE: SHA256SUMS over 528 .ply (264 raw + 264 Sim(3)). Per object: pot 72, blue cup 72 (incl. 6 at
  1024), rack 72, pitcher 48; 0 lost.
- FREEZE: `results/SHA256SUMS`, `results/gen_logs/`, `results/sim3_fits/`, `results/box_logs/` (log tails) committed
  next, BEFORE any public-scan read of these meshes. No G2 mesh has been scored or compared with a scan.
- 21:47Z after the freeze (1a3a044 pushed): screen_pkg.tar (kit + 4 public scans + 4 reference caches, sha256 91cf744b...)
  uploaded to runs/mesh-20261102-g2b-ff63482/screen/; box checked out 1a3a044 (its SHA256SUMS == the box file, cmp);
  `NP=64 box_screen.sh`: py3.13 venv with the local pins (numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0, pandas 3.1.0),
  manifest 264 meshes, 0 hash mismatches, screen6.py 64 workers. 21:48:13-21:51:20Z: 264 records, 0 errors
  (`results/screen/screen6.jsonl`, sha256 356fd302...).
- 21:52-21:54Z final store push (store.sh push-run, rc 0): runs/mesh-20261102-g2b-ff63482/ holds 564 files, 3.55 GB, all
  528 .ply + results/screen/. The 16 stage-2 sources downloaded to S/g2/sim3dl and checked against SHA256SUMS (16/16).
- 21:54:16Z box 58874418 destroyed, confirmed absent in `ops/vast.sh show`. Cost from the instance record: 1.315 h at
  $4.033/h + 71.7 GB at $2.67/TB + upload = $5.50; ledger actual $5.51. G2 total with the preempted box ~$8.31.
  Credit $108.53 at 21:55Z (other sessions' boxes included).
- Note: G2 `sam3d/ep22_blue_cup_k156_s7` regenerates the shipped blue cup's source (same crop file, cmp-identical, same
  seed) but is not byte-identical (SAM 3D is not deterministic across runs / GPUs); it is kept under the rule and flagged.
