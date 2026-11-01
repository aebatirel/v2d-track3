# GRASP-mode solver on public ep13 (eval 14's twin): build, checks, pre-registered test (1 Nov 2026, CPU, $0)

Branch `claude/grasp-ep13-20261101` (off determined-wright 5bab5c6). Pre-registration: `PREREG.md` (frozen at d8544cf
before any ep13 solve). Labels: [M] measured, [E] estimate, [H] hypothesis, [I] inference, [L] literature.
No ground truth was read by any solver or reference build (the oracle reference O is a stored public diagnostic input).
Nothing rented, nothing sent to Kaggle.

## 1. What was built
- `tools/physics_solve/grasp_window.py`: a numpy re-write of GRASP's window optimiser (Liu, Wang, Bao, Yang, Harvard
  2026; github.com/ComputationalRobotics/GRASP_code @ 992c737, MIT) from GRASP's own optimiser files
  (`grasp/optim/{surrogate,sampler,prior_ar1}.py`, `grasp/mpc/grasp_mpc.py`), with the MIT notice:
  - AR(1) prior over control knots centred on the previous window's plan (warm start), widening ×4 across the window;
  - tempered SMC with an adaptive ESS schedule and systematic resampling;
  - a locally weighted ridge quadratic fitted, at every stage, to the archive of every rollout evaluated in the window
    (rejected proposals included), in a rank-2 temporal DCT basis;
  - Langevin (MALA) proposals along that model's gradient, preconditioned by the prior covariance (MALA in whitened
    coordinates); **Metropolis–Hastings acceptance on the true simulator cost**, so the model only steers proposals;
  - adaptive step size; half of each window's initial particles carried from the previous window's final population.
  - No SPIDER-derived file was used: GRASP's THIRD_PARTY_NOTICES.md lists them (`grasp/sim/*`, `grasp/config.py`,
    `grasp/utils/*`, most of `grasp/pipeline/*`, CC BY-NC 4.0).
- `tools/physics_solve/solve.py --method grasp`: the same FlashCHORD solver (condim 3, finger kp 1.7, our
  `sharpa_hands_mid` embodiment, VOC 0) with GRASP's window optimiser instead of the annealed sampler. Same cost (kit
  ADD + regulariser, mean over robust copies), decision variables, hand gate, commit, rollbacks and rollout budget. The
  robust copies' target noise is fixed per window, so the cost is deterministic and the MH test exact.
  New options: `--method`, `--g_*` (see `--help`); `--g_sig_abs` sets GRASP's own prior widths.
- Scripts in `scripts/`: `prep_inputs.py` (local reference trees), `dev_ep31.sh` (development), `run_ep13.sh` (one arm:
  solve → official replay → exactness → jitter check), `jitter_inputs.sh`, `run_all.sh`, `gate.py`.

## 2. Checks [M]
| check | result |
|---|---|
| unit tests `tools/physics_solve/tests/grasp/test_grasp_window.py` (AR(1) inverse and adjoint, DCT orthonormal, surrogate exact on a quadratic, toy window, carry rows, MALA/MH samples the exact Gaussian posterior) | all PASS |
| default path (`--method anneal`) of the new solve.py vs the original (md5 fa511432), ep31 f0–44, same seed | identical output parquet (md5 bfecffd6), offsets and truth trajectory |
| GRASP mode: fresh load of the written parquet vs the patched truth env | target buffers bit-identical |
| GRASP mode: official zero-action replay (`tools/trace_rollout.py zero`) of its output vs its committed trajectory (ep31 smoke, 45 frames; dry run, 29 frames) | **bit-identical** (max \|Δq\| 0.0), as for our solver |
| CPU replay determinism (ep13 P, two replays) | bit-identical |

## 3. Finding: the ep13 twin references have no hand-over [M]
- The oracle-twins box locked both ep13 references with `--single_hand 1`. `pipeline/grasp_lock.py` then keeps one
  carrier per object, the hand with the most hold frames (right, f46–104), drops the other hand's holds and parks it.
