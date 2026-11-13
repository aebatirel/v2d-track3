# C1 / T1 beige-cup observed-point lathe: pre-registration

Written 2026-10-31 before any scan, mocap or parquet-pose read for this track. Scratch paths below are relative to
`SCR = /tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`.
Step-by-step log with times: `NOTES.md`.

## 1. Hypothesis
**H-BL [H]:** the method that took the blue cup from 0.523 to 0.291 cm (observed points along our own track of one
public episode, `obs_points.py` then `lathe_obs.py` with the adopted settings) does the same for the beige cup.

**Falsified** unless the lathe is a WIN (section 5) against **both** packed beige baselines:
- eval 10 (packed with library_v3, CD-O 0.856);
- eval 8 (packed with library_v3x, CD-O 0.730).

GT-free prediction, made before scoring [M]: H-BL is likely falsified. On `obs_fidelity.py`, no lathe variant
beats the library meshes (section 4), whereas for the blue cup the lathe did (4.08 against 5.86 mm). That selector is
weak (Spearman about 0.5), so this prediction is not part of the gate.

## 2. Construction (GT-free)
**Inputs:**
- observed points `SCR/obs_all/ep11_beige_cup.npz`, sha256 `7fd1dec0fa7402a26dcf9d34ff937b3ee963396ff9ba8b8f51855ea2b3cd2c94`.
  - Made by `obs_points.py` with its defaults on 27 Oct (`scripts/prep_obs.sh`).
  - Track: our sweep base track `SCR/data/sweep/ep11/poses.npz` (sha256 `99d845e3...8f75`; store run
    `20261025-sweep-a894083`, today's detection rules).
  - Hands: G1 MediaPipe `SCR/data/sweep/ep11/hands.npz` (`04e8ed23...bff9`).
  - Others: `blue_cup=meshes/library_v3/blue_cup.glb`. ROI: `meshes/library_v3/beige_cup.glb`.
- The sweep tracks were made with library_v2 meshes, and library_v2 beige equals library_v3 beige (sha256
  `f7309312...61d5`). So the points, and the lathe, are in the library_v3 beige frame. No placement step is needed.

**Settings.** `lathe_obs.py` defaults, which are exactly the adopted blue-cup lathe's settings.
- Proof: `lathe_obs.py SCR/obs/ep21_blue_cup.npz` with defaults rebuilds `SCR/lathe/ep21_blue_cup_g1.glb`
  byte-identically (sha256 `81a201cb...29f1`).
- Settings used: appendages 1, app_d 4 mm, app_min 400, spheres 0, floor base, vox_ds 1.5 mm, tmin 1.5 mm, gap 3,
  minsec 6, dh 3 mm, min_pts 8, knn 24.
- No size bound exists in these settings; nothing was set from a scan.

**The one setting that does not transfer: nesting.** The blue cup was never nested in ep21. In ep11, the beige cup
sits in the blue cup.
- `lathe_obs.py` has no frame-mask option. The mask is applied by filtering the obs npz on its per-point `frame`
  (`scripts/mask_obs.py`). `lathe_obs.py` reads only `pts` and `cam`, so the two are equivalent.
- The frame rule comes from our own census (`scripts/frame_census.py`, `results/census.json`, sha256
  `deaf0ebf...c63d`). It uses library_v3 meshes along our tracks plus the G1 hand joints.
- **Rule M_sep:** keep frames where fewer than half of the beige-surface samples lie within 12 mm (the method's own
  `other_r`) of the blue-cup surface. This keeps t = 0..62: 32 frames at stride 2 and 507,014 of 534,088 points.
- Hand-held frames are kept, and hands are removed by the method's capsules, as in the adopted blue-cup lathe (which
  kept its hand-held frames).
- Evidence for the mask [M]:
  - The 0.5 % height percentile of the cup's points is -98.6 mm in the separated hand-free frames (t 0-12) and
    -97.4 mm in the hand-held frames.
  - In the nested frames (t >= 68) it is -129.1 mm.
  - All 5,891 points below -112 mm come from nested frames, except 27.
  - So the no-mask lathe's base (-126 mm, height 190.8 mm) is contamination.
