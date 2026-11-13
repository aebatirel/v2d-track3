# Masses v2: build notes (31 Oct 2026, CPU only, nothing launched)

**What this is.** The owner approved "Masses v2" at 14:55 UTC: 4 public headroom episodes, 0.3 kg vs realistic masses,
the first mass check's design and a new rule. This folder holds:
- the evidence for the episode selection: `baselines.md` / `.json`;
- the pre-registration: `PREREG.md`;
- the reference table the boxes read: `refs_v2.json`;
- the launch strings and cost: `JOBS.txt`;
- the CPU evidence: `cpu/`.

No GPU box ran and nothing was sent to Kaggle. No commit was made here; the orchestrator commits.

## 1. Selection evidence (baselines.md)
- **Sources [M].** Every public grasp-lock rollout baseline comes from its run's `job.log` RESULT line. Those were read
  from earlier single-file copies in the scratchpad, except the first check's numbers, which come from its committed
  `summary.json`.
- **Store access.** No store listing was made. A run whose `job.log` was not local would have been fetched with one
  `hf_hub_download`; none was needed.
- **Recipe claims checked in the logs** (header lines `glock_public code …, SF, REPLAN, EVOLVE, GL_ARGS`, plus the
  `run_job.log` job strings):
  - **ev2 / ev3 / ev30rp / twin11v3** are the frozen recipe (SF 1, REPLAN 0, EVOLVE 1, onset anchor, CURVE_REP 3).
  - **twin21arc / twin21base are not.** They ran REPLAN 1, EVOLVE 0, without the onset anchor. The 25 Oct work log
    called them "frozen recipe"; their logs say otherwise.
  - **orcB** ran REPLAN 1, EVOLVE 0 (PREREG of the oracle twins).
  - **W1 (ep26)** ran code 37cc551 with one evaluation per checkpoint.
- **Meshes checked in the logs.** Every eligible run used library_v3: the make_assets lines give wooden_piece_1 extents
  13.3 cm, where library_v4 gives 12.9 cm. library_v3 is unchanged since a30ac72 (22 Oct).
- **Defaults checked in the code.** `pipeline/support_fill.py:57` defaults SF_ARC to 1, so the arc foot is the current
  default.

## 2. References (refs_v2.json; `scripts/make_table.py`)
- **What the table holds.** For the 4 chosen episodes: source run, base, and the 9 required + 2 optional files per
  episode (paths relative to `runs/<source>/`). Also the md5 + fingerprint of each `ref_gl_ilc.parquet`, the URDF md5s
  and masses, and the stored rest checks.
- **File names.** For the 24–25 Oct runs they come from the 29 Oct store listing (a local file, so no new listing). For
  orcB (30 Oct), they come from its job log (`base mck (…/0d7b4754…-0.parquet)`) and the fixed output names.
- **What the box needs, read in the code.**
  - glock_public.sh REUSE_REF reads only the base processed parquet, the base `reconstructed_stage`, the arm copy of
    `ref_gl_ilc.parquet` and `rest_check.json`.
  - mass_arm.py copies `refs/sf/ep<N>/assets` (urdf + glb).
  - So hands, e2s_raw, loaded, logs and images are not pulled. The first check pulled whole folders with listings.
