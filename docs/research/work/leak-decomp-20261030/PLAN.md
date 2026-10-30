# Leak decomposition on public episodes: final plan (30 Oct 2026, ~14:30 UTC)

Owner, 30 Oct ~13:20 UTC: dissect the pipeline on public episodes "with perfect knowledge" to find the leak; "you can
spend as much". Workflow wf_935444e9-2c5 (facts → three designs → this judgement). Labels: [M] measured, [E] estimate,
[H] hypothesis. LB = leaderboard AUC. **Nothing is launched. Every rental batch still needs the owner's go-ahead on its
cost (CLAUDE.md).** This file fixes the readings: it must be committed **before orcB's summary is read** (≈ 18:00 UTC).

## 0. How the three designs scored (1–10) and what this plan takes from each
| Design | Attribution clarity | Statistics | Buildable in ~1 day | Cost/time | LB decision value | Integrity | Sum |
|---|---|---|---|---|---|---|---|
| 1 Ladder (12 eps, cumulative rungs) | 7 (rung splits depend on order) | 6 (E12 × 2 seeds: power ≈ 0.65 at Δ 0.05) | 6 (object-anchored hands = risky new code) | 6 ($125–550) | 7 | 9 | 41 |
| 2 Factorial + Shapley (9 twins × 12 cells) | 8 (AOI/LOO are exact; F block needs new code) | 7 | 3 (216 trainings, F_t and H_t new, 30–40 h wall time) | 3 ($505) | 7 | 9 | 37 |
| 3 Decision-focused (CPU audits + 3 twins) | 6 (X* fitted to tracks mixes bias with registration) | 5 (rollouts on 3 twins only; leans on T ≈ a·S·R, ep11 residual +0.13) | 9 | 9 ($37–63) | 9 | 7 (puts an eval QA screen into a public study) | 45 |

Synthesis:
- From Design 3: the CPU reference-level backbone (all 20 episodes, deterministic, $0) and the decision table.
- From Design 2: the 6-cell pose × sim-geometry block, which gives exact add-one-in (AOI), leave-one-out (LOO) and Shapley numbers.
- From Design 1: the episode breadth, three score columns on every rollout, and the verdict rules.
- Added here: hand timing as a conditional 4th wave, and a standard-learner check for evals 1, 25 and 30.

## 1. Summary for the owner
1. On 10 public episodes where the true object motion is known, we rebuild our recipe and swap one stage at a time for its true version: scanned meshes as tracking templates, the mocap object motion, scanned meshes in the simulator, and hand timing matched to the true motion.
2. Every swap that ends in a robot rollout gets 2–3 trainings × 10 evaluations, because one policy can score 0.26–0.92 across evaluations. Mesh registration, reference building and timing are measured exactly on CPU, on all 20 public episodes, at no cost.
3. The public data has no true hands, masses, friction or spoon. Those parts are bounded, not measured, and every number says which kind it is.
4. The output is one table: the leaderboard AUC each stage loses, what "everything true" still loses (the robot/learner limit), and the eval-side fix each result triggers.
5. Cost [E]: core ≈ $215 (range $170–260); full plan ≈ $345 ($285–400), incl. 20 % contingency. About 180–230 GPU box-hours on 8–10 boxes at once. This needs a credit top-up (≈ $43 left of the $100 top-up [E, ledger 10:09 + orcB]).
6. Timing: CPU builds and checks today, perception boxes tonight, rollouts on 31 Oct, readings by 1 Nov morning. That leaves 1–4 Nov for eval fixes before the 4 Nov 22:00 UTC freeze.

## 2. Leak definitions (each number changes exactly one thing)

Notation:
- R = registered ADD-AUC vs mocap of a track or reference.
- T = rollout AUC vs mocap: mean over seeds of the 10-draw mean, failures included.
- S = sim_vs_ref; g = T − S, the quiet reference channel [M: draw sd 0.017, seed sd 0.010].

Scoring conventions, all three on every track, reference and rollout:
- **lib**: library_v3 as the submitted mesh, kit registration X_kit. This is the leaderboard convention, with the public scan standing in for the host scan.
- **\***: poses converted to scan frames by the physical relation X\*_geom (a surface fit of library_v3 to the scan, cup spin modulo symmetry), then scored with the scan.
- **trk**: like \*, but with a per-(episode, object) constant offset X\*_trk, fitted to mocap. Oracle diagnostic only.

