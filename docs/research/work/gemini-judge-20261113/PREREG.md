# Gemini judge tests G-A and G-B: protocol (pre-registration, phase 1)

Written in phase 1 (finished 23:20 UTC by this session's clock, 2026-11-12; the work log's pre-registration entry is
stamped 2026-11-13 ~00:50 UTC) **before any scored Decisions API call**. Phase 1 built the
inputs, fixed the texts and made one format dry run on synthetic images. No challenge image has been sent to the API.

Labels: [M] measured here, [C] read from code or a file, [E] estimate, [H] hypothesis.

## 0. Rules copied from the work log (2026-11-13 ~00:50 UTC entry, verbatim)

- **Test G-A (Gemini mesh selector, note 28 idea 2).** The 104 scored meshes of the 30 Oct generative probe
  (`docs/research/mesh-2026-10-26/results/gen-probe/`).
  - Per mesh: one Decisions API `score` question (5 levels, 0–4: shape match) on real crops plus renders of the
    candidate at our own tracked pose.
  - ρ = Spearman(Gemini expected score, −CD-O) over all 104 meshes.
  - **Pass:** ρ > 0.46 (the GT-free metric's value) and Gemini's top mesh is the CD-O best on more than 2 of 10
    objects.
  - **Fail:** ρ ≤ 0.46 and the top mesh is the CD-O best on 2 or fewer. Otherwise inconclusive.
- **Test G-B (Gemini track audit, note 28 idea 1).** The depth audit's rows (30 Oct; 19 public episodes, 7,835 valid
  object-frames).
  - Per row: one `noul` question ("is the outlined model aligned with the real object?") on a crop with our tracked
    mesh overlaid. Score = 1 − P(aligned).
  - Label: the depth audit's primary label (registered ADD > 2 cm, kit frame-0 alignment).
  - **Informative:** AUROC ≥ 0.75 and ≥ 8 episodes contribute positives. **Falsified:** AUROC < 0.65. Otherwise
    inconclusive. 95% CI by episode bootstrap.
- Rules for G-A and G-B:
  - The exact question texts, image layout and resolution are fixed in a PREREG file committed before the first
    scored call. Only a format dry run on non-challenge images is allowed before that.
  - Cost cap $5 of Gemini API in total; stop and report if the estimate goes over.
- Data licence (same entry): the challenge dataset is CC BY 4.0; only public episodes are sent; ground truth is never
  sent.

**Clarifications added here (they make the rules operational; none changes a bar):**
- G-A bar: the GT-free metric's pooled ρ is 0.4650 to four decimals (`selection.json`). The rule's bar is 0.46 as
  written. A ρ in (0.46, 0.4650] passes by the rule; the report then says it does not beat the GT-free metric.
- G-A ties: if several meshes of an object share the top expected score (|Δ| ≤ 1e-9), the object counts 1/n_tied
  when the CD-O best is among them.
- G-A CD-O: `cdo` in `gen-probe/rows.json` (= `cdo_eval`, the kit CD-O over the eval-pair seeds, as in
  `gen/gen_analysis.py`; the same numbers as `table.md`).
- G-B "≥ 8 episodes contribute positives": episodes with at least one positive among the answered rows.
- G-B statistic: pooled AUROC (Mann-Whitney, average ranks) and the episode-cluster bootstrap (2,000 draws, seed 0,
  percentile, withholding rules) are the depth audit's own functions, imported unchanged from
  `depth-audit-20261030/calibrate.py` (sha256 be3ac019…). The verdict uses the point estimate.