- M_sep was declared primary in `NOTES.md` before any variant was built or compared.

**Commands** (cwd `SCR/cdo_c1/t1`, python `SCR/venv/bin/python`, scripts relative to the repo):
```
python -I .../T1-beige-lathe/scripts/frame_census.py SCR/data/sweep/ep11/poses.npz SCR/data/sweep/ep11/hands.npz \
    SCR/obs_all/ep11_beige_cup.npz /home/user/v2d-track3/meshes/library_v3 census.json
python -I .../T1-beige-lathe/scripts/mask_obs.py SCR/obs_all/ep11_beige_cup.npz census.json sep build/ep11_beige_cup_sep.npz
python .../mesh-2026-10-26/scripts/lathe_obs.py build/ep11_beige_cup_sep.npz build/ep11_beige_cup_sep_g1.glb
```
- The masked npz has sha256 `6901cf45...b153`.
- Build output: axis rotational consistency 3.01 mm, wall t 3.15 mm, height 162.1 mm, r_max 40.9 mm.
- The mesh has 1 appendage: a splatted 92 x 104 x 93 mm shell over the 19 % of points that lie more than 4 mm
  outside the outer profile. It has 36,260 faces.

## 3. The scored mesh (exactly one)
| | path | sha256 | sha1[:16] (mesh_metric) |
|---|---|---|---|
| **M_sep** | `docs/.../C1/T1-beige-lathe/meshes/ep11_beige_cup_sep_g1.glb` (= `SCR/cdo_c1/t1/build/ep11_beige_cup_sep_g1.glb`) | `60e398b0f8006c6608e40b1988047aa89e35533e8bb85906c36cf9f9f8370078` | `46b06543747faf02` |

**Built, never scored** (reported GT-free only):

| Variant | sha256 | What it is |
|---|---|---|
| M_all | `970bb39e...d9ae` | no mask; base contaminated |
| M_sephf | `1553541...df32` | t 0-12, separated and hand-free |

## 4. GT-free checks (`results/obs_fidelity.txt`) [M]
`obs_fidelity.py` sum, in mm (lower = explains our points better):

| mesh | on M_sep points | on all points | on t0-12 points |
|---|---|---|---|
| M_sep lathe (scored) | 5.823 | 5.672 | 7.259 |
| M_sephf lathe | 5.814 | 5.625 | 6.984 |
| M_all lathe | 4.139 | 4.787 | 4.805 |
| library_v3 beige | **3.408** | 3.446 | **3.757** |
| library_v3x beige | 3.415 | **3.437** | 4.096 |

The opening tie-break of `fit_axis` is biased by the one-sided view of this episode [M]:
- the camera sees the cup from an elevation of 47-53 deg, within a 31 deg azimuth band, for the whole episode;
- on the M_sep points, the M_all axis is more self-consistent than M_sep's own axis (2.42 against 2.66 mm);
- 19 % of the M_sep points lie more than 4 mm outside the M_sep outer profile.

