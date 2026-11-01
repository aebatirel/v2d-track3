# Eval-10 retrain on cavity-safe collision pieces: pre-registration (1 Nov 2026; written before any result)

**Status.** CPU build only. Nothing has been launched or rented. No training, rollout, overflow count, lift or score of this
test exists. This file is committed with the code before the launch and must not be edited after it; later notes go to
BUILD.md or to dated amendments appended below section 12. The njmax-1024 diagnostic (`../eval10-njmax-20261101/`, run
`20261101-e10nj-451b82d`) was running while this was written; its result was not read for this document and does not
change it.

**Go.** The owner's go, relayed by the orchestrator (focused-pascal, 1 Nov ~05:15 UTC), with seven conditions. All are
built into this rule and the job: pack-eligible config (section 2.5), the pack-9b swap rule and seed choice (sections 3.3, 5),
the training-box gate (section 4), the lift clause (section 5.3), the binding pack-10 inclusion bar (section 5.2), disclosure
of the failed mesh gate (section 2.2), and the cost (section 10).

**Labels.** [M] measured, [R] read from another lane's committed record, [E] estimate, [H] hypothesis. Eval 10 has no ground
truth. Nothing here reads mocap, scans or `observation.objects`. Every score is GT-free, against our references V (e10v's
trained V4p reference) and P (the packed gl10A2 reference).

## 1. Evidence and hypothesis
- [M] Run `20261031-e10v-caf38fb` (eval-10 V4p retrain, `ops/jobs/ev10_v4p.sh`, commit caf38fb) read **NO-SWAP [EQUAL
  FLOOR]**. Its 10 official draws score mean sim_vs_ref **0.4593** vs V and 0.4486 vs P. The packed policy's 10 fresh draws
  (H5p7) score **0.4632** vs V and 0.4525 vs P. Both fail every draw (RPE ~15.9 cm). Training-box means were 0.4524 (s42) and
  0.4512 (s43) vs V.
- [M] The beige cup is the one the reference lifts (~23.5 cm) and nests into the resting blue cup. In e10v it is never
  lifted: beige r1 lift 0.0-0.3 cm at 13 of 14 curve checkpoints, 2.5 cm once (a knock).
- [M] e10v's training logs hold 6,010,501 (s42) and 5,846,480 (s43) "nefc overflow" lines against njmax 512. The packed
  eval-10 run `20261026-gl10A2-5e0e100` holds 8,368,544. Scored draws hold 0. The packed collision pieces
  (`meshes/carve/ev10`) overlap at the nested rest (11.9 cm3 median at f124-f160 [R]).
- [R] New pieces ev10cs4 / ev10cs5 (bold-albattani, cavity-safe; section 2.2). In FlashCHORD at sim=rl (determined-wright):
  32 worlds x 60 steps, 0 / 0 overflow lines for both (ev10cs4 hold max 448, overall 459; ev10cs5 503 / 504). The nest test
  (ev10cs4 on P, driven): the beige tracks the reference nest at 0.14 cm median against 1.02 cm with the packed pieces.
- **[H-cs]** The packed pieces' nested-rest overlap makes the cup-in-cup contact need more than 512 constraint rows in
  training, and MuJoCo-Warp drops the rest. With pieces that do not overlap at the nested rest, training at the stock limits
  is clean. The learner can then lift and nest the beige cup, and eval 10 leaves the static floor on both references.
- **Falsifiers, in order:**
  1. A training log has more than 1,000 overflow lines: the pieces are not clean at 4,096 worlds (section 5.4).
  2. Both training logs are clean, but the beige r1 lift stays below 5 cm at every curve checkpoint of both seeds. Then the
     dropped rows were not the main cause of the floor.
  3. The training-box gate is not met (section 4), or the swap rule fails (section 5).

