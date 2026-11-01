# Eval-10 cavity-safe retrain: build notes (1 Nov 2026, CPU only, nothing launched)

**Question.** Does the packed eval-10 recipe on e10v's V4p reference, retrained at the stock contact limits on collision
pieces that do not overlap at the nested rest, leave the "cup never lifted" floor, and does it pass the agreed swap rule and
the pack-10 inclusion bar?
- Rule and labels: `PREREG.md` (written before any result).
- Launch string, ledger line and after-box steps: `JOBS.txt`.
- Labels: [M] measured here, [R] read from another lane's commit, [E] estimate, [H] hypothesis.
- Machine: this Claude cloud VM (4 CPU), 1 Nov ~05:10-06:30 UTC, $0. No GPU, Vast or Kaggle. Nothing pushed.
- Eval 10 has no ground truth; nothing here reads mocap, scans or `observation.objects`.
- **PACKABLE if it passes** (stock limits; `tools/no_oracle.py` accepts it, section 5).

## 1. What is built
| file | what |
|---|---|
| `meshes/carve/ev10cs4/`, `meshes/carve/ev10cs5/` | Byte copies of the mesh lane's frozen sets (fa2ec41, 2b016b4), with `MD5SUMS` (this build's manifest), the lane's `FROZEN.md` (byte copy) and `PROVENANCE.md` (source commit, GT-freedom, layout and inertia vs ev10, the failed gate 4a, the trades). |
| `tools/e10cs_pieces.py` | `import` (git show, file by file; refuses without a matching FROZEN.md, refuses to overwrite), `check` (file set and md5 = MD5SUMS = FROZEN.md, piece counts, floor plate), `compare` (PREREG 2.2 clause (a)), `assets` (col_NN = piece_NN, URDF inertial = inertia.json, URDF md5s and inertials). |
| `tools/e10cs.py` | `pieces`, `assets`, `arms`, `cells`, `choose`, `gate`, `verify`, `verdict` (PREREG sections 2-6). It pins each set's MD5SUMS md5 and URDF md5s, and V's md5 / fingerprint / base md5. It reuses `e10v_verify.rule2` and `e10v_verdict.verdict` unchanged. |
| `ops/jobs/ev10_cs.sh` | The job. Run id `<date>-e10cs-<sha7>`; `PIECESET=ev10cs4|ev10cs5` (required, nothing else overridable). |
| `ops/jobs/glock_public.sh` | Opt-in `EVAL_CS_REF=1`: allows the PERC prefix `perc2e10css<seed>` with SPLIT=eval, episode 10, RUN local and REQUIRE_REUSE=1. That is 1 code line plus 4 comment lines; the default path is unchanged (section 6). |
| `docs/research/work/eval10-cs4-20261101/` | PREREG.md, BUILD.md, JOBS.txt, `cpu/scripts/` (tests), `cpu/mock/` (end-to-end mock), `cpu/out/` (outputs). |

- **Reused unchanged:** `tools/e10v_score.py` (scoring), `tools/e10v_verdict.py` (the rule), `tools/e10v_verify.py` (rule 2),
  `tools/e10nj.py` (overflow, lift), `pipeline/make_assets.py`, `tools/no_oracle.py`.
- ev10_v4p.sh's mechanisms reused: the re-run manifest pull and confirm() (its draw loop verbatim, static check).
- Not changed: `ops/jobs/ev10_v4p.sh`, `ops/jobs/ev10_nj.sh`, every e10v / e10nj tool, the pack jobs, `ops/box/*`
  (`cpu/out/static_checks.txt`).
- **A wrapper job, not a knob in ev10_v4p.sh.** This is the njmax build's argument. Almost every stage would need a branch:
  run id, result folder, prefix, no reference stage, cells before the choice, the gate, the verdict. ev10_v4p.sh stays
  byte-identical.

## 2. Reference: reuse e10v's V (the decision and its evidence)
- **Dependency audit [M, e10v job.log + code].** V's construction used the old pieces at four stages:
  1. the V4p track's nest seat, `nest_physics.py --pieces meshes/carve/ev10` (plain MuJoCo; e10v's log: beige dz -1.151 cm
     median over 39 settled frames);
  2. mkref and contact retargeting, on the ev10 assets;
  3. grasp lock + wrist ILC (4 iterations) and the zero-action replay / rest check in FlashCHORD on the ev10 URDFs;
  4. REPLAN 1, which was a no-op: "every object is where its reference says before its grasp; nothing to re-plan".

  rest_check.json / zero_score.txt are copied to the seed folders only because glock_public.sh's REUSE_REF requires them;
  nothing reads their values (recorded in arms.json).