- Missing answers (after the runner's retries and up to three resumes of the same command): left out and listed.
  G-A is inconclusive if more than 5 of 104 meshes are missing; G-B is inconclusive if more than 2 % of rows (> 156)
  are missing.
- Each item is asked once. The first successful answer counts. No item is re-asked because of its answer, and no
  text, image or resolution changes after this file is committed (a change needs a new PREREG version before any
  scored call of the changed test).

## 1. Integrity

- **What is sent:** public-episode video crops (CC BY 4.0), renders of our own meshes or generated meshes at our own
  tracked poses, the object's name (allowed: the kit gives names for eval episodes too) and fixed question texts.
- **What is never sent or used to build what is sent:** mocap, the `pose` field of `observation.objects`, the public
  scans, CD-O, ADD or any label. The builders open only: our tracks (`poses.npz`), our hands (`hands.npz`,
  G-A only, for `a_offset` and hand joints), the public calibration, the public videos, `meshes/library_v3`, the 104
  candidate meshes, the probe's scoring list (`score_manifest.tsv`: label, object, path, group; no score) and the
  probe's view metadata (`views/*/probe_meta.json`: which frames the generators saw). `gj_common.guard()` refuses
  paths that match ground-truth patterns (`calib_gt`, `/gt/`, `_pf.npz`, `per_frame.*`, `score_registered`,
  `result.json`, `rows.json`, `scores.jsonl`, `table.md`, `selection.json`, `.parquet`, `mocap`, scans).
- **G-B row list:** defined by the depth audit's own `valid` flag (inference side: our poses, our hands, our meshes,
  stereo depth). `gb_rows.py` reads it from the
  committed `audit.json` summaries (18 of 19 episodes: every frame valid) and from a re-audit of ep11 with the
  unchanged `pipeline/depth_audit.py` on the same inputs (poses, depth, hands sha256 equal to the original
  `audit.json`; summary identical; invalid frames 59–65 of the blue cup) [M]. A key check against the label table read
  only its `ep, frame, obj, valid` columns: **7,835 rows, identical** [M].
- **Ground truth is read only by** `score_GA.py` (`rows.json`: `cdo`, and `gtf` for the reference bar) and
  `score_GB.py` (`calib_gt/v2/per_frame.csv`: `adds_cm` and diagnostics), after all calls of that test are done.
  Both were tested on fake answers only (§6). Their reference checks reproduced the known numbers (GT-free ρ 0.4650 and
  2 hits; depth-audit `behind` AUROC 0.6002 with CI 0.40–0.781).
- **No eval episode** is touched by either test.
- **Key:** the session proxy injects the Gemini key; no script reads, sends, prints or stores a key.

## 2. API and request format

- `POST https://generativelanguage.googleapis.com/v1beta/decisions`, model `gemini-decision-1`, body
  `{model, input: [content blocks], questions: {key: question}}`. Image blocks: base64 JPEG, `mime_type
  image/jpeg`, `resolution: "high"`. Text blocks are concatenated by the API without separators, so every text block
  ends with a newline.
- Paid tier 1 limits: 1,500 requests/min, 1,000,000 tokens/min, 50,000 requests/day. The runner stays at 1,200 RPM and
  800,000 estimated tokens/min.
- Exact texts: `questions.json` (version `gemini-judge-20261113-v1`), reproduced in §3.3 and §4.3. The runner
  refuses to send a spec whose questions differ from that file.

## 3. Test G-A (mesh selector)

### 3.1 Items
- The 104 meshes of `gen-probe/score_manifest.tsv` (Pixal3D-MV 20, Pixal3D view-0 only 4, TRELLIS.2 20, TripoSG 20,
  Hunyuan3D-2.1 20, SAM 3D 20), all in our object frame (Pixal3D outputs directly; single-image outputs as their
  GT-free Sim(3) fits to our observed points).
- Extracted from the HF store `runs/mesh-20261029-gen-f3fbeb0/results/results_gen.tar` (sha256 56986e13…). **All 104
  match the frozen `SHA256SUMS`** (commit 243b854, written before any scan read) [M].

### 3.2 Pictures
- **Tracks:** the ones the probe used (store `runs/20261025-sweep-a894083/results/sweep/base/ep<N>/poses.npz`), hands
  `runs/20261025-g1-022fece/refs/perc2m/ep<N>/hands.npz` (`a_offset` = 1 on all 8 episodes). One episode per object
  as in the probe: pot 41, lid 2, blue cup and pitcher 22, boards 23, rack 26, sweeper 31, dust pan 39, beige cup 11.
