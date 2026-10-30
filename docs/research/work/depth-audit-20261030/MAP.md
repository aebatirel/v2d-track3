# Depth audit, map stage (30 Oct 2026; CPU cloud VM, $0, repo HEAD 817b135, nothing committed)

Labels: [M] measured here, [C] read from code or logs (file:line given), [E] estimate, [H] hypothesis.
- **GT rule kept.** No ground truth was read: no mocap, no `observation.objects` pose, nothing in `refine/quarantine_gt` or `refine/baseline`.
- **Eval data handled:** our own eval references, our own eval perception, and eval depth only. No tuning.
- No Kaggle call. No GPU. No git operation.

Work dir: `W=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/daudit`.
- Scripts are in `$W/scripts/`.
- Downloads are in `$W/dl_*`, each opened with `python -I`.
- Results are in `$W/work/`. Big arrays were deleted after use; `$W` holds 122 MB.

## 1. Depth cache in the store

**What exists [M]** (`list_repo_tree`, `$W/ls_depth.jsonl`). The file is the same for every episode: `depths_fs0.5.npy`, the only file per episode.

| split | episodes | frames | size |
|---|---|---|---|
| `cache/depth/public/ep<N>/` | 0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45 (20) | 5,246 | 33.6 GB, 0.88 GB (ep11) to 2.39 GB (ep0) |
| `cache/depth/eval/ep<N>/` | 1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38 (20) | 5,181 | 33.2 GB, 0.97 GB (ep37) to 2.69 GB (ep35) |

Frames per episode, from the size (header 128 bytes, then N × 1000 × 1600 × 4 bytes):
- Public: 0:373 2:343 11:137 12:181 13:190 18:353 21:186 22:189 23:325 24:275 26:158 27:246 31:290 39:319 40:260 41:299 42:257 43:326 44:249 45:290.
- Eval: 1:335 3:313 5:288 6:243 8:219 10:161 14:158 15:166 16:173 19:235 20:202 25:356 28:220 30:263 32:259 33:348 35:421 36:407 37:151 38:263.

**Format [M, C]:**
- Array: npy v1, `<f4`, C order, shape (N, 1000, 1600). Values are metres; 0 means invalid.
- The perc2 writer keeps z only in [0.15, 2.0] m and only where disparity > 1 px (`pipeline/perc2.py:122-124`).
- The sample values (public frame 0 p5/p50/p95 ≈ 0.42/1.04/1.85 m; eval ep3 0.43/1.07/1.86 m) are consistent with this.

**How it was made [C]** (`pipeline/perc2.py:96-139`):
- **Method: stereo, not mono.** FoundationStereo (checkpoint `23-51-11/model_best_bp2.pth`, `valid_iters` 32, fp16 autocast) runs on the rectified ego pair: left `ego_cam_c`, right `ego_cam_b`. Both are monochrome, 1280×800, rectified to 1600×1000 with `cv2.stereoRectify(alpha=0)`.
- **"fs0.5" = `FS_SCALE` 0.5.** Both images are downscaled to 800×500 before the network. The disparity is upsampled bilinearly back to 1600×1000 and divided by 0.5. Then z = FR·B/disp.
- **Consequences:**
  - The stored array is full rectified resolution with the full-resolution intrinsics. **No intrinsic scaling is needed.**
  - Detail is effectively half resolution, so silhouettes are blurred by about 2 px. Masks must be eroded.
- **Rectified intrinsics [M]:** KR = [[600.2, 0, 756.78], [0, 600.2, 486.37], [0, 0, 1]], baseline 0.0755 m. KR is also stored as `KR` in every `hands_refined.npz`.
- **Depth resolution [M, computed]:** one half-resolution disparity pixel ≈ 0.71 cm at 0.4 m, 1.1 cm at 0.5 m, 2.2 cm at 0.7 m. The objects sit at 0.35 to 0.5 m.

**Who wrote it [C, M]:**
- **Public:** the perc2 perception runs, pushed by `ops/box/store.sh push-depth` (`store.sh:72`).
- **Eval:** the mesh session's job `runs/mesh-20261029-evdepth-92f3d86`.
  - Script: `ops/jobs/eval_depth.sh` at 92f3d86, on branch `claude/bold-albattani-6qmxsv`.
  - It reran eval perception (`KF_MIN=120 SPLIT=eval MESH_DIR=library_v3 python perc2.py`) on all 20 episodes from 21:56 to 23:43 UTC, 29 Oct. Every `job.log` line reads "no cached depth (computed here)", then "depth pushed".
  - It wrote new tracks to `runs/mesh-20261029-evdepth-92f3d86/results/evalperc/ep<N>/`.
