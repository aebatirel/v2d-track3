# Next steps, 30 Oct 2026 (~06:30 UTC): eval-1 confirmation tonight, upload decision in the morning

Synthesis of three planners (gain per dollar, reference quality, risk). Numbers were re-checked against the cited files
or recomputed from the stored per-draw `qa_policy.json` files (CPU, no ground truth). [M] measured, [E] estimate,
LB = leaderboard AUC. Conversion [E]: +1.0 sim_vs_ref on one episode ≈ +0.038 LB (transfer 0.74–0.78, /20).

## 1. Summary for the owner
1. The eval-1 carve passed its pre-registered rule: seed 43 scored 0.931 ± 0.007 over 10 draws, against a bar of 0.852 [M]. By that plan, its pack rollout must come from one fresh official evaluation. Tonight runs that check (20 draws, ≈ $1.6) after a $0 CPU fix that stops the carved pot leaking into eval 28.
2. Kaggle scores the trajectories we submit as they are; the scorer checks provenance only for format. So pack 6's lucky draws are already banked, and the swaps add only about +0.0003 (eval 33) and +0.0004 (eval 1) on the board [E]. Their real value, about +0.007 [E], shows only if the organisers re-run our checkpoints.
3. Morning: (a) ask the organisers whether validation re-runs checkpoints and with what tolerance; (b) make one upload: pack 8, or pack 7 if tonight fails (your decision); (c) fund insurance retrains (eval 30 ≈ $8) only if re-runs count.
4. Gains we can bank on the board need episodes whose packed rollout sits at its mean: eval 10 (+0.017 if solved, low prior) and the mesh/reference side. CD-O is our worst board at 11th, and the final rank is the sum of the six board ranks. Everything here is gated on public-episode tests first.
5. Spend: about $27.5 of this session's $45 is used (ledger $21.28 + ≈ $6.2 estimated for the two eval-1 boxes). Tonight adds at most ≈ $3.5. Nothing was sent to Kaggle.

## 2. Tonight (≤ $12 cap; planned ≈ $1.6–3.5; standing overnight autonomy; nothing to Kaggle)
**Eval-1 carve result: in, PASS** (store `runs/20261030-c01s4{2,3}-328139c/job.log`, per-draw values recomputed):
- seed 43 `policy_250003456` (sha 5625b86a…): 0.9310 ± 0.0066 (ddof 1), min 0.9187, 1/10 below the packed 0.9196;
- seed 42: 0.8852 ± 0.0529.
- Rule: mean ≥ 0.8519 and sd ≤ 0.2387 (`docs/research/work/carve-20261030/RETRAIN_PLAN.md:185-194`). Both seeds
  qualify; the higher mean wins, so seed 43.
- The draws ran on the training box (`hard_ab.sh` evalrep, patched tree, 3 at a time). The evaluator hashes equal the
  official ones (b1b3ebe3 / 160d24f5).
- `RETRAIN_PLAN.md:198`: pack "ONE fresh official evaluation in the pack. Never pack one of the 5 draws." So a box is
  needed in any case. Had the carve failed, pack 7 would stay the candidate and nothing more would run.

| # | Action | Cost | Pre-registered rule | Falsifier |
|---|---|---|---|---|
| 1 | Fix the record (list below) | $0 | – | – |
| 2 | Per-episode asset root in `ops/jobs/pack_eval.sh`, plus ev01 pieces for eval 1 only in `h5_reeval.sh`; pushed before launch (blocker 2, `RETRAIN_PLAN.md:119-126`) | $0 CPU | ep1 URDFs 53/107 collision pieces; ep28 the default 43/31; evals 10/19/25/28/30 keep pack 6's asset md5 | any md5 change outside eval 1 |
| 3 | Official confirmation of eval-1 s43, N=20 (below) | ≈ $1.6 (≈ 1.05 h at ~$1.5/h; ≤ $3 if the host is slow) | pack draw 1's eval-1 rollout, by position, iff mean ≥ 0.8519, sd ≤ 0.2387 and ≤ 1/20 below 0.70; draw-1 sha = 5625b86a… | mean < 0.90 or ≥ 2/20 below 0.70: the training box does not stand in for the official evaluator |
| 3b | Optional, same box, only if the loop passes a CPU test first: 5 official draws each of 7 stored checkpoints picked by a single sweep draw (std30 180M/200M, c25s42 200M/220M, two eval-16, evb1420 50M) | ≈ $1.2 | +10 draws if the 5-draw mean ≥ H5 + 0.03 with no draw < 0.70; qualifies at a 15-draw mean ≥ H5 + 0.03 and sd ≤ H5 sd | none qualifies. Insurance only; board ≈ 0 |
| 4 | If 3 passes, build pack 8 = pack 7 + eval-1 draw 1, the same way as `results/submissions/20261030-track3g-candidate/` | $0 CPU | byte-diff touches only episodes 1 and 33; `object_mesh_b64` identical; the pushed commit holds ev01 and the item-2 code; preflight ok | – |
| 5 | GT-free depth audit, public calibration only (parallel) | $0, CPU 2–4 h | informative if AUROC ≥ 0.75 for frames with ADD > 2 cm on ≥ 8 public episodes; only then audit eval depth (`cache/depth/eval/ep*/depths_fs0.5.npy`, all 20 present [M]) | AUROC < 0.65: no reference or spoon spend |
| 6 | Optional: eval-14 zero-action replay, default vs carved reference, only if no new code is needed | ≈ $0.3 | – | replay ≥ 0.9 while policies stay < 0.7: not a reference defect |