- **Downloaded once each** (`cpu/out/store_downloads.jsonl`, 25 downloads + 6 HEAD, all OK):
  - the 4 references (ep31's from an earlier local copy);
  - their 8 URDFs: each is 0.3 kg, has one `<inertial>` block and names one mesh `../mesh/<obj>/<obj>.glb`;
  - the 4 rest checks.
- **Availability.** All 44 pull-list files of the 4 episodes exist in the store today: 44 single-file HEAD requests, 0
  listings (`cpu/out/store_availability.jsonl`).

## 3. Code changes (both opt-in; default behaviour unchanged)
### `ops/jobs/mass_check.sh`: MV2 mode (`MV2_TAB=<table> MV2_EPS="<episodes>"`)
- **Run id.** In MV2 mode the run id must contain `-mv2`. The default still requires `-mass-`, and each mode refuses
  the other's id (mock G1, G2).
- **Episodes and sources.** EPS and `SRC_EP<N>` come from the table; a `SRC_EP<N>` set in the environment wins (for
  re-runs). The episodes must be in the table's `all_eps`, so ep2 is refused (G3). The props md5 must equal the
  table's (G4).
- **Pulls.** Each listed file is one `store.sh pull-files` call, which is one `hf_hub_download`, retried, with no
  listing. It is placed at `/content/<path>` as pull-run would place it. An optional file may fail.
- **Reference check.** The pulled `ref_gl_ilc.parquet` must match the table's md5 + fingerprint.
  - Otherwise, or when a required file fails, the episode is REFUSED: its `refs/glockt/ep<N>` is moved aside, so
    mass_arm drops it, and its cells become missing (INCOMPLETE). It is never rebuilt and never swapped.
  - The details go to `stored_refs_v2.txt`.
- **Box line.** The box ends with `mass_verdict.py --rule v2 --partial`, logged as `mass_check v2 BOX RESULT`: a reading,
  not the verdict.
- **Unchanged.** Everything else is the first check's code path: mass_arm, glock_public REUSE_REF / REQUIRE_REUSE,
  mass_verify, ckpt_meta, the one push.
- **Diff discipline.** No line of the original file was removed (`diff` shows additions only). The v1 branches keep
  their text.

### `tools/mass_verdict.py`: `--rule v2` (default `--rule v1` unchanged), `--partial`
- **Entry.** `main()` returns `main_v2()` right after argument parsing when `--rule v2`. The v1 path is byte-for-byte the
  old code.
- **The v2 rule** (PREREG §5):
  - Δ(ep) is computed as in v1, from unrounded cell means;
  - the comparisons use 4 decimals: m ≥ +0.03, at least 3 of 4 d > 0, no d ≤ −0.05;
  - INVALID if any verify fails; INCOMPLETE if any of the 16 cells is missing or has fewer than 8 rollouts.
- **Merging.** `--content` and `--verify` each take one entry per box, in the same order.
  - Pairs (episode, seed) are atomic: both arms come from the one box where they are present, verified and have ≥ 8
    rollouts.
  - A pair that qualifies in two boxes gives exit 2 and no verdict.
  - A pair split over two boxes is INCOMPLETE.
- **Reported.** Cell sources, eval timeouts per cell and arm (printed after the label), sim_vs_ref Δ, the ref_auc
  spread, and harm flags.

## 4. Evidence (cpu/out)
| check | result |
|---|---|
| v1 default on the first check's stored results (`v1_unchanged.txt`) | the original and the new tool both reproduce the committed `summary.json` byte for byte, and the job.log RESULT line exactly: NOT ADOPTED, ep12 −0.0128 |
| default mass_check job unchanged (`equiv_default.txt`: the first check's mock and JOBS string, old vs new scripts, same mock path) | old (2ed46ea) vs new run of the first check's string: job log (as written and sorted), train / eval / ref audits (268 lines), all 1,719 files written, store traffic (1 upload, 4 listings + 1 download as before), summary.json, verify.json, verdict and verify lines all **IDENTICAL**; check.py 38/38 on both. The two scripts differ in md5. (A first run at different mock paths differed only by path-dependent md5s; an earlier run against HEAD compared new with new because HEAD already held a WIP commit of the new files. Both runs were discarded and fixed in the script.) |
| rule fixtures (`tests_v2.json`, `cpu/mock/tests_v2.py`) | **30/30 pass**: R1–R15 rule clauses (ADOPT; NOT ADOPTED on the mean, the 3-of-4 and the drop clause, each alone; mean exactly +0.03 passes and 0.0299 fails; Δ exactly −0.05 fails, also when float arithmetic gives −0.04999…; −0.0499 passes; Δ 0.0 and +0.00004 are not positive; exactly 3 of 4 passes; a per-seed −0.10 alone does not fail; INCOMPLETE on 7 rollouts and on a missing cell; INVALID with missing listed; PARTIAL), M1–M11 file-tree merges (two boxes; missing cell; a re-run filling the pair; a pair twice → exit 2; a pair split over boxes; verify-missing beats a summary; an unverified cell; a failed verify → INVALID; 3 episodes refused; box PARTIAL; boundary drop from files), V1 (the first check's own fixture cases, and the stored results byte for byte) |
| CPU mock of both box strings + merge + failure paths (`mock_v2.txt`, `check_*.json`, `merge_*.txt`) | box A (ep24 + ep13) and box B (ep11 + ep31): **37/37 checks each**, 8 trainings, 248 evaluations, **22 single-file downloads, 0 listings, 1 upload** each; merge → a verdict (synthetic ADOPT). Failure paths: F (an injected training failure) 34/34 checks, box INCOMPLETE, merge INCOMPLETE; R (the INCOMPLETE re-run string) 18/18, 11 downloads from F's pushed run; merge F+B+R → a verdict, with the ep13/s43 pair taken from R; A+B+R → **REFUSED, exit 2**; T (a tampered ep31 reference) → ep31 REFUSED, never trained (4 trainings), INCOMPLETE; G (guards) → a -mass- id in MV2 mode, a -mv2 id in default mode, ep2, and a changed props file all exit 1 before any download |
| operating characteristic of the rule (`power.json`) | P(ADOPT) 0.13 at no effect, 0.66 at +0.05, 0.87 at +0.09 [E, model in PREREG §7] |

Mock details (`cpu/out/mock_v2/`, `mock_v2.txt`).
- **What each box check proves** (`check_v2.py`, from what the stub FlashCHORD trainer and evaluator actually loaded):
  - every training read the ONE pulled reference, whose fingerprint equals the REAL table's (PREREG) value, and the arm
    parquets differ only in `object_urdf_paths`;
  - mass1 loaded the props masses and mass0 0.3 kg, each from its own arm folder;
  - each of the 31 evaluations per training loaded its checkpoint's arm through the checkpoint's saved `task.parquet`;
  - the paired arms had identical arguments and environment, and seeds differ only in `reset.seed`;
  - the pulled reference and assets are untouched, and `/content/assets` stays at 0.3 kg;
  - the downloads are exactly the table's 22 files, once each.
- **The store.** The fake store is built from the 16 real downloaded files plus 28 labelled stand-ins.
  `mock_table_diff.json` lists the provenance of every file and the md5 substitution for the path-re-pointed parquets.
- **Run time.** The full mock took 17 min of light CPU (24 min user); the default-equivalence mock took 10 min.

## 5. Risks and open points
- **ep11 and ep13 sit at or below their static floors with tiny sd [M].** Their d(ep) may be ≈ 0, and 0.0000 is not
  positive, so ADOPT then needs ep24 and ep31 to carry the mean and at least one of ep11 / ep13 to be above 0. This is
  the owner's rule applied to the lowest baselines; it was not tuned (PREREG §7 states it before any result).
- **The 4th slot is sensitive to step 3** (PREREG §3.3: ep31 vs ep21), and admitting pre-frozen runs would bring in
  ep26. The reviewer may object before launch; a change would be a dated amendment before any v2 number.
- **ep13's reference is not the frozen recipe** (REPLAN 1 / EVOLVE 0, the eval-14 packed recipe). The same file is used
  by both arms, so this is not a confound in Δ; it is noted in PREREG §4.
- **HF 429.** There are 22 single-file downloads per box with pull-files' own retries (5 tries, up to 20 min each). A
  file that never arrives drops its episode (INCOMPLETE), not the box.
- **Eval timeouts** are counted and printed, as in the first check: a cut rollout is unscored, and fewer than 8 scored
  rollouts make the cell missing.
- **Mock limits.**
  - The stubs do not run physics. Some store files are labelled stand-ins: base parquet, stage, glb, zero_score,
    support_fill (`mock_table_diff.json` provenance).
  - Parquet asset paths are re-pointed to the mock root, so the mock table carries those files' md5s next to the REAL
    fingerprints (asserted equal). The real md5 check runs against the real table on the box.
  - The real files the box will pull were verified to exist (HEAD), and the references themselves were checked
    (md5 / fingerprint / URDFs) on CPU.
- **Not changed.** `pipeline/refine.py`, `glock_public.sh`, `mass_arm.py`, `mass_verify.py`.

## 6. Files
- **New.**
  - `docs/research/work/masses-v2-20261031/`: PREREG.md, JOBS.txt, BUILD.md, baselines.md, baselines.json,
    refs_v2.json;
  - `scripts/`: baselines.py, make_table.py, power.py, pull_results.py;
  - `cpu/mock/`: setup_v2.sh, store_v2.py, stub_v2.py, run_mock.sh, run_all_v2.sh, check_v2.py, tests_v2.py,
    equiv_default.sh;
  - `cpu/out/*`.
- **Changed, opt-in only:** `ops/jobs/mass_check.sh`, `tools/mass_verdict.py`.
