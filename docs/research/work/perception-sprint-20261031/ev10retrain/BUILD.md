# Eval-10 retrain on the S12 V4p reference: build notes (31 Oct 2026, CPU only, nothing launched)

**Question.** If the ep11 rollout gate (`../ep11gate/PREREG.md`, run `20261031-e11g-663b7df`) PASSes, does the packed
eval-10 recipe retrained on eval 10's V4p reference beat the packed eval-10 policy under the agreed pack-10 swap rule,
against both our references? Rule, outcomes and INCOMPLETE / INVALID handling: `PREREG.md` (sections 1–9 written
~17:31 UTC, sha256 `15e33e68…` at writing, before any eval-10 V4p reference, policy or score existed; unchanged since).
Launch string and cost: `JOBS.txt`. Labels: [M] measured here, [E] estimate, [H] hypothesis. Machine: this Claude cloud
VM (4 CPU), 17:30–19:00 UTC, $0; no GPU, Vast or Kaggle; nothing committed or pushed by this step. Eval 10 has no
ground truth; nothing here reads mocap, scans or `observation.objects`.

**Job.** `ops/jobs/ev10_v4p.sh` (run id `<date>-e10v-<sha7>`), one RTX PRO 6000 box: V4p track + B0, base reference
(mck), grasp-lock stages once, seeds 42 and 43 one after the other, rule-2 seed choice, 10 official confirmation draws on
the pristine evaluator, scoring of every rollout against V and P, verify, verdict SWAP-ELIGIBLE / NO-SWAP / INCOMPLETE /
INVALID. Expected ~$3.0–7.1, central ~$4.8 [E] (JOBS.txt table).

