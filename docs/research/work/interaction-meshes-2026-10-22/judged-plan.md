# Interaction-aware meshes: verdict and implementation plan (2026-10-22, 13 days to freeze)

Labels: **[M]** measured, **[D]** diagnostic only (public scans or mocap, read after inference, never a method input), **[E]** estimate, **[H]** hypothesis.

## 0. New evidence: what each design does to the score

Before scoring the designs I ran the kit's own CD-O scorer, `metric_code/track_3/CD-O.py` `_object_chamfer_cm` (Sim(3) registration, 3 seeds). The public scans stand in for the hidden scans. Script: `/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/judge/cdo_proxy.py`. All numbers in this section are [D], in cm, lower is better.

| Object | Library (v2; v4 boards, v3 sweeper) | Design O mesh | Interaction carve, before → after |
|---|---|---|---|
| lid | 0.415 | 0.385 (4c12) / 0.368 (4 mm only) | joint min-cut, single-episode ep2 rebuild: **0.565 → 0.726** (8 → 14 pieces) |
| dust pan | 0.333 | **0.251** | – |
| board 1 | 0.223 | 0.189 | XCarve on the ep24 per-episode grid: 0.230 → 0.232 |
| board 2 | 0.220 | 0.227 | XCarve: 0.508 → 0.520 |
| pot | 0.440 | **0.727 (regression; caught by the evidence gate)** | – |
| blue cup / beige cup / pitcher / rack / sweeper | 0.526 / 0.865 / 0.885 / 0.557 / 0.314 | not prototyped | – |

- **Library mean: 0.478 cm.** Leaderboard: 0.313 (Zihao), 0.065 (SoySauceChicken).
- Caveat: library files with more than 4096 faces were scored without the packer's decimation.

**What CD-O covers.** It averages over the 36 eval (episode, object) pairs in `data/track_3_evaluation_objects.json`:

| Object | Eval pairs |
|---|---|
| wooden_spoon | 10 (no public scan, no public episode) |
| white_pot | 6 |
| blue_cup | 5 |
| plastic_dish_rack | 5 |
| beige_cup, mini_sweeper, mini_dust_pan, the two boards | 2 each |
| white_pot_lid, water_pitcher | 1 each |

The board joint shows up in exactly one eval episode (25); lid-on-pot in one (1).

**Conclusions:**
1. **Interaction carving improves physics, not mesh quality.** On CD-O it was neutral for XCarve and harmful for the min-cut on the lid [D]. Its value is sim validity: the slots, start-state overlap and standing. That only pays off where the policy actually reaches the interacting state. ep24 is currently limited by learning the lift and stand-up (0.23–0.31), so this payoff is [H] until a GPU A/B shows it.
2. **The dominant defect everywhere is thickening and filled cavities.** 51% of the 2,940 cm³ excess lies within 4 mm of the scan surface. Only observation-first fusion acts on it, and it is the only design that covers the spoon and the per-eval-episode re-fusion the owner decided on (11:20).
3. **No mesh fix currently reaches the simulator reliably.** At the assembled ep24 pose, FlashCHORD's CoACD (threshold 0.05) gives 16.9 cm³ hull overlap for the v4 boards and 17.0 cm³ for the slotted O boards [M]. The hull volume is 300.6 cm³ against a 164.1 cm³ mesh. Threshold 0.01 still gives 8.7 cm³. CoACD's concavity measure barely registers an 8 mm slot (about a 4 mm Hausdorff gap), and its result depends on the mesh: XCarve's boards gave 0.56 cm³ and Design J's synthetic boards 0.0–0.04 cm³. A collision-geometry stage is mandatory.

## 1. Scores

Scale is 1–10, 10 is best. For Risk, 10 means safest; for Effort, 10 means cheapest. The weighted total counts gain ×3, robustness ×2, risk ×1 and effort ×1, because CPU is free and the calendar is 13 days.

