# C2 track R (plastic_dish_rack): adversarial verification

- **When and where.** 2026-10-31, 21:25-21:50 UTC, on the cloud VM (4 shared cores, loaded), CPU only, $0. Code at
  repo HEAD `73f3cc0` (the track's files are unchanged since `0683232`). Verifier scratch outputs:
  `SCR/cdo_c2r_verify/` (`SCR` = `/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`).
- **What was checked.** PREREG timing (git commit and push times); the origin of every constant (against C0b AUDIT and
  REPLACEMENTS); the inputs and the A1 cleaning; the pick (recomputed); one scoring; the WIN gate and the AUC guard
  (recomputed with C0's own verdict script); mesh bytes = scored bytes = guard bytes; the frame; cost and the box.
- **Ground truth.** I scored nothing and ran no guard run. I read only the existing score / guard JSONs. All
  recomputations below use our observed points, our meshes and the committed records.
- Labels: [M] measured here without ground truth; [D] existing scan-scored record, re-read, not re-scored.

## Verdict

**No blocking finding.** The track's result stands: one scoring, CD-O 0.4413 > 0.43604, so no WIN. The guard PASS is
reported only. The mesh is **not adopted**, and H-R is falsified. Every number that decides something reproduces
exactly. Two statements need a correction (N1, N2). The rest are disclosures and caveats (N3-N10).

## 1. Checks

| # | Check | How | Result |
|---|---|---|---|
| 1 | PREREG before building | `git log` commit times; push times from the reflog of `origin/claude/bold-albattani-6qmxsv` | PREREG `01c25d2` committed 18:49:32, pushed 18:49:35. A1 `945baa5` committed 19:55:16, pushed 19:55:19. The build log's first line is 19:55:44 at commit `945baa5`, dirty=0. No C2/R build on C0b points exists before 19:55: scratch files from 19:00-19:56 are only staged inputs, raw C0b points, two PNGs of them, and the cleaned files (19:51-19:54, inputs only). **Pass.** Exception: the dev smoke build, see N3. |
| 2 | PREREG before scoring | same | Pick + mesh + fidelity table `8d53a60` committed 21:20:55, pushed 21:20:57. Scoring started 21:21:04 (NOTES). Guard runs 21:22:44-21:24:05. **Pass.** |
| 3 | PREREG unchanged after commit | `git diff 01c25d2 HEAD -- PREREG.md` | Only section 11 (A1) was appended. Sections 1-10 are byte-identical. **Pass.** |
| 4 | Code used = code pre-registered | `git diff 01c25d2 945baa5` / `945baa5 HEAD` on `scripts/`, `prim_rack.py`, `obs_fidelity.py`, `mesh_metric.py`, C0b jobs | `prim_rack.py`, `obs_fidelity.py`, `mesh_metric.py` and the C0b jobs are unchanged from `01c25d2` to HEAD. `c2r_build.sh` gained only the `C2R_EPS`/`C2R_SETS` dry-run overrides (unset in the real run: the log has no DRY line). `clean_pts.py` was added with A1. Nothing changed after `945baa5`. **Pass.** |
| 5 | Regression of the new options | md5 of `SCR/cdo_c2r/regress/{orig,mod}` | joint_joint 8fdf2444 = 8fdf2444, joint_joint_nomk 5bfa2509 = 5bfa2509. **Pass**, with the scope caveat in N4. |
| 6 | Inputs | sha256 against C0b's box `SHA256SUMS` and committed files | The 5 raw pass-B rack npz match C0b `results/box/SHA256SUMS`. `params.json` (T = 0.0045594 m, `t0_C0b (n=3)`) and the 5 marker JSONs match C0b's committed `results/box` copies. The staged cleaned files match `results/inputs_STAGED.json`. **Pass.** |
| 7 | A1 cleaning reproduces | re-ran committed `clean_pts.py` on the raw files (`SCR/cdo_c2r_verify/clean`), compared every array | All 5 episodes are array-identical to `inA1` (pts, cam, frame, lo, hi, vox, hits, free, args; same `clean` record). Kept 0.988 / 0.996 / 0.6378 / 0.5096 / 0.654. **Pass.** |
| 8 | Cleaning removed no rack | GT-free: raw points within 10 mm of a rack mesh that `clean_pts` dropped | Reference = the pick: 0 of 2.53 / 2.27 / 0.55 / 3.07 / 3.79 M near points dropped (12/13/26/27/31). Kept points > 30 mm from the pick: 0 / 0 / 11.1 / 0 / 0 % (ep26's attached cluster, as A1 says). Reference = the C0 mesh (built independently on `obs_all`): see N11. **Pass.** |
| 9 | Constants | section 2 below | All are traced to C0b AUDIT / REPLACEMENTS or declared in the PREREG as new generic bounds. None is scan-derived or U without a C0b decision. **Pass**, with notes N5-N7. |
| 10 | Pick recomputed | (a) re-applied PREREG 5 to `results/fidelity_table.jsonl`; (b) recomputed `obs_fidelity.py`'s formula unrounded for 5 meshes (`SCR/cdo_c2r_verify/fid_full.jsonl`) | (a) 96 rows, 12 per set. Ineligible: exactly `EKQ__joint_joint` and `Q__ep31_full` (not watertight). Order: K/ep12_nomk 5.483 < EK/ep12_nomk 5.485 = EKQ/joint_joint_nomk 5.485 < ... Best base: base/ep12_nomk 5.533. The gate passes: the pick is not from the base run. (b) K/ep12_nomk 5.483385, base/ep12_nomk 5.533145, EK/ep12_nomk 5.485203, EKQ/joint_joint_nomk 5.485133, C0 mesh 5.535799. These equal the committed 3-decimal values, so obs_fidelity is deterministic here. The committed `selection.json` and table are byte-identical to `runA1`'s. Re-running C0b's `c0b_check.py` on the committed pick gives watertight, 1 body, 1836 faces / 920 vertices, budget unchanged, eligible. **Pass**, see N1. |
| 11 | One scoring | grep of every `*.jsonl` in the repo and the scratchpad for the sha1 and for `c2r` labels | Sha1 `7f4eab701769d264` appears only in `results/score.jsonl` (1 record, 7 seeds, 67.9 s) and in the fidelity table. No other C2/R mesh has a score record. The scratch `candidates.jsonl` files hold no CD-O / ADD fields. **Pass.** |
| 12 | WIN gate | recomputed from `score.jsonl` | cdo_eval = mean of the 5 eval seeds (0.4398, 0.4365, 0.4424, 0.4446, 0.4432) = 0.4413 > 0.45604 - 0.02 = 0.43604: **FAIL**. add_med = median of the 7 seeds = 6.56 <= 5.79 + 2 = 7.79: pass. flips_all 0: pass. Baselines re-read [D]: C0 `clean/rack/t2.5_lean1/all_joint` sha1 b855279b68ecb432 = the shipped `plastic_dish_rack_joint_v2.glb`, cdo_eval 0.45604. library_v3 c737056fcb749935, add_med 5.79. Same 7 seeds in all three records. Differences: -0.01474 vs C0, -0.11376 vs library_v3. Board effect [E]: 5 x -0.01474 / 36 = -0.0020. **Confirmed: no WIN.** |
| 13 | AUC guard | (a) diff of the runner and verdict against C0's; (b) C0's original `guard_eval.py` on the committed run JSONs; (c) sha256 of the base JSONs | (a) The runner changes only the mesh dir, the output dir and the object list (`cd` into `cdo_c2r`; all paths absolute). The verdict differs only in OTW (rack only) and in the removed joint report; RULE and EPS are identical. (b) rack: mean dAUC +0.0147, min -0.0076 (ep12), mean dMPPE -0.08550, mean dRPE -0.03806, 5/5 twins, adopted=True: **PASS**, identical to `guard_result_c2r.json`. (c) The 5 committed base JSONs are byte-identical to C0's committed `C0/auc/base/ep*.json` and to `SCR/cdo_c0/runs/base`. The log shows no base re-run; reuse checks (base meshes 10/10, tracks 15, score_registered 6a4cd60a0d26e3f8, kit b4b99f698eb4893a, 25 staged inputs) are all true in `guard_inputs.json`. The single JSONs in scratch = committed copies. C0's rack guard +0.0158 / -0.0092 re-read from `C0/guard_result.json`. **Confirmed.** |
| 14 | Mesh bytes = scored bytes | sha256 / sha1 | Committed glb, `8d53a60` blob, `runA1/cand/K/.../ep12_nomk.glb`, the guard's `SCR/cdo_c2r/single/plastic_dish_rack/plastic_dish_rack.glb`: all sha256 `92d9fed0...3966`. The sha1 `7f4eab70...` equals `score.jsonl` `sha` (its `path` is the committed file). Committed build JSON = `runA1/cand/K/plastic_dish_rack/ep12.json` byte for byte. **Pass.** |
| 15 | Frame not aligned to library_v3 | code read + scorer rotations | `prim_rack.py` reads only obs npz files and marker JSONs. Its only ICP aligns episodes' observed points to each other for the joint fit. The pick is a per-episode ep12 fit (no ICP) in the observations' track frame. Per-seed scorer rotation: pick 2.39-3.57 deg, C0 rack 2.10-3.29 deg, library_v3 0.37-1.75 deg. So the pick sits in C0's frame family, not in library_v3's. **Pass**, inherited caveat N8. |
| 16 | Cost and box | ledger (`ledger.py show`) | `planned $0.50` 19:35Z, `actual $0.02` 19:56Z. I could not confirm the instance is gone, see N9. |
| 17 | Commit hygiene | file sizes, secret / model-name grep | Track folder 964 KB, largest file 60 KB. No key or token patterns. No model names, apart from the scratch path string `/tmp/claude-0/...`. **Pass.** |

## 2. Constants used by the pick (K/ep12_nomk) and the A1 inputs, against C0b AUDIT / REPLACEMENTS

| Constant | Value in the pick | AUDIT id, C0b class | Status |
|---|---|---|---|
| Wall / floor T | 4.5594 mm | 62 TH: thickness.py if >= 200 measurements, else t0_C0b. Rack: 3 measurements, so t0_C0b = 4.5594 mm (C0b `t0_c0b.json`) | ok |
| Lip lower bound S0_MIN = T; s1 >= 0 | s0 = T (at bound), s1 = 0 (at bound) | 87 TH (`--s0_min_t`; s1 bounds kept) | ok (both at their bounds, reported) |
| PRIM_CUP_LEAN=1; cup bounds; cup point classes / region / floor | lean on | 76 O; 89, 88, 90, 91 KEEP (T terms = C0b T) | ok |
| Peg kappa init | 1.0 | 69 KEEP (PEG_KAPPA) | ok |
| Peg kappa bounds | [0.5, 3.0] | new; PREREG section 3, "generic search bounds", committed before builds | ok; never binding (all 96 meshes: 0.956-1.776). See N6. |
| Floor placement rule | depth from all episodes' cuts, T terms = C0b T | 96 O | ok |
| PEG_SLICE, PEG_R, F_SCALE, outline init / classes, lip sampling, detect_pegs, fit_peg_row, gates | unchanged | 66, 67, 65, 84, 85, 83, 92, 93, 97 KEEP | ok |
| JOINT_TOL | 1.25 | 78 KEEP | ok (joint membership only) |
| Markers | none (nomk) | 71-73, 99, 101 MK | not used by the pick |
| Observed points | C0b pass-B, cube ROI 0.30 m, own co-object points | 133, 134 LIB; 135, 138, 140 KEEP; 142 A6 | ok |
| A1 link / voxel | 12 mm / 4 mm | 135 KEEP ("3 vote voxels") / 142 A6 | ok |
| Fidelity selector and numerics | sum of trimmed means, trim 0.9, 300 k / 200 k, seed 0 | 155 RULE (pre-registered for every object); 152-154 G | ok |
| Kit budget | 4096 / 4096 | 163 G | ok |
| Options not in the pick (reported) | E: s1e bounds [0, 1.5], init 0.3 (87 / 84). Q: G 2.5 /m, 8 frusta | 87 TH / 84 KEEP; Q: new, derived from 89 KEEP and a 0.1 m tube | see N5, N7 |

## 3. Findings

### Blocking
None.

### Non-blocking (corrections and caveats)

- **N1 (correction to the hypothesis verdict).** The fidelity prediction ">= 0.05 mm over the base pick" holds only on
  the 3-decimal values: 5.533 - 5.483 = 0.050. Unrounded it is 5.533145 - 5.483385 = **0.0498 mm**, just below the
  threshold. The prediction was reported only, so no decision changes. "Holds at exactly 0.050" should read "0.050 at
  printed precision, 0.0498 unrounded". The whole new-part effect is about 1 % of the fidelity sum, and the margin of the
  pick over EK/ep12_nomk and EKQ/joint_joint_nomk is 0.0018 mm.
- **N2 (correction to the failures list).** The box destroy time is inconsistent. The ledger `actual` line is stamped
  19:56Z and says "destroyed by agent 19:58Z". NOTES line 19:56:56 says "empty log at 19:57; destroyed 19:58". RESULTS
  and the result say "~19:56". This session has no `VAST_API_KEY`, so I could not run `ops/vast.sh show` to confirm the
  instance is gone. The orchestrator should confirm once (N9).
- **N3 (pre-PREREG dev build).** The disclosed smoke build (all three options on dev `obs_all` 12/13/27, T 5 mm)
  finished at 18:48:47, 45 s before the PREREG commit. Its fitted values (s1e 0.122, kappa 1.42 / 1.58, gx 0.48,
  gy -1.07) were in the PREREG. Git cannot show that the section 9 predictions were written before that result: no
  earlier snapshot holds PREREG.md, and the NOTES line "PREREG drafted" (18:48:10) is the only record. The thresholds
  do not look fitted to the smoke values: the E prediction (s1e >= 0.2) already failed on them. The predictions are
  reported only. A residual diagnostic of the smoke mesh (`SCR/cdo_c2r/smoke/diag`, 18:50:45) ran after the commit and
  is not mentioned anywhere. It is GT-free, dev-only and affects nothing.
- **N4 (regression scope).** The byte-identity regression ran on C0's path only (`joint`, `PRIM_T_WALL`, no
  `--markers_dir` / `--s0_min_t`). The builds use C0b's `run` path with gmg markers, and that path was not
  regression-tested. I read the whole `01c25d2` diff instead. Every change is gated by the new flags, or by keys only
  those flags create (`'s1e' in o`, `'gx' in cup`, `C2R_USED`). The one ungated edit, the `yc` slice
  `qq[nk+4+K:nk+4+2K]`, equals the old `qq[nk+4+K:]` when kappa is not fitted. So the base run equals C0b's code by
  inspection [M], not by a run.
- **N5 (S-input in the design, disclosed).** The options were chosen from diagnostics on `obs_all`. Those points carry
  library_v3's ROI and co-object carving, which C0b classes S-input (AUDIT 133 / 134). Q's bound 2.5 /m uses "0.1 m,
  the order of C0's cup-top 105 mm", measured on those points. No constant of the pick comes from them. Q is not in the
  pick, and the own cleaned points give a cup top of the same order (ep12 106.8 mm, NOTES 20:03). Q's bound binds on
  ep26 (gx = -2.5 /m, the attached clutter cluster), which is not the pick.
- **N6 (new bound).** PEG_KAPPA_B (0.5, 3.0) is new, so it cannot have an AUDIT id. It is documented as generic but
  is asymmetric in log aspect (1:2 vs 3:1) without a stated reason. It never binds. The scan brief's "fins ~2.5 mm"
  would imply an aspect well above 3, so the bound does not encode it.
- **N7 (citation).** PREREG section 3 calls AUDIT ids 84 and 87 "KEEP in C0b". C0b REPLACEMENTS classes 87 as TH: the
  s0 bound is replaced, the s1 bounds [0, 1.5] are kept. The values used are the kept ones, so nothing changes.
- **N8 (inherited frame caveat).** The observed points, and so every prim mesh, are in our tracks' object frame. AUDIT
  id 161 (U, open question F4) records that perception was seeded with our library meshes. This is not an alignment to
  library_v3, but the frame is library-seeded for C0, C0b and C2/R alike.
- **N9 (box).** See N2. I could not run "confirm destroyed" from this session. Cost at risk if it were still alive:
  storage only (the box never started).
- **N10 (reporting).** (a) ADD worsens against both baselines: 6.56 mm vs C0 5.63 and library 5.79; add_max 7.64. It
  is inside the gate, but it is a real cost if a later pack considers this mesh. (b) The CD-O change vs C0 mixes more
  than the result lists: the point source (C0b cube-ROI pass-B vs `obs_all`) and the per-episode ep12 fit vs C0's
  3-episode joint, as well as T, s0 >= T, no balls, A1 and K. (c) The largest guard drop is on ep12, the build
  episode itself (rack AUC 0.9997 -> 0.9665, registration rotation 3.18 deg), which is in-sample. (d) Rounding: mean
  dMPPE -0.0855 (float -0.08549999...) is printed as -0.086 in RESULTS. -0.085 is the correct 3-decimal value; this is
  cosmetic.
- **N11 (cleaning, independent reference).** Against the C0 mesh, A1 dropped no rack point either (section 4).

## 4. Commands (verifier; this VM, nice 10, `OMP_NUM_THREADS` 1-2; code HEAD `73f3cc0`)

```
SCR/cdo_c2r_verify/scripts/reclean.sh            # committed clean_pts.py on SCR/cdo_c2r/c0bpts -> SCR/cdo_c2r_verify/clean
python -I SCR/cdo_c2r_verify/scripts/cmp_clean.py # array comparison with SCR/cdo_c2r/inA1/pts/B
python -I SCR/cdo_c2r_verify/scripts/fid_full.py OBS(5 cleaned) K/ep12_nomk base/ep12_nomk EK/ep12_nomk EKQ/joint_joint_nomk C0 joint_v2
      -> SCR/cdo_c2r_verify/fid_full.jsonl
python -I cdo-sprint/C0/scripts/guard_eval.py C2/R-rack/results/auc SCR/cdo_c2r_verify/guard/c0rule.json
python -I cdo-sprint/C0b/jobs/c0b_check.py SCR/kit/v2d_submission_kit meshes/plastic_dish_rack_c2r_K_ep12_nomk.glb SCR/cdo_c2r_verify/check_pick.json
python -I SCR/cdo_c2r_verify/scripts/dropped_in_box.py <reference mesh>   # pick -> stdout above; C0 mesh -> dropped_c0ref.txt
```

Cleaning check against the C0 mesh, a reference independent of the cleaned points [M]:
- `clean_pts` dropped 0 of the 2.54 / 2.28 / 0.56 / 3.09 / 3.74 M raw points within 10 mm of the C0 mesh (episodes
  12 / 13 / 26 / 27 / 31).
- Kept points more than 30 mm from the C0 mesh: 0 / 0 / 10.4 / 0 / 0 %.
- So A1 removed no rack surface in any episode. Its only residue is ep26's attached cluster. In the pooled fidelity
  set that cluster is about 0.6 % of the points, inside the trimmed 10 % tail [E].