**Item 1, fixing the record:**
- Work log 04:50: eval 33's "H5 min 0.47" is really 0.576. Its "+0.003 leaderboard" is the re-run view; on the board
  it is +0.0082 sim_vs_ref ≈ +0.0003 LB.
- `track3-requirements.md:25,148` say the ranking aggregation is undefined. The FAQ says "lowest sum of metric rankings".
- Log the carve result. Close the two c01 ledger lines at ≈ $3.2 and ≈ $3.0 [E]: 2.1 h and 2.0 h, up to the
  `run_job.log` self-destroy lines at 05:02:14 and 04:54:18; the ledger has no rate for these boxes. Confirm 0 Vast instances.
- Pack-7 README: disclose that c33B draw 1 (0.9401) ranks 9th of the 10 draws.

**Item 3:**
- Command: `N=20 PICK_EXTRA="1:20261030-c01s43-328139c:ck=runs/perc2mcks/ep1-s43/policy_250003456.safetensors"
  EPS_ONLY=1 bash ops/jobs/h5_reeval.sh`.
- Why N=20: each one-episode draw takes ≈ 80 s (c33B `job.log`), so 20 draws instead of 5 cost ≈ $0.35 more. A
  policy that still fails 18 % of the time shows 0/10 bad draws with p = 0.14, but 0/20 with p = 0.02.
- Why the official evaluator: the training box gave the *packed* eval-1 and eval-30 policies 0/10 bad draws
  (0.912 ± 0.014, 0.919 ± 0.012; `runs/20261025-std0116-ee7ba8e`, `-std30-` job logs). The official evaluator gave
  5/22 (Fisher p = 0.13).
- Write the rule into the work log before launch. Label the result "board gain" only if the mean ≥ 0.9196 (the packed
  draw); between 0.852 and 0.9196 it is an insurance trade for the owner.

**Branch on item 3:**
- **Pass:** pack 8. Board [E]: 0.8139 → ≈ 0.8142 (pack 7) → ≈ 0.8146; re-run view ≈ 0.782 → 0.785 → 0.789.
- **Fail:** pack 7 stays, and eval 1 keeps pack 6's rollout. Log the gap between the training box and the official
  evaluator as measured. Mark as "basis unverified" the training-box numbers: the eval-14 carve verdict, the recipe
  arms, and arm A's eval-33 0.906. No retrain.

**Not tonight:** retrains of 14/30/16/25, fresh full-pack draws, best-of-N, mesh changes, S2 rebuilds of eval
references. Destroy every box and leave the rest unspent.

## 3. Morning decisions for the owner
**Known:**
- **Kaggle scores the submitted pose rows as a 20-episode mean** (`metric_code/track_3/AUC.py:784-818`). Provenance
  is checked only for presence, format and uniformity; `_ACCEPTED` is empty (`AUC.py:596-731`). Nothing is re-run.
- `private_fraction` is 0 (`tracks.json`). The displayed board keeps our best [M] (`results/submissions/20261026-track3e/README.md:22`).
- **Final rank = lowest sum of the six board ranks** (FAQ). Our last recorded CD-O rank, 11th, is our worst
  (`docs/research/work/26/next-steps-2026-10-27/read_scores.md:14`).
