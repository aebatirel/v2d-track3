# C1 / T2 already-scored generated picks, placed in the library frame: pre-registration

Written 2026-10-31 (~16:25 UTC) before any scan, mocap or parquet-pose read for this track. Scratch paths are relative
to `SCR = /tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`; `T2 =
docs/research/mesh-2026-10-26/cdo-sprint/C1/T2-probe-picks`. Step log with times: `NOTES.md`.

Labels: [D] public scan or mocap as stand-in, after inference; [M] measured without ground truth; [E] estimate;
[H] hypothesis.

## 1. Question and hypothesis
The batch-2 generative probe (`results/gen-probe/`) scored one SAM 3D mesh per object that its GT-free metric picked.
For three weak objects that pick has a better public-scan CD-O than the packed library mesh [D, already known]:

| object | eval pairs (episode, seed) | packed baseline CD-O | probe pick | probe CD-O per pair [D] | probe ADD med [D] | library add_med |
|---|---|---|---|---|---|---|
| water_pitcher | ep20 (20000161) | 0.894 | `gen/sam3d/ep22_water_pitcher_k174_s42` | 0.771 | 33.4 mm | 7.97 mm |
| mini_dust_pan | ep19 (19000158), ep38 (38000114) | 0.331, 0.331 | `gen/sam3d/ep39_mini_dust_pan_k297_s42` | 0.2619, 0.2592 | 7.47 mm | 5.65 mm |
| beige_cup | ep10 (10000131), ep8 (8000024) | 0.856 (v3), 0.730 (v3x) | `gen/sam3d/ep11_beige_cup_k6_s42` | 0.5191, 0.5326 | 21.8 mm | 6.97 mm |

Their CD-O gains could not be used because the probe placed them with a biased point fit (`gen/sim3_fit.py`), so their
registration ADD (which sets the body frames of AUC, SP-SR, MP-SR, RPE and MPPE) is far worse than library_v3's.

**H-T2 [H]:** placing each pick in the library_v3 object frame by a GT-free Sim(3) registration onto the library_v3
surface (the diag-2026-10-30 `lib` registration) makes it pose-safe: add_med within +2.0 mm of library_v3, no flips,
and an AUC guard pass on its public twins. Falsified per object by the gates of sections 5 and 6.

**GT-free prediction [H], made before scoring:** the placement moved each mesh only 6-9 mm and 3-4 deg from the probe
pose (section 3), while the probe ADD exceeded the library's by 26 mm (pitcher), 15 mm (beige) and 1.8 mm (dust pan).
The diag README (required material, read beforehand) reports `lib` as still worse than library_v3's pose on the
pitcher and the beige cup and better on the dust pan. So: dust pan likely a WIN; pitcher and beige likely fail the
add_med gate. Not part of any gate.

**Disclosures.** The three objects were chosen for T2 by the brief because their GT-free probe pick beat the library
on the [D] probe CD-O (the object choice is post hoc on [D]; the mesh per object was the probe's GT-free argmin, not
the CD-O best). The beige cup is already covered by T1's lathe (CD-O 0.248/0.255, AUC PASS), which dominates this pick
on CD-O; the beige pick is scored to test H-T2 on a cup and as a fallback only.

## 2. Inputs (GT-free)
| object | probe-scored mesh (`SCR/gen/mesh-20261029-gen-f3fbeb0/results/gen/sam3d_sim3/`) | sha256 | library_v3 mesh sha256 |
|---|---|---|---|
| water_pitcher | `water_pitcher_k174_s42.ply` | `9c0690fa2b2dd7002f8108e607e79b1d84ffba4e23d2904ab9a02cc740cd42cf` | `9f16ed2a...b4bb2` (= v2 = v3x) |
| mini_dust_pan | `mini_dust_pan_k297_s42.ply` | `65f23d48c47a487a0c3481d8506ff3012278424ecdfbcda8f825833449a70fb0` | `412a665e...e1a2` (= v2 = v3x) |
| beige_cup | `beige_cup_k6_s42.ply` | `4373364a569d17d16aa8bc5babe7757c50db61bf125b799793d172dea6f99e82` | `f7309312...61d5` (= v2) |

These hashes equal the frozen `results/gen-probe/SHA256SUMS` entries (commit 243b854). The sweep tracks were made with
library_v2 meshes, which equal library_v3 for all three objects, so library_v3 is the track frame.