## 1. Eval 10's stored perception track (the input of the V4p chain) [M]
The track mask10 used for eval 10 (`../mask10/eval10/inputs_sha256.txt`; T1's `t1_eval10.sh`): the pack-6 copies of
evB's perception, the one behind the packed reference (packs 6–8). All fetched here with one `hf_hub_download` each
(no listing; `scratchpad/ev10retrain/dl`), md5 equal to mask10's files:

| file | store path | md5 |
|---|---|---|
| track | `runs/20261026-pack6-5203d42/perc2/ep10/poses.npz` | `4fc5529eb457d706588e9b9fcf703baa` (sha256 `fb9103fa…` = evB's) |
| VO record | `runs/20261026-pack6-5203d42/perc2/ep10/vo.json` | `64248915f0f480069521e4847da190c3` |
| frame-0 depth source | `runs/20261026-pack6-5203d42/perc2/ep10/det_f0.npz` | `94c63769e568da177406ff6c39317349` |
| → refine's `depth0.npy` | det_f0 `depth` as float32, repeated 2×2 (T1's construction) | `d1543641b2f20cf024cdf1039631f671` |
| hands (KR inside) | `runs/20261026-pack6-5203d42/refs/perc2mck/ep10/hands_refined.npz` | `419c230800b727240663597916cba59e` |
| packed base reference's hands | `runs/20261026-gl10A2-5e0e100/refs/perc2mck/ep10/hands_refined.npz`, `hands.npz` | `419c2308…` (= pack 6's), `15196aaf02dd9fa7c0b076ccd0e4c463` |
| packed reference P | `runs/20261026-gl10A2-5e0e100/refs/glockt/ep10/processed/sequence_id=t3_ep010/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `1a5003d94852c275519066645a1b9869` (packed_refs.json '10') |
| packed checkpoint | `runs/20261026-gl10A2-5e0e100/results/glock_public/ep10/best/policy.safetensors` | md5 `1aadc812…`, sha256 `76a12265…cbb9` |
| old packed draw | `runs/20261026-pack6-5203d42/results/submission/results/episode_000010.{parquet,json}` | `64fdd856…`, `92afa9d5…` |
| eval-10 depth cache | `cache/depth/eval/ep10/depths_fs0.5.npy` | 1,030,400,128 B, 161 × 1000 × 1600, frame-0 sha256 `ab38c4d7…` (HTTP range read here) |

`tools/no_oracle.py` accepts every store path, every local input file, the V4p track and the new folder names
(`cpu/out/no_oracle_inputs.txt`: 22 inputs, none oracle-derived).

## 2. The V4p track, rebuilt on CPU from the store inputs with the committed code [M]
`tools/e10v_track.sh IN OUT PY FPY` (new; the mask10 eval-10 commands, `e11g_tracks.sh` arm T for an eval-10 input
folder: `poses.npz`, `vo.json`, `depth0.npy`, `hands_refined.npz`, no `poses_world_vo.npz`, as mask10's input), in the
gate's pinned venvs (refine numpy 2.5.4 / scipy 1.18.1 / trimesh 5.2.0 / rtree 1.4.1; physics numpy 2.4.6 / scipy 1.18.0 /
trimesh 4.12.2 / mujoco 3.8.1), code refine.py `aae1fb41…`, nest.py `7e063b94…`, nest_physics.py `e9500036…`:

| stage | md5 here | mask10 (`scratchpad/mask10/eval10/posthoc/`) |
|---|---|---|
| S12 support (`pre`) | `2a22cc61a033fe7e8e0b03c92364ae00` | `pre4`: **identical** |
| nest_physics inner (`phys`) | `2e584833455528fba036f90a4ecd02a2` | `pre4_phys`: **identical** |
| S2 → **V4p** `poses.npz` | `fa449903630d6bb42dd79131331f4b6b` | `V4p`: **identical** (also `poses_world_vo.npz` `dd64c7b2…`) |

S12 window blue_cup ← beige_cup [53, 161), pre-nest f44, held to the episode end; nest_physics settled 39 frames
(run f122–160), beige dz median −1.14 cm — the mask10 numbers (`cpu/out/rebuild/`). Run time 10 s.
`expect/V_poses.npz` (62 KB, the rebuilt file) and `expect/expect.json` (its md5, the stage md5s, inputs, code, versions)
are committed for B0 only (`.gitignore` gets a one-folder exception); the box never uses them as inputs.

**B0 environment sensitivity** (`cpu/out/b0_kernels.txt`, the same rebuild under 10 OpenBLAS kernel types):
SkylakeX and Cooperlake IDENTICAL; Haswell, Zen, Sandybridge, Prescott, Nehalem, Core2, Bulldozer, Atom **DIFFERS**
(beige cup only, every frame; worst 0.90 mm / 1.31° on Haswell and Zen; blue cup 0.0 mm; camera byte-identical): all
inside the go band (5 mm, 2°). So the box is expected to read IDENTICAL on recent Intel and DIFFERS (flagged, go on) on
AMD, as the gate. The 1.31° (vs ep11's 0.65°) leaves 0.7° of margin [M on 10 kernels; a box kernel outside them is H].

## 3. mkref's depth (PREREG 3.2 rule, applied before any V4p reference existed) [M]
mkref reads frame 0 only (table plane and disc). The depth behind the packed reference (the evB box's) was never stored.
`cpu/scripts/depth_rule.py`: mkref's own `fit_table` / `table_frame` (its defaults) on the packed reference's own input
(the raw stored track), compared with the packed base reference's `table_frame.npz` (`cpu/out/depth_rule/depth_rule.json`):

| candidate | normal angle to packed | \|Δd\| | table-frame Δ (rot / trans) | bottoms blue / beige (cm) |
|---|---|---|---|---|
| D1 det_f0 (half res, float16, 2×2) | 0.040° | 0.21 mm | 0.040° / 0.37 mm | +0.13 / −0.18 |
| **D2 eval cache frame 0** (29 Oct recomputation) | **0.000°** | **0.000 mm** | **0 / 0** | **+0.09 / −0.22** (= the packed mkref log) |

**Chosen: D2** (both clauses of the rule). D2 reproduces the packed table frame exactly, so the new reference differs
from the packed one by the track change (S12 + physics + S2), not by the table. On the V4p track D2 gives 0.004° /
0.36 mm vs the packed frame (the S2 shift of the frame-0 centroid). The job pulls the full cache (1.03 GB) and checks
bytes, shape and the frame-0 sha256 before use.

## 4. Shared code: one opt-in change, default byte-identical [M]
- `ops/jobs/glock_public.sh`: with `SPLIT=eval` a PERC prefix was allowed only as `mass<A>s<seed>` with `REQUIRE_REUSE=1`
  (no reference stage on an eval episode). The retrain must run the grasp-lock stages on eval 10's new base reference
  under a new name, so `EVAL_LOCAL_REF=1` (opt-in) also allows `perc2e10v` / `perc2e10vs<seed>`, episode 10, RUN local
  (6 added lines, 1 changed; the log message is unchanged).
- **Proof** (`cpu/scripts/guard_equiv.sh`, `cpu/out/guard_equiv/`): the guard block of `one()` is cut out of git HEAD and
  of the working tree and run as a function over 1,944 cases (SPLIT × 12 prefixes × RUN × REQUIRE_REUSE × episode ×
  EVAL_LOCAL_REF): **0 differences** with `EVAL_LOCAL_REF` unset or 0; with it = 1 exactly 9 cases change, all
  `perc2e10v[s42|s43]`, eval, episode 10, local. `bash -n` clean.
- Not changed: `pipeline/*` (refine, nest, mkref, qa, pipeline_ep), `tools/nest_physics.py`, `tools/e11g_*`,
  `tools/mass_*`, `tools/no_oracle.py`, `ops/jobs/{ep11_gate,h5_reeval,pack_eval,submit_pack}.sh`.

## 5. Scoring against both references: `tools/e10v_score.py` [M]
- The evaluator's rollout parquet holds the reference it was trained on: on the packed draw its reference columns equal
  P's rows at each `reference_frame` (max |Δpos| 0, |Δq| 6e-8). So scoring against another reference X = replacing those
  columns with X's rows; the own-reference check repeats this comparison on every scored rollout (INVALID if > 1e-6).
- sim_vs_ref is qa.py's exact metric (kit reader, world 0, 500-point sphere, warp to the reference start); RPE / MPPE /
  AUC are the score-status session's audit method (audit.py + rdlib from `origin/claude/standings-20261031`),
  re-implemented with the GT-free functions only (no mocap / scan / episode-parquet reader in the tool).
- **Check on the packed draw vs P** (`cpu/out/scorer_check/packed_draw_vs_audit.json`): sim_vs_ref **0.4563** (= qa.py,
  = packs 7/8's summary); RPE **15.7575**, MPPE **8.5438**, AUC **0.4577**, audit flag True — equal to audit.py run here on
  the same file (and to its committed evalaudit.json), per object too (blue 0.6755 / beige 0.2399 AUC; beige travel 0.69
  of 25.13 cm). failure (RPE > 5 cm): True.
- Cost: ~10 s per rollout and reference on one core; `--jobs` workers (default min(8, cores)); parallel output equals
  serial. Box: 41 rollouts × 2 references ≈ 2 min.

## 6. Verdict tool and seed choice [M]
- `tools/e10v_verdict.py` applies PREREG section 5 (clauses a/b/c/s on V and on P; INCOMPLETE / INVALID first).
  Fixtures `cpu/scripts/verdict_tests.py` → `cpu/out/verdict_tests.json`: **20/20** (pass; each clause failing alone on
  one reference = both-reference disagreement → NO-SWAP; ties hold; 9 draws on either side, no old draw, no chosen seed,
  draw 1 unscored, packed set missing → INCOMPLETE; verify failed / missing → INVALID; a NaN rollout counts toward no n →
  INCOMPLETE; a NaN that slips through as scored → INVALID; 11 draws read; the new policy at the floor → NO-SWAP).
- `tools/e10v_verify.py choose` (rule 2, local copy): equal to `mass_eval_verify.rule2` on 20,000 random seed tables
  incl. exact 0.005 gaps, thin seeds and sd ties (`cpu/out/rule2_equiv.json`: 0 differences).
- Recipe config: the packed gl10A2 checkpoint's saved config differs from the other packed grasp-lock checkpoints
  (seed43, fr32s46b, rcB) only in output_dir, task / reference parquet, the seed keys, `reference.num_frames` (episode
  length) and rcB's CURR_SCALE thresholds [M]; verify allows only output_dir, task.parquet, reference.parquet, reset.seed,
  env.reset.seed, training.seed (as `mass_eval_verify`), so `reference.num_frames` (161 = 161) and the curriculum must match.

## 7. CPU mock of the whole job (`cpu/mock/`, outputs `cpu/out/`)
A repo copy with `/content` → the mock root; stubbed GPU / IK steps (mkref stage (a) REAL then a minimal reference;
contact retargeting, grasp lock, ILC copy; the trainer saves the PACKED checkpoint's config with this run's paths and
seed, and audits every CLI training key against the packed config; the training-box evaluator and the kit's
run_policy_evaluation.py write REAL flash_chord parquets whose reference columns are the loaded reference); REAL
e10v_track.sh / refine.py / nest_physics.py, make_assets.py, pipeline_ep.sh, glock_public.sh, ckpt_curve.sh, store.sh, qa.py
(real kit), no_oracle.py, e10v_score.py / e10v_verify.py / e10v_verdict.py; a stub `hf` that serves single files and refuses
listings; the fake store holds the real input files and MOCK H5p7 rollouts of the packed policy (left at frame 0).
`run_all.sh` / `check_all.sh` → `cpu/out/mock_checks.txt`, `mock_check_<n>.txt`, `mock_<n>/`. Mock numbers are NOT
evidence about V4p.

Final run on the final code, 18:33–19:33 UTC (`cpu/out/mock_checks.txt`; 11 scenarios, 247 checks, all pass):

| scenario | injected | outcome | checks |
|---|---|---|---|
| pass | MOCK_POLICY=copy (the new policy tracks V) | **SWAP-ELIGIBLE**: vs V 0.9999 / RPE med 0.35 cm / 0 fails vs packed 0.4555 / 15.84 / 10; vs P 0.9628 / 1.07 / 0 vs 0.4474 / 15.80 / 10; seed 43 by rule 2; VERIFIED, own-reference checks 41/41 | 28/28 |
| floor | the new policy fails like the packed one (cups at frame 0) | **SWAP-ELIGIBLE [EQUAL FLOOR]** (margins 0.0008 / 0.0014; section 9 item 3) | 28/28 |
| worse | floor + the beige knocked 10 cm from f40 | **NO-SWAP** (c fails on V and P: median RPE 17.47 vs 15.84 cm) [EQUAL FLOOR] | 28/28 |
| invalid | one extra config key in seed 43's training | **INVALID** (config differs from the packed gl10A2 checkpoint in `training.mock_extra_setting`) | 24/24 |
| incomplete | seed 43's training exits 1 | **INCOMPLETE** (no chosen seed; no confirmation run) | 20/20 |
| rerun | a new box: `RERUN_FROM=<incomplete> SEEDS_TODO="43"` | **SWAP-ELIGIBLE** over both seeds; only seed 43 trained; 81 single-file pulls, 0 failed, 0 listings | 19/19 |
| topup | the 3rd official draw exits 1 | **SWAP-ELIGIBLE** (11 calls: rc 0 ×10, rc 1 ×1; 10 scored draws) | 28/28 |
| nopacked | the H5p7 run not in the store (404) | **INCOMPLETE** on the box (packed 0 scored; the summary pull gave up after ~50 s); `cpu_after.sh` then scored the H5p7 draws from the store → **SWAP-ELIGIBLE** (`cpu/out/mock_nopacked_cpu_after/`) | 24/24 |
| differs | `OPENBLAS_CORETYPE=Haswell` (a non-SkylakeX box) | B0 **DIFFERS** 0.90 mm / 1.31°, the job goes on with the box's track (mkref read its md5) → **SWAP-ELIGIBLE** | 28/28 |
| b0stop | the committed expectation replaced by the stored track | **STOP** before any reference (B0 MISMATCH) | 10/10 |
| badinput | a corrupted stored track served by the store | **STOP** before anything (md5) | 10/10 |

Every scenario: no store listing, every download single-file, exactly one store upload (the final push), hands_mp /
hand_refine / perc2 / score_registered never ran, nothing written under refs/glockt/ep10, refs/perc2mck/ep10,
results/glock_public/ep10 or refs/glock/ep10. Verdict scenarios also check: each seed trained once on its own copy of
V, seed and steps, 0.3 kg URDFs under /content/assets, every CLI training key equal to the packed config (10 keys),
mkref on the box's V4p track with the eval-10 cache and the stored hands under SPLIT=eval, the grasp-lock stages with
gl10A2's GL_ARGS and kp 400, CR `--rest_settle 1`, ≥ 10 official draws of the chosen checkpoint on the pristine
evaluator, the scored sets, VERIFIED. Scoring dominates the mock's time (~4–8 min per scenario on 2–3 cores).

## 8. What the box rebuilds that this VM cannot
E2S IK, contacts, contact retargeting (rest settle), grasp lock, ILC, re-plan, training, evaluation. The reference-level
change V vs P is therefore measured only on the box (`identity.json`: V vs P per cup over the S12 window and the
hands-off frames f122–160, and V − P blue-cup height). The mock's stage-(a) stand-in for V read 0.72 / 1.20 cm (blue,
window / hands-off) and 0.33 / 1.23 cm (beige) from P, blue −0.68 cm lower over the window [M on the mock stand-in only;
the real V adds contact retargeting and grasp lock].

## 9. Defects and findings from the mock (fixed before the final mock run; nothing launched)
1. **Re-run pulls of guessed paths** (first re-run mock, 18:27 UTC): the re-run pulled every possible best/ and
   confirmation file by name; an absent one costs `store.sh pull-files` 5 tries with 60–240 s waits (~10 min per file),
   so the re-run box sat in retries (the run was stopped; its log lines went to the job log, so the stall watchdog would
   not have caught it; the retry line: `cpu/out/mock_rerun_v1_defect_joblog.txt`). Fixed: `finish()` writes `rerun_results.txt` (the result files that exist) and a re-run pulls only
   `rerun_files.txt` + `rerun_results.txt` entries.
2. **The same cost for the optional H5p7 pulls** if the comparison set has not finished: now gated on its
   `h5_summary.json` (h5_reeval.sh writes it last) with `PULL_RETRY_S=5` (~1 min per absent file). Mock `nopacked`
   (the H5p7 run hidden) checks this path and the CPU completion after the box (`cpu/mock/cpu_after.sh`).
3. **Equal floor** (mock `floor`): a new policy that fails every draw like the packed one read SWAP-ELIGIBLE under the
   agreed rule ((b) ties at 1.0, (a) / (c) within noise on both references). The rule is unchanged; the verdict now
   reports an EQUAL FLOOR note (PREREG section 10). Verdict fixture `equal_floor_passes` documents it (21/21).
4. Test-side only: two verdict fixtures mutated the wrong draws at first (fixed; the tool was right).

## 10. Changes
| file | change |
|---|---|
| `ops/jobs/ev10_v4p.sh` | new: the retrain job (inputs + md5, depth cache check, pinned venvs, V4p track + B0, base reference, grasp-lock stages, identity, seed copies, 2 trainings, rule 2, 10 official draws, scoring vs V and P, verify, verdict, push; `RERUN_FROM` + `SEEDS_TODO` re-run) |
| `ops/jobs/glock_public.sh` | opt-in `EVAL_LOCAL_REF=1` (section 4; default unchanged, proven) |
| `tools/e10v_track.sh` | new: eval 10's V4p track from one input folder (the mask10 commands), `tracks.json` |
| `tools/e10v_verify.py` | new: `b0`, `arms`, `identity`, `choose` (rule 2), `verify` (imports e11g_verify / mass_verify / mass_arm helpers unchanged) |
| `tools/e10v_score.py` | new: GT-free scoring of rollouts against several references (qa.py metric + audit method) |
| `tools/e10v_verdict.py` | new: the PREREG section 5 swap rule |
| `.gitignore` | one exception: `docs/research/work/perception-sprint-20261031/ev10retrain/expect/*.npz` |
| `docs/research/work/perception-sprint-20261031/ev10retrain/` | PREREG.md, BUILD.md, JOBS.txt, expect/, cpu/scripts/ (dl.py, depth_frames.py, depth_rule.py, guard_equiv.sh, rule2_equiv.py, verdict_tests.py), cpu/mock/, cpu/out/ |

## 11. Risks and open points
- **Recipe config diff vs the packed checkpoint** (INVALID if any other key differs): checked on CPU only through the
  CLI keys the job passes (mock: 10 keys, 0 mismatches) and on the stored configs of other packed checkpoints; a
  FlashCHORD default that changed since 26 Oct would show up only on the box (the config is saved after training).
- **B0 band**: worst DIFFERS seen 0.90 mm / 1.31°, 0.7° under the stop (section 2).
- **The ep11 gate tests V4p on a twin without the eval-10 slide** (mask10 §4): a PASS there does not test the slide
  part of V4p; the confirmation against both references is what guards the swap.
- **H5p7 timing**: if its eval-10 rollouts are not in the store when this box ends, the verdict is completed on CPU
  (JOBS.txt "After the box"); the same code.
- **Seeds run one after the other** (~1.2 h, ~$1.5 more than two at once), for the proven glock_public path.

## Review status (31 Oct ~20:35 UTC)
- Integrity review: GO on condition of its F1/F2 (verdict-tool only, ~20 lines + one PREREG §10 line).
- Mechanics review: GO on condition of its F1 (draw 1 = the first confirmation invocation with a scored rollout) and F2
  (stop the confirmation loop after 3 consecutive draws without a rollout); F3/F4 recommended.
- The patches are tested in the reviewers' scratch copies. They are applied ONLY if the ep11 gate reads PASS (its seed-42
  interim is Δ +0.013; a PASS needs seed 43 ≈ +0.09), before the launch commit. Not launched.