- In `refs/glockt/ep13` (P) and `refs/oracle_glockt/ep13` (O) the left wrist stays at z = 57.0 cm for all 190 frames;
  its frames never come within 15.7 cm of the cup's bounding sphere. Before the lock (`refs/sf/ep13`) the left hand is
  on the cup over f20–60 and the right hand from ~f40.
- The cup's reference rises 9–12 cm by f30–40, before the right hand arrives (1.6 cm at f40) and holds (f46). The
  robot reference asks for a lift with no hand near the cup.
- So the oracle twin's O ≈ P at the floor shows ep13 is not perception-limited, but both arms shared this
  construction: "control-limited" may be "construction-limited" [I].
- Eval 14's packed reference (`20261025-evb1420-ee7ba8e`, our perception only) was also locked single-hand, but there
  the lock chose the LEFT hand, its first picker (f18–118, merged from 3 holds), and parked the right. The twins' ep13
  references are therefore not built like eval 14's.
- Hence test B in the pre-registration: the same `ref_sf` inputs re-locked without `--single_hand` (two-hand holds:
  P2 left f19–61 + right f46–104; O2 left f17–61 + right f46–99), then wrist ILC. Nominal zero-action sim_vs_ref:
  P2 0.5268, O2 0.6474 (floors 0.5561 / 0.5727; the twins' P / O give 0.5406 / 0.5724 on CPU).

## 4. Development on ep31 (before freezing; dev metric = the solver's own J_best / J_warm)
See `PREREG.md` §6. Selected G5: GRASP's own prior widths (σ 0.0044 m / rad, fingers ×10), ESS 0.5, 2 moves per stage:
0.958 (5/8 windows improved) vs our annealed sampler's 0.985 (2/8). With our wider noise, GRASP's tempering either stayed
near the prior (ESS 0.9, 0/8 improved) or reached λ = 1 and rejected every move (ESS 0.5).

## 5. ep13 results (pre-registered; jittered = mean of 16 copies with 0.5 mm / 0.005 rad target noise) [M]
Files: `results/` (each arm's `jitter.json`, `run.log`, solve JSON; `gate_*.json`). Every solver output's official
zero-action replay was bit-identical to its committed trajectory over all 190 frames.

| input | input jittered | anneal (ours) nominal / jittered | GRASP nominal / jittered | d = GRASP − anneal (paired 95 % CI; wins of 16) |
|---|---|---|---|---|
| P2 two-hand, perceived | 0.3435 ± 0.162 | 0.5270 / 0.3935 ± 0.146 | 0.6266 / 0.4176 ± 0.166 | **+0.024** (−0.071, +0.115; 9) |
| O2 two-hand, oracle | 0.6041 ± 0.093 | 0.6957 / **0.6507** ± 0.092 | 0.6929 / 0.6241 ± 0.107 | −0.027 (−0.101, +0.050; 5) |
| P twins', perceived | 0.5542 ± 0.004 | 0.5406 / 0.5542 ± 0.004 | 0.5406 / 0.5542 ± 0.004 | **0.000** (both outputs = the input: 0 windows improved) |
| O twins', oracle | 0.5707 ± 0.003 | PENDING_OA | PENDING_OG | PENDING_DA |

Floors: 0.5561 (P, P2), 0.5727 (O, O2).

**Verdicts (pre-registered rule: d_b ≥ +0.05 on the perceived input, neither d below −0.05):**
- **Test B (two-hand): FAIL** (d_b +0.024; no harm flag).
- **Test A (the owner's gate, twins' references): FAIL** (d_b 0.000). PENDING_A_NOTE
- So [H-grasp] is falsified at this CPU budget on ep13, and **no GPU step is proposed**.

Report-only readings:
- Nominal vs jittered: GRASP's nominal gain on P2 (+0.100) mostly vanishes under 0.5 mm noise (+0.024), the pattern our
  solver showed on CPU on 30 Oct. Single nominal trajectories mislead (mid-solve at f52 the GRASP run had the cup 4.3 cm
  off and the anneal run 18.7 cm off; their jittered means differ by 0.024).
- Two-hand vs single-hand (the construction): with the oracle motion the two-hand lock lifts the input from the floor
  (0.571 → 0.604) and both solvers carry the cup through the hand-over (lost at ~f60–82 instead of f27–50, within 3 cm on
  35 % of frames vs 22 %); the remaining failure is at the placement (~f100). With our perceived motion every arm is
  below the floor and "lost" at f15–17, because of the next item.
- **Our perceived cup track spins about the cup's symmetry axis while the cup rests** (12° by f8, 54° by f18, 130° by
  f26, 140° by f30; the rotation axis is the mesh's symmetry axis, |cos| 1.00; the mocap cup turns 0–9° until f24). The
  metric is ADD, not ADD-S, so this unobservable spin costs score in sim_vs_ref and in the leaderboard AUC vs mocap,
  and no robot can (or should) reproduce it. [H-spin]: canonicalising symmetry-axis spin of symmetric objects in our
  references raises both; falsifiable on public twins by the registered AUC of the canonicalised reference vs mocap.

## 6. Cost
$0: everything ran on this container's 4 CPUs (setup ~20 min; dev sweep ~45 min; eight ep13 arms ~8 h). No GPU was
rented.

## 7. For the follow-up work (owner's "perfect following" lane)
**Where things are.**
- Code (this branch): `tools/physics_solve/solve.py` (`--method grasp`, default anneal unchanged),
  `tools/physics_solve/grasp_window.py`, tests in `tools/physics_solve/tests/grasp/`; scripts in `scripts/`.
- Two-hand references: built on CPU, not stored (regenerable in 3.5 min each). Recipe: `tools/cpu_glock_zero.sh
  <ref_sf.parquet> <out_dir> "--mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"`
  on `runs/20261030-orcB-38234d1/refs/{sf,oracle_sf}/ep13/.../ref_sf.parquet` (asset paths rewritten by
  `scripts/prep_inputs.py`). On a GPU box the same thing is `ops/jobs/glock_public.sh` with that GL_ARGS (the box default
  minus `--single_hand 1`); no new code is needed. Local md5: P2 7ad0e431, O2 501e928e.
- The lock's hand choice: `pipeline/grasp_lock.py` `--single_hand 1` keeps the hand with the most hold frames (ep13:
  right, f46–104, which starts after the cup has risen); eval 14's packed lock happened to keep its first picker (left,
  f18–118).