| Design | Gain | Robustness | Risk | Effort | Weighted |
|---|---|---|---|---|---|
| 1 XCarve (minimal carve + support rule) | 3 | 6 | 7 | 8 | 36 |
| 2 Joint min-cut | 3 | 5 | 5 | 6 | 30 |
| **3 Observation-first** | **7** | 6 | 5 | 4 | **42** |

**Design 1, XCarve:**
- Slot fixed on real ep24: 80/52% → 11/0% slot fill; overlap with our tracks 2.86 → 0.0 cm³.
- The support rule rediscovered both hand-made patches: the sweeper within 2.2° of library_v3's up vector, board 2 within 1.1° of library_v4's.
- ep18 negative control: nothing carved.
- Limits: CD-O neutral; acts only on boards and lid/pot; its "library only, no per-eval carving" rule conflicts with the owner's decision.

**Design 2, joint min-cut:**
- Principled, and its GT-free track-error statistics separate the ep0 track from the good cases: observed-carve share 3.7–6.4% against 0.26–1.45%.
- Never tested on real ep24.
- Without the halving prior it cut board 2 in two.
- It made the lid's CD-O worse (0.565 → 0.726) [D].
- The support term S5 is untested.

**Design 3, observation-first:**
- Fixes the dominant defect: lid excess 231.8 → 70.6 cm³, dust pan 117.4 → 39.6 cm³, CD-O gains of 0.03–0.08 cm on three objects [D].
- The only design that opens the board slot from the cameras themselves: silhouette free votes cover 89% of slot voxels against 1% of solid wood [M].
- Assembled overlap 1.0 cm³, below the scan-on-scan floor of 1.4 cm³.
- Weaknesses:
  - pot regression (holes);
  - not yet tested on the four worst CD-O objects (cups, pitcher, rack: 13 of the 36 pairs);
  - the largest code change of the three.

## 2. Winner and grafts

**Winner: Design 3 is the backbone.** The owner's idea becomes its interaction step, built from Design 1's rules and guarded by Design 2's gates. The pieces taken from each:

- **From Design 1:**
  - the insertion split R2: it resolves the 5.4 cm³ of board 1 that Design O's residual step left contested with strong evidence on both sides;
  - R1, "closing loses", as the only rule allowed unvalidated on eval episodes;
  - the persistence gate K ≥ 5 sampled frames;
  - known-free forcing of carved voxels (+0.25 after the Gaussian);
  - `auto_rest` as the support rule, limited to unknown or weak voxels;
  - G0 compliance and G6 registration gates.
- **From Design 2:**
  - track-error gates: observed-carve share ≤ 2%, contested share ≤ 0.25;
  - the hull re-check loop after decomposition.
- **Parked:** the min-cut solver. Revisit it only if a three-object or nested case defeats the XCarve rules.
- **New stage:** simulator collision geometry that we control (S5).

## 3. Stages, in order

S5 can run in parallel with S1–S4, since it only needs meshes. All thresholds are initial values: calibrate them on public episodes only, then freeze them before any eval run.

### S0. Prerequisites (0.5 day)

**(a) What to build**
- `pipeline/recon_mesh.py`:
  - line 89: `np.linalg.svd(..., full_matrices=False)`. Today it allocates N×N: about 2 GB on real data, 45 GB on clean synthetic depth;
  - add `--save_grid`, an npz of all accumulators;
  - split lines 241–299 into `classify()` and `mesh_out()`;
  - G0: refuse any `--others`, template or input path under the public-scan or mocap directories.
- Port `cdo_proxy.py` into `pipeline/mesh_diag.py`, next to the defects and census tools. It is diagnostic-only, kept separate from method code.
- Fetch the depth caches that are not local from the HF store, as float16, every 2nd frame (as Design O did for ep23/24): ep11, 12, 13, 21, 22, 31.

**(b) Gate:** G0 is a hard fail.

**(c) Diagnostic:** the CD-O proxy reproduces the table in §0 within 0.01 cm.