## 3. Placement (GT-free; `scripts/place.py`, outputs `results/place/`)
- Sim(3) with free scale, symmetric trimmed ICP (keep 0.9 both ways, 30 iterations) of 8000 candidate surface samples
  (seed 0) onto 8000 library_v3 surface samples (seed 3). Multi-start: the 24 proper signed permutations of the PCA
  axes (initial scale = geometric mean of the PCA sigma ratios) plus the identity (the probe's point-fit pose). The start
  with the smallest trimmed symmetric mean distance wins. Functions copied from `diag-2026-10-30/sam-placement/common.py`.
- The kit's CD-O normalises scale and registers rigidly, so the placed copy has the probe's CD-O; only its frame and
  size change. The kit registration also normalises scale, so the size enters the body frame only through the anchor.
- Command (cwd `SCR/cdo_c1/t2/place`, python `SCR/venv/bin/python -I`):
  `place.py <obj> SCR/gen/mesh-20261029-gen-f3fbeb0/results/gen/sam3d_sim3/<mesh>.ply meshes/library_v3/<obj>.glb SCR/cdo_c1/t2/place/<mesh>_lib`

| object | winning start | residual mm | 2nd distinct start (angle) | scale | rot / trans from probe pose |
|---|---|---|---|---|---|
| water_pitcher | identity | 6.130 | 8.573 mm (176 deg) | 1.0001 | 2.92 deg / 8.74 mm |
| mini_dust_pan | pca03 (identity 2.778, same basin) | 2.774 | 4.468 mm (112 deg) | 0.9963 | 4.11 deg / 6.14 mm |
| beige_cup | identity | 5.304 | 9.968 mm (axis tilt 63 deg) | 0.9800 | 4.25 deg / 6.73 mm |

Transforms (s, R, t; probe ply -> placed) are in `results/place/<mesh>_lib.json`. Beige cup (axial): only the axis
and translation matter; "distinct" starts are those whose cup-axis tilt differs by > 30 deg.

## 4. GT-free checks [M] (reported; none of them switches anything)
- **Pack check** (`scripts/pack_check.py`, `results/place/pack_check.txt`): the kit packer's `budget_mesh(4096, 4096)`
  of the placed copy equals the placement applied to `budget_mesh` of the probe mesh: vertex NN median 0.0 mm (max 5-10
  mm at a few vertices); symmetric surface distance 1.36 / 0.75 / 0.95 mm against a same-mesh sampling floor of
  1.55 / 0.76 / 0.94 mm. The probe CD-O therefore carries over.
- **Observation fidelity** (`scripts/obs_fidelity.py`, `results/place/obs_fidelity.txt`), sum in mm, library_v3 /
  probe point fit / placed: pitcher ep21 6.38 / 5.95 / 7.81, ep22 6.99 / 6.44 / 8.44; dust pan ep18 3.52 / 3.40 /
  4.07, ep39 3.64 / 2.25 / 4.10, ep40 3.36 / 2.51 / 4.44; beige ep11 3.45 / 4.20 / 5.60. The library-frame placement
  explains our observed points worse than the point fit on all six twin pairs, including the twins the fit did not
  use. This objective family is the one the point fit minimises and that the diag showed biased (17/20 meshes), so it
  is reported only.
- **Cup axis** (beige): the placed cup is cleanly axial (90-deg self-invariance residual 1.8 mm, axis 4 deg from the
  track z axis); library_v3 beige is not (11.4 mm; refined axis about 11 deg from z), so no axis comparison with the
  library is meaningful.

## 5. Scoring and the CD-O gate (diagnostic [D])
**The scored meshes (exactly three, one scoring each, in this order):**

| # | object | placed mesh (`SCR/cdo_c1/t2/place/`) | sha256 | sha1[:16] (mesh_metric) |
|---|---|---|---|---|
| 1 | mini_dust_pan | `mini_dust_pan_k297_s42_lib.glb` | `2fb147b535c9f8b863b56ec80239f28809b10fe9ca881a10a5c724f209777d02` | `3a0c62f390b4646e` |
| 2 | water_pitcher | `water_pitcher_k174_s42_lib.glb` | `ba38d40931c5fcdba0535101deeabf70672588375b2ede50b9da5b697a71a253` | `c3a24a14838e92bd` |
| 3 | beige_cup | `beige_cup_k6_s42_lib.glb` | `8c6e063d7cf331246b3a4d813c7fc0bb192869d083b77f8d490f3eba52871fbf` | `ff6a0c1efed4c9b3` |

The placed GLBs (4.3-7.2 MB) stay in scratch; they are rebuilt bit-for-bit by `place.py` from the frozen probe output (verified for the dust pan: same sha256)
(HF store run folder `mesh-20261029-gen-f3fbeb0`). If one is adopted, it is copied to the HF store and git (< 10 MB).

**Command** (refuses to run if the output already holds the mesh's sha):
```
cd /home/user/v2d-track3 && MESH_SCR=SCR SCR/venv/bin/python -I T2/scripts/score_t2.py <obj> \
    SCR/cdo_c1/t2/place/<mesh>_lib.glb T2/results/score_t2.jsonl
```
`mesh_metric.evaluate()`: the kit's CD-O and registration against the kit-budgeted public scan, at the object's
eval seeds plus 30 extra seeds: 11, 22, 33, 44, 55 (the baseline records' extras), then 1001-1025.

**Gate, per eval pair** (constants in `score_t2.py`):
- CD-O: the **probe's** CD-O at that pair's seed <= packed baseline - 0.02: pitcher ep20 <= 0.874; dust pan ep19 and
  ep38 <= 0.311; beige ep10 <= 0.836, ep8 <= 0.710. (All four probe values already meet this; the placed copy's
  re-measured CD-O is reported as a consistency check only.)
- add_med <= library add_med + 2.0 mm: pitcher 9.97, dust pan 7.65, beige 8.97. add_med is the median ADD of the placed
  copy over the same 6 seeds as the library baseline record (eval seeds + 11, 22, 33, 44 [+ 55 for the pitcher]).
- flips: 0 over all seeds (31 pitcher, 32 others). A flip is a symmetry-aware rotation error > 90 deg; the beige cup
  is kit-declared axial, so a spin about the axis is not a flip.
- A pair is a **WIN** only if all three hold. Values exactly at a threshold pass.
- Reported, not gating: per-seed baselines (pitcher 0.8942; dust pan 0.3274 / 0.334; beige 0.8705 / 0.7251), add_med
  over all seeds, ADD max, rot max, the kit self-ambiguity.

## 6. AUC guard (only for an object that is a WIN on at least one pair; the C0 rule, exactly)
- **Twins** (public episodes containing the object, our perception tracks): pitcher ep21, ep22; dust pan ep18, ep39,
  ep40; beige ep11.
- **Tracks:** `world_T_obj[t] = world_T_cam[t] @ cam_T_obj[t]` from `SCR/data/sweep/ep<e>/poses.npz`
  (`scripts/auc_prep.py`, `results/auc_prep.json`). For 11, 21, 22 C0's converted files are used (their source sha256
  matches and a fresh conversion is numerically identical); 18, 39, 40 are our own conversions.
- **Runs:** `base` = library_v3 of the 10 public objects; `single_<obj>` = base with `<obj>.glb` replaced by the placed
  copy (section 5). Mesh dir hashes in `results/auc_prep.json`.
- **Reuse of C0's base:** C0's `runs/base/ep{11,21,22}.json` are reused: C0's base dir equals ours file by file
  (sha256) and the track files are C0's own (byte-identical); same `pipeline/score_registered.py` (last changed 25 Oct)
  and kit. Own base runs for 18, 39, 40.
- **Commands:** stage 0 `bash T2/scripts/run_auc.sh stage0` (downloads the public parquets for 18, 39, 40 from the HF
  dataset, links C0's for 11, 21, 22, links the public scans `SCR/data/scan`), then
  `bash T2/scripts/run_auc.sh runs <WIN objects>`; each run is
  `SCR/venv/bin/python -I pipeline/score_registered.py EP <poses_world_vo.npz> --meshes SCR/cdo_c1/t2/auc/<cfg> --t3 SCR/cdo_c1/t2/auc/t3 --kit SCR/kit/v2d_submission_kit --out SCR/cdo_c1/t2/auc/runs/<cfg>/epEP.json`.
  Verdict: `python -I T2/scripts/guard_t2.py SCR/cdo_c1/t2/auc T2/results/guard_t2.json <WIN objects>`.
- **Rule:** dX_e = X(single, e) - X(base, e) on the episode-level `perception` entry. **PASS** iff mean dAUC >= -0.005
  AND min dAUC >= -0.02 AND mean dMPPE <= +0.2 cm AND mean dRPE <= +0.2 cm, with no twin missing. Deltas unrounded on the
  4-decimal outputs. Each run is executed once; a crash may be re-run unchanged.

## 7. Adoption
An object's candidate is **adopted** for its WIN pairs iff it is a WIN on that pair (section 5) and its AUC guard
passes (section 6). For the beige cup, an adopted T2 pick is a fallback only; T1's lathe is better on CD-O.

## 8. Integrity
- No scan, mocap, parquet pose or `*_align.npz` was read for the placement, the checks or any choice. `place.py` reads
  the probe mesh and our library_v3 mesh; `obs_fidelity.py` our observed points; `pack_check.py` the kit packer only;
  `auc_prep.py` our tracks, our meshes and C0's GT-free files.
- Already-known [D] numbers before this pre-registration: the probe scores and library baselines (section 1), the diag
  README's statements on `lib` (section 1), C0's and T1's reports. C0's base AUC JSONs have not been opened.
- Scan reads after this commit: `score_t2.py` three times (one per placed mesh), then `score_registered.py` on the twins
  of WIN objects (own base 18, 39, 40 if the dust pan is a WIN; singles).