- **Eval depth is a recomputation; the depth behind the pack-6 eval references was never stored.** The camera tracks show it is equivalent [M]:
  - The camera track comes from depth PnP.
  - `world_T_cam` of the evdepth rerun equals pack 6's eval perception to **0.0 mm** on 19/20 episodes. Eval 5 differs by up to 5.6 mm.
  - The spoon tracks are identical (0.0) on all 10 spoon episodes.

**Download speed [M]:**
- Full file: ep11 (0.88 GB) took 11 s via `hf_hub_download`, about 80 MB/s.
- HTTP range read of selected frames (`$W/scripts/depth_frames.py`): 4 frames took 4.2 to 15 s, varying. Use full downloads for whole episodes.

## 2. Frame indexing and timing

All of the following are the same frame i:
- **Depth frame i** = the stereo pair at rectified video frame i (`perc2.py:84-90`), with N = min(len c, len b, parquet rows) on public. On eval, the parquet term is replaced by the video length.
- **Our pose `cam_T_<obj>[i]`** comes from FoundationPose `track_one` on the same frame, **using `depths[i]` as its depth input** (`perc2.py:473`). Registration uses `depths[0]` (`:461`).
- **Mocap row i**: `score_registered.py` uses `frames = arange(T)` for an npz source (`:85-91`).
- **Reference frame t**: mkref drops its 10 warm-up frames (mkref log: "345 frames, dropped 10 warm-up frames").

The counts agree:
- **Public [M]:** T(poses) = depth N = hands T on all 20 episodes (`refine/in/ep*/inputs.json` checks).
- **Eval [M]:** depth N, pack-6 perception T and reference T are equal on every episode checked (e.g. ep3: 313, 313, 313). Perception T equals reference T on all 20.

**FPS:** 20 (`ref_summary.json` `fps`).

**S2 note [C]** (`docs/research/work/refine/RESULTS.md`, refcheck R6):
- Our path is about 0.5 frame (23–27 ms) *late relative to mocap*. S2 shifts our poses by +0.545 frame.
- Depth and our poses come from the **same video frame**, so the audit needs **no time shift**.
- Only the calibration label (ADD of frame i against mocap row i) contains this lag. At 50 cm/s that is about 1.4 cm; at ≤ 20 cm/s it is under 0.6 cm [E].

**World frame:**
- World = rectified-left camera at frame 0 (OpenCV axes), so `world_T_cam[0]` = I [M].
- The camera travels 2.1 cm (ep11) to 5.05 cm (ev3) over an episode [M].
- cam_T(t) = inv(world_T_cam[t]) @ world_T_obj(t).

## 3. Where our per-frame object poses live

**Public, for calibration** (all local, inference-safe; `refine/README_inputs.md`). Root: `/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/refine/in/ep<N>/`.
- **`poses.npz`** [M ep11]:
  - `world_T_cam` (T,4,4) float64;
  - `cam_T_<obj>` (T,4,4) float32: template frame → rectified camera t;
  - the key order is the slot order.
- These are the 25-Oct current-recipe perc2 tracks (guard or sweep-base arms), the same ones the refine baseline scored.
- **Templates:** `library_v2`, which equals `library_v3` except `mini_sweeper` (same frame, ≤ 2.2 mm). **Render with `meshes/library_v3`.**
- **Hands:** `hands_refined.npz` holds `joints_left/right` (T,21,3) in the world frame, `valid_*`, `measured_*` and `KR`.
- **Not to be opened by audit code:** `refine/baseline/raw/ep*_lib_pf.npz` (per-frame errors vs mocap) and `refine/quarantine_gt/`. Calibration may read them only after the audit has produced its numbers.