- **What a rebuild would change [M]** (`cpu/scripts/seat_compare.py`, scratch `seat.sh`). The V4p nest seat was re-run on CPU
  with each piece set on the same S12 output, with pinned venvs as the e10v B0:
  - the ev10 run reproduces mask10's / e10v's expect track exactly (md5 fa449903...);
  - nest_physics dz (beige vs the S12 track, hands-off): ev10 -1.144 cm, ev10cs4 -2.212, ev10cs5 -2.012 (median);
  - against V's track, only the beige moves, and only in the 45 hands-off frames: ev10cs4 1.07 cm median (1.82 max),
    ev10cs5 0.88 cm (1.63). The blue cup and every in-hand frame are unchanged.
- **Decision: reuse V, byte for byte** (PREREG 2.3). It is the smallest sound change: one changed input against e10v (pieces
  plus their inertia). The gate bar and the rule's V side stay as agreed. The rule's P side cannot be helped by a rebuild.
  A rebuild is a second large change outside the orchestrator's condition.
- **Cost of the reuse, disclosed:** at rest a nesting policy's beige can sit ~1 cm below V's beige in the last ~40 frames.
- **V over P:**
  - V passed the ep11 gate.
  - V's seated beige is ~1.2 cm closer to the cavity-safe seat than P's (e10v identity.json: beige V vs P, hands-off,
    1.23 cm).
  - But the mesh lane's and determined-wright's gates were measured on P, not V. Whether V + ev10cs5 is clean at 4,096
    worlds is first measured by this job's overflow count. A CPU contact budget of V + ev10cs5 at 32 x 60 was not run here:
    it needs determined-wright's patched FlashCHORD copy. It would be an optional $0 pre-launch check for that lane: budget.py
    on V md5 5d22fc57... with `--pieces meshes/carve/ev10cs5`.

## 3. The pieces
- **Import [M].** `tools/e10cs_pieces.py import`:
  - **ev10cs4**: from fa2ec41. 50 input files, md5 list = its FROZEN.md. Per-cup md5-of-md5-list blue 8ca4996c / beige
    7f8bff4c, which equal the mesh lane's README values. MD5SUMS md5 c745ebc8c3e86cadc5301a7b2351c5c1.
  - **ev10cs5**: from 2b016b4, MD5SUMS md5 045d8921d5fe548ffebbee3cc21e798b.
  - The folders are unchanged at the lane's tip 1373603 (git diff empty), and ev10cs4 is unchanged from its build 7e4bc6a
    except the added FROZEN.md.
- **Provenance [R].**
  - The lane's README says "GT-free; nothing read here is a scan, mocap, a dataset pose field or an *_align file".
  - Inputs: lathe profiles fitted to our library_v3 meshes (md5 7542631... / 6226281..., equal to this repo's), ev10's base
    hulls, and the packed reference P for the gate frames.
  - [M] `tools/no_oracle.py` accepts both folders: no BAD name, and no .obj matches the denylist's public-scan or
    scan-template sha256s.
- **Layout [M].** The same as meshes/carve/ev10: `<obj>/piece_NN.obj`, `<obj>/inertia.json`, `<obj>/lathe_collision.json`,
  `carve.json`. meshes/carve/ev10 also has inertia.json (and an fc_test/ folder that make_assets ignores).
  `pipeline/make_assets.py` (since d9c3f7d) reads `<pieces>/<obj>/inertia.json` whenever pieces exist, so both the packed
  set and the new ones use piece-derived COM / inertia.
- **Inertia (second changed variable) [M, CPU make_assets library_v3 --pieces <set>, 0.3 kg].**
  - The same command on meshes/carve/ev10 reproduces e10v's box URDFs byte for byte (82ff6cb8... / b994e584..., e10v's
    arms.json).
  - Kept as the pipeline makes it (orchestrator decision; no copy of the packed inertia).

