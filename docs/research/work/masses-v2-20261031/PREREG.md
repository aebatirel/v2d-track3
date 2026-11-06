# Masses v2 (realistic masses on 4 headroom public episodes): pre-registration

Written 2026-10-31, 15:30–16:10 UTC. At that time no box had run Masses v2 and no Masses v2 number existed. The CPU
mock (`cpu/`) uses stub trainers and evaluators; its scores are synthetic and say nothing about masses. The only scores
used here are past public-episode rollout scores (`baselines.json`), which select the episodes. The launch commit must
contain this file unchanged. Any later change is a dated amendment at the end, with its reason, made before any v2
number. Markers: [M] measured, [E] estimate, [H] hypothesis.

The physics / Embodiment session (determined-wright, session_01D9UJC7MhytodZodnDDAU3z) reviews this file before launch.

## 1. The owner's decision and rule (verbatim)
Recorded on branch `origin/claude/determined-wright-3joens`, commit 7e3311c, `docs/work-log.md`, "2026-10-31 14:55 UTC —
determined-wright: owner approved "Masses v2" re-test":

> - Owner's point: the mass check tested only 2 episodes, and ep12 (0.92–0.93) had almost no room for a +0.03 gain.
>   Owner chose "Run re-test (Recommended)": 4 public headroom episodes (not ep2/ep12, chosen by low current library_v3
>   baseline before any run), 0.3 kg vs realistic masses, seeds 42/43, NREP 10, the mass check's shared-reference design.
>   Rule: ADOPT iff mean Δ over the 4 ≥ +0.03 AND ≥ 3 of 4 Δ > 0 AND no Δ(ep) ≤ −0.05; missing cells → INCOMPLETE.
>   ≈ $18–20 [E], 2 boxes, ~7 h. If ADOPT, the eval masses retrain (~$16–26) needs its own owner go-ahead.

Also part of the approval as relayed: a reference must be available or buildable for each chosen episode; ep2's +0.157
from the first check is motivation only and does not count; a cell with fewer than 8 scored rollouts counts as missing;
a verify failure makes the run INVALID.

## 2. Question and hypothesis
- **H-mass-v2 [H]:** on our pipeline (library_v3 meshes, our perceived references, the grasp-lock training recipe of
  `ops/jobs/mass_check.sh`), realistic per-object masses (`docs/research/physics-2026-10-30/props_masses_only.json`,
  mass only) instead of the 0.3 kg placeholder raise rollout AUC vs mocap on public episodes that have headroom: by at
  least +0.03 on average over 4 such episodes, positive on at least 3, and harming none by 0.05 or more.
- **Motivation, not evidence for the rule [M]:**
  - the first check (run `20261031-mass-2ed46ea`, NOT ADOPTED): ep2 +0.157 (SE 0.105), ep12 −0.013 at a 0.92 baseline;
  - the physics session's Round 3: +0.090 mean on 4 public episodes, but with the organiser scans as simulator meshes.
- **The experiment that can falsify H-mass-v2** is this run, under the rule in section 5.

## 3. Selection of the 4 episodes
### 3.1 Rule (fixed before any v2 run; applied in `scripts/baselines.py`, evidence in `baselines.md` / `baselines.json`)
1. **Universe.** The 20 public episodes: 0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45
   (`meta/episodes_metadata.jsonl` of the public split). Excluded by the owner: ep2 and ep12.
