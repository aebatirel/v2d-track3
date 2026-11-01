# B7 rollout reader and B8 pack guard (30 Oct 2026, ~18:20 UTC)

Plan: `../PLAN.md` §2, §4, §7 B7 / B8, CPU tests (f) and (g). This step ran on CPU only and cost $0. Nothing was
launched (no Vast, no Kaggle). No HF store calls were made: the store census uses the local listing from 29 Oct.
I committed nothing. The orchestrator's WIP commits `0e6d7d2` and `d51372e` hold earlier states of these files; the
final small edits are uncommitted on top of `d51372e`. The tests in §4 and §6 ran on the final code. Labels: [M]
measured, [E] estimate (Monte Carlo or model), [H] hypothesis.

Integrity: both tools sit after inference and read no mocap themselves.
- The reader takes rollout summaries whose scores vs mocap were computed on the box.
- The guard reads names, file hashes and checkpoint configs.
- The tests use synthetic data, the CPU mocks' fake scores and the public scans (only as hash fixtures, under neutral
  names, deleted afterwards).

Nothing here feeds eval inference. No registration correction is computed or defaulted anywhere.

## 1. Files
| File | Change |
|---|---|
| `tools/leak_read.py` | new (B7). `read` (the PLAN §4 readings), `mc` (Monte Carlo of the design through the same estimators), `refrule` (reference-level rule for Tier A), `refconv` (reference-level ΔR → LB) |
| `tools/no_oracle.py` | B8. New name rules. Content checks: symlinks resolved, sha256 vs public scans, directories walked. Restructured into `main()`; the CLI and exit codes are unchanged |
| `ops/jobs/pack_eval.sh`, `ops/jobs/submit_pack.sh` | One word each. The guard now also sees `ASSET_LIB` (the simulator library of standard-learner evals) and `LIB` (the meshes submitted in the pack). Before this change, a scan library passed in either one was never checked |
| `tierA/reader_test.py` → `reader_test.{txt,json}`, `reader_mc.json`, `reader_mc_pertwin.json` | test (g): 38/38 checks pass |
| `tierA/guard_test.py` → `guard_test.{txt,json}` | test (f) for B8: 16/16 checks pass |

