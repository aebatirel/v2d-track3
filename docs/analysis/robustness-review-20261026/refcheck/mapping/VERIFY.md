# verify_mapping: independent check of `mapping/` (27 Oct 2026, ~04:44–05:12 UTC)

I tried to refute the mapping check (does sim_vs_ref S predict the truth score T, and does the review's loss budget
hold?). My scripts and outputs are in `../verify_mapping/`. The scratch is in
`/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck/work/verify_mapping/`.

**Verdict: partly confirmed.**
- **Every measured number I re-derived reproduces**, most of them exactly.
- **Three interpretations do not hold as written:**
  - the significance of the leaderboard-transfer gap;
  - the H-rest mechanism for two of its three named objects;
  - the claim that "the changed eval references are ≈ 0.74 accurate".

Labels: **[M]** measured here (command at the end), **[D]** taken from a doc, **[E]** derived from [M] and [D]. Public
mocap was read only by scoring and diagnostics. For eval episodes, only our own packed rollouts (simulation plus our
reference) were read; eval episodes have no ground truth. CPU only, at most two light processes at a time. Repo
e2f0a6b. No commit, push or upload.

## 1. Re-derivation with my own code

I did not re-run `calibrate.py`. `myscore.py` is written from the kit source. It has its own code for:
- reading the evaluator parquet with pyarrow (not `read_trajectory`);
- reordering the mocap quaternions from w,x,y,z;
- matching frames on `frame_index` and `reference_frame`;
- the body conversion and the frame-0 scene alignment;
- symmetric point errors, in closed form over the kit's 360 or 2 discrete angles;
- the AUC, the frame-0 warp and the 5 cm-sphere ADD;
- policy grouping, keyed by the parquet-metadata checkpoint sha256 rather than the episode json.

Only the kit's ICP registration, its mesh budget and its surface sampler are imported. The sampler is needed to
reproduce the stand-in host points.

**I scored all 747 distinct public rollouts (10 episodes) myself [M].**