- **Camera:** colour camera `ego_cam_a` (2028 × 1520, the camera the generators' crops came from), colour frame
  j = k + a_offset for track frame k, `crops.geometry()` (T_a_rect, Ka, Da; equal to the values stored in hands.npz
  [M]).
- **Frames per object (GT-free, `ga_build.py`), identical for all candidates of that object:**
  1. usable frames: library_v3 silhouette inside the image (20 px margin); occlusion by the episode's other tracked
     objects ≤ 10 %; MediaPipe hand cover of the visible silhouette ≤ 25 %; track speed ≤ 8 mm/frame (median over 7
     frames); visible silhouette ≥ 4,000 px; **track check** (GT-free): edge support = share of the library_v3
     silhouette outline within 4 px of a Canny edge of the colour frame (Gaussian 5 px, thresholds 40/100), median over
     frames k−3..k+3, must be ≥ 0.5 × its median over the seed frames;
  2. seeds = the frames the generators were conditioned on (crop k of each single-image label, Pixal3D view k);
  3. 4 frames by seeded farthest-point sampling of the viewing direction in the object frame (largest minimum angle
     to seeds and chosen frames; within 2° of the best, the largest visible silhouette; ≥ 10 frames apart).
  The chosen frames are listed in §3.5. **The beige cup gets 2 frames, not 4:** its 26 usable frames all lie in
  frames 0–25 of ep11 (later frames fail the hand, motion or occlusion gates; none fails the track check), and the
  10-frame spacing leaves room for two. Its request says
  "2 pictures". All its candidates see the same 2 pictures.
- A GT-free overlay of library_v3 on every chosen frame (`sheet_GA_trackcheck.png`) shows the tracks on the objects in
  all 38 chosen frames [M, visual].
- **Why the track check (decided in phase 1, before any scored call) [M]:** the first build (no track check, kept in
  the scratchpad as `ga_v0_noedgegate/`) picked wooden_piece_1 frames 284, 197 and 230 of ep23, where a library_v3
  overlay shows our track off the board: farthest-point sampling is drawn to the odd poses of a lost track. Along that
  track the edge support is ≈ 0.4–0.6 up to frame ~138 and ≈ 0.03–0.26 from frame ~141 on (the guard re-detections
  of ep23 are at 155–245). The depth audit cannot flag those frames (the lost track lies flat on the table, so depth
  agrees: `behind_any` 0.037, `front_any` 0.053 at frame 284) and the probe's GrabCut IoU check does not either
  (0.80–0.83). No CD-O, scan or label was looked at for this decision; the overlay sheet is GT-free.
- **Window:** square around the library_v3 silhouette at the tracked pose, 1.4 × its longest edge (≥ 160 px).
- **Each picture:** left = real colour crop, right = ray-cast grey render of the candidate alone at our tracked pose,
  same distorted camera and same window (headlight + weak key light, white background), each 512 × 512; 6 px grey
  separator; 1030 × 512 JPEG, quality 90.
- **Request:** intro text, then 4 × ("Picture i:" text + picture at resolution `high`) (2 × for the beige cup), then
  the score question.

### 3.3 Exact texts
Input intro (`{name}` = slot name with spaces, e.g. "white pot"; `{n}` = 4):
> Object: {name}.
> Below are {n} pictures of this object, each taken at a different moment. In every picture the left half is a crop
> of a real photo from a head-mounted camera, with the object in the centre; hands or other objects may cover part of
> it. The right half is a grey, untextured render of a candidate 3-D model of the same object, drawn alone from the
> same camera at the same moment, so it should look like the object in the left half.

Before each picture: `Picture {i}:` (newline).

Question `shape_match`, type `score`, instructions:
> How well does the 3-D shape of the candidate model (right halves) match the shape of the real object (left halves)?
> Judge shape only: the overall form, the proportions, the thickness of walls and parts, and parts such as handles,
> rims, spouts, bristles, holes and slots. Ignore colour, texture, lighting and background, small differences in
> position, size or angle between the halves, and parts of the real object that hands or other objects hide.

Criteria (level 0 to 4):
0. No match: the model is a different kind of object, or a broken, fragmentary or badly distorted shape.
1. Poor match: the same kind of object, but with major shape errors, such as a missing or extra part (handle, rim,
   wall, base), clearly wrong proportions, or a large hole or blob.
2. Partial match: the overall form is right, but some parts are clearly wrong, such as a misshapen handle, walls far
   too thick or too thin, a lumpy or melted surface, or a wrong profile in some pictures.
3. Good match: the shape matches in all pictures, with only small differences in fine details or surface smoothness.
4. Near-exact match: the shape matches in every picture, including fine parts and thin features.

### 3.4 Scoring (`score_GA.py`)
- E = the answer's `score` (probability-weighted level, 0–4). ρ = Spearman(E, −CD-O) over the answered meshes.
- hits = objects whose highest-E mesh is the CD-O best (ties as in §0).
- Verdict as in §0. Reported beside it (never for the verdict): per-object ρ, regret and CD-O rank of Gemini's pick,
  object-cluster bootstrap CI of ρ (2,000 draws, seed 0), mean within-object ρ, Spearman between E and the GT-free
  metric, and the GT-free reference recomputed on the same meshes.

### 3.5 Chosen frames (from `frames_GA.json`)
| object | episode | usable / candidate frames | seed frames (generators saw) | chosen frames k (min angle to seeds and earlier picks, deg) | colour frames j |
|---|---|---|---|---|---|
| white_pot | 41 | 209 / 298 | 278, 279 | 110 (47.4), 72 (35.6), 215 (26.6), 90 (17.8) | 111, 73, 216, 91 |
| white_pot_lid | 2 | 285 / 342 | 321, 324 | 79 (9.2), 269 (4.0), 279 (3.0), 315 (0.9) | 80, 270, 280, 316 |
| blue_cup | 22 | 179 / 188 | 154, 156 | 75 (14.4), 52 (12.3), 9 (6.7), 87 (4.4) | 76, 53, 10, 88 |
| water_pitcher | 22 | 108 / 188 | 34, 174 | 7 (3.2), 110 (4.6), 17 (2.0), 32 (0.3) | 8, 111, 18, 33 |
| wooden_piece_1 | 23 | 135 / 324 | 27, 28 | 134 (8.6), 106 (4.9), 30 (1.3), 10 (1.6) | 135, 107, 31, 11 |
| wooden_piece_2 | 23 | 310 / 324 | 6, 298 | 56 (35.9), 69 (16.1), 46 (15.4), 30 (7.7) | 57, 70, 47, 31 |
| plastic_dish_rack | 26 | 77 / 157 | 138, 144 | 97 (1.4), 111 (1.1), 65 (2.0), 144 (0.0) | 98, 112, 66, 145 |
| mini_sweeper | 31 | 140 / 289 | 270 | 156 (38.0), 257 (15.0), 133 (11.3), 72 (8.1) | 157, 258, 134, 73 |
| mini_dust_pan | 39 | 187 / 318 | 0, 220, 297, 316 | 91 (23.0), 119 (17.8), 188 (9.8), 67 (9.7) | 92, 120, 189, 68 |
| beige_cup | 11 | 26 / 136 | 6 | 18 (6.5), 6 (0.0) | 19, 7 |

## 4. Test G-B (track audit)

### 4.1 Items
- 7,835 rows (episode, object, frame) = the depth audit's valid object-frames on its 19 primary episodes (0, 2, 11, 12,
  13, 18, 21, 22, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45; ep23 excluded as in the audit). File:
  `gb_rows.csv` (scratchpad, regenerable with `gb_rows.py`; sha256 in §8).
