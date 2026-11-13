# C1 / T1 beige-cup lathe: adversarial verification (2026-10-31)

The verifier is a separate agent; it did not build T1. Scratch: `SCR/cdo_c1/t1_verify/`, where
`SCR = /tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`.
The step log is in the `VERIFY` lines of `NOTES.md`.

Labels: [D] = public scan or mocap used as a stand-in, after inference; [M] = measured without ground truth;
[E] = estimate; [H] = hypothesis.

## Verdict
**Confirmed. No blocking item.**

- Every number in the T1 result traces to a file, and the gates and the AUC guard were applied as the brief writes
  them.
- Two independent re-runs gave identical results:
  - the GT-free build chain (census, then mask, then lathe) reproduced the scored mesh **byte for byte**;
  - the ep11 `single` AUC run reproduced every number.
- Non-blocking items, listed below:
  - an inherited provenance caveat that applies equally to the adopted blue-cup lathe, and is not flagged in T1;
  - the eval-8 frame question, which is still open [H];
  - three wording or record nits.

## What was checked, and how

| # | Check | Method | Result |
|---|---|---|---|
| 1 | PREREG pushed before any scan or mocap output | origin reflog, commit times, file mtimes, scan and cache atimes | **pass**: see the timeline below |
| 2 | Construction and choice GT-free | grep of every construction script for scan, mocap, parquet, align and pose reads; their inputs | **pass** (direct reads); inherited caveat N1 |
| 3 | Scored mesh is byte-identical everywhere | sha256 and sha1 | **pass** |
| 4 | Construction reproduces | own re-run of `frame_census.py`, `mask_obs.py sep` and `lathe_obs.py` | **pass**: byte-identical |
| 5 | Only one mesh scored; variants never scored | sha1[:16] search of the repo and the scratchpad | **pass** |
| 6 | CD-O gate as written | recomputed from `score_t1.jsonl` and `baseline_library.jsonl` | **pass**: WIN on both pairs |
| 7 | AUC guard ran on the intended mesh dirs | per-file sha256 of `base/` and `single/`, the json `meshes` field, `score_registered.py` lookup code | **pass** |
| 8 | AUC guard rule as written | recomputed deltas | **pass** |
| 9 | One AUC run re-executed | own `single` dir rebuilt from the git copies, then the same command | **pass**: identical |
| 10 | Claims behind the mask and the pack | own GT-free recompute; `pack_check.py` re-run | **pass** (record nit N3) |

### 1. Timeline (UTC, 31 Oct)
| Time | Event | Source |
|---|---|---|
| 15:29:58 | M_all (no mask) built | build mtime |
| 15:32:07-15:32:39 | masks and M_sep / M_sephf built | build mtimes |
| 15:35:08-15:35:13 | **all ten** public scan glbs read in alphabetical order | atime |
| 15:37:23 | `obs_fidelity.txt` written | mtime |
| 15:42:20 | PREREG commit `4c757ea` | git |
| **15:42:23** | `4c757ea` pushed | origin reflog: "update by push" |
| 15:42:35 | scoring starts | `score_t1.log` mtime 15:54:53 minus 738.1 s |
| 15:42:46 | `interact/v5/metric/cache/beige_cup_b4096.npz` read | atime |
| 15:57:11 / 15:58:40 | AUC base / single outputs | mtimes |
| 15:59:31 / 16:00:16 | results pushed (`c6cbc9e`, `9f35c0d`) | origin reflog |