**Eval: the policy reference ≠ the eval perception.** The pack-6 episode JSONs name the reference each rollout tracked, as `/workspace/refs/<variant>/ep<N>/processed/...`.
- The same files are in the store under `runs/20261026-pack6-5203d42/refs/...`. Their sha256 matches the building run's copy for all 6 episodes checked [M].
- **Format** (FlashCHORD ManoSharpa, one row):
  - `object_body_names`;
  - `object_body_position` (T·B·3) and `object_body_wxyz` (T·B·4), w first;
  - **table frame**: z up, table top at z = 0.60, xy origin under the frame-0 object centroid.
- **Back to camera [C, M]:**
  - `cam_T_obj(t) = inv(world_T_cam[t]) @ inv(T_table_from_world) @ OBJ_ref(t)`.
  - `T_table_from_world` is taken from `refs/perc2mck(s)/ep<N>/table_frame.npz`. The per-object z snap (`object_z_shift`) is already inside `OBJ_ref`.
  - Checked by rendering on eval 3 (§5).
- **Reference chain [M]** (`$W/work/evfeed.jsonl`, `evfeed_src.jsonl`; `scripts/evfeed*.py`):
  - mkref's own output `e2s_reference.parquet` equals `T_tab @ world_T_cam @ cam_T` (+ z shift) of its feeding perception to **0.000 mm** on all 20 episodes.
  - The **policy reference** (contact retarget with rest settle, then sf / glockt) moves objects relative to that by up to 0.5–5.0 cm and 3–14°. The spoon moves 0.6–3.7 cm and 8–14°.
  - sf and glockt leave the object poses of perc2mck's processed parquet unchanged (ep3: identical).