Commands, run from the repo root (the scratchpad is this session's):
```
python3 -I docs/research/work/leak-decomp-20261030/tierA/reader_test.py --repo $PWD --work $SCRATCH/leak/reader_test_oracle_synth \
  --noise $SCRATCH/noise --mock $SCRATCH/oracle/mockB/content --out tierA/reader_test.json --mc-out tierA/reader_mc.json --reps 4000
python3 -I tools/leak_read.py mc --reps 2000 --noise $SCRATCH/noise --ds 0.15,0.2,0.3 --rng 8 --out tierA/reader_mc_pertwin.json
python3 -I docs/research/work/leak-decomp-20261030/tierA/guard_test.py --repo $PWD --scratch $SCRATCH --fix $SCRATCH/guardfix_b8 \
  --mr $SCRATCH/leak/b8mock_oracle/mr --out tierA/guard_test.json
```
Run time on this VM: reader test 85 s, including the 4000-replicate MC; guard test 24 s [M].

## 2. Input contract for B5 (`leak_cells.sh`)
B5 does not exist yet, so the reader defines what it needs. There is **one `cell.json` per (twin, cell, seed)**, beside
that training's per-episode summary (the `glock_public` / `hard_ab` evalrep format):
```
{"twin": "ep11", "cell": "c4", "seed": 42, "summary": "summary.json", "cost_usd": 1.3,
 "config": {"commit": ..., "learner": ..., "STEPS": ..., "CURVE_REP": ..., "NREP": ..., "GL_ARGS": ..., "seed": 42,
            "pose": {"md5": <the bundle's P_o / P_s tracks or the mocap parquet + oracle_poses version>},
            "sim":  {"geom": "scan", "SF": 0, "PIECES": "", "assets_md5": ...},
            "hands": {"md5": <hands.npz + hands_refined.npz>},
            "ref":  {...}, "run": {"id": ..., "box": ...}}}
```
- **Rollout rows.** Each row needs `auc_star` (the \* score, the reader's default `--metric`), `sim_vs_ref`, and
  ideally `auc` (lib) and `auc_trk`. With those two, the cell table also reports L1 = T_lib − T\* and T_trk − T\*.
- **Config groups.** The groups are checked against the cell table (PLAN §3):
  - `pose.*`: one hash per pose source (P_o / P_s / O);
  - `sim.*`: one per geometry (lib / scan);
  - `hands.*`: one per hand timing (bundle / hT), so c1–c6 must be byte-identical;
  - `ref.*` and `run.*`: free;
  - every other key: identical within a twin;
  - `commit`, `learner`, `STEPS`, `CURVE_REP`, `NREP`: identical across twins.
- **`pose.*` holds the pose source, not the frame-converted file.** c1 and c4 share P_o, but c4's poses are P_o
  converted to scan frames. The converted files belong under `ref.*`.
- **Records that are refused (exit 2):**
  - any group hash that is not the group's majority (on a tie, every member of the group);
  - a declared stage that did not change, i.e. the same md5/sha/hash content on two levels;
  - a config seed that differs from the record's seed;
  - a missing config, or a missing `pose` / `sim` / `hands` group.

  `--drop-refused` analyses the remaining records. `--no-config-check` is for legacy summaries only, and the report
  says it was used.
- **Other formats read.** The reader also accepts an `ops/jobs/oracle_twins.sh` `summary.json`: an index entry with
  `arm: P|O`, aggregates only, and `--metric auc`.
- **B5 naming rules, so that B8 refuses its outputs:**
  - every run id carries `-orc`;
  - scan-geometry asset roots contain `scanlib` (or `oracle`);
  - c7/c8 folders carry a delimited `hT` token (`hands_hT/`, `refs/glockt_hT/`);
  - bundle folders keep `perc2scan` / `perc2gf`.

## 3. What `read` computes, and the choices where PLAN §4 left room
The rules and thresholds are PLAN §4's. Each item marked "choice" below is mine and open to review.
- **Arm (one twin, one cell).** The arm value is the mean of its seed means. SE² = max(σ̂_s², σ_s,class²)/s +
  σ_d²·Σ(1/k_i)/s², with df = s − 1.
  - *Choice:* σ̂_s² is the between-seed part, var(seed means) − σ_d²·mean(1/k), as in `scratchpad/noise/seeds.py`.
    The draws are therefore not counted twice.
  - σ_d is the observed pooled within-seed sd. With one seed, the SE is the class floor and df = ∞.
  - Class floors come from `scratchpad/noise/power.py` [M/E]: stable (0.010, 0.008), typical (0.030, 0.035), hard
    (0.10, 0.15).
  - The g channel uses (0.010, 0.017) [M, PLAN §2]. S uses the same floors as T [E].
- **Per-twin contrast.** A linear combination of independent arms, with Welch–Satterthwaite df: for two equal arms
  that is 2(s − 1), as in the plan. The per-twin verdict uses this SE, unadjusted.
- **Pooled estimate.**
  - The pooled value is the equal-weight mean over the twins that have every cell the contrast needs. Missing twins
    are listed, never imputed.
  - Tests: a paired t over twins (df E − 1) and an exact sign-flip permutation over all 2^E patterns. Both are
    one-sided, in both directions.
  - Holm runs over the primary tests (φ_T, φ_K, φ_G, plus L6 AOI when c7 ran). It is applied to the t and the
    permutation p values separately, and "leaks" needs both after Holm.
  - The AOI, LOO and total contrasts are secondary and unadjusted, and are labelled as such.
- **Verdicts.**
  - Leaks: Δ ≥ +0.03 and the tests above.
  - Truth worse: Δ ≤ −0.03, mirrored.
  - No leak: |Δ| ≤ 0.02 and the 90 % CI within ±0.04.
  - Anything else is inconclusive. Inconclusive with |Δ| ≥ 0.03 is flagged with the pre-set extension (seeds 45–46).
  - *Choice:* the L2/L3 g rule (φ_T, φ_K and the template/tracker AOI/LOO) is Δg ≥ 0.02 with the two-sided 95 % CI
    excluding 0. When ΔT passes but Δg fails, the verdict is inconclusive, with a note.
- **Split and bookkeeping.**
  - ΔT = ΔS + Δg is reported, with its residual, which is 0 by construction.
  - Also reported: sd and min over twins; failure draws (< 0.70, and > 0.10 below their seed's median); evaluation
    crashes (dropped and counted by default, `--crash zero` scores them 0); weak seeds (*choice:* ≥ 0.10 below the
    cell's best seed); and cost.
- **Players.** For each of T, K and G the reader reports AOI, LOO, Shapley and LOO − AOI:
  - T: AOI c2−c1; LOO 0 by construction, since v(T,K,·) = v(K,·); φ_T = ⅓(c2−c1) + ⅙(c5−c4);
  - K: AOI c3−c1; LOO c6−c5;
  - G: AOI c4−c1; LOO c6−c3.

  Brute force over all orderings confirms the closed forms [M].
  - **Reading note [M, algebra]:** with a pure template effect a (c2−c1 = c5−c4 = a, and c3 = c2), Shapley gives
    φ_T = a/2 **and φ_K = a/2**. True motion alone also removes the template error, so half of a template effect is
    credited to K.
  - So separate "tracker" from "template" with L3 (c3−c2, c6−c5) and L2 (c2−c1), not with φ_K alone. The test case
    in §4 shows exactly this: φ_K = 0.06 [M, synthetic] with L3 = 0.
- **Copy ceiling.** Per twin, T\*(c6) ≥ 0.90 is called copyable. A twin with ≤ 0.75 on ≥ 2 seeds is called a
  robot/learner limit; a 2-seed twin needs both seeds.
- **LB.** L = (c/20)·Σ_e Δ(twin(e)) at c = 0.74 and 1.0, with a normal 90 % band from the per-twin SEs.
  - An eval counts only when all its twins ran: eval 14 needs ep12 and ep13, and eval 8 needs ep27 and ep39.
  - Action labels: "worth" (≥ 0.005) and "top" (≥ 0.010) are judged at c = 0.74. "Drop" (< 0.002, upper bound
    < 0.004) is judged at c = 1.0.
  - Explained total = Σφ L + the ceiling's L, compared with 0.185. Only the 10 evals that have a twin enter it.
- **Reference-level helpers (for Tier A).**
  - `refrule` applies the PLAN §4 reference rule: mean ΔR ≥ 0.01 with ≥ 60 % of episodes of the same sign, plus
    > 2× the P_o-repeat noise for tracking arms; no leak at |ΔR| < 0.005.
  - `refconv` converts as (c/20)·1.025·S_e·ΔR_e, only where S_e ≥ 0.8. Spoon rows are labelled [E-analogy] and kept
    out of the total.

## 4. Test (g) results [M] (`reader_test.txt`)
- **Units.**
  - The Shapley closed forms equal brute force over all 6 orders, and efficiency holds: max error 2.2e-16.
  - The SE rule matches hand calculation in three cases: the hard floor binds (0.070852), the observed seed variance
    binds, and one seed (floor, df ∞).
  - Welch df of two equal 3-seed arms is 4.
  - Holm (0.01, 0.04, 0.03) gives (0.03, 0.06, 0.06).
  - The exact sign-flip p for 10 positive twins is 1/1024.
  - The paired t equals scipy `ttest_1samp`.
  - The LB matches a hand calculation, and eval 14 is left out when ep13 is missing.
  - `refrule` gives 5/5 expected verdicts, and `refconv` the expected rows.
- **Exact recovery.** The synthetic set is 10 twins × c1–c8 × 2–3 seeds × 10 draws, 200 records. The noise sums to
  zero per seed and per cell, and every twin has its own true effects.
  - Every per-twin and pooled contrast equals the truth (max error 1.7e-16), and so does Δg. The residual of
    ΔT − ΔS − Δg is 0.
  - φ_T + φ_K + φ_G = c6 − c1.
  - Players: T AOI 0.12, LOO 0, Shapley 0.06; K AOI 0.12, LOO 0, Shapley 0.06; G −0.035 in all three.
  - The verdicts are the ones the truths imply: φ_T and φ_K leak, φ_G is truth worse, and L3, L6 and L3/L6 LOO are
    no leak.
  - The LB equals a hand calculation (φ_T 0.0221 at c 0.74, 0.0299 at c 1.0). The copy ceilings are called correctly
    (ep24 limit, ep11 / ep39 copyable). The L1 column reads −0.01, as planted.
- **One noisy realisation** (the MC generator, same truths). Every primary and AOI estimate is within 3 SE of the
  truth (z from −1.7 to +2.4).
  - This realisation called φ_G "no leak" (−0.014 against a truth of −0.035). That is the false-equivalence risk
    quantified in §5.
- **Config refusals.** Every case below exits with rc 2 and names exactly the planted record(s); `--drop-refused` then
  reads with rc 0:
  - GL_ARGS on one arm (1 record);
  - hands md5 of one c4 arm (1);
  - P_s pose equal to P_o pose (4: c2 and c5 × 2 seeds);
  - STEPS on one twin (all 24 of ep31's records);
  - config seed ≠ record seed (1);
  - no config (1);
  - no `hands.*` group (1);
  - one c6 seed's mocap md5 (1).

  `--no-config-check` reads, and says so in the report.
- **Real formats** (the CPU mocks' fake scores).
  - On the orcB `oracle_twins` summary, c3 − c1 equals its `delta_O_minus_P` on all 3 twins (0.2302 / 0.2642 / 0.2605),
    and ΔS equals `sim_vs_ref_O_minus_P`.
  - A `glock_public` per-episode summary reads back its own auc mean (0.6665, k 6).
  - An evaluation error is counted. Dropped, the cell mean is 0.85; scored 0, it is 0.567.

## 5. Monte Carlo of the plan's design [E] (`reader_mc.json`, `reader_mc_pertwin.json`)
**Design.**
- The 10 twins and classes of PLAN §3: 2 seeds for stable and typical twins, 3 for hard. 10 draws per seed, cells
  c1–c6, 4000 replicates per scenario.
- The generator is `scratchpad/noise/sim.py`'s heavy-tailed classes:
  - hard: seed collapse with q 0.25, size 0.08–0.32;
  - failure draws with p 0.03 (typical) and 0.13 (hard).

  The hard drops are the 16 empirical drops of the H5 official draws (`noise/h5_draws.json`).
- g ~ N(seed 0.010, draw 0.017). Effects are the same on every twin. The template and motion effects move the
  reference (they appear in g); the geometry effect moves S.

Every replicate goes through the same `arm` / `combine` / `pooled` / `holm` / `verdict` code as `read`.

**Null (no effect anywhere).**
- Family-wise false "leaks" over the three primaries is **0.033**.
- Unadjusted one-sided type I, paired t and permutation: 0.04–0.06.
- Paired-t 90 % CI coverage over all scenarios: 0.89–0.92.
- Max |bias| of a pooled estimate: 0.0013.
- Secondary (unadjusted) contrasts call "leaks" or "truth worse" falsely 0–3.4 % of the time each.

**Power.** Each cell is P(reject: Holm, t and permutation agree) / P(verdict = leaks), at a true value of that
contrast of d:

| Test | d 0.03 | d 0.05 | d 0.10 |
|---|---|---|---|
| φ_T (template, Shapley) | 0.90 / 0.51 | 1.00 / 1.00 | 1.00 / 1.00 |
| φ_K (motion, Shapley) | 0.54 / 0.42 | 0.88 / 0.88 | 1.00 / 1.00 |
| φ_G (geometry, Shapley) | 0.53 / 0.41 | 0.89 / 0.88 | 1.00 / 1.00 |
| L2 AOI c2−c1 | 0.43 / 0.38 | 0.75 / 0.74 | 0.99 / 0.99 |
| L3 AOI c3−c2 | 0.43 / 0.38 | 0.76 / 0.75 | 1.00 / 1.00 |
| L5 AOI c4−c1 | 0.43 / 0.38 | 0.76 / 0.75 | 1.00 / 1.00 |

What this means for the readings [E, under this generator]:
1. **Pooled tests.**
   - A two-cell pooled contrast has power 0.75 at Δ 0.05 and 0.99 at 0.10. The plan's estimate was 0.6–0.7 and
     ≥ 0.95, so this is a little better.
   - φ_T is the strongest test: it pools c2−c1 and c5−c4, and its variance is 0.28σ² against 2σ² for an AOI.
   - At d = 0.03, P(verdict = leaks) is at most about 0.5, because the rule also needs the point estimate ≥ 0.03.
2. **"No leak" is hard to reach for AOI contrasts.** Under the null it is called with P 0.28–0.30 (φ_T 0.99,
   φ_K / φ_G 0.78). The ±0.04 CI rule needs an SE of about 0.012, and an AOI's SE is about 0.02. Expect AOI nulls to
   read "inconclusive".
3. **False equivalence.** At a true |Δ| of 0.03, "no leak" is called with P 0.09–0.15. At 0.05 it is ≤ 0.01. A
   "no leak" next to a stage whose LB matters should be read with this in mind.
4. **Per-twin calls (SE rule, unadjusted, one-sided 5 %) are conservative but weak.**
   - Type I is ≤ 0.014 in every class.
   - For an AOI, 80 % power needs about 0.05 on a stable twin (0.80), about 0.16–0.20 on a typical twin (0.77 at
     0.15, 0.92 at 0.20) and about 0.30 or more on a hard twin (0.79 at 0.30).
   - The plan's "typical ≥ 0.10" is therefore optimistic: with 2 seeds the df is 2 and t₀.₉₅ = 2.92. Per-twin φ_T
     reaches 0.99 on typical twins at 0.10.

**Not modelled [H].** The design is falsified for a contrast if the realised paired sd over twins is far above what
this generator predicts.
- Effects that differ between twins.
- Correlation between the cells of one block (same box) or across seeds.
- Selection by S.
- c7/c8.

## 6. B8 guard (`tools/no_oracle.py`) and test (f) [M] (`guard_test.txt`)
**Refused by name.** This covers the word, its parts (`EP:DIR`, `RUN@sub`, `ck=PATH`), JSON strings, resolved paths
and checkpoint configs.
- Kept from before: `oracle`, and `<date>-orc*-` run ids. The leak study's run ids are covered by this rule.
- New:
  - `perc2scan` and `perc2gf`;
  - a delimited `hT` token;
  - `leak_` / `leak-` / `leak/` (results/leak_p1, results/leak_cells, leak-decomp-…);
  - `scanlib`, in any case;
  - the organisers' scans and URDFs: `t3/mesh/<obj>/` and `t3/urdf/`, except our `wooden_spoon` there;
  - `track_3/public/mesh|urdf`;
  - the ASSET_SRC=public runs `20261022-r5ks*`.

**Refused by content.**
- An existing file or directory is resolved: directories are walked to depth 3 with symlinks followed.
- A file is refused when its real path matches a rule, or when its sha256 is a public scan or a scan-templated track.
  The hashes come from `ops/provenance/denylist.json`, minus its library_v\* entries, which are our pack meshes.
- All 13 local public scans match that list [M].
- The repo, the working directory and their parents are never walked.

**Results.**
- **Accepted (rc 0):**
  - the 20 pack-7 checkpoints: local copies with sha256 equal to `checkpoints.json`, as a kit JSON and as 20 words;
  - their 21,435 stored config strings, none of which matches;
  - the stored pack-6 / pack-7 / pack-8 checkpoint JSONs;
  - the 38 pack-6/7 words of `h5_reeval.sh` plus the libraries and carve pieces;
  - 19 look-alikes: `highThreshold`, `leaky_relu`, our spoon in `t3/mesh`, `/content/perc2`, `perc2rep`,
    `refs/glockt` and others.
- **Refused (rc 1):**
  - the oracle-twin cases, all 6 still refused, including the renamed oracle-trained checkpoint;
  - 25 B8 name cases;
  - 12 content cases under neutral names:
    - a symlink farm onto the scans, as `physics_arms.sh` builds scanlib;
    - one farm link;
    - renamed byte copies, as a directory, as `EP:DIR`, as one file, and inside an ASSET_PIECES-style directory;
    - a neutral link onto a `perc2scan` folder;
    - renamed copies of a pack-7 checkpoint whose stored config names a perc2scan / hT / scanlib reference, given
      singly, in a kit JSON, and as a directory;
  - a pack-7 JSON with one scan copy added.
- **Store census.** The old rule matches 88 of the 134,909 store paths; the new rule matches 789.
  - Every newly refused path belongs to the two ASSET_SRC=public runs, `20261022-r5ks-72ecb2f` and
    `20261022-r5ks43-72ecb2f` (701 paths, including 2 `access/` files).
  - No path is refused under the old rule but accepted under the new one, and no pack run is refused.
- **Phase-1 mock, box a** (real `perc_leak.sh`, this guard):
  - all 200/200 pushed files are refused by store path;
  - bare `perc2scan` paths are refused 64/64, and bundle tars 7/7;
  - `perc_leak.sh` now logs "guard refuses the bare perc2scan folder name". This resolves `phase1/BUILD.md` §5 item 1.
  - Bare `ep<N>/perc2` and `perc2rep` stay accepted, by design. `perc2` is the eval pipeline's own folder name, and
    P_o reads no ground truth. Their store paths carry the `-orc` id.

**Limits [M/H].**
- A scan converted to another format under a neutral name is not caught (for example `make_assets.py` output from
  scanlib copied to `/content/assets`). Hence the B5 naming rules in §2.
- The guard only sees what the pack scripts pass it. `LIB` and `ASSET_LIB` are now passed; `PDIR_ROOT`-style
  overrides are not.

## 7. Open items
- B5 must write `cell.json` per §2, with `auc_star` in every rollout row. Until it does, `read` refuses the records
  unless `--no-config-check` is given.
- I did not edit `STATUS.md` or `docs/work-log.md`; the orchestrator owns them in this workflow. Record the B7/B8 code
  version when committing.
- The MC treats the twins as independent and uses the same Δ on every twin. Once wave 1 is in, re-run it with that
  wave's realised seed and draw sd (`--class-noise`), before any interim reading. No stopping rule depends on it.