- The 15:35:08 scan reads are C0 stage 0, which hashes the ten scans (`C0/NOTES.md` 15:35:25Z, "10 scans ...
  inputs_sha256"). T1 does not read all ten scans.
- The disk is mounted `relatime`, so the 15:42:46 atime marks the **first** read of mesh_metric's beige scan cache in
  24 h. That read is T1's scoring, after the push.
- So no mesh_metric beige scoring ran before the PREREG push. This is positive evidence, not just absence.

### 2. GT-free construction
The following were searched for `scan|mocap|parquet|align|observation|pose` reads:
`frame_census.py`, `mask_obs.py`, `lathe_obs.py`, `obs_points.py`, `obs_fidelity.py` and `prep_obs.sh`.
- None reads a scan, mocap, a parquet pose or an `*_align.npz`.
- Their inputs are:
  - our sweep track `ep11/poses.npz` (sha256 `99d845e3...8f75`);
  - G1 hands (`04e8ed23...bff9`);
  - FoundationStereo depth and the calibration;
  - library meshes (ROI box, `--others`, census geometry).
- `pack_check.py` reads only our own submitted CD-O parquets.

### 3 and 4. Byte identity and reproduction
- sha256 `60e398b0f8006c6608e40b1988047aa89e35533e8bb85906c36cf9f9f8370078` is the same for:
  - the git file at `4c757ea` and at HEAD (it is the only commit that touches `meshes/`);
  - `SCR/cdo_c1/t1/build/ep11_beige_cup_sep_g1.glb`;
  - `SCR/cdo_c1/t1/auc/single/beige_cup.glb`.
- Its sha1[:16] is `46b06543747faf02`, which is the `sha` in `score_t1.jsonl` and its record `path` is the git file.
- Re-run 16:45:44 to 16:46:01Z (`SCR/cdo_c1/t1_verify/rebuild/run.log`):
  - `census.json` is byte-identical (`deaf0ebf...c63d`);
  - `mask_obs sep` keeps census frames 0..63 and 507,014 of 534,088 points;
  - `lathe_obs.py` at its defaults gives sha256 **`60e398b0...0078`**, identical. The `lathe.log` line is identical too
    (rotcons 3.009 mm, t 3.151 mm, height 162.09 mm, 36,260 faces).
- The claim that the defaults are the blue-cup g1 settings also holds:
  - `repro/ep21_blue_cup_defaults.glb` = `lathe/ep21_blue_cup_g1.glb` = `C0/meshes/ep21_blue_cup_g1.glb`;
  - all three are sha256 `81a201cb...29f1`.

### 5. One scoring
- `score_t1.jsonl` has one record.
- The sha1[:16] of the unscored variants were searched for in all repo and scratch results and appear nowhere:
  - M_all: `9149011e29a8ea99`;
  - M_sephf: `8765dfdcd412ce70`.
- `score_t1.py` refuses to score a sha twice.

### 6. CD-O gate, recomputed [D]
| Pair | Lathe at the eval seed | Threshold as briefed | Per-seed baseline (secondary) |
|---|---|---|---|
| eval 10 (library_v3 packed) | 0.2475 | 0.856 - 0.02 = 0.836 (`cdo_eval` 0.85625) | 0.8705 - 0.02 |
| eval 8 (library_v3x packed) | 0.2549 | 0.730 - 0.02 = 0.710 (`cdo_eval` 0.72995) | 0.7251 - 0.02 |

- **add_med:** the median of the 6 seeds the baseline record uses (eval seeds plus 11, 22, 33, 44).
  - Values: 5.76, 5.79, 5.90, 5.64, 5.60, 5.51, so the median is **5.70 mm**.
  - Thresholds: <= 6.97 + 2.0, and also <= 5.51 + 2.0 against v3x.
  - The 32-seed median is 5.75.
- **Flips:** symmetry-aware; 0 of 32 (beige cup axial, as the kit declares). Largest error 3.54 deg.
  - Seeds 1006 and 1025 have raw rotations of 87 and 57 deg, which are spins about the axis.
- **WIN on both pairs.** The margins are large: about 0.59 and 0.46 cm below the thresholds.
- **Board estimate** [E, public-scan proxy]: (0.6085 + 0.4751) / 36 = **0.0301**, or 0.0304 with per-seed baselines.
  The 0.030 figure is correct.

### 7 to 9. AUC guard [D]
**Mesh dirs:**
- The per-file sha256 of `SCR/cdo_c1/t1/auc/{base,single}` matches `results/auc/inputs_sha256.txt`.
- `base` = `meshes/library_v3` file for file. The spoon is absent, and it is not in ep11.
- `single` differs only in `beige_cup.glb` = `60e398b0...`.
- No `episode_000011/` subdir exists, so `score_registered.py` takes `DIR/<obj>.glb`.

**No silent fallback:**
- The current `score_registered.py` (last change `46b8389`, 25 Oct) falls back to the scan only when `--meshes` is
  absent.
- With `--meshes`, a missing mesh raises `SystemExit`. Both jsons name the intended dir in `meshes`.

**Other inputs:**
- `t3/ep11.parquet` is sha256 `3117f30e...741f`, equal to C0's.
- `t3/mesh` scans: beige `63666c81...dc50`, blue `c8d97225...ae4c`, both equal to C0's.
- Track: `world_T_cam @ cam_T_obj` recomputed from the sweep poses matches T1's npz and C0's to 1.1e-16. Both
  objects, 137 frames.

**Rule, recomputed:**
- dAUC = 0.9058 - 0.8978 = **+0.0080** (one twin, so mean = min).
- dMPPE = **-0.0638 cm**; dRPE = **-0.0436 cm**.
- **PASS.**
- ep11 is the only public episode containing the beige cup (of the 20 sweep episodes, only ep11 has `cam_T_beige_cup`).

**Cross-checks:**
- T1's base equals C0's `base/ep11.json` in both perception and registration.
- **My re-run of `single`** (16:46:50 to 16:48:03Z; dir rebuilt from the git copies, sha-equal to T1's;
  `SCR/cdo_c1/t1_verify/auc/single_ep11_rerun.json`) gives the same numbers:
  - AUC 0.9058, MPPE 1.5737, RPE 1.6954, beige per-object AUC 0.9494;
  - beige registration 4.04 deg / 0.47 cm.
  - All identical.

### 10. Claims behind the mask and the pack
**Mask evidence** (GT-free; `code/nest_check.py`, M_all axis, body points r < 51 mm):
- 0.5 % height percentile: -98.6 mm (t 0-12), -97.4 mm (t 14-66) and -129.1 mm (t >= 68).
- 5,891 points lie below -112 mm: 5,864 from t >= 68, and the other 27 all from t 44.
- This reproduces the NOTES and PREREG numbers exactly.
- The census boundary is sharp: near_blue_frac is 0.381 at t 62, 0.459 at t 63 and 0.572 at t 64. A threshold
  anywhere in 0.39-0.57 gives the same point set.

**Pack check** (re-run on packs 3 and 4):
- eval 10 beige rows = `budget_mesh(library_v3)` (0.000 mm);
- eval 8 beige rows = `budget_mesh(library_v3x)` (0.000 mm).
- Conclusion reproduced.

## Non-blocking findings

**N1. Inherited provenance, not flagged in T1.** This applies equally to the adopted blue-cup lathe (C0). T1 meets
the brief's integrity rule as written, but its inputs are on the project's own P1 / deny list:
- `gmg/evidence.md` sections 4-5 say:
  - library v1-v4: tracks templated on the scans, scans as `--others`;
  - public sweep tracks are FoundationPose-templated on library_v2;
  - obs ROI and `--others` = library_v3; hands = G1 refs (P1).
- The C0b constant audit (in progress, `C0b/NOTES.md` 16:45:02Z item 2) reports that `lathe_obs.py`'s floor rule and
  axis TIE were built in a scan-scored loop on 26 Oct.
- As far as the record shows, no beige-specific scan quantity enters the build:
  - README section 1's lathe table lists only the blue cup and the pot;
  - the beige cup was skipped in the observation round (the ep11 G1 track is wrong at frame 0).
- Owner decision O1 (compliance) is open. If the owner adopts C0b's scan-free standard, this candidate needs the same
  re-track and constants audit as the blue cup before it counts as scan-free.
- The orchestrator should carry this flag into MANIFEST and STATUS together with the disclosed scan-extents read
  (PREREG section 8).

**N2. Eval-8 frame: still open [H].**
- Eval 8's rollouts were tracked with v3x; the guard tested only a v3-family track.
- GT-free trimmed ICP (`SCR/cdo_c1/t1_verify/frame_icp.txt`, `code/frame_icp.py`) [M]:
  - lathe to v3x: 2.39 mm / 5.2 deg;
  - v3x to v3: 2.48 mm / 5.1 deg;
  - lathe to v3: 2.58 mm / 8.8 deg.
  - These are ICP fits between different shapes, so they are noisy. The lathe sits about as close to v3x as v3 does.
- Hypothesis: the eval-8 swap behaves like the ep11 twin (dAUC about +0.008). It is falsified if a v3x-frame proxy loses
  AUC.
- Cheap proxy: one ep11 run with beige = library_v3x on the same track, compared with `base`. It tests whether v3x's
  frame costs AUC against v3's.
- If the risk is not wanted, pack the lathe on eval 10 first, which the guard covers.

**N3. `results/pack_check.txt` is filtered output.**
- The committed `pack_check.py` also prints `_1` rows. These are the CD-O parquet's face-index rows, with meaningless
  distances of about 3.5e6 mm.
- The committed txt omits them. The conclusion is unaffected, but the file is not the raw output of the committed
  script.

**N4. Wording nits.**
- NOTES says "64 frames t0..62(even)". The mask keeps census frames 0..63 (64 frames), and the points come from the 32
  even frames 0..62. PREREG has this right.
- PREREG section 2 says M_sep was declared "before any variant was built".
  - The no-mask M_all was built first (15:29:58), and its 191 mm height motivated the mask.
  - The declaration did precede the M_sep and M_sephf builds (15:32:07) and `obs_fidelity` (15:37:23). Everything was
    GT-free, so this is wording only.

**N5. Not measured** (stated by T1, confirmed open):
- the joint ep11 effect with C0's blue-cup lathe.
  - C0's `single_blue_cup` on ep11 already moves the beige per-object AUC (0.9334 to 0.9361) through the shared
    frame-0 scene alignment, with dRPE +0.214 cm.
  - This matters only if the blue cup is packed; it is held back in pack 9a.
- whether the mask mattered (M_all and M_sephf are unscored).

**N6. STATUS.md and `docs/work-log.md` were not updated by T1**, as the brief required. The orchestrator should add
the entries.

**Not a problem:** README line 148 says the ep11 track is wrong at frame 0.
- That is the G1 track; T1 used the sweep track.
- On the sweep track, the t 0-12 points agree with the hand-held frames (0.5 % height percentiles -98.6 against
  -97.4 mm) [M].

## Verifier's own scan reads (disclosure)
- One `score_registered.py` run (ep11 `single`, re-execution of an existing run). It reads the public scans and the
  ep11 parquet. It was for verification only, and nothing was chosen from it.
- Everything else I ran is GT-free: the rebuild chain, `pack_check.py`, ICP, `nest_check.py`, hashing and
  timestamps.
- No mesh was scored. Cost: CPU only, $0.