- **Tracks:** the audit's own perception tracks (guard or base sweep per episode, `refine/README_inputs.md` §2), **all
  19 sha256-identical to the `poses` input recorded in each `audit.json`** [M].

### 4.2 Pictures
- **Camera:** the rectified left camera our tracks live in (`ego_cam_c` video, `track_overlay.rectify_maps`, 1600 ×
  1000, K equal to the audit's K [M]); video frame t = track frame t = depth frame t (frame counts equal on all 19
  episodes [M]). This camera is mono (its mp4 channels differ by ≈ 2–3 grey levels), so the crops are grey.
- **Window:** square around the silhouette of our library_v3 mesh at our tracked pose, 1.6 × its longest edge (≥ 160
  px), black outside the image.
- **Picture:** left = the clean crop, right = the same crop with the external outline of the silhouette (closed with a
  9 px ellipse; every face filled) in magenta, 2 px, anti-aliased; each 448 × 448; 6 px grey separator; 902 × 448
  JPEG, quality 90. No silhouette touches the crop border [M].
- **Request:** intro text, the picture at resolution `high`, the noul question.

### 4.3 Exact texts
Input intro (`{name}` as in G-A):
> Object: {name}.
> The picture has two halves that show the same crop of one video frame from a head-mounted camera. Left half: the
> frame as recorded. Right half: the same frame with a magenta outline, the outline of a 3-D model of this object
> drawn where an object tracker places it in this frame.

