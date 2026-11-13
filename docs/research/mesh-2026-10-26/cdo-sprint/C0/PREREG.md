# C0 AUC guard: pre-registration

Written 2026-10-31 ~15:40 UTC, before any scoring of this test. Up to this commit nothing in this sprint has read
ground truth. No mocap or parquet pose has been read, no public scan has been opened, and no CD-O scoring has been
run. The only inputs were our meshes, our perception tracks (sweep `poses.npz`), the kit roster, and existing score
records written on 26-27 Oct.

## 1. What C0 is
C0 changes the **packed** mesh of four objects in the current submission (pack 7). The simulator copies and the
rollouts stay unchanged. The other 19 eval pairs, the spoon among them, keep their pack-7 mesh. Pair list:
`roster.json`. Pair-to-mesh mapping: `MANIFEST.json`.

| Object (eval pairs) | C0 mesh (repo path) | sha256 (first 16) | Public [D] CD-O cm / ADD mm / flips, library_v3 → C0 | Score record |
|---|---|---|---|---|
| white_pot (6) | `results/prim/meshes/white_pot_ep41_fit.glb` | 355ad72e397e1080 | 0.4371 / 6.67 / 0 → 0.3417 / 3.05 / 0 | `results/prim/potlid/metric_all.jsonl` `potlid/fit/ep41` |
| white_pot_lid (1) | `results/prim/meshes/white_pot_lid_ep2_fit_v2.glb` | 0bac47f4b86e9ae3 | 0.4211 / 8.12 / 0 → 0.2199 / 4.46 / 0 | `results/prim/clean/lid_scores.jsonl` `clean/lid/t2.5_fit` |
| plastic_dish_rack (5) | `results/prim/meshes/plastic_dish_rack_joint_v2.glb` | c22f504ccb885541 | 0.5551 / 5.99 / 0 → 0.4560 / 5.37 / 0 | `results/prim/clean/rack_scores.jsonl` `clean/rack/t2.5_lean1/all_joint` |
| blue_cup (5) | `cdo-sprint/C0/meshes/ep21_blue_cup_g1.glb` | 81a201cb23325161 | 0.5233 / 9.97 / 0 → 0.2906 / 4.09 / 0 | `results/lathe_obs.jsonl` `lathe_obs_g/a1/ep21/blue_cup` |

- Each file is matched to its score record by the record's `sha` field: sha1[:16] of the file, as computed by
  `scripts/mesh_metric.py`.
- The original build files in the scratchpad still have the same hashes.
- Repo paths are relative to `docs/research/mesh-2026-10-26/`.

Flags carried from the source records:
- **Lid, T_LID 2.5 mm:** this is the value that leaked from the scans into the first brief. It is kept as the midpoint
  of the pre-registered clean-up grid, and all of 1.5, 2.5 and 4.0 mm passed (worst 0.224 / 5.06).
- **Rack, T_WALL 2.5 mm:** the same kind of leak, and the same clean-up result (worst 0.458 / 6.23). The leaning cup
  holder is the GT-free fidelity choice.
- **Blue cup selector:** `obs_fidelity.py` was written after the five blue-cup lathes had already been scored (work
  log 26 Oct, ~16:40). The pick is GT-free, but the selector was not pre-registered.
- **Blue cup after budget:** after the kit's `budget_mesh` the blue-cup mesh is not watertight (11 bodies). The
  library mesh is not watertight either, and the kit never checks watertightness.

## 2. Why a guard
The submitted mesh also sets the kit's registration of the scan to our mesh. That registration fixes the body frames
of the pose boards (AUC, SP-SR, MP-SR, RPE, MPPE). On 26 Oct, swapping the pitcher for a single twin cost -0.0045
AUC on the board. So a CD-O gain can cost pose score. The test below measures that cost on public twins.

## 3. Frozen inputs (hashes at this commit)

**Mesh directories** (scratchpad `cdo_c0/`):
- `base/` holds the 10 public objects from `meshes/library_v3`.
- `c0/` is base plus the 4 swaps.
- `single/<o>/` is base plus that one swap.
- Every file is listed with its sha256 in `inputs/mesh_dirs_sha256.json`. `c0` differs from `base` in exactly the 4
  swapped files, and each `single/<o>` in exactly one.

**Perception tracks:** scratchpad `cdo_c0/tracks/ep<e>/poses_world_vo.npz`.
- Converted from `data/sweep/ep<e>/poses.npz` with `world_T_obj[t] = world_T_cam[t] @ cam_T_obj[t]`, the recipe of
  `pipeline/perc2.py:495`.
- These are our own inference outputs. Source and output sha256: `inputs/tracks.json`.

**Code and kit:**

| File | sha256 (first 16) |
|---|---|
| `pipeline/score_registered.py` (last changed in 46b8389) | 6a4cd60a0d26e3f8 |
| `scripts/run_auc_guard.sh` | 9ffb498e43102194 |
| `scripts/guard_eval.py` | ba34dcc3fe33f3d9 |
| kit `v2dlb/track3_pose.py` | b4b99f698eb4893a |
| kit `v2dlb/mesh_budget.py` | 8f29481d52a82c46 |