2. **Eligible baseline.** A finished grasp-lock run on that episode that meets all of these:
   - (a) it trained the current training recipe: glock_public.sh, 70,004,736 steps, FDR + VOC, kp 400, seed 42, with the
     checkpoint chosen on the mean sim_vs_ref of 3 evaluations (CURVE_REP 3);
   - (b) its code is at or after 2c1e4dd (24 Oct, the frozen recipe's validation);
   - (c) it simulated library_v3 meshes, with no carve pieces, no other library, and no support-fill setting that a
     later pre-registered test superseded (twin21base's SF_ARC=0 was the losing arm of the arc-foot test of 25 Oct).
     References built before the arc-foot fallback existed (ev3, ev30rp, twin11v3) qualify as they are. Whether today's
     support fill would add a foot to their unstable starts (ep11's beige cup, ep24's board 2 at f62, ep31's sweeper) is
     not known. Each stored file is used unchanged, by both arms;
   - (d) the objects were at 0.3 kg;
   - (e) at least 5 official rollouts were scored as registered ADD-AUC vs mocap;
   - (f) its finished reference is in the store in the layout mass_check.sh reuses: base processed parquet and stage,
     `refs/sf/ep<N>/assets` as the single asset root with 0.3 kg URDFs, `refs/glockt/ep<N>/…/ref_gl_ilc.parquet`, and
     `results/glock_public/ep<N>/rest_check.json`.
3. **One baseline per episode.**
   - If several runs are eligible, the baseline comes from the run whose reference was built with the frozen reference
     recipe that mass_check.sh builds: SF 1, REPLAN 0, EVOLVE 1, GL_ARGS with approach 15 and the onset anchor.
   - If none was, it comes from the most recent eligible run.
   - The baseline is that run's logged mean registered AUC, to 4 decimals.
4. **Ranking.** Rank by baseline, lowest first, and choose the lowest 4. Ties (within 0.005) go to more rollouts, then the
   frozen recipe, then the lower episode number.
5. **No baseline, no rank.** An episode without an eligible run is not ranked, and no number is invented for it.
   - A fallback metric (reference-level AUC) is not needed: 8 episodes have eligible rollout baselines, so at least 4 do.
   - The Phase-1 track-level AUC (P_o, library_v3) is shown in `baselines.md` as context only.
6. **Once chosen, an episode is never swapped.** If a chosen episode fails on a box (pull, md5 / fingerprint refusal,
   training or checkpoint failure, fewer than 8 scored rollouts), its cells are missing, so the run is INCOMPLETE. The
   missing pairs are re-run on the same stored reference (section 5.3).

### 3.2 Result [M: past public scores; `baselines.json`]
| rank | episode (task) | baseline AUC vs mocap | n | run (reference) | reference recipe |
|---|---|---|---|---|---|
| 1 | **ep24** (Planter_Stand: two boards) | **0.2406** (sd 0.125, min 0.090) | 5 | 20261024-ev3-2c1e4dd | frozen |
| 2 | **ep11** (Cup_Stack: beige into blue cup) | **0.5249** (sd 0.004) | 5 | 20261025-twin11v3-0e8aebb | frozen |
| 3 | **ep13** (Cup_In_Dish_Rack: hand-over, flip) | **0.5428** (sd 0.001) | 10 | 20261030-orcB-38234d1, arm P | SF 1, REPLAN 1, EVOLVE 0 (eval 14's packed reference recipe); no frozen-recipe reference exists for ep13 |
| 4 | **ep31** (Brush_Dishrack: sweeper, rack) | **0.6951** (sd 0.122, min 0.453) | 5 | 20261024-ev30rp-07eef1a | frozen (+ DET_REPROP, now default) |
| 5 | ep21 | 0.7723 | 5 | 20261025-twin21arc-ee7ba8e | REPLAN 1, EVOLVE 0, arc foot |
| 6–8 | ep27 / ep18 / ep39 | 0.9489 / 0.9573 / 0.9579 | 5 each | ev2 / ev3 / ev3 | frozen |

**Chosen: ep24, ep11, ep13, ep31.** All four have the stored reference of the baseline run itself, so the control arm
trains on the file that produced the baseline. No reference is built on a box.
- Every store file the job pulls was checked to exist by a single-file HEAD request: 44 of 44 present on 31 Oct
  (`cpu/out/store_availability.jsonl`).
- Each reference file was downloaded once. Its md5 and fingerprint are in `refs_v2.json`, and its URDFs are at 0.3 kg.

**Not ranked, with the reason** (details in `baselines.md`):
- **ep26: older code and recipe.** It has a 0.3827 run (W1), but on code 37cc551 (23 Oct, before the frozen recipe),
  with library_v4 and a checkpoint chosen on ONE evaluation per checkpoint.
- **ep0, ep22, ep23, ep40–45: no rollout at all.** They have never had a grasp-lock rollout. Their only stored references
  are 20 Oct refsweep perceptions, from before the hands / mkref / contact-retarget pipeline.
- **Variants not used:**
  - ep11: twin11v3x (library_v3x), and orcB arm P (carve pieces ev10; asset root `/content/assets_ev10`, not a stored
    `refs/sf` copy);
  - ep21: twin21base (SF_ARC=0, the superseded control arm);
  - E-runs of 23–24 Oct (code before 2c1e4dd);
  - ep31: orcB arm P (0.7830, eligible), not used because a frozen-recipe reference with a baseline exists (step 3).

### 3.3 Sensitivity of the selection (stated now, so the reviewer can object before launch)
- **ep24, ep11 and ep13 are chosen under every reading** that requires a current-code library_v3 rollout baseline.
- **The fourth slot depends on step 3.**
  - Step 3 as written prefers the frozen recipe, which gives ep31 at 0.6951.
  - Preferring the most recent run instead would give ep31 orcB at 0.7830, which ranks above ep21's 0.7723, so ep21
    would take the slot.
  - Step 3 prefers the frozen recipe because that is what mass_check.sh builds and what the first check used: ep12's
    stored frozen reference, and ep2 rebuilt with the frozen recipe.
- **Admitting pre-frozen runs (dropping step 2b) would add ep26 (0.3827) at rank 2 and push ep31 out.** It is not
  admitted, because ep26's number is not the current recipe's:
  - its checkpoint was chosen on one noisy evaluation (on 23 Oct, E2's ep21 single-evaluation pick read 0.831 and
    averaged 0.27 over 5);
  - it came from older code;
  - it used a re-plan of a pot ejected at the start, which the current recipe does not run.

## 4. Design (fixed; the first check's design, four episodes, two boxes)
| | ep24 | ep11 | ep13 | ep31 |
|---|---|---|---|---|
| box | A (`<date>-mv2a-<sha7>`) | B (`<date>-mv2b-<sha7>`) | A | B |
| stored reference (reuse, never rebuilt) | 20261024-ev3-2c1e4dd, base `mcs` | 20261025-twin11v3-0e8aebb, base `mck` | 20261030-orcB-38234d1, base `mck` | 20261024-ev30rp-07eef1a, base `mck` |
| ref_gl_ilc.parquet md5 / fingerprint | 424a3952… / 83b9bdd4… | fbf03ebd… / 495226c2… | 414d0200… / 231ba753… | 0cdf57f7… / 3cf0e9c1… |
| objects: M0 → M1 mass (kg) | wooden_piece_1 0.3 → 0.1389, wooden_piece_2 0.3 → 0.1409 | blue_cup 0.3 → 0.128, beige_cup 0.3 → 0.1367 | blue_cup 0.3 → 0.128, plastic_dish_rack 0.3 → 0.3865 | mini_sweeper 0.3 → 0.045, plastic_dish_rack 0.3 → 0.3865 |
| frames | 275 | 137 | 190 | 290 |
| start (stored rest check) | board 2 drifts 8.3 mm / 3.9° | beige cup falls 84 mm / 65° by f11 | cup 3.7 mm / 2.4° | sweeper tips 19 mm / 19° |

Full md5s, fingerprints, URDF md5s and pull lists are in `refs_v2.json`.
- **Arms.**
  - M0 = `mass0`: the 0.3 kg placeholder.
  - M1 = `mass1`: `props_masses_only.json` (md5 d5508930…). COM unchanged, inertia scaled by m / 0.3.
  - `tools/mass_arm.py` gives each arm its own asset copy and parquet copy of the ONE shared reference, as in the first
    check. Only `object_urdf_paths` differs between the arms' parquets, and only the `<mass>` / `<inertia>` lines between
    their URDFs.
- **Recipe.**
  - `ops/jobs/mass_check.sh` unchanged in substance: REUSE_REF=1 REQUIRE_REUSE=1, 70,004,736 steps, FDR + VOC, the
    default curriculum, kp 400, CURVE_REP 3, NREP 10, PAR 2, TRAIN_SLOTS 2, EVAL_TIMEOUT 1200 (`-k 60`), one store push.
  - No reference stage runs. SF / REPLAN / EVOLVE / GL_ARGS are only logged.
  - The opt-in MV2 mode adds only the table-driven, single-file pulls with an md5 + fingerprint check, the run-id guard
    and the box-level reading (BUILD.md).
- **Cells.** 4 episodes × 2 arms × 2 seeds (42, 43) = 16, run on 2 boxes with 8 trainings each, in 4 waves of 2. Per seed
  there is one glock_public.sh call, which trains the first episode's two arms, then the second episode's two arms.
- **Box split.** A = {ep24, ep13}, B = {ep11, ep31}. Each box gets one rack episode (heavier contact) and one without,
  with 465 vs 427 frames. Both boxes use one commit, the same offer class and the same snapshot.
- **Checkpoint choice:** mean sim_vs_ref of 3 evaluations, with no ground truth.
- **Scoring:** NREP 10 official evaluations of the chosen checkpoint. Each is scored as registered ADD-AUC vs mocap
  (`score_registered.py --meshes library_v3`) and as sim_vs_ref.
- **Store traffic:** 22 single-file downloads per box (9 required + 2 optional files × 2 episodes), no store listing,
  one upload.
- **Known asymmetries, stated now.**
  - All four references were made at 0.3 kg, so masses enter RL training and evaluation only. This is the situation of
    an eval retrain on stored references, as in the first check.
  - ep13's reference was built with REPLAN 1 / EVOLVE 0 (eval 14's packed recipe); the other three with the frozen
    recipe.
  - The build variant is a property of each episode's one shared file, the same for both arms.

## 5. Rule (fixed; `tools/mass_verdict.py --rule v2`, CPU, after both boxes)
### 5.1 Definitions (as the first rule)
- Cell = episode × arm × seed.
- Cell mean = the mean registered AUC vs mocap of its scored rollouts, unrounded.
- Seed mean = the mean of an arm's two cell means.
- Δ(ep) = seed mean(M1) − seed mean(M0).
- Δ(ep, s) = cell mean(M1, s) − cell mean(M0, s).
- **Comparisons use the reported precision.** d(ep) = Δ(ep) rounded to 4 decimals, and m = the mean of the four unrounded
  Δ(ep), rounded to 4 decimals. The first rule compared unrounded values, and on its data both conventions give the same
  readings: ep2 +0.1570, ep12 −0.0128, NOT ADOPTED.
  - The two differ only within 5e-5 of a bar. There, rounding makes a reported −0.0500 fail "≤ −0.05" and a reported
    +0.0300 pass "≥ +0.03", as the owner's rule reads.
  - Unrounded floating point would read an exact −0.05 as −0.04999…, which passes (fixture R6b).
### 5.2 Verdict
- **ADOPT** realistic masses for eval retrains **iff** m ≥ +0.03 **AND** at least 3 of the 4 d(ep) > 0 **AND** no
  d(ep) ≤ −0.05. A d(ep) of exactly 0.0000 is not positive.
- **NOT ADOPTED** otherwise, naming every failed clause. The eval pipeline keeps the 0.3 kg placeholder.
- **INVALID** if any box's `mass_verify.py` fails. There is no reading, and missing cells are listed with it.
- **INCOMPLETE** if any of the 16 cells is missing (no chosen checkpoint, refused or failed episode) or has fewer than 8
  scored rollouts. There is no reading.
- The first rule's per-seed drop clause (−0.05 per seed) is NOT part of v2. Per-seed deltas are reported only.
### 5.3 Merging the boxes; INCOMPLETE re-runs
- **Inputs.** The merge reads each box's pushed run folder. Each file is a single download: per cell
  `results/mass{0,1}s{42,43}_glock_public/ep<N>/best/summary.json`, plus `results/mass_check/verify.json` and
  `arms_ep<N>.json`.
- **Pairs.** A pair (episode, seed) is taken whole, both arms, from the one box where both arms are present, verified and
  scored ≥ 8. Arms of one pair are never combined across boxes.
- **Duplicates.** A pair that qualifies in two boxes is refused (exit 2, no verdict).
- **Re-runs.** An INCOMPLETE re-run box (`<date>-mv2r-<sha7>`) runs only the missing (episode, seed) pairs, both arms. It
  uses the same table with `SRC_EP<N>=<v2 run id>:<base>:reuse`, so it pulls the same reference files from the v2 run,
  checked by md5 + fingerprint. Then the rule is applied once to the merged set.
- **Never.** No swap to another episode, no extra seeds, no re-run of a pair that has a reading.
### 5.4 Reported with the verdict (not part of the rule)
- Every cell: mean, sd, min, n, the 10 AUCs, the chosen checkpoint.
- Per seed: Δ(ep, s).
- sim_vs_ref Δ, and the rollout-noise SE of Δ (as in the first check).
- ref_auc per cell (must be equal across an episode's cells) and the static floor.
- Evaluation timeouts per cell and arm, printed after the label.
- A harm flag where d(ep) ≤ −0.03.

## 6. Verify step (unchanged: `tools/mass_verify.py`, on each box)
For each chosen checkpoint it follows the chain the official evaluator uses: saved config → `task.parquet` → reference →
`object_urdf_paths` → URDF. It checks that:
- the URDFs carry the arm's masses (COM kept);
- the reference fingerprint equals the source's;
- the arm parquets differ only in `object_urdf_paths`;
- the two arms' saved configs differ only in `output_dir` / `task.parquet` / `reference.parquet`, or by the arm's name;
- `reset.seed` is the seed and the steps are 70,004,736;
- the rollouts' `checkpoint_sha256` is the chosen checkpoint's.

Any failure makes the run INVALID. A cell without a chosen checkpoint is listed as missing, which makes it INCOMPLETE.
Timeouts are counted.

## 7. Noise and power (stated before any v2 result; `scripts/power.py`, `cpu/out/power.json`)
- **First check, per cell [M].** Rollout sd 0.29–0.37 on ep2 (bimodal) and 0.017–0.024 on ep12. The rollout-noise SE
  of Δ was 0.105 (ep2) and 0.0066 (ep12). Control seed means were 0.552 / 0.581 (ep2) and 0.928 / 0.920 (ep12).
- **The chosen episodes' baselines [M].** Rollout sd (sample) is 0.139 on ep24 and 0.136 on ep31. On ep11 and ep13 it is
  0.005 and 0.001: both sit at or below their static floor (ep11 floor 0.595; ep13 floor 0.5416, orcB).
- **Between-training sd of a cell mean [M/E].** Measured seed pairs give 0–0.10 (ep24 std-learner pair 0.099, ep12
  glock pair ≈ 0). Assumed values: 0.10 (ep24), 0.06 (ep31), 0.02 (ep11), 0.01 (ep13).
- **Model [E].** SE of Δ(ep) = √(σ_s² + σ_r²/10): 0.109 (ep24), 0.020 (ep11), 0.010 (ep13), 0.074 (ep31). SE of the
  mean Δ is 0.033.

| true Δ on every episode | P(ADOPT) [E] | P(mean clause) | P(3 of 4 > 0) | P(no Δ ≤ −0.05) |
|---|---|---|---|---|
| 0 | 0.13 | 0.18 | 0.31 | 0.51 |
| +0.03 | 0.46 | 0.50 | 0.84 | 0.66 |
| +0.05 | 0.66 | 0.73 | 0.92 | 0.75 |
| +0.09 (Round 3's mean) | 0.87 | 0.97 | 0.98 | 0.88 |
| −0.03 | 0.003 | 0.04 | 0.01 | 0.29 |
| +0.12 on ep24 and ep31, 0 on ep11 and ep13 | 0.59 | 0.81 | 0.66 | 0.92 |

- **Bounds.** With the first check's per-cell sds on all four episodes, P(ADOPT) is 0.13 / 0.49 at true Δ 0 / +0.09 if
  every episode behaved like ep2, and 0.00 / 1.00 if every episode behaved like ep12.
- **Reading [E].** About 1 in 8 chance of a false ADOPT with no effect. About two in three to detect +0.05, and nearly
  nine in ten to detect Round 3's +0.09.
- **Which clause binds.** Under noise, "no Δ ≤ −0.05" binds on ep24 and ep31. On ep11 and ep13 the sign is decided by
  small effects, and 0.0000 is not positive.
- **Predictions [H, not part of the rule].**
  - ep24 and ep31 are the most likely to move (Round 3: ep24 +0.084 with scans; the sweeper goes from 0.3 to 0.045 kg).
  - ep11's library_v3 reference starts with the beige cup falling: a mesh / stability failure that masses may not change.
  - ep13 is learner-limited: orcB with the true motion scored O = P = 0.544.
  - So ADOPT will most likely need ep24 and ep31 to rise by enough to carry the mean, and at least one of ep11 / ep13 to
    move above 0.

## 8. What each outcome buys
- **ADOPT:** realistic masses go into the eval retrains (the shelved `ops/jobs/mass_eval.sh` prep: O1 / O2, ≈ $16–26 [E]).
  - That retrain needs its own owner go-ahead.
  - Each eval policy is swapped only by its own rule: the multi-draw mean must be ≥ the packed draw.
  - Nothing goes to Kaggle without the owner.
- **NOT ADOPTED:** the 0.3 kg placeholder stays, and masses are closed for eval retrains before the freeze unless the
  owner decides otherwise. Left open, each needing its own pre-registered test:
  - references rebuilt under the masses (the physics session's condition);
  - a pot/lid-specific effect (ep2), which needs a fresh public pot/lid episode.
- **INCOMPLETE:** re-run the missing pairs (section 5.3), at about $1.5–3 per pair [E].
- **INVALID:** no reading. Fix the cause and re-run; the owner decides on that spend.

## 9. Overlaps, and why they do not confound
- **ep11 rollout gate (this session, prepared, not launched).** It trains ep11 on P_o + S2 references, control vs V4p,
  with the packed eval-10 recipe (gl10A2, SF 0, carve pieces ev10), in folders `perc2e11{c,t}*`, on its own box.
  - v2's ep11 cell trains on twin11v3's library_v3 reference in `refs/mass*` folders, on box B.
  - Different references, folders, boxes and run ids. Each experiment's contrast (control vs V4p; M0 vs M1) lies within
    its own box, on one shared file, so neither changes the other's Δ.
  - Their results meet only downstream: the eval-10 retrain plan already keeps masses-only and masses + nest arms apart.
- **The physics session's recipe screen (determined-wright, running).** It covers ep2 / 12 / 18 / 24 with physS1
  references, which are scan meshes, not library_v3. It shares ep24 with v2 by episode only.
  - It uses other references, other arms (recipe, not mass) and its own boxes.
  - Neither experiment reads the other's outputs or uses its results to select or tune.
  - They share the HF store (429 risk). v2 makes 22 single-file downloads per box and no listing.
- **The first check** contributes the code, the verify step and the noise numbers, and nothing to the v2 cells. Its ep2
  and ep12 are excluded.

## 10. Integrity
- Public episodes only: no eval episode, no Kaggle, no pack.
- **Ground truth.**
  - Mocap is read only by `score_registered.py`, after each rollout.
  - The selection used past public rollout scores only, recorded in `baselines.json` before any v2 run.
  - Nothing here tunes on eval results.
- **Masses.** They are the physics session's props, fixed before the first check (md5 d5508930…), never fitted and not
  changed. The box refuses another props file.
- **Run ids and folders.** Run ids carry `-mv2` (`-mv2a`, `-mv2b`, `-mv2r` for re-runs), and the job refuses others. The
  arm folders are `refs/mass{0,1}*` and `results/mass{0,1}s*_glock_public`, which no pack pulls.
- **This file.** The selection and rule are fixed here. The reviewer's changes, if any, are dated amendments made before
  any v2 number.

## 11. Cost (JOBS.txt)
- Per box, 8 trainings in 4 waves, no reference build. The basis is the first check: 6.25 h for 8 cells including one
  ~0.3 h on-box build.
- **≈ 5.3–7.9 h per box, central ≈ 6.2 h** [E] (waves of 75–100 min, setup 0.2–0.75 h). At $1.30 / $1.45 / $1.55 per
  hour that is ≈ $6.9 / $9.0 / $12.2 per box.
- **Two boxes: ≈ $14–25, central ≈ $18** [E]. The owner's estimate was ≈ $18–20. Wall time is ≈ 6–8 h, the boxes running
  in parallel.
- Ledger planned: $9.00 per box.

## 12. Review amendments (31 Oct 2026 ~16:45 UTC, before any launch; no v2 result exists)
Two reviews (selection/integrity: NO-GO until F1+F2; mechanics: GO). Sections 1–11 above are unchanged; the owner's rule
is unchanged. Changes, all in `tools/mass_verdict.py --rule v2` (v1 default byte-identical, re-checked):
- **F1 (blocking, fixed):** a box that never wrote or pushed `verify.json` (died, watchdog, push failure) made the merge
  read INVALID. Now its pairs are unverified, i.e. missing → **INCOMPLETE** (rerun only those pairs), as the owner's
  "missing cells → INCOMPLETE" says. INVALID needs a verify.json that exists and fails.
- **F2 (blocking, fixed):** a NaN/inf rollout AUC could produce a false ADOPT. A non-finite AUC is now not a scored
  rollout (it counts toward neither the cell mean nor the 8-rollout minimum); a non-finite Δ makes the run INVALID.
- **F3 (decision, owner's literal rule):** the clauses now compare values rounded to 9 decimals (float noise only), not
  4: "Δ > 0", "mean ≥ +0.03" and "Δ ≤ −0.05" read as the owner wrote them (so +0.00004 counts as positive; an exact
  −0.05 still fails). Reports show 4 decimals. §5.1's "4-decimal comparison" is replaced by this.
- **F4 (mechanics):** an INCOMPLETE re-run of a REFUSED episode leaves `SRC_EP<N>` unset, so the table's source run is
  used (still md5 + fingerprint checked).
- **F5 (record):** JOBS.txt was written ~15:32 UTC and this PREREG committed in 276f275 at 15:43 UTC (not "16:30" /
  "15:30–16:10"). The step-4 tie rule has no effect (only tie: ep18/ep39 at ranks 7–8). One more §3.3 reading: admitting
  twin21base with the lowest run per episode would make ep21 (0.6565) the 4th episode. The selection stays as written
  (ep24, ep11, ep13, ep31); the reviewer confirmed ep31 under 3 of 5 readings and that it is not cherry-picked.
- Evidence: fixtures 31/31 (`cpu/out/tests_v2.json`: R10 flipped to the literal rule, R10b NaN → INVALID added; v1 stored
  summary reproduced byte for byte); the reviewer's dead-box test now gives INCOMPLETE for a box with no verify.json
  (with or without interim pushes); a NaN rollout in files is dropped as unscored; a NaN Δ gives INVALID.
- Observation for the owner (from §7, restated): ep11 and ep13 sit at measured floors, so ADOPT needs one of them
  strictly above 0; P(ADOPT) ≈ 0.59 even if ep24 and ep31 gain +0.12 [E].