**(d) Falsification:** none; this is infrastructure.

**(e) Cost:** under 2 CPU h, $0.

**(f) Decision:** the baseline every later stage is measured against.

### S1. Observation-first fusion core, with a fallback per object

**(a) What to build.** In `recon_mesh.py`, port `obsfuse2.py`, `obspost2.py`, `localfb.py` and `gate_ev.py`:
- grid: 2 mm voxels inside a region of interest (`--roi`, the first-pass mesh plus 4 cm);
- truncation cascade 4 → 12 mm: the 4 mm field where it has ≥ 3 votes, otherwise the 12 mm field, flagged "thickness unobserved";
- `NF3`/`NV` free-space counters;
- "adj" closing: fill an unknown pocket only if ≥ 50% of its boundary is observed-inside, and never fill voxels seen free;
- below-table becomes a counter `NB` that only blocks closing, using one plane per rest window rather than per frame. Today's per-frame `below_carve` erased board 2's real wood: TSDF mean +0.9 with it, −0.7 without, and 126 cm³ missing [M][D];
- marching cubes on the continuous TSDF;
- decimation that keeps the mesh watertight.

New hypothesis for the pot: set the truncation per object as max(4 mm, 2.5·σ_eff), with σ_eff from the surface moments [H].

**(b) Gates.** If any fails, that object falls back to today's rules at 2 mm.
- Unexplained evidence ≤ 0.05. Measured: pot 0.234 fails; others ≤ 0.024.
- Watertight, one main component, ≤ 4096 faces.
- Stable at every observed unassisted rest where the fallback mesh is stable.

**(c) Diagnostic thresholds, all 10 objects with public scans:**
- CD-O proxy no worse than the library by more than 0.02 cm on any object;
- mean CD-O proxy improves by ≥ 0.04 cm (from 0.478);
- volume outside the scan's hull falls on every object.

**(d) Falsification:**
- If ≥ 2 of blue cup, beige cup, pitcher and rack fail the gate, or none of them improves by ≥ 0.03 cm, then observation-first is only a thin-plate fix. Keep it for the objects that pass and today's mesher for the rest.
- [H] adj closing opens the blue cup's interior. Falsified if the cavity stays more than 30% filled; the defects study measured 37%.
- [H] σ-adaptive truncation fixes the pot. Falsified if the pot still has unexplained evidence above 0.05 or a CD-O proxy above 0.44.

**(e) Cost:** 1.5 days of work; about 4–6 CPU h, measured at 1.5–13 min per object and episode; $0.

**(f) Decision:** the mesher for library_v5 and for eval re-fusion. Closes task #11.

### S2. Silhouette free space

**(a) What to build:** port `maskfuse.py` into `recon_mesh.py` behind `--video`.
- The colour model comes from our own first-pass mesh's visible samples.
- The depth occlusion test stays in place.
- A partner of the same colour never votes free.
- Free when `NMF ≥ 3` and `NMF ≥ 0.5·NMV`. This overrides depth saying "inside".

**(b) Gates, ground-truth-free.** The silhouette is turned off for an object when either fails:
- false-free share on 4 mm strongly-observed inside voxels ≤ 2% (measured: board 1 1%, board 2 0%);
- an object-versus-background colour contrast test.

**(c) Diagnostic:**
- slot fill ≤ 0.2 for each board (measured 0.00 / 0.05);
- real material removed ≤ 2% of the scan volume per object;
- CD-O proxy no worse than S1 by more than 0.01 cm.

**(d) Falsification:** if the white objects (pot, lid, cups) show false-free above 2% even with the contrast gate, the silhouette is limited to objects that pass the contrast gate.

**(e) Cost:** 0.5 day; 2 min per object and episode; $0.

**(f) Decision:** whether slots and narrow gaps are recovered from observation, with interaction as backup.

### S3. Interaction exclusion (the owner's idea)