**Ground truth for scoring only:**
- public parquets of the 15 twins from HF `nvidia/video_to_data_challenge`, `track_3/public/data/chunk-000/`;
- the public scans in scratchpad `data/scan/`, the same files the [D] CD-O numbers used.

Both are staged by stage 0 of the runner, after this commit, and their hashes are written to
`cdo_c0/runs/inputs_sha256.txt`.

## 4. Twins and runs
Twins are public episodes, scored with the sweep's perception tracks.

| Object | Twins |
|---|---|
| white_pot | {0, 2, 26, 27, 41, 42, 43, 44, 45} |
| white_pot_lid | {0, 2} |
| plastic_dish_rack | {12, 13, 26, 27, 31} |
| blue_cup | {11, 12, 13, 21, 22} |

Runs (51 in total):
- `base` and `c0` on all 15 episodes;
- `single/<o>` on the twins of o: pot 9, lid 2, rack 5, blue cup 5.

Each run is one `score_registered.py` call. Registration seeds are fixed by the script (`1_000_003*ep + 101*slot`), so
base and swap runs differ only in the mesh file.

## 5. Rule (exactly as briefed)

**Metrics.** Each run reports the `perception` entry of its JSON. This is the episode-level registered score over all
of the episode's objects, as the board scores an episode. Per-object AUC is reported as well.

**Adoption rule.**
- dAUC_e = AUC(single swap o) - AUC(base), for each twin e. dMPPE_e and dRPE_e are defined the same way, in cm.
- Object o is **ADOPTED** iff all of these hold over o's twins:
  - mean dAUC >= -0.005;
  - min dAUC >= -0.02;
  - mean dMPPE <= +0.2 cm;
  - mean dRPE <= +0.2 cm.
- **C0-final** = the adopted objects. There is no other selection.
- Joint `c0` deltas over all 15 twins are reported, not used to select. SP-SR and MP-SR are reported.

**Run policy.** Each run is executed once. Failures are reported, not retried with changed settings. A crash may be
re-run unchanged: the runner skips runs whose JSON exists.

Two completions of the rule, fixed here before any result:
- **Missing data:** if a base or single run for one of o's twins still has no result after one unchanged re-run, o is
  **not adopted**, and the failure is reported.
- **Float handling:** the inputs are the 4-decimal values `score_registered.py` writes. Deltas are compared unrounded,
  with a 1e-9 tolerance for float representation. A value exactly at a threshold passes.

## 6. Exact commands (stage 2; CPU, $0)
```
cd /home/user/v2d-track3
bash docs/research/mesh-2026-10-26/cdo-sprint/C0/scripts/run_auc_guard.sh stage0
nohup bash docs/research/mesh-2026-10-26/cdo-sprint/C0/scripts/run_auc_guard.sh runs \
  > /tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/cdo_c0/logs/runs.log 2>&1 &
# when "RUNS done" is logged (a usage-limit kill is resumed by re-running the same command unchanged):
/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/venv/bin/python -I \
  docs/research/mesh-2026-10-26/cdo-sprint/C0/scripts/guard_eval.py \
  /tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/cdo_c0/runs \
  docs/research/mesh-2026-10-26/cdo-sprint/C0/guard_result.json
```

The runner runs two streams at nice 5: base and c0 alternating per episode, and the singles. The per-run call is:
```
python -I pipeline/score_registered.py EP cdo_c0/tracks/epEP/poses_world_vo.npz --meshes cdo_c0/<cfg> \
  --t3 cdo_c0/t3 --kit kit/v2d_submission_kit --out cdo_c0/runs/<cfg>/epEP.json
```
- `cfg` is one of `base`, `c0`, `single/<o>`.
- The output tag replaces `/` with `_`.
- `t3/` holds `ep<e>.parquet` and `mesh/<obj>/<file>`, symlinked to the staged parquets and `data/scan`.

Time: 51 runs on 4 shared cores, about 0.5-2 h [E, not timed; a timing run would read ground truth].

## 7. What is reported
- Per object:
  - the per-twin dAUC, dMPPE, dRPE, dSP-SR and dMP-SR;
  - per-object AUC and registration (rotation, anchor shift) for base and swap;
  - mean and min;
  - the verdict.
- The joint c0 deltas.
- Failures.
- The CD-O estimate for C0-final from `cdo_estimate.json` (`adopted_subsets_cm`, or recomputed with the same
  arithmetic for other subsets) [E].

## 8. Integrity
- No mesh, threshold or twin set is changed after this commit.
- No new CD-O scoring is run.
- Scan and mocap are read only by `score_registered.py` in stage 2.
- Nothing is tuned on these scores.
- The eval-pair decision uses only this rule.

**Known caveats** (stated before the results):
- [D] ep0 and ep11 had failed perception tracks in the G1 diagnostic with library_v2 meshes, on the lid and the beige
  cup respectively (work log 25 Oct 23:50). Whether the sweep tracks used here share those failures is not checked
  (checking would read ground truth). [H] Deltas on those twins may be noisy.
- [H] The board's own AUC change will differ from the twins' change, because the hidden scans, anchor and point
  sampling differ (see the `score_registered.py` docstring).
- The 22 Oct owner decision on per-episode eval meshes and the provenance tier of public-built meshes are owner
  questions. They are not settled by this test.
