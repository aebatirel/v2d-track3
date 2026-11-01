# E0 box run (CD-O sprint): C0's mesh methods rebuilt on the eval episodes

Run id `mesh-20261031-e0-b05f001`, code commit `b05f001001fe3d4a80659e32c1d1c9fa91f3276d` (PREREG.md, `jobs/` and
`inputs/` unchanged since 705652a). Job `bash docs/research/mesh-2026-10-26/cdo-sprint/E0/jobs/e0_box.sh`. Labels:
[M] measured, [E] estimate. Eval inference only. No scan, mocap, parquet pose or `*_align` file went to the box, and
nothing here is scored against ground truth (none exists for eval).

## Result in one line
**E0-DONE rc=0 [M].** All 17 eval pairs (pot 6, lid 1, rack 5, blue cup 5) went through hands, observed points and
builds with 0 failures. All 49 candidates were built, plus 352 fidelity tasks and 53 frame/budget checks. The
pre-registered pick ran on the box. The box lived about 15 min, the job took 11.5 min, and it cost about **$0.13** [E].
The prep estimate was 40-60 min and $0.5-1.

## Box
| | |
|---|---|
| Offer | 57321792: Connecticut US, AMD EPYC 7K62, 96 of 96 cores effective, 252 GB RAM, 775/779 Mbps, reliability 0.997, RTX 5070 (unused), $0.487/h all-in (80 GB disk included), download $0.29/TB |
| Why | Custom Vast bundles query (verified, on-demand, >= 32 effective cores, >= 64 GB RAM, >= 80 GB disk, reliability >= 0.98, >= 500 Mbps, CUDA >= 13.2 for the default py313 image). This was the cheapest offer with >= 48 cores and >= 90 GB RAM, and nproc equals the effective core count. Fallbacks: 58547191 (Japan), 57153197 (Belgium) |
| Instance | 58555214, image `vastai/pytorch:2.11.0-cu130-cuda-13.2-mini-py313-2026-10-16`, `SETUP=none DISK=80` |
| Create | `SETUP=none DISK=80 V2D_COMMIT=b05f001001fe3d4a80659e32c1d1c9fa91f3276d ops/vast.sh create 57321792 mesh-20261031-e0-b05f001 'bash docs/research/mesh-2026-10-26/cdo-sprint/E0/jobs/e0_box.sh'` |
| Ledger (session mesh-bold) | planned $1.00 (16:25Z, cap $8); actual **$0.13** (16:40Z), an estimate from the instance clock: ~15 min x $0.486/h plus ~22 GB downloaded at $0.29/TB |
| End | The box pushed to the store and self-destroyed. It was gone from `ops/vast.sh show` at 16:40:39Z [M] |

## Timeline (UTC, 31 Oct) [M]
| Step | Time | Duration |
|---|---|---|
| create | 16:25:29 | - |
| image pull, clone, run_job start | 16:25:29-16:28:50 | 3.4 min |
| frozen-code sha1 check (7 files OK), venvs (MAIN-OK, MP-OK; Python 3.13.16 and 3.12.3; all `req_*.txt` pins installed exactly) | 16:28:51-16:29:01 | 10 s |
| inputs (45 files sha256 OK) + eval depth 14 episodes, 21.43 GB, all sizes OK | 16:29:01-16:31:46 | 2.8 min (depth 129.5 s, ~165 MB/s) |
| hands (MediaPipe, 14 episodes in parallel) | 16:31:48-16:34:18 | 2.5 min (73-150 s per episode) |
| obs_points (17 pairs in parallel, stride 2, all with `--hands`) | 16:34:18-16:37:05 | 2.8 min (21-164 s per pair) |
| builds (20 tasks; the serial `prim_rack.py run` over 5 episodes took 123 s) | 16:37:05-16:39:09 | 2.1 min |
| fidelity (352 tasks, 96 workers) | 16:39:09-16:39:37 | 28 s |
| frame + budget checks (53 tasks) | 16:39:37-16:39:46 | 9 s |
| select, SHA256SUMS (1062 files, 530 MB), store push | 16:39:46-16:40:22 | 36 s |
| self-destroy (second push, delete) | 16:40:22-16:40:39 | 17 s |

Total job time was 11.5 min (`run_job.log`: "job exit 0 after 11 min total"). The box lived about 15 min.
Cosmetic: the job log's first line says "cpus 2". GNU `nproc` honours `OMP_NUM_THREADS`, which the script exports
as 2 just before that line. The worker count (96) was taken before the export, and `run_job.log` reports 96 CPUs.