**(a) What to build:** new `pipeline/xcarve.py`, from `minimal/xcarve.py` plus `obs/resid.py`, run on saved S1/S2 grids. Claims are summed over every public episode where both objects are tracked.
- Only voxels that are weak on one side may be carved: closure-only, coarse-only or unknown.
- R1: closing loses.
- R2: insertion split across the motion. An insertion is travel > 2 cm with straightness > 0.7.
- R3: evidence ratio ≥ 2.
- Ties are not carved; they are reported.
- S2MDF projection (d₁ + d₂ ≥ 0) is the last-resort tie-break at the end-state pose only. It is never the partition rule, because it splits the slot column diagonally.

**(b) Gates:**
- G1, relative-pose jitter: drop static-segment frames more than 5 mm from their 9-frame median.
- Strong contested volume on both sides ≤ 5% of the smaller solid or ≤ 10 cm³; otherwise skip the pair.
- Observed-carve share ≤ 2%, contested share ≤ 0.25.
- K ≥ 5 sampled frames.
- Carve ≤ 10% of the solid, with the number of components unchanged.
- G6: registering the carved mesh to the uncarved one moves it by ≤ 2 mm and 2°.

**(c) Diagnostic:**
- ep23 and ep24 assembled overlap ≤ 2 cm³ with our tracks;
- ep2 closed overlap ≤ 7.6 cm³ (the scan-on-scan overlap under mocap);
- ep18: 0 carved; ep31: the rack loses ≤ 1 cm³;
- ep0 (flipped lid) and ep26 (broken rack track) are rejected by the gates;
- the CD-O proxy of every carved object gets no worse by more than 0.01 cm.

**(d) Falsification:**
- If ep0 passes the gates, the gates are not protective: carving is not allowed on eval episodes.
- If the CD-O proxy gets worse by more than 0.02 cm on any carved object, the carve goes only to the collision copy (S5), never to the submitted mesh. That needs the owner's OK.
- If S1+S2 alone already give ep24 ≤ 2 cm³, the interaction step becomes only a safety net.

**(e) Cost:** 1 day; seconds per pair; $0.

**(f) Decision:** whether the owner's idea changes the submitted meshes or only the physics copy, and which rules may run on eval episodes. Proposed: R1 always, R2 only when an insertion is detected and G1 passes, parameters frozen.

### S4. Support rule (replaces the hand patches)

**(a) What to build:** new `pipeline/rest_support.py` from `minimal/auto_rest.py`, reusing `flatten_base.flatten` (lines 16–22).
- Flattening edits only unknown or weak voxels.
- The rest-detection threshold scales with each track's own jitter. This fixes the missed ep18 f189–352 rest (1.75 mm/frame jitter against a 2 mm threshold).

**(b) Gates:**
- accept only if stable at the observed rest and no other observed rest regresses;
- G6 registration ≤ 2 mm and 2°.

**(c) Diagnostic:**
- reproduces library_v3 (sweeper) and library_v4 (board-2 edge) within 3°, with margin > 0;
- the 5 already-stable cases stay untouched;
- every scan pose with a tip angle of at least 2° has one of ours within 10° that is also stable;
- CD-O proxy no worse by more than 0.01 cm.

**(d) Falsification:** a Newton/MuJoCo drop test at the observed rest. If a mesh the rule accepts still tips more than 3° within 2 s, the hull-stability test does not predict the simulator; switch acceptance to the drop test.

**(e) Cost:** 0.5 day; 1 CPU h; $0.

**(f) Decision:** retire hand-made `flatten_base` runs and the v3/v4 patches.

### S5. Collision geometry we control

**(a) What to build:** new `pipeline/collision_decomp.py`.
1. Run CoACD on our mesh.
2. For each hull, measure the volume of known-free voxels inside it: carved, silhouette-free, `NF3 ≥ 2`, below-table.
3. Re-split any hull holding more than 0.3 cm³ of them: CoACD on that hull's part of the solid at a lower threshold, with a voxel-box fallback.
4. `make_assets.py` writes one `<collision>` element per convex piece.