| Claim (mapping) | Mapping | Mine [M] | Survives? |
|---|---|---|---|
| T, R, S per rollout | — | 746/747 identical to 4 dp; 1 differs by 0.0001 in T (0.2018 vs 0.2017, ep18 r4kfi sweep; a rounding edge) | yes |
| Parquets / distinct / policies | 2819 / 747 / 288 (266 own-mesh) | 2819 / 747 / 288 (266) | yes |
| S vs box `qa_policy.json` | 733/733 | 733/733 (664 direct, 69 match one entry of a mean's `rep` list) | yes |
| T vs box `score_registered` | 202/202 | 216/216 (I also count scan-vs-"public scans") | yes |
| k (T = kS), own-mesh, all | 0.982, n 266, RMSE 0.040 | 0.9815, RMSE 0.0405 | yes |
| k, R ≥ 0.95 | 0.985, n 125, RMSE 0.029 | 0.9846, RMSE 0.0294 | yes |
| k, S ≥ 0.8 and R ≥ 0.95 | 0.976, n 37, RMSE 0.015 | 0.9756, RMSE 0.0154 | yes (23 of the 37 are ep27; per-episode k 0.984 / 0.965 / 0.959 for ep27 / 18 / 39) |
| k, episodes weighted equally | 0.969–0.972 | 0.9712 / 0.9722 / 0.9693 | yes |
| Box summary.json means | 58, LS 0.976, sum 0.989; 0.983 without the newest | 58, 0.976, 0.989; 0.983 | yes; see §3.1 |
| T/S at S 0.9–1.0 | 0.978 / 0.981 / 0.800 | 0.9776 / 0.981 / 0.7997 | yes |
| ep21 high-S residual vs k·S | −0.17 | −0.169 (S 0.97–0.985, T 0.774–0.797) | yes |
| S ≥ 0.8, 55 policies | S·R RMSE 0.029, bias +0.022; a 1.025, RMSE 0.020; kS RMSE 0.045 | 0.0292, +0.0223; 1.0249, 0.0195; 0.045 | yes |
| Within-group slope dT/dS | 0.94 / 0.97 / 0.88; ep21 0.71 / 0.74 | 0.9406 / 0.9696 / 0.884; 0.712 / 0.739 | yes |
| 1063 high-S pairs | dS·R: RMSE 0.018, bias +0.001, ratio 1.003; dS alone 0.95 | 0.0179, +0.0007, 1.0028; 0.950 | yes, but see §3.3 on leverage |
| sd(T\|S) per draw, policy S ≥ 0.8 | 0.0082 | 0.0082 (38 policies, 187 rollouts) | yes; it does not fit the low-S evals (§3.4) |
| 60 most recent rollouts | k 0.83 | 0.8304 (52 ep21 rollouts, 8 ep11) | yes |
| Evaluator add_auc vs S | corr 0.977 vs 0.986; RMSE 0.057 vs 0.040 | 0.9773 vs 0.9856; 0.0569 vs 0.0405 | yes |
| Frame-local excess T − mean(g_s·g_r) | +0.035, +0.025 of it in rest frames; R < 0.95: +0.047, +0.043 | +0.0352, +0.0249; +0.0466, +0.0429 | numbers yes; mechanism partly no (§3.2) |
| Per-object rest excess | ep11 blue cup +0.25, ep31 rack +0.10, ep12 rack +0.09, ep24 board 2 +0.05, ep26 pot +0.04, ep26 rack −0.03 | +0.254, +0.101, +0.088, +0.048, +0.042, −0.030 | numbers yes |
| Product vs S·R | RMSE 0.055 vs 0.058; 0.029 vs 0.030 at S ≥ 0.8 | 0.0546 vs 0.058; 0.0288 vs 0.0301 | yes |
| Leaderboard transfer, pack 3 → 4 | 0.743; 0.759 of 0.979·dS; σ 0.053 | 0.743, 0.759, 0.0527 [E]; dS re-measured per packed rollout (§3.4) | arithmetic yes; σ is too small |
| Eval-specific loss, pack 4 | 0.073–0.088 | 0.0733–0.0878 for k 0.969–0.985 [E] | yes |
| Implied spoon accuracy | 0.80 / 0.76 / 0.73 | 0.7997 / 0.761 / 0.731 for a = 1 / 1.015 / 1.027 [E] | yes |
| Model transfer for the 7 changed evals; eval 33 | 0.88; 0.62 ± 0.10 | 0.882 (2.64σ); 0.623 ± 0.096 with their σ [E] | arithmetic yes; ± 0.15 with S-dependent noise |

The per-episode table also reproduces row by row (`my_fits.json` → `per_episode`).

Not re-derived:
- S_mesh (H-yard);
- the frame-local dT_local of H-local.

## 2. Classic-error hunt: what I looked for and found

- **Quaternion order [M]:** confirmed w-first in the public parquets.
  - Reading the stored mocap quaternion as x,y,z,w collapses R to 0.00–0.50 on every episode (`check_frames.json`).
  - Every evaluator parquet declares `xyzw` in its metadata. I read the columns by name.
- **Object slot order [M]:** in 747/747 rollouts, `object_body_name` by `object_body_id` equals the public episode's
  object order. My reader refuses any mismatch, and none occurred.
- **Frame indexing [M]:**
  - every rollout starts at `reference_frame` 0 and covers the whole public episode (747/747);
  - mocap row = `frame_index`, and all quaternion norms are 1 ± 6e-8.
- **Off-by-one probe [M]:** I scored R with the mocap shifted by −2…+2 frames.
  - It peaks at 0 for ep2, 18, 26, 27 and 39.
  - It peaks at −1 for ep11, 12, 21, 24 and 31, gaining 0.002–0.011 in R. There the reference at frame f matches the
    truth at f − 1.
  - This is not an indexing bug in the check: the kit pairs frame f with frame f, and so does the check. It is a
    property of those references, about one frame (50 ms) of lag, and it is the timing check's business.
  - **[H]** A perception lag of about one frame in these five references. Falsify by measuring the lag of each
    episode's perception poses_world_vo.npz against mocap: no lag there means it enters in mkref.
- **Mesh library [M]:**
  - The libraries differ only for the sweeper (v2 vs the others), the beige cup (v3x), the pitcher (v3p) and the
    boards (v4).
  - The `make_assets` extents tell each of these apart (≥ 0.3 cm).
  - I re-grepped the job.log of 10 runs. They agree with the assignments, including that ep11 twin v3x used the v5
    cup.
  - The 134 box `score_registered` files written with a different library name than the simulated one are all for
    objects whose meshes are md5-identical across those libraries, so they are correctly scored.
- **Run, version and copies [M]:**
  - 2819 listed files collapse to 747 by LFS sha256.
  - The local file sha256 equals the listed sha256 in 747/747 cases.
  - No public evaluator parquet lies outside `results/`.
- **Pack references [M]:** the 7 changed evals of pack 3 → 4 track the same reference, bit-identical in both packs.
  This rules out the confound that dS mixed a change of target with a policy gain.
  - My S of each packed rollout equals `summary.txt` in all 20 episodes.
  - The 13 unchanged evals are the same rollouts (`pack_refs.json`).
- **Per-object vs per-episode averaging:** T and S average over objects in every case, as the kit does, so the two
  are consistent. The fits are dominated by a few trainings (ep18 75 policies, ep12 and ep24 47 each). The mapping
  check reports the equal-weight k for this; I confirm it.
- **Symmetric objects:** S has no symmetry; T and R have it. This is not a source of error in the numbers. ep12 blue
  cup S_obj·R_obj ≈ T_obj (residual −0.0004 at S ≥ 0.8).

## 3. The reported problems: do they survive?

### 3.1 "0.979 has no recipe and does not reproduce" — survives
- I widened the search, which strengthens this point:
  - The mapping check's path regex `/ep(\d+)[/-]` skips the 87 per-run top-level `summary.json` files (keyed `epNN`).
  - I downloaded and parsed them. They add **no new distinct policy means**: all are copies of per-episode files.
  - Per-rollout pooling (319 distinct box rollouts) gives LS 0.977 and a sum ratio of 0.990.
  - No drop-one subset gives 0.979 for LS, sum or mean ratio (`box_k.json`).
- The only 0.979 I found is the LS ratio of the per-policy *maxima*, 0.9785. That is not a natural recipe and is
  probably a coincidence.
- The size is right, so the impact on the review is small (eval-specific loss 0.073–0.088 against 0.082 [E]).

### 3.2 "T = S·R is biased low; the excess sits on objects that rest in the truth while our reference drifts" — the bias survives; the mechanism holds for one of the three objects

The bias reproduces: +0.022 at S ≥ 0.8 and +0.035 overall. Direct per-frame look (`rest_detail.json`, top-3-S
rollouts each) [M]:

| Object | Truth moves | Reference drift | Sim drift | Error at frame 0 (sim / ref) | Mean error vs truth (sim / ref) | T_obj vs R_obj |
|---|---|---|---|---|---|---|
| ep11 blue cup | ≤ 0.5 cm | **5.4 cm, 33°** | 0.4 cm | 0.02 / 0.03 cm | 0.3 / 1.8 cm | 1.00 vs 0.86 |
| ep12 rack | ≤ 0.4 cm | 0.8 cm (error varies only ±0.6 cm) | 1.4 cm | **0.86 / 1.40 cm** | 0.85 / 1.46 cm | 0.99 vs 0.94 |
| ep31 rack | ≤ 0.15 cm | 1.8 cm (±1.0 cm) | 1.2–2.0 cm | 3.3 / 3.1 cm | **2.6–3.5 / 3.2 cm** | 0.68–0.78 vs 0.73 |

- **ep11:** H-rest exactly as stated. The truth and the simulation rest; our reference drifts.
- **ep12:** our reference does not drift. It carries a static offset of 1.4 cm that is already present at frame 0.
  The simulation's frame-0 configuration lands nearer the truth (0.86 cm).
  - **[H]** Physics settling resolves the reference's cup-rack interpenetration in a direction that matches the
    truth. Falsify by comparing the reference's and the simulation's frame-0 cup→rack vectors with the mocap one: no
    gain toward the mocap kills it.
- **ep31:** the simulation is **not** nearer the truth. It is closer than the reference in only 29–74 % of frames,
  and T_obj ≈ R_obj. The excess comes from errors that do not compound: a 3 cm static offset plus small tracking
  deviations barely move g(e_t), while g(e_s) charges the deviations. That is a saturation of the AUC, not "the
  simulation leaves the object where the truth is".
- The README text "the simulation leaves them where they are, which is where the truth is" is wrong for ep31 and
  misdescribes ep12.
- The practical conclusion still stands: S·R under-predicts T, and both loss buckets over-count.
- H-rest's own falsification test (excess on rest objects whose reference drifts > 1 cm) cannot tell these
  mechanisms apart: ep31 passes it with the wrong mechanism. A sharper test: H-rest as stated predicts T_obj > R_obj
  on rest objects. That holds for ep11 and ep12 and fails for ep31.

### 3.3 "The marginal transfer at high S equals R" — survives, with less evidence than it reads

- 1048 of the 1063 high-S pairs come from episodes with R 0.93–0.97 (ep12 474, ep27 360, ep18 140, ep39 74; mean R
  0.95). Only 15 come from ep21 (R 0.78).
- At R ≈ 0.95, "transfer = R" and "transfer = 0.95 always" are the same prediction. The test that transfer tracks R
  rests on the single ep21 pitcher. There the measured transfer is 0.72, and dS·R over-predicts by 7 % (Σ dT / Σ dS·R
  = 0.93).
- With both policies at S ≥ 0.8 (280 pairs), transfer is 0.93 at a mean R of 0.95 (`extra_checks.json`).
- H-local's falsification ("no better than dS·R") has little power for the same reason: the local and global R
  barely differ where the pairs are.

### 3.4 "Leaderboard transfer 0.743 ± 0.053, ≈ 4σ below the public slopes and 2.6σ below the model" — the value survives; the significance is overstated

- The arithmetic and the inputs reproduce:
  - S per packed rollout is re-measured [M];
  - the same reference is used in both packs [M];
  - the Kaggle AUCs are [D].
- σ is too small. It uses the public sd(T|S) of high-S policies (0.0082) for all 14 draws. But eval 10 (S 0.34 →
  0.45) and eval 33's pack-3 draw (0.61) lie where the public sd(T|S) is 0.024 (S 0.3–0.7, 49 policies) [M].
- With S-dependent noise, σ(transfer) = **0.085**. The gaps then become:

  | Comparison | Gap |
  |---|---|
  | public slope 0.94 | 2.3σ |
  | public slope 0.97 | 2.7σ |
  | `loss_budget.py`'s 0.88 | **1.6σ** |

  Eval 33 alone comes to 0.62 ± 0.15 [E]. Eval-specific T|S noise is unknown and can only add to this.
- "Transfer ≈ R" is a high-S law. Eval 10's gain is at low S (bin 0.3–0.6), where public T/S is 1.04–1.05 for
  R ≥ 0.85 and 0.93 for R < 0.85, so its transfer need not be R.
- **Unverified assumption [open]:** that the public Kaggle AUC averages all 20 eval episodes with equal weight. The
  kit's `score()` drops a `Usage` column. A public/private split by episode or row, which nothing in the repo
  documents, would change the denominator of dLB / (Σ dS / 20).
- **So:** "the changed eval references look ≈ 0.74 accurate" is a model-dependent reading of one noisy measurement,
  ± 0.085 or more. It is not a measurement, and against the model's 0.88 the gap is below 2σ.
- H-scale's proposed test, a pack that changes only one episode, needs dS ≳ 0.2 to reach σ ≈ 0.05 with one draw
  each, because σ = √2 · 0.0082 / dS. A typical dS of 0.06 gives σ ≈ 0.19, which cannot separate 0.95 from 0.85.

### 3.5 Other items
- **"T = kS only when R ≳ 0.93":** survives. The low-R, high-S failure is one object (ep21 pitcher); the mapping
  check says so.
- **a by episode at S ≥ 0.8 [E]** (the measured Σ T / Σ S divided by R): 1.055 (ep12), 1.023 (ep27), 0.999 (ep18), 1.003 (ep39), 1.033 (ep21). The pooled
  1.025 hides that spread, and the spoon solve inherits it.
- **The "60 most recent" point:** survives.
- **H-yard:** survives for the evaluator add_auc part, which I checked. The S_mesh part was not checked.
- **The fixed items:**
  - (a) Six hard-run rollouts are scored with the scans. Their job.log starts at 04:36–04:49Z on 21 Oct, before route A
    (10:20Z [D]). I reproduce their T, R and S with that assignment.
  - (b) and (c) are process notes, with no number to check.

## 4. H-freeze: a cheap test (new, `freeze_test.json`) [M]

**Test.** I froze the named object in the reference, at its frame-0 pose or at its median position, and re-scored R
and the stored simulations' S. T is unchanged. The objects were chosen with mocap knowledge (they rest in the truth),
so this is not the GT-free trigger.

| Object (reference) | R before | R after freeze | S before | S after | T |
|---|---|---|---|---|---|
| ep11 blue cup (v3x / v3) | 0.884 / 0.899 | 0.953–0.974 / 0.964–0.973 | 0.48 / 0.45 | 0.57 / 0.53 | 0.570 / 0.528 |
| ep12 rack (main / other) | 0.935 / 0.932 | 0.935 / 0.943 | 0.952 / 0.756 | 0.950 / 0.765 | 0.933 / 0.734 |
| ep31 rack (two references) | 0.823 / 0.853 | **0.800** / 0.873 | 0.740 / 0.644 | 0.77 / 0.68 | 0.743 / 0.657 |

- **ep11:** strongly supported. With the frame-0 freeze, S equals T to 0.001; with the median freeze, to 0.002–0.008.
- **ep12 and ep31:** not supported. The main ep12 reference is flat, and one ep31 reference gets worse.
- By its own criterion (R must rise on ep11, ep12 and ep31), H-freeze is falsified as a general rule. It survives for
  references that drift while the truth rests, which matches the mechanism split in §3.2. Static offsets need a
  different fix.

## Commands (all CPU, session container, venv `.../refcheck/venv`, from `refcheck/verify_mapping/`)

```
python -I run_score.py all $W/all.jsonl     # 747 rollouts, own scorer, 04:45-04:55 UTC (~10 min, one core)
python -I box_k.py                          # box summary.json means incl. top-level files (downloaded to $W/store)
python -I pack_refs.py                      # pack 3 vs 4 references and S (eval: our own rollouts only)
python -I my_fits.py                        # fits, bins, per-episode, slopes, pairs, noise, recent60 -> my_fits.json
python -I check_frames.py                   # frame-shift, quaternion-order and rest probes -> check_frames.json
python -I rest_detail.py                    # per-object mechanism detail -> rest_detail.json
python -I freeze_test.py                    # H-freeze cheap test -> freeze_test.json
python -I lb_derived.py                     # leaderboard / loss-budget arithmetic -> lb_derived.json
python -I extra_checks.py                   # S-dependent noise, pair leverage, inventory hashes, eval add_auc
python -I frame_split.py                    # frame-local excess and rest split, 713 rollouts (05:03-05:09 UTC)
python -I box_check.py                      # my S / T vs box qa_policy / score_registered
```

`W=/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck/work/verify_mapping`.
The mesh library per rollout is taken from the mapping rows. I checked it by hand on job.logs (§2) and did not
re-infer it for every run.