| eval | policy ref (variant) | feeding perception + table frame |
|---|---|---|
| 1, 16, 19, 28 | perc2mcks | `runs/20261026-pack6-5203d42/perc2/ep<N>/poses.npz` + `refs/perc2mck(s)/ep<N>/table_frame.npz` |
| 3, 5, 6, 10, 15, 20, 35, 36, 37, 38 | glockt | pack 6 `perc2/ep<N>` + `refs/perc2mck/ep<N>/table_frame.npz` |
| 8 | glockt | `runs/20261025-evb0810-ee7ba8e/perc2/ep8` + its `refs/perc2mck/ep8/table_frame.npz` (beige cup re-tracked, 36 cm from pack 6's track; `library_v3x` beige cup) |
| 14 | glockt | `runs/20261025-evb1420-ee7ba8e/perc2/ep14` + its table (blue cup 38 cm from pack 6's) |
| 25 | perc2mcks | `runs/20261026-c25s42-feb0407/perc2/ep25` + its `perc2mcks` table (both boards about 36 cm: the identity fix) |
| 30 | perc2mcks | `runs/20261025-std30-ee7ba8e/perc2/ep30` + its `perc2mcks` table (sweeper 44.5 cm from pack 6's) |
| 32 | glockt | `runs/20261026-fr32s46b-5e0e100/perc2/ep32` + its table (blue cup 25 cm) |
| 33 | glockt | `runs/20261026-fr3233s43-6a8a0e2/perc2/ep33` + its table (blue cup 34 cm; same reference in pack 7) |

- The camera track is identical (0.0 mm) in every source run versus pack 6.
- **Hands:** `refs/perc2mck/ep<N>/hands_refined.npz` in the same runs. Hands depend only on the camera.
- **Side finding [M]:** on 8, 14, 30, 32 and 33, the evdepth rerun's cup or sweeper tracks differ by 25–45 cm from pack 6's eval perception. The audit could show which of the two agrees with depth.
- **Not covered:** the pack-8 candidate's eval-1 reference (c01s43 carve).

## 4. Per-frame ADD in `pipeline/score_registered.py` (calibration side only)

**What it does [C]:**
- **Registration:** registers our mesh (`--meshes`, `budget_mesh` 4096 faces / 4096 vertices) to the public scan (`T3._register_object_body`, seed 1,000,003·ep + 101·slot).
- **Anchor:** moves the poses to the scan's surface-centroid anchor.
- **Scene alignment (once, at frame 0):** on the first object without a symmetry axis, or for cups-only scenes on object 0's axis plus the direction to object 1 (`T3._align_registered_scene`).
- **Scoring:** 1000 scan points about the anchor; ADD-AUC over thresholds 1–9 cm (`object_pose.py:25,96`).

**`--per_frame` exists (`:39, :114-117, :156-158`):**
- The npz holds `names`, `frames`, `perception_pos_cm` (T,B) and `perception_add_cm` (T,B).
- For a rollout dir it holds the same per source (`sim_`, `reference_`, `static_floor_`).

**Gap that matters for labels:**
- `add_cm` is the **plain** point-to-point ADD. It does not apply the cup axis (order 360) or the lid's 180° symmetry. The AUC uses `T3._symmetry_point_errors` with those symmetries.
- So per-frame labels for blue_cup, beige_cup and white_pot_lid would count unobservable spins as error.
- **Build item:** under `--per_frame` only, add a key `<src>_adds_cm` = `T3._symmetry_point_errors(ach[:,:,s], ref[:,:,s], pts[s], axes[s], orders[s])·100`. Default outputs stay unchanged.

**Further label caveats:**
- **Frame 0.** The label is *registered* ADD after frame-0 scene alignment: the anchor object's frame-0 error is removed, the depth audit sees absolute error. This mismatch can only lower AUROC [H].
- **Existing per-frame files.** They exist at `refine/baseline/raw/ep<N>_{lib,scan}_pf.npz` (commit 1972dcb, 29 Oct). They lack the symmetric key.
- **Cost.** Re-running is cheap: 44 jobs took 2 min 33 s on 4 cores (`refine/README_inputs.md` §3).

## 5. Sanity overlays [M]: our meshes rendered at our poses vs the stored depth

**Method** (`$W/scripts/sanity_overlay.py`):
- Embree ray casting (embreex 4.4.0.post1, `pip --target $W/pylib`) of all objects into one z-buffer at full resolution with KR.
- Per object: pixels where it is front-most, eroded 4 px; residual r = observed − rendered.
- "behind" = r > +1.5 cm (free space where our surface should be). "front" = r < −1.5 cm (an occluder, or our surface too far).
- All tables below use the eroded mask; valid depth fraction 1.0 everywhere.

**ep11 (public, 2 cups), full download:**

| frame | blue_cup median r (cm) | behind | front | beige_cup median r (cm) | behind | front |
|---|---|---|---|---|---|---|
| 0 | +0.44 | 0.075 | 0.026 | +0.09 | 0.001 | 0.014 |
| 20 | +0.14 | 0.062 | 0.133 | −0.29 | 0.016 | 0.116 |
| 40 | +0.12 | 0.025 | 0.157 | +0.03 | 0.003 | 0.088 |
| 68 | +0.26 | 0.078 | 0.249 | +0.11 | 0.000 | 0.043 |
| 100 | +0.73 | 0.109 | 0.011 | +0.05 | 0.007 | 0.025 |
| 136 | +0.57 | 0.028 | 0.012 | +0.30 | 0.000 | 0.002 |

All 137 frames took **16.7 s in one process** (0.12 s/frame for 2 objects):
- blue_cup behind-fraction p50 / p90 / max = 0.06 / 0.13 / 0.27 (frame 97); 4 frames > 0.2;
- beige_cup 0.002 / 0.014 / 0.13;
- median r p10/p50/p90 = −0.74/+0.35/+0.76 cm (blue) and −0.11/+0.09/+0.27 cm (beige);
- front fractions of up to 0.25 come from hands during manipulation.

**Thin objects, range reads:**

| episode | frames | object | median r (cm) | behind fraction |
|---|---|---|---|---|
| ep40 | 0/90/180/259 | dust pan | +0.20 / +0.12 / −0.07 / +0.21 | ≤ 0.013 |
| ep18 | 0/120/240/352 | sweeper | −0.17 to +0.03 | ≤ 0.025 (front 0.19–0.28 at 240/352) |
| ep18 | same | dust pan | +0.15 to +0.22 | ≤ 0.010 |

**Eval 3 (eval depth), frames 0/100/200/312:**

| poses | object | median r (cm) | behind fraction |
|---|---|---|---|
| pack-6 perception | pot | +0.39 / −0.01 / −0.24 / +0.20 | – |
| pack-6 perception | spoon (8.6k–21k px) | +0.38 / +0.22 / +0.06 / +0.39 | 0.015 / 0.056 / 0.042 / 0.008 |
| policy reference (glockt) mapped back | spoon | +0.28 / +0.24 / +0.09 / +0.64 | about the same |
| policy reference (glockt) mapped back | pot | frame 100: −3.29 | front 0.60 at frame 100 |

At frame 100 the reference pot sits 4.66 cm from the perception pose (contact-retarget rest settle). Depth sees the pot's surface 3.3 cm in front of where the reference puts it, while perception agrees (−0.01). **That error shows up only on the "front" side.**

**Conclusions:**
- Units are metres.
- Frame i of the depth matches frame i of the poses.
- No intrinsic scaling is needed.
- The table-frame reference maps back to the camera.
- Static agreement is a few mm (median |r| ≤ 0.7 cm).

## 6. Build design (refined from planner A2 by the evidence above)

**`pipeline/depth_audit.py` (inference side).**

*Inputs:*
- `--poses poses.npz` (perception mode), or `--ref REF.parquet --table table_frame.npz --poses poses.npz` (reference mode: `world_T_cam` from the poses, objects from the reference);
- `--depth depths_fs0.5.npy` (mmap);
- `--meshes DIR`: `library_v3`, or `library_v3x` for eval 8's beige cup;
- `--hands hands_refined.npz` (KR plus joints);
- `--out DIR`; `--stride` (default 1).

*Guards and provenance:*
- Reuse `refine.assert_inference_input`.
- Reference mode needs a narrower parquet allowance: a parquet only under `refs/*/` whose schema has `object_body_position` and no `observation.objects` column.
- Write input sha256s and the commit into the output JSON.

*Per frame (fixed now, before any GT is read):*
- z-buffer and per-object id by Embree. Also each object rendered alone, for visibility.
- **Hand mask (new):** our MediaPipe joints projected with `inv(world_T_cam[t])`, bones drawn as 1.2 cm-radius capsules, `valid` frames only.
- **(1) Free-space score `behind`** (primary, pre-registered): over valid-depth pixels where the object is front-most, eroded 4 px, outside the hand mask, the fraction with observed > rendered + 1.5 cm.
- **(1b) `front`** (exploratory): the fraction with observed < rendered − 1.5 cm outside the hand mask, plus the signed median r.
  - Eval 3 frame 100 shows that a reference pushed away from the camera appears only here.
- **(2) Rest height:**
  - Only on frames our own track labels as resting (`refine.moving_labels`) and only for objects not on or over another object (`refine.support_relation`).
  - Fit a RANSAC plane to depth in a ring of 8–40 px around the rendered silhouette (other objects and hands excluded).
  - Output: the signed distance of our mesh's lowest point to that plane (cm).
- **(3) Hidden flag:** vis_frac = (front-most ∧ not (r < −1.5 cm) ∧ valid) / (pixels rendered alone). Hidden if vis_frac < 0.20. The score is NaN when hidden.

*Outputs:* `audit.npz` with per-(T,B) arrays (`behind`, `front`, `med_r_cm`, `vis_frac`, `n_px`, `hidden`, `rest_h_cm`, `rest_mask`, `hand_frac`), plus `audit.json` with per-object summaries.

**`pipeline/depth_audit_calib.py` (GT side, run strictly after all audits exist).**

*Labels:*
- Primary: `perception_adds_cm` > 2 cm from score_registered `--per_frame` with `--meshes meshes/library_v3`, after the symmetric key is added.
- Secondary: the same with S2-shifted poses (`refine.py --steps S2`, no GT), to separate the lag that depth cannot see.

*AUROC:*
- Mann-Whitney U on pooled object-frames, excluding hidden ones. No sklearn here; use `scipy.stats.rankdata`.
- 95 % CI by episode-cluster bootstrap (2000 draws).
- Also report the mean within-episode AUROC (only where both classes have ≥ 10 frames) and per-class AUROC with n_pos / n_neg. Per-class pooling alone can be driven by baseline differences between objects: the blue cup's behind level is already higher on ep11.

*Pre-registered rule* (to be written in the work log before scoring):
- Informative iff pooled AUROC ≥ 0.75 on ≥ 8 episodes that contribute positives.
- Falsified iff pooled AUROC < 0.65.
- In between: inconclusive; no reference or spoon spend.
- Report the hidden-frame count and its share of positives.

**Eval step (only if informative):**
- Same script, two modes per episode:
  - (a) perception mode on the feeding perception, comparable to the calibration;
  - (b) reference mode on the policy reference, which is what the policy tracks.
- Per-episode predicted reference loss = mean behind over visible frames, mapped through the public score-to-ADD relation.
- **Spoon test:** evals 3, 5, 6, 15, 16, 32, 33, 35, 36, 37, against the public thin-object range (sweeper 18/31, dust pan 18/39/40).
  - The thresholds are fixed on public before any eval number is looked at.
  - The spoon is thinner (2.9 × 5.2 × 32.2 cm) than both stand-ins.

## 7. Calibration episodes (all 20 public episodes have depth, our poses and hands)

**Primary set (19):** 0, 2, 11, 12, 13, 18, 21, 22, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45.
- **ep23 is reported separately.** It is a frame-0 identity swap of two near-identical boards (lib AUC 0.041, `refine/README_inputs.md` §4).
- That error is consistent with depth by construction, so it is an expected false negative [H].

**Classes:**

| class | episodes |
|---|---|
| white_pot | 0, 2, 26, 27, 41, 42, 43, 44, 45 |
| white_pot_lid | 0, 2 |
| blue_cup | 11, 12, 13, 21, 22 |
| beige_cup | 11 |
| plastic_dish_rack | 12, 13, 26, 27, 31 |
| water_pitcher | 21, 22 |
| mini_sweeper (thin) | 18, 31 |
| mini_dust_pan (thin) | 18, 39, 40 |
| boards | 23, 24 |

- The count of positives (ADD > 2 cm) is unknown until scoring. It was deliberately not looked at.
- Episodes with known low per-object AUC (pitcher 21/22, rack 31, boards 24, blue cup 11/12/13) will supply most positives [E].
- Thin-class AUROC may rest on few positives. Report n_pos and do not apply the rule to a class with < 30 positives.

## 8. Disk and time estimates

**Disk:**
- 21 GB free now [M].
- One episode at a time: peak 2.4 GB (public) or 2.7 GB (eval).
- Three in parallel: ≤ 8 GB. Delete each cache after its audit.
- Per-episode audit outputs < 5 MB.

**Public pass:**
- Download about 7 min total at ~80 MB/s [E from M].
- Render and metrics 0.12 s/frame [M], about 11 min for 5,246 frames on one core. Hand masks and rest planes are estimated at ×1.5–2.
- About 15–25 min wall on 3 processes [E].

**Calibration:** symmetric per-frame scoring of 20 episodes in about 2 min, then AUROC in seconds [E].

**Eval pass (if informative):** about 15–25 min for 5,181 frames, plus the reference mode, ≈ ×2 [E].

**Build:**
- Script writing and unit checks: about 1.5–2 h [E].
- Checks: an identity render test (render a frame's depth, feed it as observed, expect `behind` = 0), and a planted 3 cm pose shift (expect behind or front > 0.5).

**Cost:** $0, CPU only.

## 9. Blockers and risks (none stops the build)

1. **Not independent of the tracker [C, H]: the main limit on AUROC.**
   - FoundationPose `register` and `track_one` consumed these same depth frames (`perc2.py:461, 473`). So `behind` is a self-consistency check.
   - It catches lost tracks, guard holds while the object moved, and reference edits (contact retarget).
   - It misses errors that agree with depth: identity swaps of similar objects (ep23), spins of symmetric objects, mesh-scale bias.
   - Falsifier: the pre-registered AUROC rule.
2. **Label mismatch [C].** The registered ADD removes the anchor object's frame-0 error, and the 0.545-frame lag is in the label but not in the depth. Mitigations: the symmetric key, the S2-shifted secondary label, and the within-episode AUROC.
3. **The policy reference ≠ the audited perception on eval [M].** Rest settle moves objects up to 5 cm and 14°, and 6 episodes come from re-tracked perception.
   - Calibration is on perception tracks. Applying it to references assumes the same score-to-error relation [H].
   - So report both eval modes.
4. **Occluders [M].** Hands produce front residuals (up to 0.25–0.28 of pixels). Reference errors pointing away from the camera are invisible to `behind` alone. The hand mask is new and untested.
5. **Eval depth is a 29 Oct recomputation.** Its equivalence rests on identical camera tracks (19/20 at 0.0 mm; eval 5 at 5.6 mm), not on a byte comparison, because the original eval depth was never stored.
6. **Tooling.** No open3d or pyrender here. embreex installed cleanly into `$W/pylib` (200k rays in 0.19 s [M]). Without it, a numpy z-buffer splat would be needed.