First verify three things on CPU:
- the kit evaluator takes object URDFs from our reference (`mkref --assets`);
- Newton loads several collision meshes per link as separate shapes;
- FlashCHORD's per-shape CoACD (`scene/objects.py:159–178`) returns an already-convex piece as one hull.

**(b) Gates:**
- hull-union volume ≤ 1.15 × the solid's volume;
- known-free volume inside hulls ≤ 0.5 cm³;
- ≤ 32 hulls per object;
- hull overlap at static co-located frames ≤ 1 cm³.

**(c) Diagnostic:**
- ep24 assembled hull overlap ≤ 1 cm³ (v4: 16.9);
- ep2 lid/pot ≤ 2 cm³;
- 64-world build no more than 2× today's (4.2 s, 0.61 GB).

**(d) Falsification:** CPU replay of the ep24 end state with `replay_probe`/`contact_probe`. If the boards held at the tracked relative pose separate by more than 2 mm, or FlashCHORD re-decomposes our pieces, the only route left is FlashCHORD's decomposition config. That is an owner decision, since it is evaluator-side.

**(e) Cost:** 1 day; 1 CPU h; $0.

**(f) Decision:** whether shape fixes reach the rollout at all. Without S5, S3 and S4 change nothing in simulation.

### S6. library_v5, compliant

**(a) What to build:** `ops/build_library.sh`, from the scratchpad `recon_library2.sh`, `man2.txt` and `finalize_lib.sh`.
1. Pass 0 with `--others` set to none.
2. Pass 1 with our own pass-0 meshes as `--others`.
3. S1 → S5, then `mesh_color`.
4. Write `meshes/library_v5` plus a manifest of inputs and the commit.

Every object fuses all of its public episodes; the boards use both ep23 and ep24. Tracks come from `perc2m`: public episodes re-tracked with our own meshes, iterated once.

**(b) Gate:** G0. The manifest must show no scan-templated tracks.

**(c) Diagnostic:** rerun the defects, census and CD-O proxy against v2/v4. Registered AUC (`score_registered.py`) per public episode ≥ v2/v4 − 0.01.

**(d) Falsification:** if v5 built on perc2m tracks is worse than v5 built on scan-templated tracks by more than 0.03 cm in mean CD-O proxy, tracking quality is the bottleneck: run perc2m once more.

**(e) Cost:** 1.5 days; 6–10 CPU h. perc2m re-tracking of the 20 public episodes ≈ $3–6 GPU [E].

**(f) Decision:** v5 replaces v1–v4 everywhere: `LIB` in `train_eval.sh` and `own_eval.sh`, which still default to v1. This unblocks a compliant submission.

### S7. Per-eval-episode re-fusion and the spoon, rehearsed on public twins first

**(a) What to build:** `pipeline/eval_mesh.sh`.
1. Eval tracks seeded by v5 → S1 and S2 on that episode.
2. S3's safe subset with frozen parameters → S4 → S5.
3. Spoon: no library mesh exists, so bootstrap a template from the first frames (mask plus depth), then track → fuse → track once more. Silhouette and the 4 mm truncation are essential, because a thin handle at today's 12 mm truncation becomes a rod about 2 cm thick.

**(b) Gates:**
- all frozen gates from S1–S5;
- consistency check, CD-O-style distance between the eval mesh and the v5 mesh ≤ 0.3 cm;
- on failure, fall back to the v5 mesh. This needs the owner's OK: he said "library only as a tracking seed".

**(c) Diagnostic:** run the whole chain on public twins as if they were eval episodes (no ground truth until scoring). Twins: ep2→1, ep24→25, ep18→19, ep11→10, ep12→14, ep27→28, ep31→30, ep21→20, ep39→38, ep41→3/5/6.
- per-episode CD-O proxy ≤ v5 + 0.03 cm;
- registered AUC ≥ v5 − 0.01.