| cup | quantity | packed ev10 | ev10cs4 | ev10cs5 (used) |
|---|---|---|---|---|
| blue | COM mm | (0.73, 1.55, 2.99) | (0.54, 1.15, 15.77) | **(0.46, 1.04, 19.05)**: +16.1 mm along the axis |
| blue | ixx / iyy / izz | 9.849e-4 / 9.838e-4 / 4.405e-4 | 9.884e-4 / 9.879e-4 / 4.579e-4 (+0.4 / +0.4 / +4.0 %) | 1.0036e-3 / 1.0031e-3 / 4.448e-4 (+1.9 / +2.0 / +1.0 %) |
| beige | COM mm | (1.52, 5.53, -4.17) | (1.54, 5.51, -5.57) | as ev10cs4 (-1.4 mm) |
| beige | ixx / iyy / izz | 8.904e-4 / 8.903e-4 / 2.990e-4 | 9.044e-4 / 9.043e-4 / 2.683e-4 (+1.6 / +1.6 / -10.3 %) | as ev10cs4 |
| URDF md5 | blue / beige | 82ff6cb8 / b994e584 | 8511f0d3 / 1a8cb9d8 | ac8d296b / 1a8cb9d8 |
| collisions | blue / beige | 53 / 49 | 24 / 21 | 24 / 21 |

- **The choice: ev10cs5** by PREREG 2.2: (a) [M] 46 / 51 identical, only the plate + 4 records differ
  (`cpu/out/pieces_compare_cs5.json`); (b) [R] be1e893, 0 / 0 lines; (c) both before 06:30 UTC.
- **Indicative only (plain MuJoCo over-counts against MuJoCo-Warp), ev10cs5 [R, the mesh lane's README section 10]:**
  - f124 drops: 0 of 16 copies through the floor (ev10cs4: 6 / 16);
  - gate-1 max overlap at f124: 3.9 cm3 against their 3.0 bar (FAIL; the median is unchanged at 0.206);
  - f111: 3 of 16 plain-MuJoCo copies overflow (gate 2 FAIL);
  - gate 4a blue 0.402 (FAIL, as every set);
  - blue COM 16.1 mm toward the base (19.05 mm in file z).
- **The FlashCHORD numbers [R]:** determined-wright be1e893 gives 0 / 0 overflow lines at 32 x 60, max 503 / 504 rows of 512.
  Headroom is 8-9 rows (ev10cs4 448 / 459). **At 4,096 worlds the worst world may occasionally exceed 512**, so the job's
  first check is the overflow count, with PREREG 5.4's > 1,000-lines label. The 8 mm nest test (05:17 UTC; release max depth
  4.0 vs 5.5 mm, driven 0.12 vs 0.14 cm) used determined-wright's own 8 mm variant (30.7 cm3), close to but not
  byte-identical with ev10cs5's plate (30.93 cm3) [R].

## 4. Pack eligibility: the config diff (`cpu/out/config_diff_test.json`, 7/7 pass) [M]
The test uses `tools/e10cs.py config_diff`, the function the box's `cells` step runs. It is the same flattened
stored-config diff as `tools/e10nj.py identity`.
- REAL packed gl10A2 checkpoint (sha256 76a12265...) vs REAL e10v s43 checkpoint (bcc51063...): 480-key config. The diff is
  `env.reset.seed, output_dir, reference.parquet, reset.seed, task.parquet, training.seed`, all allowed. sim / env.sim read
  512 / 256.
- A stand-in of this job's s43 checkpoint (e10v's with only the paths rewritten to `perc2e10css43`) gives the same diff, and
  no_oracle accepts it.
- That is the stored config this job writes:
  - ev10_cs.sh's recipe lines are e10v's verbatim but PIECES (static check);
  - the training CLI template is glock_public.sh's, unchanged;
  - TRAIN_ARGS equal e10v's REAL job log line (mock check);
  - PIECES does not enter the config: the pieces reach FlashCHORD only through V's URDF paths, which `cells` checks by md5.
- Negative controls: a 1024 stand-in (sim keys outside the allowed set, non-stock limits) and an extra config key are both
  caught. no_oracle still refuses the 1024 stand-in.

## 5. The pack guard accepts this run (`cpu/out/guard_test.json`, 23/23) [M]
- **Accepted (18):**
  - the run id `20261101-e10cs-abc1234` and its store paths;
  - `perc2e10css42 / 43`, the refs / runs / results folders and `results/ev10_cs`;
  - `ev10_cs.sh`, `e10cs`, `eval10-cs4-20261101`;
  - both piece folders (as names and walked by content);
  - an `EP:DIR` word;
  - the stock stand-in checkpoint and a kit checkpoints JSON naming it.