- The submitted meshes register the pose metrics (`AUC.py:444-458,824-877`); the pitcher swap cost −0.0045 [M].
- The checkpoint hash is kept "for later validation", and top solutions must provide reproducing code
  (`docs/research/work/14/c2/faqs.txt:31-34`). Places stay provisional until verified, and a held-out evaluation runs
  after the close (`track3-requirements.md:24,149`).
- 2 final picks; unlimited uploads in the last 3 days; freeze 4 Nov 22:00 UTC (`track3-requirements.md:37,44`).
- The evaluator is not reproducible between draws [M]: H5 eval 30 sd 0.255, min 0.262. `tracks.json` assumes it is
  deterministic.

**Assumed or unknown:**
- whether validation re-runs and re-scores checkpoints, with what tolerance, and for which places;
- how much the held-out evaluation counts;
- how final picks work per board;
- the upload cap (the FAQ says 5 per week per track; 6 uploads in 3 days went through [M]);
- whether a CD-O-only upload is allowed.
- The website's "broader dataset" quote comes from the risk planner and was not re-checked here.

**Ranked decisions:**
1. **Ask the organisers ($0).** Questions: are checkpoints re-run, with what tolerance, for which places; how much the
   held-out evaluation weighs; how final picks work per board; whether CD-O-only uploads are allowed. The answers set
   the value of every variance item. The FAQ names Discord or email, and only the owner can send.
2. **One upload, one slot: pack 8 if item 3 passes, else pack 7** (`results/submissions/20261030-track3g-candidate/`,
   sha 137c8687…).
   - Board +0.0003 to +0.0007 [E]; re-run view +0.003 to +0.007 [E].
   - Worst case [E]: the swapped rollouts differ from the kept ones by 1.0–1.5 cm per object (risk planner). Through
     the scorer (ADD-AUC over 1–9 cm, 20-episode mean), that bounds the move at about ±0.008 LB per swapped episode.
   - Read the board afterwards as a transfer measurement only. Reverting rollouts by board score would tune on eval
     ground truth (CLAUDE.md), so it is the owner's call, as are the final picks.
3. **Two-level replacement rule ($0).** A swap is a board gain only if the new multi-draw mean ≥ the *packed draw*.
   Between H5 + 0.03 and the packed draw it is an insurance trade, decided by the owner. Tonight's eval-14 rule lacked
   this check: a 0.645 policy would have passed at ≈ −0.010 LB [E].
4. **Insurance retrains, only if re-runs count (skip any episode 3b already covers).**
   - Eval 30, 2 standard-learner seeds plus a 10-draw check: ≈ $7.5–8 (measured basis: ≈ 2 h and $3.0–3.3 per seed on c01).
     - Value: ≈ +0.0046 LB on re-run if a seed is stable at 0.92, so ≈ +0.002 expected [E].
     - Board ≈ 0: P(fresh ≥ packed) = 3/11 [M].
     - The v2 carve drops the sweeper through the rack; a v3 needs a CPU test first.
   - Eval 16 grasp-lock, 2 seeds: ≈ $5, re-run ≈ +0.0008 [E].
   - Park 14, 25 and 32: eval 14's six variants all scored 0.58–0.66; eval 32's three retrains scored 0.63–0.74,
     against its packed 0.866.
5. **Eval 10, the one bankable policy lever.**
   - Packed 0.456 vs H5 0.450 ± 0.007, so not lucky. Reaching 0.90 ≈ +0.017 LB [E], which passes DDD's 0.827. The
     prior is low: 7+ attempts have failed.
   - Gate: CPU diagnosis, then GPU only if the ep11 twin gains ≥ +0.05 mocap AUC on 2 seeds. Adopt if the 10-draw
     mean ≥ 0.506 with sd ≤ 0.05.
6. **CD-O-only upload** with the mesh session's pot, lid and rack meshes: 0.402 → ≈ 0.367 [E]. The rank change is
   unknown without a board snapshot. Needs the organisers' OK.
7. **Not recommended:**
   - best-of-N packing (≈ +0.009 LB [E] for a ≈ $2.5 run; breaks rule (d) and "we cannot pick and choose");
   - re-drawing only the episodes packed below their mean (selection on outcome).