## Per-pair status [M] (all OK, 0 failures)
| Object | Eval ep | Hands: right / left frames measured | obs: frames, kept points | Builds |
|---|---|---|---|---|
| white_pot | 1 | 192/335, 259/335 | 168, 3.28 M | fit, nostem, tsdf, thick OK |
| white_pot | 3 | 193/313, 263/313 | 157, 4.97 M | 4 OK |
| white_pot | 5 | 129/288, 254/288 | 144, 4.20 M | 4 OK |
| white_pot | 6 | 133/243, 228/243 | 122, 2.82 M | 4 OK |
| white_pot | 8 | 202/219, 218/219 | 110, 2.56 M | 4 OK |
| white_pot | 28 | 209/220, 157/220 | 110, 4.65 M | 4 OK |
| white_pot_lid | 1 | (ep1 above) | 168, 1.50 M | t2.5 fit, tsdf OK |
| plastic_dish_rack | 14 | 151/158, 122/158 | 79, 2.17 M | full, nomk OK (rack run) |
| plastic_dish_rack | 15 | 105/166, 157/166 | 83, 2.27 M | full, nomk OK |
| plastic_dish_rack | 16 | 163/173, 155/173 | 87, 2.13 M | full, nomk OK |
| plastic_dish_rack | 28 | (ep28 above) | 110, 2.41 M | full, nomk OK |
| plastic_dish_rack | 30 | 251/263, 190/263 | 132, 3.81 M | full, nomk OK; joint + joint_nomk over all 5 |
| blue_cup | 10 | 150/161, 152/161 | 81, 0.40 M | g1, g0 OK |
| blue_cup | 14 | (ep14 above) | 79, 0.97 M | g1, g0 OK |
| blue_cup | 20 | 119/202, 199/202 | 101, 1.12 M | g1, g0 OK |
| blue_cup | 32 | 235/259, 232/259 | 130, 1.07 M | g1, g0 OK |
| blue_cup | 33 | 296/348, 268/348 | 174, 1.51 M | g1, g0 OK; merged g1 over all 5 OK |

Hands sanity: in two-hand frames, the right wrist lay right of the left wrist in 0.99-1.00 of frames in every episode.
The rack joint fit used all 5 episodes, since each one's own full fit was within JOINT_TOL of the best. The rack's
own `prim_rack.py` selection also picked joint (6.419), which matches the table.

## Pre-registered pick (box `e0_select.py`, PREREG section 4; fidelity = `obs_fidelity` sum_mm on ALL eval points of the object, in-sample for E0)
| Object | Pick | fid ALL mm | C0 | library_v3 | C0/pick | lib/pick | eligible | Recommendation (PREREG 6) |
|---|---|---|---|---|---|---|---|---|
| white_pot | `pot/ep3/fit` (`cand/white_pot/white_pot_ep3_fit.glb`, sha256 af321725...) | 2.922 | 2.914 | 3.881 | 0.997 | 1.328 | 18/24 | E0, no flag |
| white_pot_lid | `lid/ep1/t2.5_fit` (`cand/white_pot_lid/white_pot_lid_ep1_t2.5_fit.glb`, e3dd5861...) | 1.675 | 1.772 | 5.186 | 1.058 | 3.096 | 1/2 | E0, no flag |
| plastic_dish_rack | `rack/joint/joint` (`cand/rack/t2.5_lean1/plastic_dish_rack/joint_joint.glb`, fc67c59b...) | 6.419 | 6.245 | 5.881 | 0.973 | 0.916 | 12/12 | E0, no flag |
| blue_cup | `cup/ep32/g1` (`cand/blue_cup/ep32_blue_cup_g1.glb`, e6c18b2a...) | 2.646 | 2.723 | 2.906 | 1.029 | 1.098 | 11/11 | E0, no flag |

Exclusions: every tsdf variant (pot 6 of 6, lid 1 of 1) has a raw mesh that is not watertight, so those were
excluded by the pre-registered rule. No candidate failed the frame check or the kit budget. C0 vs library_v3 frame
check reproduces `../C0/frame_check.json` exactly (centroid 5.4369 / 7.3134 / 11.4617 / 3.5250 mm for pot / lid /
rack / cup). Full tables and per-episode diagnostics: `box/selection.md`.

Observations (facts from the table, no rule changed):
- The pot pick does not beat C0 even in-sample (C0 is 0.3 % lower), and neither does the rack pick (C0 2.7 % lower).
  Both stay within the pre-registered 15 % margin, so the rule says E0.
- On the rack, library_v3 has the lowest ALL fidelity of all meshes (5.881, 8.4 % below the pick). It is also the lowest
  of all 14 rack meshes on episodes 14, 15, 16 and 28. On ep30, C0 is lowest (7.339), then the pick (7.379), checked
  over every row of `fidelity.jsonl`. The rack rule compares only against C0, so this changes
  nothing, but a reviewer should see it: E0's in-sample advantage did not show up for the rack.
- The cup pick beats library_v3 by 9 % and C0 by 3 % in-sample. The lid pick beats C0 by 5.5 %.

## Where things are
- HF store `aebatirel/v2d-store`, `runs/mesh-20261031-e0-b05f001/`: `inputs/` (uploaded before launch),
  `results/e0/` (1062 files, 530 MB: obs, hands, cand, axis, fid, check, logs, `selection.*`, `fidelity.jsonl`,
  `SHA256SUMS`), box logs (`run_job.log`, `job.log`, `watchdog.log`), `COMMIT` = b05f001.
- Local copy: `<scratchpad>/cdo_e0/box/dl/runs/mesh-20261031-e0-b05f001/` (575 MB; the download took 484 s). It
  passes `sha256sum -c SHA256SUMS` 1062 of 1062 [M].
- Git (this folder, `box/`): `selection.md`, `selection.json`, `fidelity.jsonl`, `candidates.json`, `e0_job.log`,
  `run_job.log`, `status_{hands,obs,build}.txt`, `SHA256SUMS`. Meshes stay in the store. The `path` fields in these
  files are box paths: `/content/results/e0/...` = store `runs/mesh-20261031-e0-b05f001/results/e0/...`.

## Failures and relaunches
None: one box, one launch, no relaunch, no hold. The stall watchdog never fired.