**A fair single- vs two-hand RL test on public ep13 [E]** (not run; GPU, the owner's go):
- One box, one commit, the frozen grasp-lock recipe (`glock_public.sh`, 70M steps, `SF=1`, the same REPLAN and EVOLVE
  settings for every arm), the same perceived base reference (`perc2mck` ep13), assets and seeds; arms differ only in
  GL_ARGS:
  1. single-hand as packed (`--single_hand 1`, right carries from f46);
  2. single-hand first picker (left carries all, eval 14's construction; needs a small `grasp_lock.py` option, e.g.
     choose the hand with the earliest hold);
  3. two-hand (no `--single_hand`).
- At least 2 seeds per arm (ep2-type seed chaos), NREP 10 official evaluations, the checkpoint chosen by sim_vs_ref
  (GT-free) and scored by registered AUC vs mocap (public evaluation only); a pre-registered rule such as arm − arm 1
  ≥ +0.05 mean over seeds with no seed below −0.05.
- Do the symmetry-spin canonicalisation first or as a fourth factor: on our perceived ep13 track it dominates the early
  error, so without it all arms may stay below the floor (as every perceived arm here did).
- Cost [E]: 6 trainings (3 arms × 2 seeds) at 2 concurrent per box wave ≈ 3 waves × 1.1–1.4 h + setup ≈ 4–5 h ≈
  $5.5–7.5 at $1.3–1.5/h.

**What the GRASP optimiser is still good for.** Little, right now. At equal CPU budget it ties our annealed solver (test
B: +0.024 / −0.027, both within noise); its gains appear only on nominal replays, which do not survive noise. Its
design needs far larger archives (2,000 particles, ≤ 64 stages × 5 moves per window in the paper; here 32 × 8 batches).
Keep the code (default off); revisit only at GPU scale (1,024–4,096 worlds, as G2 for our solver) and only behind a new
pre-registered gate. The bit-identical replay check and the fixed-noise robust cost carry over to any solver.

## 8. Making our perceived motion physically possible (proposal, 1 Nov ~19:55 UTC; nothing run yet)
**The gap, measured on ep13 [M].** Same two-hand construction, same solver budget; only the object track differs:
jittered zero-action sim_vs_ref of the input 0.344 (our perceived track) vs 0.604 (mocap track); after either solver
0.39–0.42 vs 0.62–0.65. The reference itself is close to mocap by AUC (0.940 vs 0.964), so the loss is not "where" the
cup is but motions a robot cannot produce. Earlier results point the same way: eval 10's twin ep11 O − P +0.345 in RL
(perception-limited, "our reference nests the beige cup deeper than the shapes allow").

**What is already falsified (do not repeat as is):** generic smoothing (zero-lag RTS on tracks, kit gate −0.00011),
projecting rest poses onto the support (ΔAUC −0.0107, 17 / 20 worse; overlaps were mostly mesh shape), re-tracking.

**Four GT-free repairs, each with a public falsification test** ([H]; order = expected value per cost):
1. **Symmetry-axis spin canonicalisation.** For rotationally symmetric objects (cups; mesh PCA with two near-equal
   axes, or a rotational self-registration check), split each frame's rotation into swing (tilt, observable) and twist
   (about the symmetry axis, unobservable). Keep the swing; hold the twist constant while the object rests and let it
   follow the holding hand's twist while held. ep13: our track twists 140° by f30 with no cause [M]; ADD (not ADD-S)
   charges it in both sim_vs_ref and the leaderboard AUC. Test ($0, CPU): blue / beige cup twins (ep11, 12, 13, 21, 22):
   reference AUC vs mocap must not drop (registered, as score_registered), zero-action jittered sim_vs_ref should rise.
   Caveat: a cup with a visible handle has an observable twist; apply only where the twist is unobservable.
2. **No mover, no motion.** An object may move only while an assigned hand is in contact (or it is supported by a moving
   object, or falling). Outside those windows hold the pose; inside a hold, express the object in the holding hand's frame,
   keep that relative pose near-constant (low-pass in the hand frame) and recompose. This removes perception jitter the
   hand cannot produce while keeping the hand-driven motion. Different from the falsified rest projection (that moved
   rest heights onto the support; this freezes motion in time and ties held motion to the hand). Test: as in 1, on all
   20 public episodes.
3. **Hand assignment that matches the object's motion.** The carrier must be the hand in contact when the object starts
   moving; hand-overs need an overlap window. ep13's `--single_hand 1` picked the hand with the most hold frames (right,
   f46), after the cup had risen at ~f20 [M]; eval 14's packed lock kept its first picker (left) but then carries the cup
   one-handed through the human's two-hand hand-over (keen-heisenberg's videos: all three replays fail at f42–46).
   Options: a first-picker rule, or two-hand holds only inside hand-over windows. Test: the single- vs two-hand RL test in §7.
4. **Feasibility preflight on every reference.** Replay each reference with the object welded to its assigned hand
   (FlashCHORD's virtual object controller at full assist) and flag frames where the object would pass through the table
   / rack / another object, or moves with no hand in reach; repair with the smallest pose change. Our solver's zero-action
   jitter check is the score: a physically possible reference keeps the cup within 3 cm under 0.5 mm noise.

Suggested first step ($0, CPU, this container, after the ep13 arms finish ~21:00 UTC): repair 1 on ep13's P2 and the
zero-action jitter check (P2 0.344 → ?), then the ref-vs-mocap AUC on the cup twins (needs the public dataset download).