Question `aligned`, type `noul`, instructions:
> Is the outlined 3-D model aligned with the real object, so that the magenta outline lies on the real object's edges?

Criteria:
- true_description: The outline follows the real object's visible edges all the way round, apart from gaps of a few
  pixels: the model has the real object's position, size and orientation. Parts of the object hidden by hands or other
  objects do not count.
- false_description: The outline is visibly shifted, rotated, tilted or scaled against the real object, follows
  another object, or lies where the object is not.

### 4.4 Scoring (`score_GB.py`)
- score = 1 − `noul`; positive = `adds_cm` > 2 (the depth audit's primary label; 1,447 positives in 16 episodes on
  all 7,835 rows [M]).
- Pooled AUROC, episode-bootstrap CI, verdict as in §0. Checks: spec rows = label-table rows; the audit's `behind`
  AUROC on the answered rows (0.600 on all rows).
- Reported beside it (never for the verdict): per-episode and per-class AUROC, leave-one-episode-out range, mean
  within-track AUROC, thresholds 1 / 3 / 5 cm, the two alternative alignments of the audit's verification
  (`adds_glob_cm`, `adds_f0all_cm`), flag rates at P(aligned) < 0.5, Spearman with `behind`.

## 5. Cost

**Dry run [M]** (`dryrun_format.py`, one request, synthetic primitives only: a mug render beside a cylinder render in
the G-A layout, and a box with a shifted outline in the G-B layout, both at `high`, with both exact questions):
HTTP 200 in 1.5 s; 2,855 input tokens = 693 text + 2,162 image (≈ 1,081 per image); **cost $0.0003**. Both answer
types came back in the documented format (`score` with `probabilities`, `legend`, `confidence`; `noul` with
`confidence`). Text runs at ≈ 3.7 characters per token.

**Estimate [E]** (image 1,081 measured – 1,120 documented; text at 3.7 chars/token):