## 4. Longer term (pipeline; each gated on public-episode scores)
- **S2 timing advance as a pipeline default.**
  - Evidence: adopted on public data at +0.0061, 17/20 better (`docs/research/work/refine/RESULTS.md`).
  - Wire `refine.py --steps S2` before mkref in `pipeline_ep.sh` for future builds and the held-out run.
  - Do not retrain eval policies for it: an after-the-fact +0.545-frame shift of public rollouts gains only
    +0.0004 to +0.0028 [M], below the 0.03–0.1 spread between retrain seeds.
- **Our meshes as tracking templates** (≤ $2.5, with the mesh session).
  - Evidence: with stale scan templates the tracker scores 0.993–0.998, with our meshes 0.871–0.961
    (`docs/analysis/robustness-review-20261026/refcheck/chain/README.md:160-161`).
  - Experiment: re-track 12 public episodes, both arms in one job.
  - Adopt if the mean ≥ base + 0.010, no episode drops by more than 0.02, and there are no new flips. Falsifier: a gain
    below +0.005.
  - Only then the eval route: ≈ $25–40 for +0.003–0.005 [E]. A board swap must beat svr_packed × acc_old.
- **Spoon** (10 eval episodes): its ≈ 0.067 share of the re-run loss is a fitted inference (spoon accuracy solved to
  0.805), not a measurement.
  - No spend until audit item 5 shows the error.
  - Then a hold-phase pose = wrist × grasp, validated on public thin objects (ep18/31/39/40): ≥ +0.005, no drop > 0.02.
- **Pitcher (eval 20):** a mesh-session item. Needs registration stable on ep21 and ep22, plus re-tracking with the
  same mesh. Lesson from pack 5: the twin went 0.776 → 0.874, yet the board fell −0.0045 [M].
- **Owner ideas, ranked by evidence:**
  1. SAM2 masks, first as QA (rendered-reference IoU, ≈ $3–5, same AUROC rule).
  2. A second tracker, only on spans the audit flags.
  3. A whole-clip optimizer, only as the home for depth or mask terms. The GT-free S1/S3/S4 scored −0.0077 / −0.0013 / +0.0003.
  4. VLM phases last: +0.0002 even with mocap phases.

## 5. Planner disagreements and how they were resolved
- **Official re-check of eval 1.**
  - Positions: reference planner none; risk N=5 with no draw < 0.80; gain-per-dollar N=20.
  - Chosen: N=20 with ≤ 1/20 below 0.70. `RETRAIN_PLAN.md:198` already needs a fresh official draw, and the extra
    draws cost ≈ $0.35.
- **Eval-30 retrain tonight.**
  - Positions: gain-per-dollar yes if conditions hold; reference planner "best per dollar"; risk no.
  - Chosen: not tonight. Its board value is ≈ 0, and its re-run value waits on the organisers.
  - The reference planner's "$10–12 for +0.0057" is overstated: ≈ $7.5–8, and that gain is conditional (≈ +0.002 expected).
- **Checkpoint screen:** optional 3b. It is cheap and may make retrains unnecessary, but it must not delay item 3.
- **Spend:** the reference planner's $32.4 counted the mesh session's $4.36 (ledger). This session: $21.28 + ≈ $6.2 ≈ $27.5.
- **Box destruction:** the gain-per-dollar planner said no destroy line was logged. Wrong: both `run_job.log` files
  log `self-destroy: job finished rc=0`. Still check Vast.
- **"chosen checkpoint missing; using":** it is neither a newest-checkpoint fallback nor a log/code mismatch. It comes
  from the unused base-checkpoint lookup (`hard_ab.sh:156`; BASE_EVAL=0 on eval, `:33`). The evaluated checkpoint came
  from `selection.json`, and its rollouts carry sha 5625b86a….
- **Numbers corrected:**
  - Seed 43's sd is 0.0066 (ddof 1), not 0.0068.
  - Packed-rank sums are 69/80 (expected 40, z ≈ 3.2) and 43/120 (expected 60), not 70 and 50. The luck sits in the
    8 high-variance episodes.
  - The bound "±0.0025 LB per swap" is too tight: ≈ ±0.008.
- **Bankable gains: references only (gain-per-dollar), or eval 10 too (risk)?** Both are kept: eval 10 is the one
  bankable policy lever, at a low prior.
- **Risk's post-upload revert rule:** made record-only. Acting on it would select rollouts by eval ground truth.