## 2. Design (fixed now)
### 2.1 Box and job
- One RTX PRO 6000 (96 GB) on demand, snapshot `pt2.11-cu130-py313-20261020`.
- Job: `ops/jobs/ev10_cs.sh` at the launch commit. Run id `<date>-e10cs-<sha7>`; the job refuses any other.
- Job string: `PIECESET=<set> bash ops/jobs/ev10_cs.sh`. The job refuses a set other than ev10cs4 / ev10cs5. Nothing else
  can be overridden from the job string.

### 2.2 The collision pieces (the one changed input) and the set-choice rule
- Both sets are imported as `meshes/carve/<set>/`: a byte copy of the mesh lane's frozen folder, an md5 manifest
  (`MD5SUMS`), the lane's own `FROZEN.md` and a `PROVENANCE.md`.
  - **ev10cs4**: from `origin/claude/bold-albattani-6qmxsv` commit fa2ec41 (built 7e4bc6a). MD5SUMS md5
    `c745ebc8c3e86cadc5301a7b2351c5c1`. Blue 24 pieces, beige 21.
  - **ev10cs5**: from commit 2b016b4 (built 7935261). MD5SUMS md5 `045d8921d5fe548ffebbee3cc21e798b`. It is ev10cs4 with the
    blue floor plate at 8 mm instead of 6 mm.
- **Set-choice rule (pre-stated; design-test numbers only, never an eval result).**
  - **Primary: ev10cs5**, used if all three hold:
    - (a) every piece other than the blue floor plate (`blue_cup/piece_16.obj`) is byte-identical to ev10cs4 by md5. The four
      records that follow the plate may differ: `blue_cup/inertia.json`, `blue_cup/lathe_collision.json`, `carve.json`,
      `FROZEN.md`. Every beige_cup file must be identical. Checked by `tools/e10cs_pieces.py compare`.
    - (b) determined-wright's FlashCHORD 32 x 60 contact-budget recheck on ev10cs5 shows 0 / 0 overflow lines (sampled and
      explicit resets).
    - (c) both (a) and (b) are in by 06:30 UTC on 1 Nov.
  - **Otherwise: ev10cs4**, frozen at fa2ec41.
- **Application (recorded 1 Nov ~05:40 UTC, before any result of this test):**
  - (a) holds [M]: 46 of 51 files are identical. The differing files are piece_16.obj (22.665 -> 30.933 cm3) and the four
    records. `cpu/out/pieces_compare_cs5.json`.
  - (b) holds [R]: determined-wright commit be1e893 (05:23 UTC), contact_budget/README.md "ev10cs5 check": 0 / 0 lines at
    32 x 60, sampled hold max 503 (median 467), explicit max 504. Headroom is 8-9 rows, against ev10cs4's 53-64.
  - (c) holds: ev10cs5 was frozen at 05:16 UTC and checked at 05:23 UTC.
  - **The set is ev10cs5.** The job takes it as `PIECESET=ev10cs5`. The job re-checks MD5SUMS against the pinned md5 and
    clause (a) on the box, and records the set, its manifest and the URDF inertials in `summary.json`.
- **Provenance, failed gate and trades** (details in each set's `PROVENANCE.md`):
  - The mesh lane's README says "GT-free" and "Nothing read here is a scan, mocap, a dataset `pose` field or an `*_align`
    file" [R]. `tools/no_oracle.py` accepts both folders [M].
  - **The mesh lane's gate 4a "blue kept volume" FAILS** for both sets: 0.384 (ev10cs4) and 0.402 (ev10cs5) against the
    lane's bar of 0.80. It fails for every cavity-safe set and for the packed ev10 too (0.381), because the blue visual mesh
    fills its own cavity. Accepted on the owner side because the risk that gate guards is tested directly by
    determined-wright's FlashCHORD drop / nest checks (6e32856, 4f5ff63, be1e893). The lane's A4 rules are at commit fedccf6.
  - Other trades, all disclosed: the raised cavity floor (6 / 8 mm plate); a thin release margin for ev10cs4 (5.49 of 6 mm
    in FlashCHORD, ~4 mm of margin with 8 mm); the beige settling deeper than the reference; blue outer faces up to
    3.3-3.9 mm outside the lathe profile; beige pieces 8 mm (plus up to 5.4 mm) inside its mesh; the pose floor (visual
    meshes overlap 80.6 cm3 at f124-f160 whatever the pieces). For ev10cs5 the lane's plain-MuJoCo gates 1 (max 3.9 cm3,
    bar 3.0) and 2 (f111, 3 of 16 copies over) fail. These are indicative only: plain MuJoCo over-counts against
    MuJoCo-Warp, which is the gate (b) that passed.