| test | requests | tokens per request | total tokens | cost |
|---|---|---|---|---|
| G-A | 104 | ≈ 4,800–4,950 (4 images + ≈ 470 text; beige cup 2 images) | ≈ 0.50 M | ≈ $0.05 |
| G-B | 7,835 | ≈ 1,330–1,370 (1 image + ≈ 250 text) | ≈ 10.4–10.8 M | ≈ $1.04–1.08 |
| **total** | 7,939 | | ≈ 11 M | **≈ $1.1** (runner's own conservative estimate $1.15) |

Under the $5 cap, so **no subsample**. Rails: the runner stops before a request that would take the cache's measured
spend past `--max_usd` (G-A 0.5, G-B 3.0 in §7). Contingency, only if the measured spend after the first 500 G-B rows
projects above $4.5 for G-B: stop and report to the owner (no unregistered subsample). The fallback subsample, if the
owner approves it, is every k-th frame of each track (k the smallest integer bringing the projection under the cap),
the same verdict rule on that subsample.

Time [E]: G-B is token-limited, ≈ 14 min at 800k tokens/min; G-A under a minute.

## 6. Scripts (this folder) and their checks

| file | side | role |
|---|---|---|
| `gj_common.py` | inference | geometry (imported from `track_overlay.py`, `crops.py`), guard, renderer, crops |
| `ga_build.py` | inference | G-A frames, pictures and request specs |
| `gb_rows.py` | inference (+ key-only check) | G-B row list from the audit's valid flags |
| `gb_build.py` | inference | G-B pictures and request specs |
| `questions.json` | – | the exact texts, resolution |
| `run_gemini.py` | – | resumable runner, JSONL cache of every request/response, cost cap, no key handling |
| `score_GA.py` | **ground truth** | G-A statistic and verdict |
| `score_GB.py` | **ground truth** | G-B statistic and verdict |
| `dryrun_format.py` | – | the one format dry run on synthetic images |
| `make_sheets.py` | – | contact sheets |
| `frames_GA.json` | inference | G-A frame selection log (parameters, usable frames, edge support, picks) |
| `sheet_GA_white_pot.png`, `sheet_GA_objects.png`, `sheet_GB_examples.png` | – | example inputs, exactly as sent (examples chosen by model name or track position, not by score) |
| `sheet_GA_trackcheck.png` | – | GT-free library_v3 overlay on the 38 chosen G-A frames (not sent) |

Checks done [M]:
- runner on fake answers (`--fake`): all 7,835 G-B and 104 G-A specs; resume skips answered ids; a $0.01 cap stops
  after 71 requests; mixing fake and real answers in one cache is refused;
- `score_GB.py` on fake answers: AUROC ≈ 0.49 (random answers), `behind` check 0.6002; refuses fake answers without
  `--allow_fake`; the bootstrap reproduces the audit's CI exactly (0.40–0.781, 63.9 % of draws < 0.65);
- `score_GA.py` on fake answers: ρ 0.023 (random answers); the GT-free reference reproduces ρ 0.4650 and 2 hits;
  refuses fake answers without `--allow_fake`; with 10 answers removed it reports INCONCLUSIVE (missing data);
- `score_GB.py` with only 71 answered rows reports INCONCLUSIVE (missing data).

## 7. Phase-2 commands (exact)

```
S=/tmp/claude-0/-home-user-v2d-track3/c39cfb04-cc2f-58cd-b84d-df803d82b152/scratchpad/gem
W=/home/user/v2d-track3/docs/research/work/gemini-judge-20261113
PY="$S/venv/bin/python -I"
# 0. verify the frozen inputs (sha256 of specs and questions as in §8)
sha256sum $S/ga/specs_GA.jsonl $S/gb/specs_GB.jsonl $W/questions.json
# 1. G-A (104 requests), then score
$PY $W/run_gemini.py --specs $S/ga/specs_GA.jsonl --cache $S/ga/cache_GA.jsonl --questions $W/questions.json --test GA --max_usd 0.5
$PY $W/score_GA.py --cache $S/ga/cache_GA.jsonl --specs $S/ga/specs_GA.jsonl \
    --rows /home/user/v2d-track3/docs/research/mesh-2026-10-26/results/gen-probe/rows.json --out $W/results
# 2. G-B (7,835 requests), then score
$PY $W/run_gemini.py --specs $S/gb/specs_GB.jsonl --cache $S/gb/cache_GB.jsonl --questions $W/questions.json --test GB --max_usd 3.0
$PY $W/score_GB.py --cache $S/gb/cache_GB.jsonl --specs $S/gb/specs_GB.jsonl \
    --labels /home/user/v2d-track3/docs/research/work/depth-audit-20261030/calib_gt/v2/per_frame.csv \
    --calibrate /home/user/v2d-track3/docs/research/work/depth-audit-20261030/calibrate.py --out $W/results
```
- Each run command may be repeated (resume) up to three times for unanswered items; then missing items count as
  missing (§0).
- Caches (every request and response) and the pictures go to the HF store under
  `runs/gemini-judge-20261113/` after the run; the results JSON/MD and a summary go to git.
- A test is scored only after all its calls are done. G-A may be scored before G-B is run; nothing from G-A changes
  G-B.

## 8. Frozen inputs (sha256)
| file | sha256 |
|---|---|
| scratchpad `ga/specs_GA.jsonl` (104 specs; every picture pinned by sha256) | `2d3879ba5acd2e1ffcdaa0e71636a58b44b9333c7550e20ec1c76ec0a21a6ead` |
| scratchpad `gb/specs_GB.jsonl` (7,835 specs; every picture pinned by sha256) | `8f24e33a78c2aad1c8c8e8f8216091c3bf9c70fafebbbfae23d9e44f703351a1` |
| scratchpad `gb/gb_rows.csv` | `5f18f53d1037f2330a477847097fb9251394fa13dc2df4e3a122921e80715347` |
| scratchpad `ga/frames_GA.json` (copied here as `frames_GA.json`) | `b9547cd3ac5fc0f48ef84f00c308d99e6d14a5fc5e519d95fb4a166955742f54` |
| `dryrun_format.py` | `9fa4cd991c0b6ff0c9d33bf266ab4c5096689e0bb115a2b5f188e7ae51f07ab9` |
| `ga_build.py` | `c0ab175b7107f8acb0c60b41e4e9478941bcf8d4876da1bf751a24a2ef89da10` |
| `gb_build.py` | `49d54986619436158193b21937cfee895f4cb7cd4880b813b4ff5127cc174cac` |
| `gb_rows.py` | `e28884d2fdfde24743ed2a36d7fad691d43356e8f07df9e8c5029ca049cd78e2` |
| `gj_common.py` | `669cfafc90194a465858055a19ded0b8e0e22d472e082f9c161a802c523039fc` |
| `make_sheets.py` | `b7acd0fda5fade89861356bae08f756341bb4492fe4580bb99a30d6bf0367288` |
| `questions.json` | `a62f4d0db25245122d98df06a36ee4075614992c94189b81705a0913ca12d869` |
| `run_gemini.py` | `6b5fcca36175ffe50b307d46340cd5a0d4ed9a10db1e2718f7d287ad028688f6` |
| `score_GA.py` | `976899522de9546a7e1696878237732f78d7bcace62ee92d494a6865172c8615` |
| `score_GB.py` | `e8cb53c89ede2b52d1b9b2916d0e1e1a05d4cde63a363f55f390feffa039a7b2` |

## 9. What this can and cannot show [H]
- G-A tests whether a calibrated visual judge ranks shape quality better than the geometric GT-free metric. The
  judge sees only views our camera saw. On six objects the usable frames cover few viewing directions: the chosen
  frames lie within 0–2° (rack), 0.3–4.6° (pitcher), 0.9–9.2° (lid), 1.3–8.6° (wooden piece 1), 4.4–14.4° (blue cup)
  and 0–6.5° (beige cup) of the frames the generators saw (§3.5). There the judge mostly sees the side the generator
  was given, plus shading cues of the unseen shape. The pot (up to 47°), sweeper (38°), wooden piece 2 (36°) and dust
  pan (23°) show more new sides.
  Falsifier of "the judge adds information over the GT-free metric": ρ ≤ 0.4650 and hits ≤ 2.
- Renders are at our tracked pose, so a candidate whose Sim(3) registration is off looks turned or shifted; the
  question asks to ignore small differences, but large registration errors may lower the score although CD-O ignores
  them [H]. Reported, not corrected.
- G-B: the label is mostly not a camera-frame error (depth audit, "Label alignment"); a judge that sees only the
  camera frame inherits that limit [H]. The alternative-alignment AUROCs are reported for this reason.
- G-B crops are grey (mono camera). Our library cups are lumpy two-body meshes; their outlines can look wrong where
  the pose is right [H].
