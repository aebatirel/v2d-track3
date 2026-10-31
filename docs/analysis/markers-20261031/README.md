# GT-free marker correction layer (spoon first), 31 Oct 2026 — FAILS its public gate

CPU only (this cloud VM, 4 cores), $0. No Vast, no GPU, no Kaggle; nothing posted; no eval reference or pack changed.
Labels: [M] measured here, [E] estimate, [H] hypothesis. Ground truth (public mocap, public scans) is read only by
`pubscore.py` and `diag_fix.py`, after inference. The pass rule was written in `PREREG.md` before scoring
(block 1 at 18:52 UTC, method frozen in block 2 at 19:38 UTC, first score 19:38 UTC).

## Answer first

1. **Public validation FAILS the pre-registered rule, clearly [M].** 16 units (white_pot × 9, white_pot_lid × 2,
   blue_cup × 5), kit registered chain, per-object AUC:
   - primary layer: mean ΔAUC −0.083, 1/16 improved, worst −0.407 (lid ep2, through the pot's frame-0 anchor);
   - every variant fails: no vote −0.080, no carry −0.041, raw fused fixes −0.039 (worst −0.088).
   - Episode RPE rises in 8 of the 9 two-object episodes it touches (+0.03 to +1.35 cm); ep11 falls (−0.14).
2. **Why [M, post-hoc oracle diagnostic `diag_fix.json`]: on public objects our FoundationPose tracks are already more
   accurate than single-frame marker fixes from the 1280×800 mono pair.**
   - Pot: track 0.26–0.42 cm vs marker fixes 1.0–2.2 cm on the same frames (fix better on 1–8 % of them).
   - Lid (3 markers, 66–92 % full fixes): 3-marker fixes tie the track (1.16–1.19 vs 1.10–1.21 cm); 2-marker fixes
     are worse (2.1 vs 0.9–1.1 cm).
   - Blue cup: fixes 1.0–1.4 cm vs track 0.7–1.3 cm.
   - Note 17's gains assumed an emulated 10 mm / 5° prior. Our real public prior is 3–13 mm, and a marker sphere is
     only ~12–16 px wide in b/c, so the per-frame fix noise (3-marker rigid-fit rms 1.0–4.5 mm, roll sd 3–13° per
     frame on the spoon) is larger than the tracker's own error.
3. **Spoon census on the 10 eval spoon episodes (GT-free) [M].** Table below. ≥ 2 markers in 34–73 % of frames
   (73–89 % at rest in 8 of 10). ≥ 3 markers in only 2–18 % (1–27 % at rest). M1, the lateral neck marker that
   carries roll, is the bottleneck: it is often seen edge-on, beside its black base.
4. **Spoon layout from our own video [M].** Triangle 54.9 / 195.9 / 154.3 mm (template from note 20:
   53.5 / 194.6 / 153.2). Rigid-fit residual 2.0 mm median (p90 3.2) over 94 complete rest sets.
   - Placed in our body frame from our tracks, it sits 5.4–8.8 mm from the template's modelled markers. That is a
     5.9° rotation, 5.1° of it roll about the handle, plus 5.8 mm.
   - So our track's mean roll and the template's marker model disagree by ≈ 5° [M]. Which one is right is not
     measurable without ground truth. The physical rest check (`spoon_rest.json`) cannot separate them: per-frame
     marker roll sd is 3–13°, and both readings sit near the same stable rest.
5. **What it would have changed on eval (GT-free sizes; NOT adopted) [M]:**
   - Frame-0 roll corrections in the spoon-anchored episodes: +7.0° (32, vote 7 vs 2), +0.6° (33, abstain, but
     14 mm translation), 0.0° (35), −1.4° (36), +0.1° (37).
   - Median per-frame corrections are 3–11 mm and 2.5–7°.
   - **Eval 16, frames ≥ 120 (the rack placement):** the layer would move the spoon down by a median 21.6 mm. Its
     lowest point would go from 12.6 mm above our table plane to 19.7 mm below it, which is physically impossible.
   - [H] Probable cause: the rack carries a marker pair 153.5 mm apart (public layout, `census_public_plastic_dish_rack`),
     almost equal to the spoon's M2–M3 distance (154.3 mm). Near the rack, 2-marker spoon fixes can lock onto rack
     markers. Falsifier: relabel eval-16 fixes with the rack's detections excluded and check whether the downward
     shift vanishes.
   - So markers do not explain or fix eval 16's support problem.

## Census (eval spoon, layout-consistent sets; `data/census_eval_wooden_spoon.json`)

Columns: share of frames with a layout-consistent set of ≥ 2 / ≥ 3 markers. Rest = still per our own track; hand = a
perceived hand joint within 4 cm of the tracked spoon.

| eval | anchor | all ≥2 / ≥3 | rest ≥2 / ≥3 | hand ≥2 / ≥3 |
|---|---|---|---|---|
| 32 | yes | 0.49 / 0.06 | 0.81 / 0.13 | 0.45 / 0.01 |
| 33 | yes | 0.34 / 0.02 | 0.73 / 0.02 | 0.34 / 0.03 |
| 35 | yes | 0.66 / 0.18 | 0.87 / 0.27 | 0.64 / 0.17 |
| 36 | yes | 0.55 / 0.10 | 0.89 / 0.14 | 0.51 / 0.09 |
| 37 | yes | 0.73 / 0.05 | 0.78 / 0.01 | 0.65 / 0.09 |
| 3 | no | 0.60 / 0.13 | 0.88 / 0.18 | 0.55 / 0.11 |
| 5 | no | 0.69 / 0.16 | 0.82 / 0.17 | 0.60 / 0.16 |
| 6 | no | 0.70 / 0.16 | 0.83 / 0.15 | 0.64 / 0.15 |
| 15 | no | 0.45 / 0.08 | 0.39 / 0.13 | 0.53 / 0.02 |
| 16 | no | 0.50 / 0.08 | 0.50 / 0.09 | 0.52 / 0.06 |

- Public objects (same detector, free discovery): lid ≥ 3 in 66–92 % of frames; pot ≥ 2 in 17–77 %, ≥ 3 in 0–18 %;
  blue cup ≥ 2 in 4–82 %.
- Layout discovery found < 2 pooled markers for both wooden pieces, the pitcher and the sweeper. Their markers face
  away at rest, or they are seen in one episode only.

## Method (all GT-free; files in this folder)

| file | role |
|---|---|
| `mlib.py` | rectified ego stereo rig exactly as `pipeline/perc2.py` (left = ego_cam_c, right = ego_cam_b), video IO, eval/public perc2 track paths |
| `detect.py` | marker detector. Polarity-free gradient circle Hough. Robust sub-pixel circle fit. Uniform-interior and black-base contrast cues. Stereo pairing on rectified rows: the measured per-episode b/c row offset is −0.2 to −2.0 px; then NCC and a 3-D radius check. Nothing learned |
| `scan.py` | per-frame stereo detections inside our track's projected mesh box (+4 cm) |
| `mklayout.py`, `census.py` | rest mask from our track, body-frame clustering, layout-consistent labelled sets (pairwise-distance backtracking, prior gate 5 cm / 30°), layout = stereo shape placed by complete-set medians, census |
| `guided.py` | second, relaxed detection pass in small windows around the predicted markers |
| `correct.py`, `apply.py` | correction layer. Steps: gate 3 cm / 20°; outlier rejection; 9-frame smoothing; bounded carry; static-segment vote with abstain (≥ 4 votes, ≥ 2× runner-up) |
| `run_obj.sh` | per-object pipeline: pass 1 → guided → pass 2 |
| `consensus.py` | dropped variant: cross-episode constellation registration. It gave spurious 3-point registrations (pot ep42 175°) and was dropped before scoring (`data/consensus_*_dropped.json`) |
| `spoon_rest.py` | physical roll check at rest against our mesh's stable rests and our table plane |
| `eval_sizes.py` | GT-free size of the eval corrections (`eval_sizes.json`) |
| `pubscore.py`, `diag_fix.py` | scoring only (public mocap via `docs/analysis/rpe-decomp-20261031/rdlib.py`) |

Inputs:
- eval and public ego_cam_c/b videos (organiser dataset; the b videos were fetched for this work);
- the public calibration;
- perc2 tracks: eval `runs/20261026-pack6-5203d42` and the 32/33 runs listed in `mlib.PERC_EVAL`; public 25 Oct
  sweep/guard;
- our library_v3 meshes and our spoon template;
- our table frames and hands.

No mocap, `pose` field, scan or scan-derived constant reaches inference. The note-17 scan catalogue is not used. The
spoon template's video-measured layout (note 20) only seeds labelling; the layout is re-measured.

Reproduce (scratch S = this session's scratchpad, cv2 from `$S/eg/pylib`):
1. `scan.py SPLIT EP OBJ` for every (episode, object).
2. `run_obj.sh public OBJ EPS`, and `run_obj.sh eval wooden_spoon 3,5,6,15,16,32,33,35,36,37 spoon`.
3. `apply.py public EP OBJS OUT --eligible white_pot,white_pot_lid,blue_cup`.
4. `pubscore.py`.

Runtime: scans 1–6 min per (episode, object) on one core, ≈ 50 CPU-min in total. Everything else takes minutes.

## Limitations and what could still be tried (hypotheses, not run)

- Only the b/c pair was used (f ≈ 600 px on the rectified grid). [H] Adding ego_cam_a (f ≈ 1150, 2×) as a third view
  should cut the per-frame fix noise by ≈ 2× and raise M1 recall. Falsifier: the 3-marker fix error on public lid/pot
  frames (diag_fix) stays ≥ the track error.
- [H] A marker layer could still help where our track is bad (thin, fast, occluded spoon in hand). Public data has no
  spoon, and on the marker objects we can score, the tracker is already better than the fixes. So that claim cannot
  pass a public gate with this detector.
- The 5° roll disagreement between our track mean and our template's marker model is a GT-free fact. Which side is
  right needs ground truth, or an organiser answer on the spoon scan.