### 2.3 Reference: e10v's stored V, reused byte for byte
- **V** = `runs/20261031-e10v-caf38fb/refs/perc2e10v_glockt/ep10/.../ref_gl_ilc.parquet`: md5
  `5d22fc5782a919f2466988768d0708fa`, trajectory fingerprint `8f408d5101f108cda929fd3ee346e970`. Base reference
  `refs/perc2e10vmck/ep10` md5 `ca4ae8dcbc290d66ce09d6ad69a09410`.
- It is pulled through e10v's re-run manifest, as the njmax diagnostic does. Each seed trains on a byte copy,
  `refs/perc2e10css<seed>_glockt/ep10`.
- V names its URDFs as `/content/assets/urdf/<cup>_rigid.urdf`. On this box that path holds this box's make_assets build
  with the new pieces. So V trains on the new pieces with no file of V changed.
- **Did V's construction depend on the old pieces? Yes, in four places [M]:**
  - the V4p track's nest seat (`tools/nest_physics.py --pieces meshes/carve/ev10`, plain MuJoCo);
  - mkref / contact retargeting with ev10 assets;
  - grasp lock, wrist ILC and the zero-action replay / rest check in FlashCHORD with ev10 URDFs;
  - REPLAN 1 ran, but was a no-op (e10v job.log: "every object is where its reference says before its grasp; nothing to
    re-plan").
- **How much would a rebuild with the new pieces move V? [M]** On CPU, the V4p nest seat was re-run with each set on the
  same S12 output. The ev10 run reproduces mask10's V4p track exactly (md5 fa449903...). Against it, the beige moves only in
  the 45 hands-off frames after its release: by 1.07 cm median, 1.82 cm max with ev10cs4, and 0.88 / 1.63 cm with ev10cs5.
  The blue cup and every in-hand frame are unchanged (`cpu/out/seat_compare.json`).
- **Decision: reuse V.** It is the smallest change that is sound:
  1. It is one changed input against e10v: the same V, recipe, seeds and box type. A difference from e10v is then the
     pieces' effect (with their inertia, section 2.4).
  2. The training-box gate bar (0.4632 vs V) and the swap rule's V side stay defined as agreed.
  3. The rule must also hold against P, which no rebuild of V changes. P's beige sits even further from the cavity-safe seat
     (V vs P beige 1.23 cm median in the hands-off frames [M, e10v identity.json]).
  4. A rebuild would mean a new track, new B0 and new reference stages: a second large change. The orchestrator's
     condition allows e10v's V or the packed P only.
- V over P: V passed the ep11 public-twin gate (+0.142), and its seated beige is closer to the cavity-safe seat. The cost of
  the reuse is known [M]: at rest the beige can settle ~1 cm below V's beige in the last ~40 frames. That limits, but does
  not stop, a nesting policy's score.

### 2.4 Recipe: e10v's, exactly; two changed variables
- `ops/jobs/glock_public.sh` with ev10_v4p.sh's recipe lines, verbatim but for `PIECES=meshes/carve/$PIECESET` (static
  check):
  - LIB library_v3, SF 0, SETTLE 0, REPLAN 1 (unused: REUSE_REF), EVOLVE 0;
  - CURVE_REP 3, NREP 10, PAR 2, TRAIN_SLOTS 2, STEPS 70,004,736, EVAL_TIMEOUT 1200;
  - GL_ARGS as e10v; FDR rewards + VOC fix (TRAIN_ARGS byte-identical to e10v's job log, mock check); kp-400 embodiment;
  - REUSE_REF=1, REQUIRE_REUSE=1; no reference stage runs.
- Seeds 42 and 43, trained one after the other, one glock_public.sh call each. The opt-in `EVAL_CS_REF=1` allows the prefix
  `perc2e10css<seed>`.
- Stock contact limits: no `sim.*` override anywhere (njmax 512 / nconmax 256).
- **Changed variable 1: the collision pieces** (ev10cs5: blue 24 / beige 21 pieces, against ev10's 53 / 49).
- **Changed variable 2: the URDF mass properties.** make_assets.py takes each cup's COM and inertia from the pieces'
  `inertia.json` (uniform solid of the pieces, scaled to 0.3 kg). The packed ev10 set does the same, with other values. The
  pipeline's piece-derived inertia is kept, as the packed run did; copying the packed inertia would make the collision body
  and the mass properties inconsistent [M, CPU make_assets]:

| cup | quantity | packed ev10 | ev10cs4 | ev10cs5 (used) |
|---|---|---|---|---|
| blue | COM, mm | (0.73, 1.55, 2.99) | (0.54, 1.15, 15.77): +12.8 mm along the axis | (0.46, 1.04, 19.05): +16.1 mm |
| blue | ixx / iyy / izz | 9.849e-4 / 9.838e-4 / 4.405e-4 | +0.4 / +0.4 / +4.0 % | 1.0036e-3 / 1.0031e-3 / 4.448e-4: +1.9 / +2.0 / +1.0 % |
| beige | COM, mm | (1.52, 5.53, -4.17) | (1.54, 5.51, -5.57): -1.4 mm | as ev10cs4 |
| beige | ixx / iyy / izz | 8.904e-4 / 8.903e-4 / 2.990e-4 | +1.6 / +1.6 / -10.3 % | as ev10cs4 |
| URDF md5 blue / beige | | 82ff6cb8... / b994e584... (= e10v's box) | 8511f0d3... / 1a8cb9d8... | ac8d296b... / 1a8cb9d8... |

  A result therefore tests "the cavity-safe pieces with their own mass properties", not the collision geometry alone.

### 2.5 Pack eligibility (orchestrator condition 1)
- Every stored-config key of a chosen checkpoint must equal the packed eval-10 checkpoint's (gl10A2, sha256 76a12265...),
  with these exceptions: `output_dir`, `task.parquet`, `reference.parquet` (the reference) and the seed keys `reset.seed`,
  `env.reset.seed`, `training.seed`. The sim and env.sim limits must read 512 / 256.
- The collision pieces do not appear in the config. They reach training through V's URDF paths, which are checked by md5
  (section 3.1).
- [M, CPU] `tools/e10cs.py`'s own diff (the box's `cells` step) gives these results (`cpu/out/config_diff_test.json`):
  - the REAL e10v s43 checkpoint (bcc51063...) vs the REAL packed one differs only in the allowed keys, at 512 / 256;
  - a stand-in carrying this job's names gives the same result, and no_oracle accepts it;
  - a 1024 stand-in is caught, and so is an extra key.

## 3. Checks and seed choice
### 3.1 Before training (any failure: STOP, INVALID)
- **The piece set.**
  - The MD5SUMS md5 must equal the pinned one, and file set = MD5SUMS = FROZEN.md (`tools/e10cs.py pieces`).
  - For ev10cs5, clause (a) is re-checked on the box.
  - `tools/no_oracle.py` must accept the folder.
- **The assets** (`tools/e10cs.py assets`):
  - each col_NN.obj is a byte copy of piece_NN.obj;
  - the URDF inertial equals inertia.json scaled to the URDF mass;
  - each URDF md5 equals the pinned one for the set (the same command on meshes/carve/ev10 reproduces e10v's box URDFs
    [M]).
- **The seed copies** (`tools/e10cs.py arms`):
  - V md5, fingerprint and base md5 equal e10v's arms.json and the pinned values;
  - V's URDFs exist, weigh 0.3 kg and carry the set's md5;
  - e10v's packed reference, packed checkpoint and old packed draw match their md5;
  - `tools/no_oracle.py` must accept every input.

### 3.2 Per-seed verification after training (pack 9b PREREG 1.3 style; `tools/e10cs.py cells`)
- The chosen checkpoint is followed as the official evaluator loads it: saved config -> task.parquet -> this seed's copy
  (md5 = V) -> object_urdf_paths -> URDFs, each with the set's md5, 0.3 kg, under /content/assets.
- The config must pass section 2.5's diff against the packed checkpoint at stock limits. Steps must be 70,004,736 and
  reset.seed must be the seed.
- best/ must be the curve's choice, and the training-box rollouts must name its sha256.
- Status per seed: VERIFIED, INVALID or MISSING (no chosen checkpoint).

### 3.3 Seed choice (pack 9b PREREG section 2)
- Over the two seeds, each needing a VERIFIED cell with at least 8 scored training-box rollouts (NREP 10, sim_vs_ref vs V):
  1. the higher mean wins;
  2. if the means (4 decimals) are within 0.005, the lower sd (ddof 1) wins;
  3. if still tied, seed 42.
- An INVALID cell makes the run INVALID. A missing or thin seed makes it INCOMPLETE. There is no single-seed fallback.
- **Compared with e10v's rule 2:** the ordering is the same, and the job calls e10v's own `rule2` function. Pack 9b adds that
  both seeds must come from VERIFIED cells and that an INVALID cell takes the episode out. That is the rule used here: cells
  are verified before the choice, not after the confirmation as e10v did.

## 4. The training-box gate (orchestrator condition 3)
- The 10 official confirmation draws run **only if** at least one VERIFIED seed with n >= 8 has a training-box mean
  sim_vs_ref vs V **above 0.4632**. That is the packed policy's fresh-draw mean vs V [M, e10v summary.json]. The comparison
  is strict, with 1e-9 in favour of "not met".
- Otherwise the job reports **NO-SWAP ("training-box gate not met")** and ends without confirmation draws. It still scores
  the training-box draws, the packed side and the old packed draw, and reports the overflow and lift.
- The gate does not pick the seed; section 3.3 does. If the gate is met by one seed and the rule picks the other, the rule's
  pick is confirmed.

## 5. Swap rule, labels and reported clauses (`tools/e10cs.py verdict`)
### 5.1 The agreed swap rule (pack 9b PREREG section 4, verbatim; applied to eval 10 on both references, as e10v did)
> Per episode, over >= 10 fresh official draws, GT-free: (a) mean sim_vs_ref >= the packed policy's fresh-draw mean;
> (b) failure rate (GT-free RPE vs our reference > 5 cm, audit.py) <= the packed policy's; (c) median GT-free RPE not
> worse; secondary: new packed draw (draw 1 by position) >= old packed draw - 0.05.

How the rule is applied here:
- N = the chosen checkpoint's 10 confirmation draws on the pristine evaluator (ev10_v4p.sh confirm(): the kit's
  `run_policy_evaluation.py`, one call per draw, 1,200 s cap; at most 13 calls; stop after 3 rollout-less calls in a row).
  Draw 1 is the first call, in order, that produced a scored rollout.
- K = the packed policy's 10 fresh eval-10 draws, run `20261031-h5p7-1a7cdff`.
- Old packed draw: pack 6's eval-10 rollout (md5 64fdd856...). It is still the board pack's: 9a+ and 9b carry the same file
  [M].
- For each X in {V, P}: (a_X), (b_X), (c_X), (s_X), as in e10v's PREREG section 5. Comparisons use 1e-9 in favour of "holds".
- Scorer: `tools/e10v_score.py`, unchanged. Verdict: `tools/e10v_verdict.verdict`, unchanged.
- **SWAP-ELIGIBLE** iff every clause holds on both references, the run is verified, and n(N) >= 10 and n(K) >= 10.
  Otherwise **NO-SWAP**. A disagreement between the references is NO-SWAP.

### 5.2 Binding pack-10 inclusion rule (orchestrator condition 5)
- A SWAP-ELIGIBLE eval 10 enters pack 10 **only if** its expected sim_vs_ref gain on the episode is at least 0.02. The gain
  is defined as (mean sim_vs_ref of N) - (mean sim_vs_ref of K) **on V and on P**: both must be >= 0.02.
- Otherwise the result reads "SWAP-ELIGIBLE but below the 0.02 inclusion bar: NOT included".
- This replaces the earlier idea of a +0.05 "material" label. The rule itself is unchanged.
- The lesson behind it [M]: pack 9b's eval-33 swap passed the rule on a GT-free proxy gain of +0.0018, then scored
  about -0.016 vs mocap on the board.

### 5.3 Reported clause (not gating): lift
- The beige r1 lift is at least 5 cm at one curve checkpoint or more (`tools/e10nj.py lift`: max over frames of the
  achieved height minus the first-frame height). Reported per seed next to e10v's curves, with the blue value.

### 5.4 Overflow label (the FIRST check; the rule still applies)
- O = the "nefc overflow", "broadphase overflow" and "narrowphase overflow" lines of each seed's training log, counted by
  `tools/e10nj.py overflow`. This is the attempt that produced the checkpoints: `runs/perc2e10css<seed>_glock/ep10-s<seed>/
  train.log`.
- If a training log has **more than 1,000** such lines, the result is labelled **"pieces not clean in training"** and
  reported as such. The swap rule and the inclusion bar still apply.
- Also reported: the requested-njmax distribution, the counts in OOM-retry, curve, training-box and confirmation logs, and
  e10v's 6.0 M per seed as the baseline.

### 5.5 Label order
1. **INVALID**: a STOP; a failed check of section 3; verify failure; an INVALID cell.
2. **INCOMPLETE**: a seed missing or thin (no choice).
3. **NO-SWAP ("training-box gate not met")**.
4. The rule of 5.1: SWAP-ELIGIBLE / NO-SWAP / INCOMPLETE (fewer than 10 scored draws on either side, or the old draw not
   scored) / INVALID (identity or NaN).

The inclusion reading (5.2), the overflow label (5.4), the lift clause (5.3) and an **EQUAL FLOOR** note (both sides fail
>= 90 % of draws on both references) are attached to every label.

## 6. INVALID and INCOMPLETE
- **INVALID** means no reading. It covers any check of section 3; a confirmation draw naming another checkpoint; a failed
  own-reference check; no_oracle refusing the chosen checkpoint; a non-finite clause.
- **INCOMPLETE** means no reading. This job has no re-run mode: completing it needs a new decision. Its causes are a missing
  or thin seed, fewer than 10 scored confirmation draws, the packed side not complete on the box (then scored on CPU after,
  same tool), or the old draw not scored.

## 7. What each outcome buys
- **SWAP-ELIGIBLE and included (5.2):** the confirmation's draw-1 rollout becomes eval 10's candidate for pack 10. The pack is
  built and validated on CPU (`tools/pack_swap_rollouts.py`, no_oracle). The commit of this job is that pack's code commit.
  **The owner decides any upload, in the session where he gives the word.**
- **SWAP-ELIGIBLE but below the bar, NO-SWAP, INCOMPLETE or INVALID:** eval 10 stays as packed.
- Any next eval-10 step (for example a V rebuilt with these pieces, given the measured ~1 cm seat offset) needs its own
  pre-registration and go.

## 8. Integrity
- No ground truth exists for eval 10, and none is read. Inference (training, checkpoint and seed choice) reads our
  reference, our meshes, our pieces and the kit roster.
- Nothing is tuned on an eval result:
  - the piece set was chosen by design tests only (2.2);
  - V is e10v's, fixed before this test;
  - the gate bar and the old-draw values come from e10v's finished, pre-registered run.
- New names only: refs/perc2e10css<seed>_glock*, runs/perc2e10css<seed>_glock, results/perc2e10css<seed>_glock_public,
  results/ev10_cs. e10v's files are read and never written under e10v's result names.
- `tools/no_oracle.py` accepts this run's names and stock checkpoints (packable), and still refuses the njmax diagnostic's
  [M, `cpu/out/guard_test.json`].

## 9. Expected effect and power [E]
- If H-cs is right, the policy leaves the floor by a large margin. The ep11 public twin's true-motion reference stacks at
  0.940. A nesting policy against V would sit around 0.7-0.9 vs V. P differs in the nest, so it reads lower. Such a result
  would clear the gate, the rule and the +0.02 bar on both references by wide margins.
- If H-cs is wrong, the policy stays at the floor (~0.45 vs V). The gate (0.4632) then most likely stops the confirmation:
  e10v's seeds read 0.4524 / 0.4512 with sd ~0.017. A floor policy above the bar by noise would still face the rule and
  the +0.02 bar, which a floor cannot clear (EQUAL FLOOR, ~0 expected gain).
- The expected leaderboard effect is not estimated here. The +0.02-on-both bar exists because small GT-free gains did not
  transfer (5.2).

## 10. Cost [E]
Basis [M], e10v (`20261031-e10v-caf38fb`, the same box type, its job.log):
- 139 min for setup + V4p track and reference stages + 2 trainings + 10 draws, billed **$3.25** at $1.375/h;
- setup and inputs took 10 min, the track and reference stages 9.7 min;
- seed 42 took 54.2 min and seed 43 55.6 min (training ~47 min, curve + 10 evaluations ~8 min each);
- the choice, 10 draws, H5p7 pulls and scoring took 9.6 min.

| stage | low (h) | central (h) | high (h) |
|---|---|---|---|
| boot, snapshot restore, setup, make_assets, piece / asset checks | 0.15 | 0.20 | 0.60 |
| e10v pulls (~40 single files, ~15 MB), seed copies, guard | 0.03 | 0.06 | 0.20 |
| 2 trainings (70M) + curves (7 x 3) + 10 training-box evaluations each | 1.60 | 1.85 | 2.50 |
| 10 official draws (skipped if the gate is not met: -0.1 h) | 0.08 | 0.10 | 0.25 |
| scoring (~41 rollouts x 2 references), verify, verdict, push | 0.05 | 0.08 | 0.20 |
| **total wall** | **1.91** | **2.29** | **3.75** |
| **$ at 1.27 / 1.375 / 1.50 per h** | **$2.4** | **$3.1** | **$5.6** |

- The ledger plans **$3.50**. The high column covers a slower training (+35 %) and slow setup.
- Tail risks: a failed final push waits 60 min (+~$1.4). A STOP before training ends after setup (~$0.5-1.2, including
  run_job.sh's 30-min FAIL_HOLD).

## 11. Not covered
- A rebuilt V with the new pieces (section 2.3 has the measured seat offset).
- ev10cs4 as a second arm.
- njmax changes (the diagnostic's lane).
- Eval episodes other than 10.
- A re-run mode.

## 12. Files
Job `ops/jobs/ev10_cs.sh`; tools `tools/e10cs.py`, `tools/e10cs_pieces.py`; opt-in `EVAL_CS_REF` in
`ops/jobs/glock_public.sh`; pieces `meshes/carve/ev10cs4`, `meshes/carve/ev10cs5`; build notes `BUILD.md`; launch, ledger
and after-box steps `JOBS.txt`; CPU evidence `cpu/`.