## 5. Scoring and gates (diagnostic [D])
**One call, once.** It refuses to run if the output already holds this mesh's sha:
```
cd /home/user/v2d-track3 && MESH_SCR=SCR SCR/venv/bin/python docs/research/mesh-2026-10-26/cdo-sprint/C1/T1-beige-lathe/scripts/score_t1.py \
    docs/research/mesh-2026-10-26/cdo-sprint/C1/T1-beige-lathe/meshes/ep11_beige_cup_sep_g1.glb \
    docs/research/mesh-2026-10-26/cdo-sprint/C1/T1-beige-lathe/results/score_t1.jsonl
```
This runs `mesh_metric.evaluate()`: the kit's CD-O and registration on the kit-budgeted scan.
- Seeds: the eval seeds 8000024 (eval 8, slot 0) and 10000131 (eval 10, slot 1).
- Extra seeds (30): 11, 22, 33, 44 (the baseline record's own extras), then 1001-1026.

**CD-O gate, per eval pair** (baselines as briefed):
- eval 10: CD-O at seed 10000131 <= 0.856 - 0.02 = **0.836**;
- eval 8: CD-O at seed 8000024 <= 0.730 - 0.02 = **0.710**.

Each pair also needs:
- **add_med** <= 6.97 + 2.0 = **8.97 mm**, the median ADD over the same 6 seeds as the baseline record (eval
  seeds + 11, 22, 33, 44);
- **0 flips** over all 32 seeds.
  - A flip is a symmetry-aware rotation error over 90 deg. The kit declares the beige cup axially symmetric, so a
    spin about the axis is not a flip; turning upside down is.

A pair is a WIN only if all three hold. H-BL survives only if both pairs are WINs.

**Reported, not gating:**
- per-seed baselines: eval 10 at 0.8705 - 0.02, eval 8 at 0.7251 - 0.02 (library_v3 at its eval-10 seed, v3x at
  its eval-8 seed);
- add_med against v3x (5.51 + 2.0);
- add_med over all 32 seeds;
- cdo_all, ambiguity, ADD max.

Float handling: a value exactly at a threshold passes. Seed values are mesh_metric's 4-decimal values.

## 6. AUC guard (only if at least one pair is a WIN)
- **Twin:** ep11, the beige cup's only public episode.
- **Track:** `world_T_obj[t] = world_T_cam[t] @ cam_T_obj[t]` from `SCR/data/sweep/ep11/poses.npz` (`perc2.py:495`
  recipe).
  - C0's converted `SCR/cdo_c0/tracks/ep11/poses_world_vo.npz` is used if its sha256 matches a fresh conversion.
- **Runs:**
  - `base` = the library_v3 dir of the 10 public objects;
  - `single` = base with `beige_cup.glb` replaced by M_sep, placed in the library frame as built.
- **Command per run:**
  `SCR/venv/bin/python -I pipeline/score_registered.py 11 <poses_world_vo.npz> --meshes <dir> --t3 <t3> --kit SCR/kit/v2d_submission_kit --out <json>`.
  - `t3` holds `ep11.parquet` plus `mesh/` (public scans).
- **Reusing C0's base:** C0's `base/ep11` run is reused only if every file of `SCR/cdo_c0/base` equals the
  `meshes/library_v3` file by sha256 and the track npz matches. Otherwise our own base is run.
- **Rule:** dAUC = AUC(single) - AUC(base) on the episode-level `perception` entry.
  - PASS iff dAUC >= -0.005 (one twin, so mean = min = this value), dMPPE <= +0.2 cm and dRPE <= +0.2 cm.
  - Deltas are compared unrounded on the 4-decimal outputs.
- **Each run is executed once.** A crash may be re-run unchanged.

## 7. Eval 10 packing check (no scoring; `scripts/pack_check.py`, `results/pack_check.txt`) [M]
The submitted CD-O vertex rows were compared with the kit packer's `budget_mesh` of each library mesh:
- `results/submissions/20261025-track3c` (pack 3, the CD-O upload behind 0.402):
  - eval 10 beige = **library_v3** (max vertex distance 0.000 mm; v3x 23.7 mm);
  - eval 8 beige = **library_v3x**.
- `20261026-track3d` (pack 4): the same.

So STATUS.md (25 Oct, "adopted for evals 10, 8") is wrong for the packed meshes. The eval lane ("only eval 8") is
right.

## 8. Integrity and disclosure
- No scan, mocap, parquet pose or `*_align.npz` was read for construction, masking or choice.
- `frame_census.py` reads our tracks, our hands and our library meshes only.
- The author read the scan-extents table in `README.md` section 1 (required material; it gives the beige scan as
  10.4 x 11.1 x 16.9 cm) before choosing the mask.
  - The mask was asked for in the brief and is justified above from our census alone.
  - Influence of that table on the choice cannot be fully excluded.
- Scan reads after this commit:
  - `score_t1.py` once (mesh_metric);
  - if a pair is a WIN, `score_registered.py` on ep11 (base and single).