- **Still refused (5):** the njmax run id, `results/ev10_nj`, `perc2e10njs43`, the 1024 stand-in and a kit JSON naming it.
- On the box, `confirm()` runs no_oracle on the chosen checkpoint and its results before any official draw
  (`no_oracle_choice.txt`, required by verify). no_oracle also runs on the piece folder and on every e10v input.

## 6. Default paths unchanged [M]
- **glock_public.sh** (`cpu/scripts/guard_equiv.sh` -> `cpu/out/guard_equiv/summary.txt`): the PERC guard block of one() was
  cut from d153ea9 and from the working tree and run over **11,232 cases** (SPLIT x 13 prefixes x RUN x REQUIRE_REUSE x
  episode x EVAL_LOCAL_REF x FC_DR_PATCH x EVAL_NJ_DIAG x EVAL_CS_REF).
  - With EVAL_CS_REF unset or 0: **0 differences**.
  - With EVAL_CS_REF = 1: exactly 16 cases change, all newly ALLOWED and all `perc2e10css42|43` / eval / episode 10 /
    local / REQUIRE_REUSE=1.
  - The static check confirms 1 code line added and 0 removed.
- **ev10_v4p.sh is byte-identical.** Its end-to-end mock 'pass' (31 Oct's harness, unchanged) re-run on this build's code
  reads **SWAP-ELIGIBLE** (section 8).
- `cpu/out/static_checks.txt`: ALL PASS. It covers:
  - 24 files / folders unchanged since d153ea9, including make_assets.py, no_oracle.py, meshes/carve/ev10 and library_v3;
  - the recipe lines verbatim but PIECES;
  - the confirm() draw loop (4 differing lines: names and the overflow count in its log line);
  - bash -n / py_compile;
  - the run-id and PIECESET refusals;
  - no sim limit named in the job;
  - both piece sets pass check, and clause (a) holds.

## 7. Verdict fixtures (`cpu/out/verdict_tests.json`, 21/21) [M]
Synthetic result folders, no scores of any real run:
- **Gate:**
  - e10v-like seeds (0.4524 / 0.4512) give NO-SWAP "training-box gate not met";
  - a mean exactly at 0.4632 does not meet the strict gate;
  - a thin seed (n 7) and an INVALID seed are not counted.
- **Labels:** missing seed -> INCOMPLETE; INVALID cell -> INVALID; verify failure and STOPPED -> INVALID; 9 confirmation
  draws -> INCOMPLETE.
- **Swap rule:** a_V holds with a_P failing -> NO-SWAP; c_V failing -> NO-SWAP.
- **Inclusion bar:**
  - +0.037 / +0.0375 -> INCLUDE;
  - +0.037 / +0.0075 -> SWAP-ELIGIBLE, NOT included;
  - exactly +0.02 / +0.02 -> included;
  - +0.002 (pack 9b-like) and an EQUAL FLOOR +0.007 -> NOT included.
- **Overflow:** 1,001 lines -> "pieces not clean in training" attached, rule still applied; 1,000 -> no label.
- **Lift:** 5.0 cm holds, 0.2 cm does not.
- **Seed choice:** within 0.005 -> lower sd; 0.006 apart -> higher mean; full tie -> 42.

## 8. CPU mock of the whole job (`cpu/mock/`, outputs `cpu/out/`)
- **Harness:** the e10v mock's setup.sh / run_mock.sh / hf_stub.py, and this folder's `stub.py`: the njmax mock's stub plus
  e10cs*.py REAL, the trainer's full argv in its audit, and MOCK_OVF_512 default 0.
- The fake store is this build's own e10v mock push, renamed to `20261031-e10v-caf38fb`, with e10v's REAL curve.json files.
- **Test-only edits (`fix_store.py`, recorded per scenario in `test_edits.json`):**
  - V's two asset-path columns are rewritten to the mock box's content root. On a real box both are /content. The
    fingerprint is unchanged, and e10v's arms.json md5 follows.
  - The repo COPY's three V pins in e10cs.py are set to the mock V. The piece-set, URDF and packed-sha256 pins are the real
    ones.
- **REAL:** ev10_cs.sh, glock_public.sh, ckpt_curve.sh, store.sh, make_assets.py (on the real piece folders), qa.py with the
  real kit, no_oracle.py, e10cs.py, e10cs_pieces.py, e10nj.py, e10v_score.py, e10v_verdict.py.
- Mock numbers are NOT evidence about H-cs.

Final runs on the final code, 1 Nov ~05:40-06:30 UTC (`cpu/out/mock_checks.txt`, `mock_check_<n>.txt`, `mock_<n>/`):

| scenario | injected | outcome (mock numbers) | checks |
|---|---|---|---|
| e10v | the DEFAULT path: `bash ops/jobs/ev10_v4p.sh`, e10v's mock 'pass' (MOCK_POLICY=copy) | SWAP-ELIGIBLE, VERIFIED | 28/28 |
| pass5 | ev10cs5; policy tracks V; 0 overflow lines | gate met (0.9997 / 0.9999); **SWAP-ELIGIBLE, INCLUDE** (gain V +0.544, P +0.512); beige lift 23.8 cm; chosen s43 | 34/34 |
| floor4 | ev10cs4; cups left at frame 0 | **NO-SWAP, training-box gate not met** (0.4555 / 0.4546 < 0.4632); no official draw; lift 0.2 / 0.3 cm | 34/34 |
| unclean5 | ev10cs5; policy tracks V; 5,000 overflow lines per training log | **SWAP-ELIGIBLE [pieces not clean in training]**, INCLUDE (the rule still applies) | 34/34 |
| invalid5 | ev10cs5; one extra config key in seed 43's training | **INVALID** (cells: s43 config differs in training.mock_extra_setting); no choice, no official draw | 29/29 |
| tamper5 | one blue piece edited in the box's repo copy | STOP at the piece check ("md5 differs from MD5SUMS: blue_cup/piece_03.obj"; clause (a) also fails) -> INVALID; nothing pulled, trained or evaluated; verdict and push still written | 12/12 |
| badset | `PIECESET=ev10cs6` | refused at the start (exit 1); nothing pulled, run or pushed | 3/3 |

Every full scenario checks the following:
- no store listing; every download is a single file of e10v's run or of the H5p7 draws; exactly one upload;
- nothing written under e10v's, the njmax run's or the packed names;
- the piece set's pinned MD5SUMS md5 (and clause (a) for ev10cs5);
- the REAL make_assets build's URDF md5s and 24 / 21 collisions;
- arms equal to e10v's arms.json, V naming the set's URDFs, not e10v's;
- no_oracle accepting the pieces and every input;
- **two trainings** (seeds 42 / 43, 70,004,736 steps, on the seed copies, loading the set's URDFs at 0.3 kg);
- **no sim.* override; saved sim / env.sim 512 / 256**;
- every CLI key equal to the packed config;
- **TRAIN_ARGS byte-identical to e10v's REAL job-log line**;
- the CLI key set = the glock_public.sh template + TRAIN_ARGS;
- REUSE_REF twice, no reference stage;
- the collision-pieces log line naming the set;
- overflow counts = the injected counts, and the label;
- lift 7 x 3 per seed with e10v's REAL controls (2.5 / 0.3 cm);
- cells (VERIFIED, config diff within the allowed keys, stock limits);
- the choice = the pack 9b rule;
- the gate;
- 10 official calls at stock 512 on the pristine worktree only when the gate is met, and no_oracle accepting the chosen
  checkpoint;
- scored counts (conf 10 / 0, packed 10, old 1, train 10 + 10) with every own-reference check ok;
- the inclusion reading;
- the summary's piece set, MD5SUMS md5, the 50-line manifest and the URDF inertials.

**Two harness fixes during the build:**
- The check first read the trainer's argv one element short (a check bug, not the job's).
- The job's `cp -n` (warns on new coreutils, and in the mock that stderr line clobbers the head of job.log) became
  `[ -e d ] || cp`.

The six cs scenarios were re-run after both fixes, so all of them are on the final code: **174 / 174 checks** with the e10v
row. The e10v row ran on this build's glock_public.sh and the unchanged ev10_v4p.sh; the later fixes touch only
ev10_cs.sh / e10cs.py, which the default path does not run.

## 9. Commit and PREREG
- Branch `worktree-agent-a85860be5329e0f22`, based on `origin/claude/focused-pascal-2nz9s1` d153ea9.
- Commits:
  - 9f49f4a: the piece import, e10cs_pieces.py and the seat check;
  - 13c4133: PREREG.md, the job, e10cs.py, the glock_public.sh opt-in, the tests and the mock;
  - then the build notes, the mock outputs and two small fixes (the job's `cp -n`, a truncated failure message).
- **PREREG.md sha256 `d7d31381ef97f8b06952989324d51e64998740fa25358b00c79b735b5a474259`**, committed in 13c4133 before any
  result and unchanged since.
- The launch commit must contain it unchanged.
- The e10v default-path mock ran on this build's glock_public.sh (with the opt-in) and the unchanged ev10_v4p.sh. The later
  fixes touch only ev10_cs.sh / e10cs.py, which the default path does not run.

## 10. Risks and open points
1. **The headroom is thin.** ev10cs5's 32 x 60 maximum is 503 / 504 of 512. At 4,096 worlds a few worlds may exceed 512, and
   a policy that starts nesting may add rows. PREREG 5.4 labels > 1,000 lines; the rule still applies.
2. **The gates were measured on P, not on V** (section 2). V + ev10cs5 at 4,096 worlds is first measured by this job.
   Optional pre-launch: determined-wright's budget.py on V.
3. **The seat offset.** The cavity-safe seat is ~0.9 cm (ev10cs5) below V's beige at rest. It caps, but does not block, a
   nesting policy's score. A V rebuilt with the new pieces is a later, separately pre-registered step.
4. **Two changed variables:** the pieces and their inertia (blue COM +16.1 mm). A result cannot separate them.
5. **The gate uses training-box draws** (patched FlashCHORD tree, 1 world, explicit resets). The official evaluator can be
   harsher; the confirmation draws are the official test.
6. **Floor-level noise.** A floor policy might pass the 0.4632 gate by noise: e10v's seeds' sd ~0.017, and one 10-draw
   max was 0.4724. That costs ~5 min of draws. Such a policy would face the rule and the +0.02-on-both bar, which a floor
   cannot clear.
7. **No re-run mode.** INCOMPLETE needs a new decision.
8. **Store dependence:** e10v's run (rerun_files.txt, V, base, packed copies, curves) and H5p7's draws. All were read in
   the mock's store layout. The real files were read by the njmax build on 1 Nov.
9. **The old packed draw** is pack 6's eval-10 rollout (md5 64fdd856...). Packs 9a+ and 9b carry it unchanged [M], so the
   secondary clause compares against the board's current rollout.

## 11. Re-running the CPU evidence (S = the session scratchpad, R = the repo)
- Python with numpy / pyarrow / trimesh: `S/map/scoring/venv/bin/python`.
- Assets per set: `python pipeline/make_assets.py meshes/library_v3 S/e10cs/assets/<set> --pieces meshes/carve/<set>`, then
  `python3 tools/e10cs_pieces.py assets --assets S/e10cs/assets/<set> --pieces meshes/carve/<set>`.
- Seat: `bash S/e10cs/scripts/seat.sh ev10 ev10cs4 ev10cs5` (pinned venvs S/ep11gate/{e11g_venv, phys_venv}, input
  S/ev10retrain/cpu_rebuild). Then `cpu/scripts/seat_compare.py --base S/e10cs/seat/ev10/V/ep10/poses.npz --cand
  ev10cs4=... --cand ev10cs5=... --out cpu/out/seat_compare.json`.
- `cpu/scripts/config_diff_test.py --repo R --packed <gl10A2 policy.safetensors> --e10v <e10v s43 policy.safetensors> --work
  <dir> --out cpu/out/config_diff_test.json`.
- `python -I cpu/scripts/guard_test.py --repo R --standin <dir>/standin_e10cs_s43/policy.safetensors --neg
  <dir>/neg_njmax1024/policy.safetensors --work <dir> --out cpu/out/guard_test.json`.
- `bash cpu/scripts/guard_equiv.sh R cpu/out/guard_equiv` (~4 min); `bash cpu/scripts/static_checks.sh R
  cpu/out/static_checks.txt`; `python -I cpu/scripts/verdict_tests.py --repo R --work <dir> --out cpu/out/verdict_tests.json`.
- `bash cpu/mock/run_all.sh [scenario ...]`. Run e10v first; each scenario takes ~10-15 min on 4 cores, mostly scoring.