**(d) Falsification:** if per-episode meshes are worse than v5 on at least half of the twins, submit v5 for the known objects and re-fuse per episode only for the spoon.

**(e) Cost:** 2 days; 0.5–1 CPU h per episode. GPU falls inside the planned eval perception run (owner plan ≈ $60).

**(f) Decision:** which mesh source to use per (episode, object) in the submission. Closes task #13.

### S8. GPU A/B of the physics effect

**(a) What to build:** `ops/jobs/hard_ab.sh` with v5 assets against v4 on ep24 and ep18, plus ep2 as a control. Seed 42, 250M steps, 6 repeat evaluations each.

**(b) Gate:** `sim_vs_ref` needs no ground truth (correlation 0.98 with AUC).

**(c) Diagnostic:** registered AUC for v5 ≥ v4 on ep24 and ep18, and ≥ v4 − 0.02 on the control.

**(d) Falsification:** if v5 does not beat v4 on ep24, slot physics is not the limit (learning the lift is). Stop investing in interaction physics.

**(e) Cost:** ≈ $8–12 [E], at about $2 per training plus the evaluations.

**(f) Decision:** use v5 assets in the final eval run (owner plan ≈ $70).

## 4. What to stop doing, and where v3/v4 fit

**Stop:**
- **Hand-made per-object patches.** `flatten_base` with hand-picked frames was how v3 and v4 were made. Its `flatten()` function stays, but only as the primitive that `rest_support` calls.
- **Public scans as `--others`** (all of v1–v4), and scan-templated tracks as fusion input.
- **Single-episode builds when more episodes exist.** The boards used ep23 only, although ep24 has better slot views.
- **Today's defaults:** 12 mm truncation with fill closing, a Gaussian on the binary solid, and per-frame `below_carve` free votes.
- **Trusting CoACD at threshold 0.05** to keep narrow features.
- **Carving with hand capsules** (conflict is about equal to the carve; ShapeGrasp reports the same failure) **or from compliant bristle contacts.**
- **Treating track errors as shape evidence:** the ep0, ep11 and ep26 overlaps.
- **Judging mesh changes by overlap or excess volume alone.** Always add the CD-O proxy and registered AUC.
- **Further min-cut development for now.**

**v3/v4:**
- They are not compliant, because they were built on v2 boards and sweeper fused with scan `--others`, so they must not be submitted.
- They stay as the A/B baseline and as the regression targets for S4: `auto_rest` must reproduce their up vectors within 3°.
- v4's edge flattening does not touch the joint (+0.15 cm³ overlap).

## 5. Schedule (about 13 days)

| Days | Work |
|---|---|
| 1 | S0; baseline eval submission with the current pipeline as insurance (owner step 1) |
| 2–3 | S1 on all 10 objects |
| 4 | S2 |
| 5 | S3 and S4 (S5 in parallel) |
| 6–7 | S6, including perc2m |
| 7–9 | S7 and the spoon |
| 8–9 | S8 |
| 10–12 | final eval run |
| 13 | buffer |

Mesh work is CPU only. GPU for this plan: perc2m ≈ $3–6 plus A/B ≈ $8–12 [E], on top of the owner's planned eval runs.

## 6. Owner decisions needed

1. Fall back to the v5 mesh on eval episodes when the per-episode mesh fails its gates.
2. Allow a collision copy that differs from the submitted mesh (same body frame), if S3 harms CD-O.
3. Approve the GPU for perc2m re-tracking (≈ $3–6) and the S8 A/B (≈ $8–12). The organisers' answer on using scans for tracking is still pending.
4. If S5 fails, decide whether to change FlashCHORD's decomposition config.

Prototype sources to port, all under `/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/`: `obs/` (obsfuse2, maskfuse, obspost2, localfb, gate_ev, resid), `minimal/` (xcarve, auto_rest, coacd_check), `joint/joint_cut.py` (gate statistics only), and `judge/cdo_proxy.py`, which I added this session to measure §0.