All stage leaks below are read on \*, so registration never leaks into them.

| Leak | Definition | Level |
|---|---|---|
| L1 registration (submitted mesh) | T_lib − T\* on identical poses. Constant tracking bias = T_trk − T\*, reported beside it, not inside it | every track, reference and rollout; CPU, $0 |
| L2 template shape | R\*(P_s) − R\*(P_o): same depth cache, box and commit; noise floor from a P_o repeat. Rollout: AOI c2−c1, at scan geometry c5−c4 | GPU perception + rollouts |
| L3 tracker, given a true template | 1 − R\*(P_s). Rollout: c3−c2 and c6−c5 (the owner's "perception tested with the given scans"). Split by phase (frame-0 / untouched rest / held-moving / post-release) × hand occlusion, and by init vs drift (re-anchor at the mocap frame-0 pose) | CPU on Phase-1 tracks; rollouts |
| L4 reference construction | R after each mkref stage (raw → table + snap → contacts/IK → contact retargeting → S2 → grasp-lock trained reference). Run on O (pure construction defect) and on P (amplification) | CPU (stage a here; b–f on a CPU box with rtvenv) |
| L5 sim object geometry | AOI c4−c1 (perceived references, as on eval); LOO c6−c3 (true references) | rollouts |
| L6 hand timing (not true hands) | AOI c7−c1, LOO c8−c6. CPU: onset/release lag and fingertip-to-true-surface gap during true motion | rollouts (conditional), CPU |
| L7 copy ceiling | 1 − T\*(c6): robot + learner + physics (0.3 kg) + evaluator under true motion and true shape | rollouts |
| L8 spoon | Not measurable (no scan, no mocap). Bound from thin proxies (sweeper ep18/31, dust pan ep18/39/40) by anchor role, plus GT-free blind meshes (P_gf) | [E-analogy] only |

**Shapley.** Exact over {template T, motion K, geometry G} from c1–c6, because v(T,K,·) = v(K,·): φ_T = ⅓(c2−c1) + ⅙(c5−c4); φ_K and φ_G follow from the same table; φ_T + φ_K + φ_G = c6 − c1. AOI is the eval planning number (fix one stage, the rest stays ours). LOO is the owner's "true version of everything else". LOO − AOI is the stage's interaction.

**LB conversion, fixed now.** L_LB = (c/20)·Σ_e Δ(twin(e)), with c ∈ [0.74, 1.0], the measured transfer [M, refcheck/mapping].
- Eval → twin map: 1→ep2, 10→ep11, 14→mean(ep12, ep13), 19→ep18, 20→ep21, 25→ep24, 28→ep27, 30→ep31, 38→ep39; eval 8 → mean of ep27 and ep39.
- Reference-level ΔR on the other public episodes converts by a·S_e·ΔR_e (a = 1.025), only for evals with S_e ≥ 0.8 [M, RMSE 0.020]. The spoon evals get [E-analogy] rows, never added into the [M] total.

## 3. Experiment matrix

**Tier A, CPU, all 20 public episodes, deterministic, $0.** Runs on this VM plus one Vast CPU box (≈ $0.12–0.19/h, owner-allowed 13:25); first on `refine/in`, then re-run on the Phase-1 tracks.
- A1: L1 per (episode, object) at X_kit, X\*_geom and X\*_trk, plus a flip rate over 50 host-scan perturbations (decimate to 30 %, 1 mm noise, 10 % holes).
- A2: L3 phase split. A3: L4 construction stages, on O and on P. A4: hand audit against the mocap object motion. A5: frame-0 re-anchor.
- A6: scorer sanity (mocap through the kit submission path = 1.000) and frame-conversion invariance (≤ 0.002).
- A7: 2 s hands-free settle of every mocap rest configuration under lib, lib+carve and scan collision. This gates c4–c6 per twin: scan geometry is valid only where drift ≤ 1 cm and ≤ 5°.

**Phase 1, GPU perception** (from `ops/jobs/perc_ab.sh`, one depth cache per episode, 3 boxes). Per episode: P_o (our templates); P_s (scan templates) [oracle]; a P_o repeat on 10 episodes (GPU noise floor); and in Phase 1b, P_gf (the mesh session's blind meshes of sweeper and dust pan) on ep18/31/39/40. Each episode's bundle is pushed once: tracks, VO camera, depth0, plus the `refine/in` hands with md5 recorded. Every Phase-2 cell of a twin uses exactly this bundle.

**Phase 2, rollout block per (twin, seed).** One box per block runs 3 waves of 2 trainings. The 4th wave holds c7/c8 if H_t passes its CPU gate before launch.

| Cell | Object poses in the reference | Sim objects | Hands | Ground truth read |
|---|---|---|---|---|
| c1 P_o·lib | Phase-1 P_o | library_v3 + the twin's SF / carve pieces | perceived (bundle) | none (public; still an `-orc` run) |
| c2 P_s·lib | P_s → lib frames by X\*_geom | as c1 | identical bytes | scans |
| c3 O·lib | mocap → lib frames by X\*_geom (`oracle_poses` v2, gravity align, P_o camera) | as c1 | identical | mocap |
| c4 P_o·scan | P_o → scan frames | public scans (`_collision.glb` for boards and sweeper), SF=0, no pieces, 0.3 kg | identical | scans |
| c5 P_s·scan | P_s, native frames | as c4 | identical | scans |
| c6 O·scan | mocap in scan frames (no `--meshes`) | as c4 | identical | mocap + scans |
| c7 P_o·lib·hT (cond.) | c1 | as c1 | time-warped so holds start and end with the mocap motion (±1 frame) | mocap |
| c8 O·scan·hT (cond.) | c6 | as c4 | as c7 | mocap + scans |

Fixed for every cell: learner, steps (70,004,736), `GL_ARGS` (orcB PREREG §1), `CURVE_REP=3`, `NREP=10` (official evaluator code on the training box) and seeds. A per-cell gate G0 (reference ≥ 0.95 vs mocap for O cells, support check, frame-0 within 3 cm of perception) runs first; a failed cell is logged and not trained.

| Twin | Eval | Objects | Class (noisier of twin and eval sd, Facts 3) | Recipe (eval twin's packed one; parity checked by the policy session) | Seeds |
|---|---|---|---|---|---|
| ep11 | 10 | beige + blue cup | stable | grasp lock, gl10A2: SF=0 REPLAN=1 EVOLVE=0; ev10 pieces in lib cells | 42, 43 |
| ep39 | 38 | dust pan | stable | grasp lock | 42, 43 |
| ep12 | 14 | blue cup, rack | typical | grasp lock, evb1420 | 42, 43 |
| ep21 | 20 | blue cup, pitcher | typical | grasp lock | 42, 43 |
| ep27 | 28 | rack, pot | typical | grasp lock | 42, 43 |
| ep2 | 1 | pot, lid | hard | grasp lock (+ standard learner, Phase 3) | 42, 43, 44 |
| ep13 | 14 | blue cup, rack (hand-over + flip) | hard | grasp lock, SF=1 as orcB | 42, 43, 44 |
| ep18 | 19; spoon proxy | dust pan, sweeper | hard | grasp lock | 42, 43, 44 |
| ep24 | 25 | wooden pieces | hard | grasp lock (+ standard) | 42, 43, 44 |
| ep31 | 30; spoon proxy | sweeper, rack | hard | grasp lock, SF=1 as orcB (+ standard) | 42, 43, 44 |

That makes 25 blocks: 150 trainings, plus 50 in c7/c8. Left out of rollouts but kept in Tier A: ep0 (scan-template frame-0 failure), ep23 (identity swap), ep22 and ep26 (duplicate twins), ep40–45.

**Phase 3, standard-learner check.** ep2, ep24, ep31 × {c1, c3, c6} × seeds 42 and 43 = 18 trainings, as std30 / c01 / c25s42 (250M steps, sweep, NREP 10). Reason: the twin recipe differs from the packed recipe for evals 1, 25 and 30 (Facts 2 gap 2).

**Power** [E, Facts 3 at E = 10]: pooled ΔT ≈ 0.6–0.7 at Δ 0.05 (2–3 seeds) and ≥ 0.95 at Δ 0.10; pooled Δ_g MDE ≈ 0.014 at one seed, less at 2. Per-twin calls from ΔT need stable ≥ 0.05, typical ≥ 0.10, hard ≥ 0.30; from Δ_g, ≈ 0.045 on any twin. Before launch, the exact design runs through `scratchpad/noise/sim.py`.

| Item | Boxes at once | Box-h [E] | $ [E] | Basis |
|---|---|---|---|---|
| Tier A + CPU box | 1 CPU | 8–12 | 1–2 | $0.12–0.19/h |
| Phase 1 perception (+1b) | 3 | 8–10 | 11–15 | Design 3 E2 estimate |
| Phase 2, 6 cells × 25 blocks | 8 (10 if wave 1 shows no HF 429) | 100–138 | 130–200 | orcB: 3 waves 4.0–5.5 h, $5.2–8.0 [E, JOBS.txt] |
| Phase 2, 4th wave c7/c8 (if H_t passes) | same boxes | 28–35 | 40–50 | +1.1–1.4 h per block |
| Phase 3 standard learner | 6 (3 sequential trainings each) | 40–46 | 55–68 | c01: 2.0–2.1 h, $3.0–3.3 per training [M] |
| **Core** (Tier A + Phases 1 and 2 with 6 cells) / **Full** (+ c7/c8 + Phase 3) | | ≈ 115–160 / 185–230 | **142–217 / 237–335**; +20 % contingency → **≈ $215 / ≈ $345** | |

**Run order (UTC).**
- 30 Oct 14:30–20:00: commit this file; build list (§7); Tier A on `refine/in`; mocks. ~20:00: batch 1, Phase 1 (≈ $15, go-ahead). ~00:00: bundles arrive; Tier A re-run; H_t gate.
- 31 Oct ~02:00: batch 2 (go-ahead). Wave 1 = seed 42 on all 10 twins; wave 2 = seed 43; wave 3 = seed 44 on the hard twins plus Phase 3. Launches are staggered by 10 min.
- Primary reading once all 20 two-seed blocks are in (≈ 31 Oct 18:00); final reading with the third seeds and Phase 3 (≈ 1 Nov 06:00). Both are reported.
- Boxes push once, self-destroy, and run the stall watchdog. A job that is making progress is never cut.

## 4. Pre-registered readings → eval pipeline

**Analysis unit:** the seed mean. SE² = max(observed seed var, σ_s,class²)/s + σ_d²/(s·k), with df 2(s−1) [Facts 3 §5].
- Pooled estimate: the equal-weight mean over the 10 twins, paired t plus sign-flip permutation. Holm correction across the primary rollout tests (φ_T, φ_K, φ_G, plus L6 if it runs).
- Every ΔT is reported as ΔS + Δg, with the mean, sd, min, failure draws, weak seeds and cost. Checkpoints are selected by S, as on eval; every curve checkpoint is also re-scored vs mocap (the O-arm selection advantage).

| Verdict | Rollout rule | Reference-level rule (CPU, deterministic, 20 eps) |
|---|---|---|
| Leaks | Δ ≥ +0.03, one-sided 95 % lower bound > 0 after Holm, permutation agrees. L2/L3 also need Δ_g ≥ 0.02 with a CI excluding 0 | mean ΔR ≥ 0.01 and ≥ 12/20 episodes the same sign; tracking arms also > 2× the P_o-repeat noise |
| No leak | \|Δ\| ≤ 0.02 and 90 % CI within ±0.04 | \|ΔR\| < 0.005 |
| Truth worse | Δ ≤ −0.03, upper bound < 0: a construction defect (frames, carves, scan collision). Fix it before attributing | same sign rule, negative |
| Inconclusive | anything else. Only pre-set extension: seeds 45–46 on the hard twins for that contrast's two cells, if \|Δ\| ≥ 0.03 | – |

**Copy ceiling per twin:** T\*(c6) ≥ 0.90 means copyable; ≤ 0.75 on ≥ 2 of 3 seeds means a robot or learner limit, so no reference spend for that eval type.

**Acting:** L_LB ≥ 0.005 is worth eval work; ≥ 0.010 is top priority; < 0.002 with an upper bound < 0.004 drops the stage. Fixes ≤ 0.003 LB ride along with retrains triggered elsewhere and never trigger one alone. A swap banks only if its multi-draw mean is ≥ the packed draw.

| Result | Eval-side change (each needs its own public gate and the owner's go-ahead) |
|---|---|
| L1 ≥ 0.03 AUC on an object in ≥ 2 eps | registration-safe submitted mesh in lib's body frame, swapped without retraining, only with 0/50 perturbation flips (pitcher precedent −0.0045 on Kaggle [M]) |
| L2 leaks (AOI c2−c1) | mesh session: GT-free templates for the objects carrying φ_T, then re-track and retrain the affected evals. **Spoon:** R(P_gf) ≤ R(P_o) − 0.05 on the thin proxies → rebuild the spoon mesh and re-track the 10 spoon evals (largest residual, ≈ 0.06–0.08 LB [E]). No leak → stop template work |
| L3 leaks | the phase split picks the fix: frame-0 init (multi-hypothesis), held span (pose = wrist × grasp), untouched rest (static freeze; GT version +0.069 on ep11 [M]), occlusion (cams b/c) |
| L4: a stage costs ≥ 0.02 on O in ≥ 3 eps | GT-free mkref fix gated on P (refine gate). The snap on perfect poses already costs 0.031 on ep11/31 [M] |
| L5 AOI ≥ 0.03 | collision copies / carves at eval (mesh + physics sessions). LOO > 0 but AOI ≈ 0 → fix the reference first. Negative → keep our meshes in sim |
| L6 AOI ≥ 0.03 | GT-free re-timing from perceived object motion in grasp lock, tested on public P arms. Otherwise close hands (bound ≤ 0.017 LB [E]) |
| L7 ≤ 0.75 (ep11, ep24 likely) | learner/embodiment spend for that task type; park eval 10 if c6 < 0.75 |
| Phase 3 sign ≠ grasp-lock sign on a twin | the learner, not the reference, decides eval 1/25/30 work |
| Explained total vs 0.185 | Σ L_LB + ceiling loss. A gap > 0.03 means the twin map or the spoon proxy is wrong; it is reported, not forced closed |

## 5. Already measured and reused vs new

| Reused [M] | Value | Source |
|---|---|---|
| P tracks and hands, 20 eps; R lib/scan | 0.892 / 0.908 | `docs/research/work/refine/results/baseline_summary.json` (inputs 1972dcb) |
| O raw / after snap (ep11/13/31) | 1.000; 0.969 / 1.000 / 0.969 | `oracle-twins-20261030/PREREG.md` §2.1–2.2 |
| S2 timing | +0.0061, 17/20 (adopted) | `refine/RESULTS.md`, `results/gates.json` |
| Scan-template tracker (20 Oct code) | 0.966–1.000 on 9/10 | `docs/analysis/robustness-review-20261026/refcheck/chain/README.md` §4. Code-date confound, so Phase 1 re-measures it |
| T ≈ 1.025·S·R at S ≥ 0.8; transfer 0.74 | RMSE 0.020 | `refcheck/mapping/README.md` (2bb20e3) |
| Noise classes, power | σ_s/σ_d per class | `scratchpad/noise/*.json` |
| H5 per-eval draws | weights, classes | `docs/analysis/h5-20261029/h5_summary.json` |
| physS0/S1 (ep2/12/18/24) | ep2 S0 0.944 vs ours 0.31–0.45 (confounded) | store `runs/20261030-physS{0,1}-6a814df/job.log`. Off-ladder: lib-frame references in a scan sim |
| Hand proxies | arrival 9 frames early, release 23 late | `origin/claude/keen-heisenberg-engcwz:docs/analysis/roman-meeting-20261030.md` |
| Human-hand pure copy | falsified | `origin/claude/determined-wright-3joens:docs/research/physics-2026-10-30/README.md` |
| orcB (running, 38234d1) | P vs O on ep11/13/31, seed 42 | read under its own PREREG. A pilot and drift check, not pooled: it uses on-box perception, not the frozen bundle |

New: X\*_geom/X\*_trk and the three-column scoring; Tier A A1–A7; Phase-1 P_s, P_gf and P_o repeat; cells c2, c4–c8 everywhere, and c1/c3 on 7 new twins; Phase 3; the H_t code.

## 6. Split with the other sessions (messages to send after this file is committed)
- **Physics / Embodiment (determined-wright):** "Leak plan committed at `docs/research/work/leak-decomp-20261030/PLAN.md`. Please: (1) freeze the scanlib recipe (`physics_arms.sh` lines 17–22) for our c4–c6 and review those job strings; (2) review or co-run the A7 settle probe; (3) optional, on your ledger: S1 plausible-mass arms at c6 on these 10 twins, seed 42, labelled 'plausible, not true'; (4) record the physS0/S1 verdict (ep2 S1 − S0 = −0.208 reads 'harm' by your rule); (5) run no new scan or O arms on ep2/11/12/13/18/21/24/27/31/39, to avoid duplicates."
- **Roman-meeting analysis (keen-heisenberg):** "Your 'everything true' CPU replay becomes a feasibility probe of our c6 references on the 10 twins: does the zero-action plan keep objects on the mocap path, and do the scans settle at their mocap frame-0 poses? It is descriptive only (zero action mis-ranks arms in 15/64 cases; CPU and GPU diverge [M]). A settle failure invalidates c6 on that twin."
- **Mesh (bold-albattani):** "Please: (1) X\*_geom fits, or a review of ours; (2) host-perturbation flip rates for library_v3, plus 200 seeds for the spoon; (3) blind sweeper and dust-pan meshes built the spoon way (no scan, no library_v3 lineage) by 31 Oct 06:00 for P_gf; (4) registration-safe candidates, only if L1 leaks."
- **Policy review (magical-mccarthy):** "Please check, read-only, that each twin's ENV/GL_ARGS matches its eval's packed recipe, and that Phase 3 matches std30/c01/c25s42."
- **Out of scope here:** a GT-free gross-failure screen of our eval references (Design 3 A0). It touches eval outputs, so it gets its own plan.

## 7. Build list, CPU tests before any GPU, risks

**Build:**
- B1 `tools/xstar_fit.py`: X\*_geom (multi-start ICP, spin-aware) and X\*_trk.
- B2 `pipeline/frame_xform.py`, plus `oracle_poses.py --xform`: lib ↔ scan for `poses.npz` and `poses_world_vo.npz`.
- B3 `tools/leak_tierA.py`: A1–A7 → json.
- B4 `ops/jobs/perc_leak.sh` (from `perc_ab.sh`): depth once, P_o / P_s / repeat / P_gf, one bundle per episode.
- B5 `ops/jobs/leak_cells.sh` (from `oracle_twins.sh`): CELLS c1–c8, bundle input, scanlib for G = scan, G0 per cell, run id must contain `-orc`, one push. Phase-2 setup skips videos and perception weights to reduce HF load.
- B6 `tools/hold_timing_oracle.py` (H_t) [H].
- B7 `tools/leak_read.py`: SE rule, Holm, permutation, Shapley/AOI/LOO, Δg/ΔS, LB map. It refuses arms whose config hashes differ outside the declared fields.
- B8 extend `tools/no_oracle.py` to refuse scanlib assets and `perc2scan`, `perc2gf` and `hT` folders.

**CPU tests, all before any GPU:**
- (a) Mocap through the kit path scores 1.000; lib → scan → lib round trip < 1e-6. (b) Frame invariance: T\* computed two ways agrees within 0.002; cup spin is checked.
- (c) H_t gate: median onset/release offset ≤ 1 frame, hold gap no worse than +0.2 cm, no new penetration > 1 cm. If it fails, run 6-cell blocks and record that.
- (d) Every job string mocked with a stub trainer and evaluator, as for orcB. (e) Arm-diff audit: within a twin only the declared stage differs; hands md5-identical; GL_ARGS, seeds and steps identical.
- (f) Guard tests on every new folder and id. (g) `leak_read.py` on synthetic data with known effects, plus the Monte Carlo of this exact design. (h) A7 settle gates.

**Risks and mitigations:**
1. **Frames.** X_kit can differ from the physical X\* (pitcher, sweeper 3°); cups spin up to 145° [M]. Cells are always built with X\*_geom, and X_kit is used only for the lib score.
2. **Non-determinism.** Draw failures 8–14 %; the same seed does not reproduce; boxes differ [M]. Seed-mean SE, blocks, a per-box zero-action fingerprint, and no stopping on interim data.
3. **Recipe drift.** One commit L0 for all of Phase 2. orcB and physS0/S1 are separate strata. Config hashes are checked.
4. **ev10 pieces were fitted to perceived geometry.** They may hurt c3 (a negative interaction booked to K). ep11 is reported per twin.
5. **Scan collision ≠ true physics.** A7 gates it, and c4–c6 are labelled "scan geometry, 0.3 kg".
6. **HF 429.** One bundle pull and one push per box, ≤ 8–10 boxes, staggered starts, no listings.
7. **Calendar.** If waves slip, the primary reading uses whatever two-seed blocks have finished at 1 Nov 06:00, and missing blocks are listed. Jobs are not cut.
8. **Spoon and host scan.** These are never [M]. Public scans stand in for the host's.
9. **Integrity.** Every cell, c1 included, runs under `-orc` ids, so nothing from this study can enter a pack. Public episodes only, no eval data, no Kaggle, nothing tuned on eval. A registration correction learned from mocap is never a default.
