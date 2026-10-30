# Status (2026-10-21, evening; times TRT = UTC+3)

## 2026-10-30 ~09:45 UTC: owner decision — object physics may be set "where allowed"; MANO hand back on the table
- **Owner:** keep the simulator's own world (solver, contact model) but set the objects' physical properties (mass,
  friction, ...) as far as allowed so the simulation follows the video. This replaces our own "do not change the world"
  line (note 26 §F) for object properties. Checked today: the FAQ (raw PDF) and the kit's Track 3 README contain **no
  rule on physics or object properties**; FAQ: "Other embodiments are welcome, including ...".
- What is ours to set: object mass / COM / inertia in our URDFs (`pipeline/make_assets.py`, today the 0.3 kg kit
  placeholder for every object with thin-shell inertia). Friction is one global `scene.contact_friction` (1.0, all
  shapes incl. hands and table); per-object friction would need code changes (off-limits for the pinned re-run).
  `object_free_joint_damping` acts as a brake no real object has: not used.
- Honesty constraints proposed (owner to confirm): one value set per object shared by every episode, physically
  plausible (volume × material density, solid inertia), never fitted to mocap or to eval results, declared in the
  report. Mass is not observable from video alone (forces are invisible).
- MANO licence (read today): non-commercial research use; no redistribution or derivative made available to third
  parties. Usable on our machines; the Apache-2.0 release would ship a builder script, not MANO-derived files.
- Next (not started, needs go-ahead): per-object plausible masses + solid inertia from our meshes; CPU zero-action
  replays on public episodes with the new URDFs; pre-registered rule before any GPU retrain.

## 2026-10-30 ~06:40 UTC: batch 2 generative probe done ($4.36, box destroyed; results [D])
Report: `docs/research/mesh-2026-10-26/results/gen-probe/README.md`. Code: `docs/research/mesh-2026-10-26/gen/`.
- Five generators were run on our crops and posed views; 104 one-shot scan scorings. Mean CD-O over 10 objects:
  - SAM 3D 0.501 and Pixal3D-MV 0.490 (each beats library_v3 on about half the objects);
  - Hunyuan3D-2.1 0.602, TRELLIS.2 0.594, TripoSG 0.984;
  - library_v3: 0.477.
- Oracle best-of-generated per object: 0.315; beats our best hand-built only on the pot and the blue cup.
- Pose side is worse (generated meshes ADD 10-29 mm vs library ~6 mm).
- The GT-free selector is too weak (Spearman 0.46).
- No submission change. SAM 3D access is approved. Its 12.4 GB of checkpoints sit in the HF store under the run
  folder and can be deleted.

Also read `docs/context-and-decisions.md` for the owner's goals, preferences and earlier answers.

## 2026-10-30 ~06:45 UTC: PACK 7 UPLOADED (owner-approved) — AUC 0.81460, our best, but 7th: the field moved
- Pack 7 = pack 6 + eval 33 from arm B. AUC 0.81460 (+0.0007), RPE 3.932, MPPE 2.921, SP-SR 0.85, MP-SR 0.65.
- AUC board: 0.940 / 0.931 (DDD) / 0.883 / 0.870 / 0.860 / 0.856 / **0.8146 us** / 0.773. 5th needs ≈ +0.046.
- Small variance swaps cannot close this; large levers only (reference side, spoon, eval 10).
- ~08:10: GT-free depth audit FALSIFIED (AUROC 0.600 < 0.65; fragile): depth cannot flag our typical 2–3 cm
  reference errors, so it does not justify reference/spoon spend. Running: eval-1 official confirmation (58370419),
  worst-5 videos (58363797).

## 2026-10-30 ~06:20 UTC: eval-1 carve passes on the training box; pack-7 candidate built (NOT uploaded); plan written
- **Eval 1 (placement carve, standard learner):** seed 43 0.931 ± 0.006 (10 draws, training box), seed 42 0.885 ± 0.050;
  rule mean ≥ 0.852, sd ≤ 0.239: pass. Needs an official-evaluator confirmation (N = 20, ≈ $1.6, rule pre-registered
  in the work log 06:20), because the training box showed 0/10 bad draws for policies the official evaluator fails
  5/22 times. Job prepared and verified on CPU first (workflow wf_02052244-fe2).
- **Leaderboard scoring (kit `AUC.py`):** the submitted trajectories are scored as they are, nothing is re-run. So
  pack 6's lucky draws are banked; swaps (eval 33, eval 1) add ≈ +0.0003 to +0.0007 [estimate]. Their larger value
  (≈ +0.007 [estimate]) appears only if the organisers re-run checkpoints at validation (unknown).
- **Pack-7 candidate** `results/submissions/20261030-track3g-candidate/` (pack 6 + eval 33 from arm B; sha 137c8687…;
  integrity and provenance verified). **Not uploaded; the owner decides.**
- **Plan:** `docs/research/work/next-steps-2026-10-30/PLAN.md` (owner decisions: ask organisers about re-runs; one
  upload, pack 8 or 7; insurance retrains only if re-runs count).
- Spend this session: $27.27 actual of $45. 0 boxes running.

## 2026-10-30 ~04:50 UTC: eval-33 candidate CONFIRMED (0.934 ± 0.008, 10 draws); eval-14 carve failed
- **Eval 33:** arm B's checkpoint passes the pre-registered rule (needs ≥ 0.884, sd ≤ 0.137) against the packed
  policy's H5 0.854 ± 0.137. Candidate for the next pack; **the owner decides any upload** (nothing sent).
- **Eval 14 carve:** both seeds fail (0.617 ± 0.236, 0.579 ± 0.099 vs bar 0.645). Packed eval-14 policy stays.
- **Running:** eval-1 carve retrain, 2 seeds (boxes 58340108/118), results ≈ 06:00–07:00 UTC; rule mean ≥ 0.852,
  sd ≤ 0.239.
- Spend this session: $21.28 actual + ≈ $11 planned of $45.

## 2026-10-30 ~03:30 UTC: recipe arms inconclusive; packed recipe stays. Carve retrain running; eval-33 confirmation
- **Recipe arms** (A control vs B CURR_SCALE 0.4 vs C ball kd 2, 5-eval means): no signal and no falsification for B or
  C by the pre-registered rule, so no second seed. Details: work log 30 Oct 03:25.
- **Eval-33 candidate** (B's checkpoint, 0.923 ± 0.013 on 5 draws): 10-draw confirmation box, rule fixed beforehand
  (mean ≥ 0.884, sd ≤ 0.137). A fresh retrain alone (A: 0.906 ± 0.058) also beats the packed policy's H5 mean 0.854.
- **Running:** carve retrain batch (evals 1 and 14, 2 seeds each, NREP 10; boxes 58340108/118/125/131, results
  ≈ 06:00–07:00 UTC). Rule: eval 1 mean ≥ 0.852 and sd ≤ 0.239; eval 14 mean ≥ 0.645 and sd ≤ 0.199.
- **Refine stage:** S2 (0.545-frame timing advance) adopted on public data (+0.006, 17/20); S1/S3 rejected, S4 neutral.
- Spend this session: $16.90 actual + $19 planned of $45. Nothing sent to Kaggle.

## 2026-10-29 ~23:15 UTC: H5 done. Pack 6 was lucky; true expected ≈ 0.78 on the leaderboard
- **10 fresh draws per packed checkpoint:** mean of means **0.8755** vs packed 0.9164. A re-run of today's policies
  ≈ 0.78 AUC on the leaderboard (estimate, transfer 0.74–0.78). Summary: `docs/analysis/h5-20261029/h5_summary.json`.
- **High-variance episodes:** 1, 14, 25, 30, 33. Re-seed/retrain candidates by the pre-registered rule: **1, 14, 30,
  33**. Three of them (1, 14, 30) have reference collision causes, so placement collision copies come next.
- **Running:** recipe arms A/B/C (control, CURR_SCALE 0.4, ball kd 2) on ep12 / eval 32 / eval 33; refine-stage
  build (CPU). Spend so far: $2.45 actual + $13.50 planned of this session's $45.

## 2026-10-29 ~21:30 UTC: owner topped up $100 (credit $103.51); this session owns GPU launches overnight
- **Owner's instructions:**
  - full autonomy overnight to improve the algorithm and pipeline;
  - **nothing to Kaggle without approval**;
  - check changes on public episodes now and then.
- **Session:** `claude/focused-pascal-2nz9s1`, now merged with `main-bsky37` (2bb20e3).
  - Carry-control research is in note 26 (`docs/research/notes/26-carry-control-force.md`).
  - The reference audit tool is `pipeline/audit_ref.py`.
- **Coordination:**
  - this session is the only GPU launcher tonight; the main-branch session (blocked on the top-up) stays paused;
  - the mesh session (`bold-albattani`) is CPU-only;
  - spend ledger: `ledger/spend.jsonl` in the HF store.
- **Budget split** (owner, ~21:45 UTC: "give mesh session vast credits"):
  - this session ≤ $45;
  - mesh session (bold-albattani, session_01W8Softjo2xx7o6ofSiheuQ) ≤ $25, informed by message with the ledger
    protocol;
  - reserve ≥ $30 for the owner's review.
- **Plan, in priority order:**
  1. H5: 10 more evaluations of all 20 packed checkpoints.
  2. Fixes for the verified reference defects, validated on public twins against GT (CPU), then retraining.
  3. Recipe tests: curriculum end stage (`CURR_SCALE`) and ball-wrist damping, with a same-code control.
  4. Spoon proxy check.
  5. Eval-10 task-side change, tested on its public twin (ep11) first.
- Choice rules are pre-registered in the work log before each batch.

## 2026-10-27 ~06:15 UTC: eval-10 zero-start test falsified; waiting for the owner's top-up
- `20261027-e10Z-aa7b5f8`: 0.4459 (5-eval) < gl10A2 0.4539, so eval 10 is unchanged; box destroyed. Credit $3.52,
  0 boxes.
- Best leaderboard: 0.81391 (pack 6), 5th; DDD 0.827.
- Eval 10 is parked: RL avoids the stack from ≈ 1M steps whatever the start (work log 27 Oct). A retry needs a
  task-side change (relaxed termination in the nest phase, or more clearance).
- After the top-up (owner): placement carves for 14 / 28 / 30 / 1; 10 evaluations of all 20 packed checkpoints
  (robustness review H5, ≈ $2); spoon proxy measurement (CPU).

## 2026-10-27: eval-10 zero-start test running (last of the credit); top-up pending
- `20261027-e10Z-aa7b5f8`: residual actor head with a zero-initialised mean (`zero_dense`), exploration 0.05,
  frozen-variant plan, carved cups. ≈ $1.5. Rule pre-registered (work log, 27 Oct).
- 05:20 UTC: its first training failed at start (STEPS not divisible by 4096; fixed) and its push failed (store.sh bug
  from 26 Oct; fixed). Training restarted on the same box with the finished plan (REUSE_REF=1); results ≈ 06:00 UTC.
- Best leaderboard: 0.81391 (pack 6), 5th; DDD 0.827. Credit ≈ $6.8 before this box.

## 2026-10-26 ~17:15 UTC: SIXTH SUBMISSION — Track 3 AUC 0.81391 (our best); DDD 0.827 still 4th
- Pack 6 (`results/submissions/20261026-track3f/`): pack 5's rollouts (eval 10 gl10A2, eval 32 s46) with eval 20's
  pitcher mesh reverted.
- Today's failed ideas, all recorded:
  - the eval-10 stack (rim collision, learned avoidance from the first checkpoint);
  - the early-checkpoint test;
  - the interruptible seed race;
  - the pitcher mesh swap (−0.0045).
- Credit ≈ $12; 0 boxes. Open levers: eval-10 training start (zero-residual init / lower exploration), placement
  carves, spoon proxy measurement (robustness review).

## 2026-10-26 ~15:35 UTC: push to beat DDD (0.827): three boxes running
- **Pack 5** (`20261026-pack5-526918b`):
  - eval 32 = s46, eval 10 = gl10A2;
  - eval 20's submitted pitcher → our lathe reconstruction (`meshes/library_v3p`; twin ep21 registered 0.776 → 0.874
    with the same rollouts);
  - then upload.
- **Eval-10 early-checkpoint test** B′ / C′ (`20261026-e10B/e10C-6762f80`), results ≈ 16:30 UTC; a pack 6 if one
  wins.
- Mesh-swap tests: only the pitcher gains (`docs/analysis/meshswap-20261026/`).

## Mesh session status entries (branch `claude/bold-albattani-6qmxsv`, merged into main 2026-10-30)

## 2026-10-27 ~13:30 UTC: building the A+B mesh engine (CPU, $0); research verdict: generic-only route failed
- **Owner wants:** A (generic automatic engine) + B (agent-authored part programs per object), with minimal CD-O
  against the public scans. Selection stays GT-free, and oracle numbers are reported separately.
- **Research workflow `wf_c5cfe08d-5e2` (work log 13:20):** both generic-only probes were refuted (pot structure, dust
  pan), and the GT-free gate was blind to a missing wall.
- **Stage 1 running:** `wf_31952e44-35c` builds `docs/research/mesh-2026-10-26/autokit/`:
  - loader;
  - per-frame refinement;
  - thin shell;
  - part DSL;
  - gates v2;
  - integration, then audits.

  Stage 2 follows: authoring, GT-free selection, one pre-registered scan round.
- **Correction:** under the owner's 22 Oct decision (eval meshes re-fused per eval episode), new eval meshes need eval
  depth (≈ $2–4 GPU, owner go-ahead). The 07:10 "no eval depth needed" holds only for a pack swap of public-built
  meshes.
- **Deadline:** the owner handles the leaderboard freeze (13:40); do not plan around it.

## 2026-10-27 ~07:10 UTC: kit-of-parts meshes done (CPU, $0, branch `claude/bold-albattani-6qmxsv`)
Report: `docs/research/mesh-2026-10-26/README.md` §9. Pre-registered rules and all results are in the work log.
- **Passing objects:** white pot, lid and dish rack now beat library_v3 on the public scans [D].

  | Object | CD-O (cm) | ADD (mm) | Flips |
  |---|---|---|---|
  | Pot | 0.437 → **0.342** | 6.7 → 3.05 | 0/8 |
  | Lid | 0.421 → **0.220** | 8.1 → 4.46 | 0/6 |
  | Rack | 0.555 → **0.456** | 6.0 → 5.37 | 0/7 |

- **Boards fail.**
  - Board 1 flips on 1 of 6 seeds.
  - Board 2's ep23 track looks like board 1.
- **Leak found and removed.** My brief gave the builders scan-measured thicknesses. A pre-registered clean-up re-ran
  the lid and rack over 1.5 / 2.5 / 4.0 mm. Both pass at every value. Fidelity, which uses no ground truth, also
  dropped the scan-informed upright cup holder.
- **Eval:** the meshes come from public episodes like library_v3 and share its frame, so they need no eval depth.
  Swapping pot, lid and rack ≈ CD-O 0.402 → 0.367 [E].
- **Owner decision:** swap only the packed mesh ($0, frames match), or also the simulator copy (GPU re-run of the
  affected eval episodes)?
- **Still pending (owner):**
  - eval depth run (≈ $2–4, for cup lathes on eval);
  - WeVisOne test (≈ $1–1.5);
  - generative probe (≈ $4–8, plus code permission).

## 2026-10-26 ~16:40 UTC: mesh accuracy research round (branch `claude/bold-albattani-6qmxsv`, CPU only, $0)
Report: `docs/research/mesh-2026-10-26/README.md`. Also there: ledger of all past mesh work, three literature
reviews, scripts and results.
- **Why it matters:** CD-O ours 0.402 cm against leaders 0.112–0.154. The same mesh registration sets the body frames
  of all five pose boards.
- **Measured [D]:**
  - Our stereo points along our own tracks lie a median 0.85–1.9 mm from the scans and cover 60–90 % of most objects
    (rack 28 %). The 4 mm binary-blur mesher discards that accuracy (walls 12–20 mm against real 2–4 mm).
  - The scans are thin double walls and **partial** (no deep inner cup wall). CD-O's RMS-radius scale fix punishes a
    wrong area distribution: blue-cup lathe 0.382 as scored vs 0.316 at true scale.
- **New method (GT-free), `lathe_obs.py`:** a thin-walled lathe fitted to observed points.
  - Blue cup 0.523 → **0.291** (ep21; ADD 10.0 → 4.1 mm, 0/7 flips). Ep22: 0.364. Merged: 0.396 (fusion hurts again).
  - `obs_fidelity.py` (GT-free) picks the right episode.
  - Pot not yet: 0.413–0.468 vs 0.437 (inflated handle).
  - Screened Poisson on raw points fails (≈ 1.0).
- **Generative models (SAM 3D, TRELLIS.2, Hunyuan3D) were never tried.** Crops are ready (`crops.py`).
  - The sandbox blocked running third-party model code here.
  - SAM 3D gives HF 403 (token lacks the gate).
- **Owner decisions needed:**
  - (1) permission to run third-party generative model code;
  - (2) request SAM 3D access and give the token gated read;
  - (3) GPU probe P1, ≈ $4–8 (ceiling $12), on a box separate from the eval-10 boxes;
  - (4) licence choice (Hunyuan excludes EU/UK/KR).
- Nothing in the submission pipeline was changed.
- **~18:30 UTC eval meshes:**
  - Page: https://claude.ai/artifact/TSEF4dCCSRdErBcfCPR2Ex (submitted eval meshes in 3-D, overlays on the eval
    videos, public comparisons).
  - New-method eval meshes need eval depth, which was never cached: `ops/jobs/eval_perc.sh`, ≈ $2–4, owner
    go-ahead. Single-frame (frame-0) lathes fail on public data (1.1–1.3 cm, flips), so they are not used.
  - **Found:** the submitted white-pot mesh (6 eval pairs) has an open base, a ≈ 4–5 cm hole; the eval-10 beige cup
    has an open base; the pitcher is see-through. Simulator impact not checked.

## 2026-10-26 ~15:25 UTC: eval-10 check done (CPU); one small GPU test proposed
- Cause: every learner learns to avoid the beige cup. The open-loop plan carries it, but the cup hits the blue cup's
  rim (6–7 cm misalignment in the simulation) and is flung after release.
- `docs/analysis/ev10-stack-20261026/README.md`. New tools, off by default: `grasp_lock.py --rest_below_cm`,
  `wrist_ilc.py --hold` (object-level ILC). Best CPU replay 0.632, not robust (0.42–0.54 under ±3–6 mm jitter).
- Zero action of the frozen-variant plan: 0.663 vs submitted 0.447. A zero-residual policy is not used: the kit asks
  for a trained policy (22 Oct rule).
- Proposed, not rented: eval 10 frozen variant with checkpoints every 1M steps for 20M (curve includes near-plan
  checkpoints), ≈ $2. Credit $17.29, 0 boxes.

## 2026-10-26 ~13:20 UTC: batch done; eval-10 grasp-lock idea falsified; eval 32 → s46 (small)
- Eval 10: grasp lock on the carved cups never lifts a cup (A 0.454, B 0.438; current 0.452). Rule winner A by 0.002.
- Eval 32: seeds 44–46 → s46 0.803 vs s42 0.779 (rule winner s46).
- Both winners wait for the next pack (together ≈ +0.001 AUC, estimate). Credit $17.29, 0 boxes.
- Robustness review running in session_012XqAPiLToh4uBKNWqzx3bV (`docs/analysis/robustness-review-20261026.md`).

## 2026-10-26 ~11:35 UTC: five boxes running (owner go-ahead), on demand
- Eval 10, grasp lock on the carved cups (SF=0, PIECES ev10): `20261026-gl10A2-5e0e100` (eval_both variant) and
  `20261026-gl10B2-5e0e100` (frozen variant).
- Eval 32, frozen recipe, seeds 44 / 45 / 46: `20261026-fr32s44b/45b/46b-5e0e100`.
- ≈ $10.5 together, results ≈ 12:50 UTC. Choice rules pre-registered (work log, 26 Oct). Then pack 5 and upload.
- Interruptible boxes were paused within ≈ 10 min, so the seed race on interruptible is not viable today.

## 2026-10-26 ~11:00 UTC: FOURTH SUBMISSION — Track 3 AUC 0.81056, 5th (DDD passed us at 0.82716)
- Pack 4 (`results/submissions/20261026-track3d/`):
  - carved collision copies with the standard learner: eval 10 (s43; s42's chosen checkpoint was pruned) and eval 25
    (s42);
  - eval 33 = frozen seed 43;
  - 3/5/15/16 restored to pack 2's seed-43 rollouts.
  - Our mean 0.912. Boards: SP-SR 0.85, MP-SR 0.65, RPE 4.03 cm, MPPE 2.94 cm.
- Gaps: 4th DDD 0.827 (+0.017), 3rd 0.865 (+0.054). 0 boxes running.
- Open owner decisions: seed race pilot (interruptible, ≈ $10–12, `docs/research/seed-race-20261026/`); next levers in
  `docs/analysis/episode-scoreboard-20261026.md`.

## 2026-10-26 ~09:45 UTC: eval 25 → carve s42; eval 32 keeps s42; eval 10 / eval 33 still running; seed race proposed
- Waiting: eval-10 carve s42 / s43 and eval-33 frozen s43 (≈ 10:30 UTC), then one pack and upload.
- Owner question on many seeds: analysis and proposal in `docs/research/seed-race-20261026/README.md` (level at 40 %
  predicts the final, R² 0.79; one cut at 40 %; ≈ $12–13 per episode for 8 seeds). Not rented; needs the owner's go.

## 2026-10-26 ~07:35 UTC: batch running (owner go-ahead); forensics delivered
- Running (credit $41.63 at launch):
  - eval-25 slot carve, standard learner s42 / s43 (57773973 / 57773975), results ≈ 09:30 UTC;
  - eval-10 hybrid cups, standard learner s42 / s43 (57781951 / 57781953), ≈ 10:15 UTC;
  - frozen recipe s43 for 32 + 33 (57781954), ≈ 09:30 UTC.
- Choice rules pre-registered (work log 26 Oct). Then one pack with
  KEEP_RESULTS="20261025-pack3-3758189 20261025-pack2-46b8389" (restores the seed-43 rollouts of 3/5/15/16) and upload.
- Forensics: `docs/analysis/forensics-20261026/README.md`; 20 videos sent to the owner (store
  `runs/20261026-subvid2-d9c3f7d/results/sub_videos/`).

## 2026-10-26 ~07:20 UTC: forensics running; packing bug found; eval-25 carve retrains running
- **Bug:** the third submission packed the FIRST pack's seed-42 rollouts for evals 3, 5, 15, 16 (not the rule-chosen
  seed-43 ones): pulled old submission folder + `cp -n`. ≈ −0.005 Track 3 (estimate). Fixed in pack_eval.sh (empty
  folder + sha check); the next pack restores them.
- Running: eval-25 carve retrains (57773973 s42, 57773975 s43; results ≈ 09:30 UTC); video box 57776867
  `20261026-subvid2-d9c3f7d` + follow-up for 3/5/15/16.
- Forensics report draft: `docs/analysis/forensics-20261026/README.md` (score split, per-episode causes, hull census,
  hidden losses, ranked plan). Eval-10 hybrid cup collision copy built and CPU-tested (`meshes/carve/ev10/`); GPU
  rerun not yet proposed to the owner.

## 2026-10-26: eval-25 slot carve passes both CPU tests; GPU rerun proposed (not rented)
- `pipeline/interaction_carve.py slot` cuts the boards' slots into the SIMULATOR collision copy only (the submitted mesh
  is unchanged), from our own identity-correct eval-25 reference: 21 + 11 convex pieces in `meshes/carve/ev25/`.
- CPU proxy (MuJoCo, board 2 dragged along the reference): board 2 at assembly 1.17 cm / 103.7° (today's shapes)
  → **0.06 cm / 0.5°** (cut). Collision overlap 11.8 → 0.17 cm³.
- FlashCHORD's own physics (`tools/carve_fc_test.py`, Newton/MuJoCo Warp CPU, dt 0.01, gravity, both boards
  spring-driven): board 2 relative to board 1 **7.47 cm / 47.9° → 0.12 cm / 0.4°**.
- Proposed: `ops/jobs/carve_rerun.sh` eval 25, seeds 42 + 43, ≈ $8–10, choice rule pre-registered in the work log
  (26 Oct). Credit $47.20. Next CPU work: eval 10's cup collision copy (lathe / cavity).

## 2026-10-25 ~23:10 TRT: THIRD SUBMISSION — Track 3 AUC 0.78893, 4th (was 0.58252, 9th)
- All six boards (agent upload; receipt `results/submissions/20261025-track3c/`):
  - AUC **0.789, 4th**: 1–3 are 0.932 / 0.884 / 0.865; 5th is SRL at 0.752.
  - SP-SR 0.80 (5th, tied), MP-SR 0.60 (4th), RPE 4.59 cm (4th), MPPE 3.29 cm (4th), CD-O 0.402 cm (11th).
- **What changed** (GT-free choices, rules fixed before results):
  - standard learner on evals 1, 19, 25, 28, 30;
  - references rebuilt with the track guard for 8, 14, 20, 32, 33;
  - the frozen recipe won 32 and 33;
  - eval 25's boards are named correctly;
  - eval 20 has the arc foot (twin 0.657 → 0.772);
  - eval 8 uses the v5 beige cup.
- **Left as before:**
  - eval 10 (stacked cups: njmax overflow, about 15× slower simulation; needs the blue cup's cavity carve);
  - 3, 5, 6, 15, 16, 35–38.
- **Cost:** ≈ $54.6 of the $100 top-up; credit $47.20; 0 boxes running.
- **Next candidates (not started):**
  - eval 10's collision cavity carve;
  - second seeds for the bimodal episodes (25, 33);
  - 3 and 16 with the standard learner;
  - the parked lathe meshes for CD-O (owner decision on the organiser question).

## 2026-10-25 ~18:10 TRT: owner topped up $100 → pre-registered eval rerun batch running (9 boxes, ≈ $13.4/h)
- **Running** (code ee7ba8e / 02de0c7; details and instance ids in the work log, 25 Oct ~14:55 UTC):
  - `eval_both`: 8 + 10 (library_v3x), 14 + 20, 32 + 33;
  - `std_learner`: 1 + 16, 19 + 28, 30;
  - ep21 arc-foot twin: SF_ARC=0 vs SF_ARC=1, which decides whether eval 20's rebuilt policy is used;
  - **eval 25 with the board identity repair** (`ops/jobs/eval_idfix.sh`). Its stored reference had the two boards
    swapped and one turned 180°. The GT-free knob rule is ported to `pipeline/identity_fix.py` and reproduces
    approach 1 on eval 25 and public ep24.
- **Next:** collect the choices, then pack with `KEEP_RESULTS=20261025-pack2-46b8389` plus the PICKs, upload the five
  pose boards and CD-O, and read the ranking. Est. ≈ $50 in all; ≈ $50 is left for a second round chosen from these
  results.

## 2026-10-25 ~13:45 TRT: contact slot names fixed (mkref column, analysis scripts, report corrections)
**Branch:** branch `claude/inspiring-mendel-lbgp9e`, started from `main-bsky37` 53929d0. Merge it into the working
branch; T2/P1 ran there in parallel.

**Owner's choice:** mkref writes a new `contact_slot_names` column (PROBE_SITES + 'palm', one name per contact slot) in
`loaded/` and `processed/`; `mano_link_names` is unchanged.

**Compatibility:**
- Checked [C] against the evaluator-pin source (8c778f90): FlashCHORD `load_reference` ignores columns it does not
  name; the kit's `from_parquet` drops them; E2S keeps the kit class.
- Round trip on the ep12 reference [M]: identical contacts, wrists and fingers through `load_reference`
  (`tests/test_contact_slots.py`).
- The first real mkref run after this commit is the end-to-end check: its VALIDATION step runs `load_reference`.
- Training is unaffected: FlashCHORD and our pipeline use any-slot activity only.

**Analysis code:**
- Slots are labelled through `tools/contact_slots.py`. The column is used when present; older mkref references fall
  back to the mkref order; anything else is refused.
- Fixed: `human_grasp_census.py`, `contact_plot.py`, `mano_where.py`, `mano_contacts.py`, `refload.py` and
  `human_board.py`.

**Reports:** the biomech (§0, §0.2, §9.2), plates (§3), boards (§2.2) and starts (§2.2, §3.2, §4.2) reports carry dated
notes with corrected tables. Every old number was first reproduced exactly; the corrected outputs are new files.

Corrected readings [M] (our perception, no GT):
- ep2 lid: palm 0.00 (the old "palm 0.76–0.80" was the thumb tip).
- Pot handle: the palm is at the far end, the thumb nearer the pot.
- Pitcher: palm 0.92–0.93.
- Plates, boards and sweepers: perceived thumb 0.03–0.35 (ep39 pick-up 0.51).
- No measured thumb-vs-finger opposition.
- The F4 "palm on the knob" lid design and the "like the human's clamp" claims now rest on mechanics only.

## 2026-10-25 ~12:45 TRT: owner's approaches researched; grip portfolio + event anchoring built; CPU tests running
**Research (CPU/web, `docs/research/approaches-2026-10-25/`):**
- Approach 1, meshes from motion: carve only the simulator collision copy (slots, nesting, start overlaps), never the
  submitted mesh. Big side finding: our eval-25 board identities look swapped, so that episode is near zero vs truth.
  The GT-free identity rule (marker knobs vs frame-0 video) is a prototype; rerun eval 25 (≈ $4–6).
- Approach 2, primitives: lathe fits help the blue cup and pot on CD-O (0.523 → 0.307, 0.437 → 0.319 cm, diagnostic
  vs public scans; board CD-O ≈ 0.405 → ≈ 0.33 if adopted) and give the beige cup a flat base. Boards, pitcher, lid,
  rack and plates are not fixed by primitives.
- Approach 3, grasp taxonomy: a type classifier on our hands does not work (noise); the owner's phase model and a
  try-every-grip portfolio scored in the simulator do. Training steps: more steps rarely rescue a low start
  (`training-steps.md`).
- Contact slots in references are in mkref PROBE_SITES order, not `mano_link_names` order (older audits mislabelled).

**Built (default off, recipe unchanged):** `grasp_lock --events 1` (load before lift-off, release at the placement;
`pipeline/object_events.py`), `pipeline/grip_types.py` (board clamp long/short, platform; thumb on top because the
Sharpa thumb cannot reach the fingertips), `grasp_evolve --from0 --f1 --cvar --push_cm --rescore`,
`tools/grip_portfolio.sh` + `grip_choose.py`, `tools/cpu_glock_zero.sh`, `tools/window_score.py`.

**CPU tests (pre-registered at cb86b5b):** T2 event-anchored windows **FAILED** (0 of 4 twins improved; not adopted).
P1 grip portfolio on ep24 board 1 **not falsified**: short-end clamp worst-quartile 0.475 vs copy 0.321, but it lifts
the board only 4.9 cm by f30; the GPU A/B after fine-tuning (≈ $8–12) decides adoption.

**GPU batch (25 Oct ~18:50 TRT):** owner topped up $100. The pre-registered eval rerun batch + eval 25 identity
repair is run by ANOTHER session (branch `claude/inspiring-mendel-lbgp9e`, 9 boxes from 14:51 UTC). This session
launched duplicates by mistake and destroyed them in setup (≈ $0.9); it does not touch that session's boxes.

## 2026-10-25 ~09:50 TRT: fixes validated overnight; eval reruns wait for the top-up (credit $1.82)
**Kaggle (unchanged since 01:00 UTC):** AUC 0.58252 (first submission 0.57468), MPPE 6.69 cm, RPE 8.82 cm, SP-SR 0.50,
MP-SR 0.40.

**Validated on public data (rules written before each test):**
- On-table detection rule: ep11 tracking 0.102 → 0.898 (shipped).
- Track guard (below-table poses → re-register / re-detect / hold): 8 public episodes 0.724 → 0.782 (ep0 0.50 → 0.96),
  no regression (shipped). It changes eval references 8, 14, 32, 33 only.
- v5 beige cup (fused along the fixed ep11 track): CD-O 0.856 → 0.730; ep11 twin 0.525 → 0.570 → adopted for evals 10, 8
  (`meshes/library_v3x`).
- Arc foot (unobserved round base completed as an 8-sector foot, simulator geometry only): ep21 pitcher stands (4.7 mm /
  1.2° vs a 158 mm fall); GPU twin still to run; changes eval 20.
- Owner: "use both" learners → the standard learner next to the grasp lock on the 12 episodes below gate 0.9.

**Negative results:** perception precision sweep (no gain; base kept); v5 library worse than v2 except the beige cup;
v5 pitcher = v3 pitcher.

**Next (pre-registered batch, ≈ $50, needs the top-up):** rebuild + both learners for evals 8, 14, 32, 33, 20, 10;
second learner on stored references for 1, 16, 19, 25, 28, 30; ep21 arc-foot twin; pack; upload.

## 2026-10-24 ~22:55 TRT: night work (owner asleep, "do as much as you can with the vast money", credit $29.98)
- Running: `20261024-seed43-61101f5` (57567887): a second seed for evals 19, 3, 5, 15, 16 and 28 on the same
  references. The better seed is chosen by mean sim_vs_ref.
- Next: CPU fixes (detection guard, start-overlap rule, capped beige cup, spoon diagnosis), then public validation,
  then a rerun of evals 1, 8, 10 and 30, then a second pack and Kaggle upload. See the work log for every step.

## 2026-10-24 ~22:35 TRT: eval videos (20) sent; low-score analysis `docs/analysis/eval-20261024-low-scores.md`
- Causes, from the diagnostics and the videos: (A) broken meshes: the pitcher is a twisted shell, the beige cup an
  open shell, the boards lack their slots (evals 20, 10, 25); (B) perception: objects tracked onto the person's left
  wrist / white watch (30 from frame 0; 33 and 14 when the cup is hidden); (C) grasps: lid never lifted (1), dust pan
  (19), boards, spoon (33); (D) spoon accuracy vs the truth ≈ 0.12 (inference).
- Next, in priority order: spoon, mesh v5 (owner directive), hand and wrist masking in perception, grasps. Each is
  validated on public twins first.

## 2026-10-24 ~21:45 TRT: FIRST LEADERBOARD SCORE — Track 3 AUC 0.57468, 9th
- All six boards (owner joined): AUC 0.575 (9th), SP-SR 0.45 (11th), MP-SR 0.35 (9th), RPE 12.6 cm (13th), MPPE 8.7 cm
  (10th), CD-O 0.405 cm (10th). Leaders: MPPE 1.2 cm, CD-O 0.11 cm.
- Uploaded by the agent through the owner's Kaggle token (network secret; `tools/kaggle_upload.py`). Board: 0.932 /
  0.884 / 0.865 / 0.752 / 0.730 / 0.662 / 0.636 / 0.630 / **0.575 us**. Other five boards: owner must Join first.
- Below the 0.68 estimate: perception loses ~19 % on eval (3–4 % on public twins); estimated mostly the spoon
  (spoon factor ≈ 0.72 by inference). Spoon perception + mesh become the top priority inside the v5 rebuild.

## 2026-10-24 ~21:20 TRT: FIRST FULL SUBMISSION PACKED — waiting for the owner's Kaggle upload
- `results/submissions/20261024-track3/track3_submission.parquet` (20 episodes, 9,120 rows, 1.3 MB, 0 mesh warnings,
  code commit 6f1aea3). Packed rollouts sim_vs_ref mean 0.710; projected ADD-AUC ≈ 0.68 (0.62–0.72).
- Owner: upload (`python3 submit/v2d_submit.py track3_submission.parquet --track track_3 -m "..." --wait` from the kit),
  share the repo with GitHub `Nvidia-V2D-Challenge`, send the organiser email. Next: mesh pipeline v5 (owner directive).

## 2026-10-24 ~20:40 TRT: all 20 eval policies trained; final pack running (`20261024-pack-31ef267`, 57544403)
- sim_vs_ref mean 0.692 (spoon 0.860, others 0.525); weak: 1 lid 0.30, 10 cups 0.33, 20 pitcher 0.29, 25 boards 0.24,
  30 sweeper+rack 0.47, 33 cup+spoon 0.39, 14 cup+rack 0.51. Projected ADD-AUC ≈ 0.66 (0.60–0.70), ≈ 6th on the
  23 Oct board. The owner uploads the packed file to Kaggle.

## 2026-10-24 ~20:10 TRT: owner directive — rebuild every mesh for the simulation (v5), after tonight's pack
- Plan (`docs/mesh-v5-spec-draft.md` + today's pitcher base completion): CPU port, G1 re-track 16 public episodes
  (≈ $2–3), library v5 with stand tests, G2 public-twin validation vs GT (≈ $15–20), G3 20-eval rerun + pack (≈ $33).
  Total ≈ $50–55; second submission ≈ 27–28 Oct. GPU steps need the owner's go-ahead.

## 2026-10-24 ~18:05 TRT: 20-episode eval run — six boxes running (owner topped up $50)
- evA 1,3,5 | evB 6,8,10 | evC 14,15,16 | evD 19,20,25 | evE 28,30,32 | evG 37 (all `20261024-ev?-664e5fd`, $9.17/h
  together); evals 33/35/36 (evF) and 38 (ev2) are done. Then `ops/jobs/pack_eval.sh` over ev2 + evA-G; the owner
  uploads to Kaggle. Estimate ≈ $29-33 in total, ready about 4 h after 15:05 UTC.

## 2026-10-24 ~15:05 TRT: eval run under way (box F: eval 33/35/36); six boxes wait for credit
- GPU validation of the recipe (registered AUC vs mocap, 5 evaluations): ep39 0.958, ep18 0.957, ep27 0.949, ep12
  0.868 (one rollout in five fails), **ep24 (boards) 0.241 ± 0.125** (standard RL 0.31: boards stay weak, only eval
  25 has boards). Eval 38 done: sim_vs_ref 0.9997, checkpoint in the store (ev2 run).
- Rules check (owner asked, 15:40): the method is within the published rules as read. Three items are open and need
  the organisers (email draft `docs/organiser-email-draft-2026-10-22.md`, now 5 questions, not sent): the kp 400
  wrist embodiment, mesh provenance (library_v3 built along scan-templated tracks; v5 rebuild not done), and the
  spoon template.
- Box F done: eval 35 0.9915, eval 36 0.9935, **eval 33 0.391** (sim_vs_ref; our perceived cup track tilts 90–130°
  after frame 48: a perception failure). Eval 33 retrained after a GPU OOM (fixed: at most 2 trainings per GPU).
- Expected result of this run (estimate, revised after eval 33): 20-episode ADD-AUC ≈ 0.74 (0.58–0.85). Leaderboard on 23 Oct 21:52 UTC:
  0.930 / 0.884 / 0.831 / 0.730, so the estimate is about 4th. The weak episodes are eval 1, 20, 25 (and 28).
- Box F 57507961 (`20261024-evF-38877d0`) running; credit $7.73 at 12:00 UTC, the other 16 episodes (A-E, G ≈ $20)
  wait for the owner's top-up. Then `ops/jobs/pack_eval.sh` over all eval runs (ev2 + evA-G).

## 2026-10-24 ~14:15 TRT: GPU validation of the onset anchor + robust evolutionary grasp search running
- Boxes 57498018 (`20261024-ev3-2c1e4dd`: ep39, ep18, ep24) and 57498007 (`20261024-ev2-2c1e4dd`: ep12, ep27, then eval
  38 from the eval videos). ~3 h, ~$8; credit $14.08 before. Owner wants the 20-episode eval run tonight (~$25-30;
  needs ~$20 more after this).
- CPU results so far (zero action, no policy): ep39 0.176 -> 0.877 (robust at mm level), ep18 0.135 -> 0.352 (chaotic;
  needs the robust search), ep24 in progress. Research reports in `docs/research/grasp/`.

## 2026-10-24 ~10:15 TRT: owner chose option 2 — one recipe (grasp-lock) with designed grasps; research first
- Eval run on hold. Root-cause audit of every failed public episode + in-depth research (hand anatomy and
  biomechanics, evolution of human grasping, robot thin-object / tool grasping, evolutionary algorithms vs RL,
  FlashCHORD capabilities): workflow `wf_cdd41283-528`, reports in `docs/research/grasp/`. Then the grasp design,
  CPU tests, and a costed GPU test plan for the owner.

## 2026-10-24 ~10:00 TRT (07:00 UTC): overnight robustness batch done; eval-run plan waits for the owner
- Report for the owner: Claude Docs "V2D Track 3 overnight report, 24 Oct" (https://claude.ai/artifact/SnxYC73hNa84NFPjFDCpRH).
- No boxes running. Credit $4.08 (overnight spend $12.72 measured).
- Results (registered AUC vs mocap, 5 evaluations): grasp-lock strong on rigid graspables (ep27 0.957–0.972, ep12
  0.854–0.910, eval spoon sim_vs_ref 0.97), weak on plates and stacked / unsupported starts (ep39 0.174, ep18
  0.22–0.41, ep21 0.281, ep2 0.306, ep26 0.383; ep31 0.767). **Standard FDR RL (250M) lifts the ep39 dust pan:
  0.802 ± 0.280** (4 of 5 rollouts 0.94), as it solved ep18 (0.776 / 0.889).
- Keep: early approach 15 cm, re-plan (kept only when replay improves), 3 evaluations per checkpoint, support fill
  (neutral). Drop: recovery training (drop starts), library_v4 flattened boards. Early stopping off (owner).
- Proposal (owner's ruling needed: "we cannot pick and choose"): `ops/jobs/eval_both.sh` (7a08bf4, not run) =
  grasp-lock learner on every eval episode, standard learner on the same reference where the grasp lock tracks
  below 0.9, then `tools/choose_learner.py` (mean sim_vs_ref vs the perceived path; picked the better learner in
  3 of 3 public pairs). Option B ≈ $45–55, ≈ 7 h, staged (first box eval 38 + eval 3). Projected eval ADD-AUC ≈ 0.77
  (estimate, range 0.67–0.86); leaderboard #3 is 0.831 (23 Oct 21:52 UTC).
- Owner decisions open: the choice rule, go-ahead + top-up (≈ $60), which rollout to pack (fresh unmodified
  evaluator by default), Kaggle upload.

## 2026-10-23 ~23:00 TRT: 5 boxes running — support fill, grasp re-plan in the simulated world, recovery training
- Owner: "snap and grasp in a dynamic world; a drop should not stop the recipe" → both parts built and approved:
  - **part 1** re-plans holds against the simulated world (`grasp_lock.py --sim_trace`, `glock_public.sh REPLAN`);
  - **part 2** adds recovery training to FlashCHORD: drop starts with relaxed termination
    (`ops/box/patch_flashchord_drop.py`, `FC_DROP_START`, training only, CPU-tested).
- Running:

  | box | run | test |
  |---|---|---|
  | A | `20261023-sf18-bfb973a` | ep18 with the support fill |
  | B | `20261023-sf1227-bfb973a` | ep12 + ep27 with the support fill |
  | C | `20261023-rp18-a674fd7` | ep18 without the fill + REPLAN 2 |
  | D1 | `20261023-dr18-a674fd7` | ep18 without the fill + drop starts 0.2 |
  | D2 | `20261023-dr12-a674fd7` | ep12 with the fill + drop starts 0.2 (regression check vs B) |

- Credit $14.41 at 22:55 TRT; total of these batches ≈ $9.4.
- After results: videos of ep18 (`ops/jobs/vid_after.sh` on a held box, or locally from the pushed traces).

## 2026-10-23 ~21:30 TRT: support-consistent meshes (stability certificate) ready; public check ep18/12/27 next
- Owner: the mesh should physically support the start pose, with a mathematical stability condition. Done in
  `pipeline/support_fill.py` (notes 25):
  - criterion: the COM must be over the support polygon with margin d ≥ 3 mm and tip angle atan(d / h) ≥ 3°;
  - as-is poses are judged after quasi-static rocking of up to 3°;
  - otherwise the smallest certified underside fill (0.5–2 cm) is added, if it stays in free space along our
    reference;
  - `tools/rest_check.py` checks it in the simulator (zero action: within 5 mm / 2° until grasped). On the round-2
    ep18 trace the brush moved 88.7 mm / 81.7°.
- Decisions on the public references:
  - ep18 brush: 1 cm fill; dust pan as is;
  - ep12: cup 0.5 cm fill, rack blocked;
  - ep27: pot 1 cm fill;
  - ep24: unchanged, so its 0.202 stands.
- The human holds the ep18 plates with a thumb–fingers clamp (palm contact 0–13%), so the grasp rule is unchanged for
  this test.
- Next: `glock_public.sh` with SF=1 on ep18 (alone) and ep12 + ep27; ≈ $4, approved with the $10 top-up.

## 2026-10-23 17:25 TRT (14:25 UTC): **eval spoon episodes: ep3 0.968, ep35 0.978 (fine-tuned, mean of 5 evaluations)**
- Recipe that works on eval ep3: wrap grasp-lock reference (`grasp_lock.py`, wrap on the handle) + wrist ILC + **kp 400
  wrist embodiment (`sharpa_hands_mid`)** + RL fine-tune (FDR + VOC fix). Official evaluator (VOC 0, frame 0), sim_vs_ref
  vs our reference, one evaluation each: 40M 0.965, 60M 0.980, **70M 0.981** (policy committed:
  `results/e2e/spoon_20261023/ep3_ft_k400_s42_policy_70M.safetensors`, sha256 f889339d…), 90M 0.965. Zero action on
  the same reference 0.658; RL alone 0.380 / 0.413; floor 0.439. The same fine-tune with the kp 25 wrist fails
  (0.23–0.42, spoon not lifted) → the stiff wrist is essential. Repeat evaluations of the chosen checkpoint still to do.
- eval ep35: single-hand wrap carry with the anatomy closing (`--mcp_first 1 --close 10 --palm_clear -0.001`) 0.521 at
  zero action (was 0.15–0.27; RL alone 0.337; floor 0.112); copying the human's hand switches fails so far (the copied
  left-hand bowl grasp drops the spoon: 0.07–0.18). Fine-tune of the kp 400 version running (`ft_ep35k.sh`, 70M).
- Physics-aware design (notes 24): minimal-force squeezes hurt (ep3 0.309); a firm squeeze + anatomy closing order
  helps ep35 but the same rule costs ep3 0.2 at zero action (not isolated yet).
- **eval ep35 fine-tune (kp 400 reference, zero action 0.412): 40M 0.979; 5 repeated evaluations mean 0.978 (sd
  0.002)**; seed 43 reproduces (40M 0.973). ep3 70M 5 repeats mean 0.968 (sd 0.020); ep3 seed 43 at 40M 0.843 (the pot,
  held by the copied human grasp, is the variable part) → train 70M and select by repeated sim_vs_ref.
  Policies: `results/e2e/spoon_20261023/ep3_ft_k400_s42_policy_70M.safetensors`, `ep35_ft_k400_s42_policy_40M.safetensors`.
- Box `20261023-spoon3R-4c31271`: hold expires 14:30 UTC, the watchdog pushes runs/ + results/ and destroys it.
  `/content/glock` (references, traces, videos) in the HF store `runs/20261023-spoon3R-4c31271/glock`.
- Next (owner go-ahead + cost needed, Vast top-up likely): the other 8 spoon eval episodes (≈ $12–15 one seed); validate
  the recipe on public episodes with other objects against ground truth (≈ $6–8); a secure second-hand (bowl) grasp.

## 2026-10-23 15:15 TRT (12:15 UTC): wrap grasp-lock reference beats RL on ep3; ep35 release being fixed
- `pipeline/grasp_lock.py` + `pipeline/wrap_grasp.py` + `pipeline/wrist_ilc.py`: a built wrap (power) grasp on the
  spoon handle, locked to the object during the hold, wrist lag corrected by ILC. Zero action, evaluator physics,
  sim_vs_ref (our reference only): **ep3 0.462** (floor 0.439, VOC-fixed RL s42 0.380); **ep35 single-hand carry
  0.267** with the v4 release (floor 0.112, VOC-fixed RL s42/s43 0.289/0.337). ep35 still loses the spoon at the final
  release (f404); v5 release (unroll fingertips first, then lift the palm away) running.
- Rehearsal (VOC fix): ep35 s43 final 0.337; ep3 s43 at 230M/250M at 12:08 UTC. Then the ep3 wrap RL fine-tune
  (`/content/glock/ft_ep3.sh`, seed 42, 250M) starts by itself on the same box.
- Box `20261023-spoon3R-4c31271` held to 14:30 UTC (`/content/hold_until.sh`); copy `/content/glock/*` off first.

## 2026-10-23 12:45 TRT (09:45 UTC): spoon root cause = VOC explosion; rehearsal restarted on the fix (2 seeds)
- Rehearsal seed 42 (FDR + detection rules + capped lead-in): **ep3 0.410 (floor 0.439), ep35 0.105 (floor 0.112)**,
  no object moves in any rollout. Reference, contact labels and the in-hand physics checked out (work log).
- **Root cause [measured]:** FlashCHORD's virtual object controller (VOC) scales torque by the MEAN inertia; the spoon's
  long axis has 1/38 of that, so with VOC > ~0.13 (curriculum stages 1.0 → 0.25, ≈ 64M of 250M steps) the spoon
  explodes in training (zero-action replay from frame 0: 1.9 m off at frame 3 CPU, 1e8 m at frame 30 GPU; stock VOC
  0.25 → 82 m by frame 60, 0.1 → 13 cm). Fix `ops/box/fc_v2d_voc.py` (torque R I Rᵀ α), default on via
  `FC_VOC_INERTIA` in `lib.sh fc_patches`; patched VOC 1.0/0.5/0.25 stays stable. Training only (evaluator VOC 0).
- **Owner (≈09:30 UTC): restart with the fix, 2 seeds each** (≈ $15). Both boxes restarted in place 09:34 UTC at
  8db32a1 (`restart_job.sh`; old runs kept as `/content/{runs,results}/perc2mc_voc0`, logs `*_voc0.log`):
  `export SPLIT=eval CONTACT_RETARGET=1 RETRIES=0 SEEDS_MIN=2 EPS=<3|35>; bash ops/jobs/auto_runs.sh`.
  Seed 42 ≈ 12:10 UTC, final ≈ 15:00 UTC. Credit $19.82 at ≈ 09:30 UTC.
- **11:15 UTC owner decision: build a secure grasp-lock reference** (grasp-first; security over replication; gate on
  zero-action replay before RL; develop on public episodes). In progress (work log 14:15 TRT).
- Learning curves (VOC-fixed seed 42): pick-up learned at 70–90M as VOC fades; drop point flat from 90M to 250M
  (ep3 f105–109, ep35 f141–147) → longer training unlikely to fix the hold.
- Owner asked about non-RL alternatives: plan in `docs/research/notes/23-grasp-controller-and-rl-handoff.md`
  (grasp controller written into the reference, then RL fine-tune); waits for the fixed rehearsal and a go-ahead.
- Measured (`tools/hand_object_gap.py`): the reference puts the right fingers on the spoon; zero action reaches
  1.5–3.3 cm; the seed-42 (stock VOC) policies pulled the wrist 35–43 cm away (learned avoidance).
- The rollout videos from `render_rollout.sh` were misleading (view_policy ends episodes on drift and restarts at
  frame 0, the evaluator does not). Evaluator-like renders of the failed seed-42 policies running
  (`scratchpad/render_eval.sh`: failure terms off, VOC caps 0, no reset assist).

## 2026-10-23 00:50 TRT: FlashDexRetarget-style rewards ready for a 2-episode x 2-seed A/B
- Owner (22:xx TRT 10-22): "start developing the flashdexretarget version"; test on a few public episodes, per-episode
  training, ≈ $10 (ep12 + ep18, seeds 42 / 43); if acceptable, go to the full 20.
- **Port, training reward only** (`ops/box/fc_v2d_fdr.py`, installed by `ops/box/patch_flashchord_fdr.py`, inert
  unless `FC_FDR_OBJ` / `FC_FDR_TIPS` are set): the `object_keypoints` slot becomes FDR's point match (128 points on
  our own object mesh at its true size, top-3 error, exp(-e/0.1)); the `force_closure` slot becomes FDR's one-sided
  fingertip bound (exp(-max(0, d_sim - d_ref)/1 cm), d_ref from our reference robot tips). Weights: object 20, tips 6,
  wrench support 10 → 3, unintended contact -10 → -2; hand terms unchanged (0.25 / 0.25). The checkpoint config keeps
  FlashCHORD's own term names (unpatched evaluator loads it). Not ported: K=10 future encoder, per-hand actor-critic,
  multi-reference training, FDR terminations, FDR's 5.8 cm point normalisation (we use true size: the score is ADD).
- **Correction:** FlashCHORD's Sharpa recipe already lets the policy move the wrist ±20 cm / ±1 rad from the reference
  (normalized rational mapping up to the clip; 5 cm / 0.15 rad is only the gain near zero), so no action change.
- CPU tests passed (ep18 reference; `scratchpad/fdr/test_fdr*.py`): both terms 1.0 on the reference, object +2 cm →
  0.8187 = exp(-0.2), hands +5 cm → tip term 0.11–0.71, mesh distance = trimesh within 0.002 mm, eager env steps OK.
- **Owner (04:35 TRT): FDR is the default (`FDR=1` in auto_runs; `FDR=0` = stock). Fix the spoon episodes before the
  full launch.** Spoon plan ≈ $10–12 (work log 04:40): ep35 + ep36 with FDR, detection dumps + replay, ep3 end to end.
- **FDR A/B done (04:15 TRT): FDR rewards help.** Registered AUC, 6 evaluations each: ep12 0.790 → 0.891 (s42) /
  0.762 (s43); ep18 0.715 → 0.776 (s42) / 0.889 (s43, all rollouts succeed). Mean of four runs 0.830 vs 0.753.
  Recommendation: FDR rewards as the default training (owner to confirm). Table `results/e2e/fdr_20261023/`.
- **ep35 retrain with the capped lead-in: 0.147** (was 0.127, floor 0.112): the start was not the main limit. The
  reference turns the spoon up to 140° (in-hand reorientation); hypothesis: FlashCHORD's 1 m axis-point reward gives
  no gradient past ~0.3 rad. Next test: ep35 with FDR rewards (≈ $3).
- Ready to launch (commit after this one; `ops/vast.sh V2D_COMMIT=<head> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create
  <WS offer> <run_id> '<job>'`): ep35 + FDR `export SPLIT=eval CONTACT_RETARGET=1 RETRIES=0 EPS="35" FDR=1; bash
  ops/jobs/auto_runs.sh` (≈ $3); detection dumps `bash ops/jobs/det_dump.sh` (≈ $2); full eval with FDR = the same
  auto_runs job with all 20 eval episodes (≈ $50–60, one training per GPU, WS cards).
- Credit $4.54, no instances. Next GPU needs a top-up: ep35 + FDR (≈ $3), detection dumps (≈ $2), then the first
  full eval submission with FDR (≈ $50–60).
- **ep35 (spoon alone, eval): weak, sim_vs_ref 0.127 vs static floor 0.112** (box self-destroyed 00:27 TRT, ≈ $6).
  The simulated hands never move; the spoon stays on the table. Cause [measured]: the right hand is first detected at
  f6 and mkref's lead-in brought it in from 18 cm away in 6 frames (60 cm/s); with zero action the simulated wrist
  is 16 cm behind by step 10 (wrist limit 15 cm). Fixed generically: `mkref --lead_in_speed 0.2` (commit 20d0017).
  Retrain ep35 to confirm (≈ $3–5) before the eval run.
- Spoon detection fix, CPU side ready (commit 2aaca55): perc2 dumps all frame-0 candidates (`DET_DUMP`, `DET_ONLY`),
  `tools/det_replay.py` (52 rule variants, grid + selection rule fixed in advance), `tools/det_score.py` (public
  labels, 18 episodes / 72 frames rendered). Needs one GPU job `ops/jobs/det_dump.sh` (≈ $1.5–2) for the dumps.
- VLM / grounding research done (`scratchpad/vlm/`, summary in the work log 01:30 TRT): ship first the cheap fixes
  (soft size term, part-of merge rule) replayed on public frame-0 dumps; Grounding DINO tiny as an extra assignment
  term second; a VLM verifier only after the first submission.

## 2026-10-22 evening (19:10 TRT): priorities by score weight
- Final AUC = plain mean over the 20 eval episodes; objects equal within an episode. Object shares: **spoon 32.5 %**,
  pot 15 %, blue cup 12.5 %, rack 12.5 %, dust pan 7.5 %, beige cup 5 %, sweeper 5 %, lid / pitcher / boards 2.5 % each.
- ep24 with the organisers' meshes (s42): 0.389 vs 0.307 with ours; board 2 is never lifted in any rollout (it floats
  2.6 cm above the table in our reference at the grasp) → ep24's limit is mostly not the mesh. Seed 43 pending
  (box 57224262). Boards are 5 % of the score → stop ep24-specific spending.
- Next: spoon reconstruction / registration robustness first; generic support constraint (objects at rest sit on the
  table); mesher evidence round `wf_f198e86a-d3b` running; sweeper flips at eval ep30's registration seed.

## 2026-10-22 morning (09:20 TRT): overnight closed; next = physically valid meshes built from interactions
- Last box (L, ep12 rest settle + stable pose) done: 0.740 ± 0.032 vs retargeting alone 0.790 ± 0.023 (one seed).
  Rest settling helps only where an object cannot stand by itself (ep18). Overnight spend $49.76 (credit $2.93,
  no instances). Report final: `docs/overnight-2026-10-22.md` (results, recommendation, spend per run id).
- Owner (08:30–09:00): ep24 also has the two hands snapping onto one board and boards without their interlocking
  slots; asked whether the per-object patches are robust (they are not: hand-made per object/episode) and suggested
  building the meshes from how the pieces interact. Two research workflows running (literature sweep + verification;
  interaction census over our 12 two-object public episodes, mesh-vs-scan defect diagnostics, code map, three designs
  judged). Plan to follow in `docs/` (sim-valid meshes).
- Waiting on the owner: top-up for GPU tests (ep24 with slots + standing edges, ep18 second seed ≈ $10).
- **Owner decisions (11:20):** reconstruct the spoon ourselves; generalised automatic rules OK; per eval episode
  re-create the mesh from that episode's video (library mesh only as a tracking seed); room map dropped (GT-registered).
- **Plan proposed (11:25), awaiting go-ahead + ≈ $60 top-up for step 1:** (1) baseline eval submission with the current
  pipeline; (2) mesher fix (TSDF zero level, thin walls, CPU); (3) automatic physics check + repair incl. interaction
  carving; (4) per-eval re-fusion + spoon reconstruction; (5) floor guard (done 11:40); (6) public-twin validation
  ≈ $40; (7) final eval run ≈ $70. Library must be rebuilt (v5): v1–v4 used public scans as `--others`.

## 2026-10-22 overnight (owner asleep; $50 top-up, credit $52.69 at 01:00 TRT; "go crazy, I trust you")
Plan: round 1 = contact-retargeted references ("k") on ep12, ep18, ep24, ep27 (seed 42, 250M, sweep) + 6 repeat
evaluations each of the new and the base policies; round 2 = second seed + fixes for what fails; round 3 = confirm the
best setup with a fresh seed. Live log of rounds: `docs/work-log.md` (2026-10-22 entries).

Morning summary (07:10 TRT; full report `docs/overnight-2026-10-22.md`, rows `results/e2e/overnight_20261022/`):
registered AUC with our meshes, mean of 6 evaluations: base ep12 0.725 / ep27 0.942 / ep18 0.345 / ep24 0.297;
contact retargeting 0.790 / 0.911 / 0.32–0.36 / 0.31 (consistent rollouts, mean ≈ +0.01). No variant lifts ep18
above ~0.38 or ep24 above ~0.32. Root causes found: ep18's reconstructed sweeper cannot stand (rounded underside) and
falls with no hand near it once the object assist is off; objects float 1–4 cm above the table in our references
(ep12, ep24, ep27); ep24's limit is learning the lift/stand-up. Fixes: `flatten_base.py` + `meshes/library_v3`,
`contact_retarget --rest_settle 1` (stable rest poses); GPU tests running: K = ep18 kfi (≈ 08:00 TRT), L = ep12 kr
(≈ 09:00 TRT). Credit $7.55 at 06:55 TRT; both boxes self-destroy.

## 2026-10-21 night: contact-anchored retargeting ready for the GPU A/B (prepared before the top-up)
Details: `docs/work-log.md` (22:35–23:05 TRT entries). Vast credit **$2.69**, no instances running.
- **Diagnosis (measured):** the robot hand in our references sits 16–20 mm (p95) inside the objects at most contact
  frames (easy and hard episodes alike); the evaluation starts without the training's 20-step object assist.
- **`pipeline/contact_retarget.py`** (owner: "snap the fingertips, let the wrist follow"): per frame, human fingertips
  near a surface become contact targets; wrist pose (±6 cm / ±0.5 rad) and finger joints are solved so the robot
  pads reach them while the simulator's own collision (CPU MuJoCo on the scene's convex pieces) reports no
  penetration. CPU, 3–6 min per episode. Simulator check: ep24 penetrating frames 242 → 62 / 275 (p95 20.1 → 6.0 mm),
  ep18 ~77 % → 41 / 361 (p95 16 → 2.7 mm), no hand–hand overlap, frame 0 clean (0.8° / 0.7°). Remaining one-step pops
  are mostly carried boards falling (the policy must grip), not penetration.
- **Wired in:** `pipeline_ep.sh` stage 3c (`CONTACT_RETARGET=1`, E2S parquet kept as `e2s_reference.parquet`);
  `ops/jobs/hard_ab.sh` (pull a run's perception + references, retarget, train 250M seed 42 with the sweep, then 6
  repeat evaluations each of the new policy and today's base policy from `policies/`, registered scores; also scores
  the ep12 / ep27 controls left in the store).
- **Launch after the top-up and the owner's go-ahead (≈ $7–8 for both at 23:10 TRT offers of $1.62–1.75/h, ~2.2 h):** two RTX PRO 6000 boxes,
  `ops/vast.sh V2D_COMMIT=<head> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run_id>
  'PAIRS="24:20261021-auto24-966eb96:mcs" bash ops/jobs/hard_ab.sh'` and the same with
  `PAIRS="18:20261021-auto18-966eb96:mc"`. Falsified if the new mean (sim_vs_ref and registered AUC over the
  repeats) does not beat the base mean on both episodes.
- Next after that (ideas with tests in `docs/forensics-2026-10-21.md`): physics search over hand motions (SPIDER /
  Do as I Do style) for the remaining hard segments; object-scaled keypoint reward; one-sided fingertip reward.

## 2026-10-21 afternoon: validation of the new pipeline (owner topped up $10; credit $19.79 at 14:58 TRT)
Details: `docs/work-log.md` (15:20 TRT onwards).
- **HF PRO (owner, 2026-10-21):** 1 TB private storage included, then pay-as-you-go $18/TB/month. `store.sh` refuses
  uploads once the store holds `STORE_MAX_GB` (800); checkpoints kept every 10th (was 25th); eval depth caches are
  pushed (`own_eval.sh PUSH_DEPTH=1` default). The store still reports 99.5 GB used.
- **Validation, round 1 (box 57047922, 11:58–12:51 UTC, ≈ $1.4):** ep18 mkref refused our dust pan (3.5 cm under the
  table); both ep24 trainings were SIGKILLed in the 4096-world build. Causes found and fixed (details in the work log):
  - mesh undersides filled solid (dust pan 3.5 cm, white pot 5.5 cm under the table) → `recon_mesh --below_carve`,
    `meshes/library_v2` (pot now 13.1 × 19.0 × 36.2 cm vs scan 13.2 × 18.9 × 35.7; registered AUC 0.991–0.998);
  - Newton splits coloured meshes into one shape per colour (174 per board) → `make_assets.py` writes colourless
    simulator copies (reproduced and verified on CPU with FlashCHORD's pins: 64 worlds 4.2 s / 0.61 GB).
- **Validation, round 2 (commit 966eb96 + 47518d5, two boxes from 13:22 UTC).** Final hard-episode scores today
  (registered, our own meshes): **ep18 0.396** (mc s42; static floor 0.637; reference 0.982), **ep24 0.232** (mcs s42 =
  wrist cost 3.0 + hand separation; floor 0.229; reference 0.816). Earlier (scans): ep18 0.128 / 0.337, ep24 0.236 / 0.152.
  - Found and fixed on CPU replays (`scratchpad replay_probe.py`, `contact_probe.py`, FlashCHORD pins): the two robot hands
    overlapped at ep24's reset (right hand unseen f0–16 and held next to the left) → `mkref --hand_sep 0.04 --lead_in 10`;
    ep24 0.080 → 0.232.
  - Falsified: mid-stiffness wrist (ep18 0.193, ep24 0.050), larger joint clearance (10 mm: finger deeper in the board).
  - Rollout noise: one policy, 8 evaluations, 0.13–0.41 vs mocap; `sim_vs_ref` (no GT) correlates 0.98.
  - Controls ep12 + ep27 running on box 57058717 (newest code, RETRIES=0), results ≈ 22:30 TRT; credit ≈ $2 after.
- **Forensics and ideas for the owner: `docs/forensics-2026-10-21.md`** (architecture shortcomings, embodiment options
  incl. NVIDIA's `sharpa_hands_primitive` (CPU-tested, helps ep24's start), manipulation-type segmentation prototype
  `tools/manip_segments.py`, physics preflight gate, SPIDER-style references; research on the two leaders pending).

## 2026-10-21 (owner topped up: credit $27.19 before the batch)
Details and commands: `docs/work-log.md` (2026-10-21 entries).
- **Hard-episode A/B batch done** (3 boxes destroyed 11:35 TRT; **credit $10.63**, the batch cost ≈ $16.6;
  training took 3.3 h at ~21k steps/s per policy with two per box). Sim vs mocap AUC (registered ≈ same):
  **ep21 pouring 0.826** (SP 1, MP 1; ref 0.985), **ep24 planter boards 0.235 = static floor** (boards never lifted),
  **ep18 sweeper + dustpan 0.127 / 0.337, below the static floor 0.61** (the sweeper falls). Wrist cost 3.0: no
  consistent effect. Policy failure on hard tasks is the main risk (eval twins 19, 25, 30, 38).
- **(Resolved: squash, then HF PRO in the afternoon.) Blocker: the HF store is full** (99.6 GB of the private quota; final pushes failed with "Private storage limit
  reached"). Cause: `store.sh push-run` pruned checkpoints one directory level too high, so every 5M-step policy and
  state went up (state_ files of finished runs: 44 GB). Prune fixed (7b4621e). Freeing space needs the owner:
  delete finished runs' state_ files + `super_squash_history` (irreversible), or a larger HF plan.
- **Leaderboard moved** (2026-10-21 00:55 UTC): Zihao Guo AUC 0.831 (SP 0.95, MP 0.75, CD-O 0.313), SoySauceChicken
  0.823 (CD-O 0.065), SRL 0.657. The bar is 0.831.
- **The official pose scorers now register our submitted mesh to the hidden scan** (kit `metric_code/track_3`,
  `_score_registered_track3`): mesh ICP → poses moved to the scan's anchor and axes → one frame-0 scene alignment on
  the first object without a symmetry axis → symmetry-aware errors (cup spin and lid 180° not scored).
  `pipeline/score_registered.py` reproduces it locally with the public scan as stand-in. With the scan as our mesh the
  20-episode perception mean is unchanged (0.8828 → 0.8824); ep12 0.998 → 0.940 (the rack now sets the rotation),
  ep11 0.873 → 0.913.
- **Mesh quality is now first-order for all five pose metrics.** Damaged-scan test (6 episodes, mean AUC): clean
  0.987, convex hull 0.947, bottom missing 0.904, 3 mm noise 0.825, 5 mm thicker 0.608 (flat objects register
  flipped). Scale errors are free.
- **FAQ (current):** "participants should reconstruct the objects to generate object trajectories and submit their
  own reconstructed meshes" → **owner decision**: (A) reconstruct first, track with our own mesh (compliant, more
  work) or (B) keep tracking with the public scans and submit only our own meshes (rule risk); and ask
  v2d_challenge@nvidia.com whether public scans may be used for tracking.
- **Own-mesh reconstruction** (`pipeline/recon_mesh.py`, CPU in the cloud VM, 1.5–4 min/object; versions v0–v6 in
  the work log): TSDF of our stereo depth in the object frame along our tracks; table (per-frame refit plane),
  hands and other tracked objects carve but never vote surface; auto closing (fill vs near). Registered AUC with
  our mesh / with the scan: **ep41 pot 0.998 / 0.999, ep23 boards 0.997 / 0.999** (v5), ep39 dustpan 0.953 / 0.997
  (v3; the edge filter hurts it), ep21 cup + pitcher 0.917 / 0.975 (v3). Risk: board registration flips 180° in
  0–25 % of sampling seeds depending on small parameter changes. Multi-episode fusion implemented, not yet tested.
  QA tool for eval tracks: `pipeline/track_overlay.py`.
- **Eval-episode plumbing** done in code (`SPLIT=eval`), not yet run on a box. Eval ep1 videos have 335 frames =
  the kit roster.
- `.gitignore` had hidden `results/`; `results/e2e`, `results/registered`, `results/recon` are now committed.

## Night of 2026-10-20 → 21 (owner asleep; mandate: spend the $25 Vast credit on retries, fix failures, research)
Details and every command: `docs/work-log.md`. Branch `main-bsky37`.
- **Infrastructure works on Vast.** Snapshot restore 2 min (`ENV_SNAPSHOT=pt2.11-cu130-py313-20261020`), full setup
  10 min, HTTPS `ops/vast.sh exec` instead of SSH (SSH blocked), headless rollout video `pipeline/render_rollout.sh`.
- **First end-to-end score was invalid** (AUC 0.009): mkref's table fit picked the floor, objects fell 60 cm. Fixed
  (support-plane choice + guard). ep12 perc2 + oracle retrained on box 1, results ≈ 01:20–01:40.
- **Perception:** compactness detection prior (now default) → 20-episode mean AUC 0.883 → 0.932 (ep26 0.065 → 0.988).
- **Reference (hands → robot):** (1) Viterbi hand-identity linker (default) fixes the ep12 hand-over swap; A/B over
  all episodes running (`ops/jobs/hands_ab.sh`). (2) Robot wrist jumps of 10–31 cm/frame come from NVIDIA's E2S IK
  (wrist cost 0.2 vs fingertips 1.0, warm-start drift); `mkref --wrist_cost 3.0` cuts them to ≤ 8 cm on ep44/ep12
  (fingertip error +1–2 cm). Bone normalisation and a larger `mano_to_robot_scale` did not help.
- **Robot:** mid-stiffness wrist embodiment `flashchord_conf/embodiment/sharpa_hands_mid.yaml` (kp 400 vs 25 N/m;
  FAQ allows other embodiments; owner to confirm before any submission uses it).
- **End-to-end results, ep12 (public; sim vs mocap, our scorer with the kit metric functions):**

  | run | config | AUC | SP | MP | MPPE | robot tracking (sim vs ref) |
  |---|---|---|---|---|---|---|
  | perc2 | greedy hands, NVIDIA retarget weights, default wrist | **0.890** | 1.00 | 1.00 | 1.5 cm | 0.863 |
  | oracle | mocap objects (diagnostic only) | 0.858 | 1.00 | 0.00 | 1.8 cm | 0.855 |
  | vw | Viterbi hands + mid-stiffness wrist | 0.860 | 1.00 | 1.00 | 1.8 cm | 0.841 |
  | vc | Viterbi hands + E2S wrist cost 3.0 | 0.604 (failed) | 0 | 0 | 7.7 cm | 0.576 |

  Reading: on ep12 the robot, not perception, sets the score (~0.14 AUC lost in tracking; ±0.03 between policies);
  the mid wrist gave no measurable gain; wrist cost 3.0 failed once (one seed). Loss in the good runs = final cup
  placement (ends ~8 cm off, on the rack edge).
- **Hand linker:** Viterbi was mixed over 18 episodes (fixes the ep12 hand-over, follows spurious tracks elsewhere);
  greedy is the default again.
- **ep27 (pot into rack) vc: AUC 0.965, SP 1, MP 1, MPPE 0.9 cm; ep2 (pot + lid) vc: AUC 0.926, SP 1, MP 1,
  MPPE 1.3 cm.** Both rollouts reproduce the video (pot flipped onto the rack; lid off, pot lifted). Best run per
  episode over 12/27/2: mean AUC 0.927 (public, one seed each; not a leaderboard estimate).
- All boxes destroyed; Vast credit $2.22 left (≈ $22.8 spent on 2026-10-20). Results in the HF store and `results/e2e/`.

## Path to the first score (route A, owner decision 2026-10-21; "do whatever it takes for the best score")
1. Mesh library v1 from the public videos (CPU here; `meshes/library_v1/`, coloured by `mesh_color.py`; spoon = our
   parametric model). Fused pot on episodes 41–45: registered AUC 0.958–0.987 vs 0.966–0.999 with the scan, no flips.
2. One GPU box, `ops/jobs/own_eval.sh` (~3 h, ~$4.5): assets from our meshes; H2 check (tracking with our meshes on
   8 public episodes, scored against mocap); perception + hands + references for the 20 eval episodes.
3. Visual QA of the eval tracks (`qa_eval.sh` → `results/qa/`), fix the worst.
4. **Owner: top up Vast ≈ $60**, then 20 trainings on ~10 boxes (`ops/jobs/train_eval.sh`, RESUME_FROM = the
   own_eval run, 2 per box, ~3.5 h, ≈ $50).
5. Pack (`tools/pack_submission.py --meshes` = our library per episode, `--code-commit` URL), **owner uploads**
   (Kaggle rules accepted for the 6 Track 3 competitions; repo shared with GitHub user `Nvidia-V2D-Challenge`).
6. Iterate on the weakest episodes (policy fallback when a rollout is worse than not moving; spoon; meshes).

## Next steps (proposed for the owner, updated 2026-10-21)
0. **Meshes and the FAQ rule** (new, highest priority): finish reconstruction v0 on all objects (public episodes,
   CPU), then (H2) a GPU run tracking with our own reconstructed mesh instead of the scan, measured on public
   episodes; decide A/B with the owner; spoon from its parametric model or reconstruction.
1. **Multi-seed per episode** and pick the policy by sim-vs-our-reference (no GT): policy variance is ±0.03 and a
   catastrophic failure (ep12 vc) can happen in one seed.
2. **Wrist IK cost**: test 1.0 vs 3.0 vs 0.2 over several episodes and seeds (3.0 removed the jumps; one failure on
   ep12, successes on 27 and 2).
3. **Eval run plumbing**: perception on eval videos with object names from the kit json; spoon model + frame decision;
   then a first 20-episode submission (≈ $50 on demand at ~$2.4 per policy, less with interruptible boxes).
4. Open questions: njmax overflow and the mid-wrist embodiment vs the rules; spoon frame A vs B.
- **Open questions for the owner:** njmax 512 overflows in training (raising it changes sim settings → ask the
  organisers); the mid wrist (embodiment) for submissions; spoon frame (A vs B).

## Goal and constraints
- **Goal:** top of the NVIDIA V2D Challenge Track 3 leaderboard (ranked by AUC), plus the Industry Innovation award.
  Freeze 2026-11-04 17:00 EST. The owner said "anything goes" for the leaderboard, within the rules.
- **Budget:** the professor considered $1,000–1,500 reasonable. The plan below needs about $110–200 of GPU time.
- **Owner-only actions:** Vast.ai account and credit, challenge registration, accepting the Kaggle Track 3 rules,
  sharing a repo with the organisers (this one or a cleaned copy), uploading submissions. The agent cannot sign up,
  sign in or pay.

## How Track 3 is scored (verified from the kit)
- Submitted rows must be **FlashCHORD rollouts from the official evaluator** of a trained policy per eval episode, with
  evaluator code digests, a checkpoint digest and a GitHub commit URL on every row. Perception output alone cannot be
  submitted. The packer is `tools/pack_submission.py` in the kit.
- 20 eval episodes: 1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38. Their objects are in the
  kit's `data/track_3_evaluation_objects.json`. **Wooden spoon in 10** (3, 5, 6, 15, 16, 32, 33, 35, 36, 37; slot 0 and
  alone in 35–37). **White pot in 6** (1, 3, 5, 6, 8, 28).
- Metrics: one rigid warp from slot 0 at frame 0, no scale fix. AUC = ADD swept over 1–9 cm (trapezoid; ranking metric);
  SP-SR (≤ 10 cm and ≤ 0.5 rad); MP-SR (< 3 cm and < 30° for every object); RPE; MPPE (6 points at 5 cm).
- Leaderboard on 2026-10-12: SoySauceChicken AUC 0.765 / SP 0.80 / MP 0.50 / MPPE 3.0 / CD-O 0.583. Other teams
  0.23–0.37. Leaving every object at its frame-0 pose scores about 0.446.

## What works (measured)
- **Simulator and evaluator on Colab G4** (RTX PRO 6000 96 GB):
  - FlashCHORD at the evaluator pin (`8c778f90`); jax 0.10.2, warp 1.14, newton 1.2, mujoco 3.8.1.
  - Sharpa FlashSAC trains at about 45,300 env steps/s with a 40.5 GB peak (`XLA_PYTHON_CLIENT_PREALLOCATE=false`),
    so a 250M-step policy takes about 1.5–2 h.
  - The official evaluator (1 world, trajectory export) works. A 20M-step tissue-box policy scored AUC 0.918 against
    its own reference.
- **Perception** (`pipeline/perc2.py`) on the 20 public episodes, scored with the kit's metric functions against mocap:
  **mean AUC 0.809, SP 0.90, MP 0.85, MPPE 4.76 cm**. Per episode:
  - 0.986–0.998: 12, 13, 23, 27, 40.
  - 0.935–0.962: 18, 22. Episode 2 ≈ 0.98, inferred from the mean.
  - 0.795–0.887: 11, 21, 24, 31, 41, 42, 43, 44, 45.
  - Failures: 39 at 0.550 (dustpan offset about 5 cm once moving); 0 at 0.179 (lid 180° symmetric, so its rotation
    is wrong from frame 0); 26 at 0.031 (white pot inside the white rack; wrong detections).
- **Hands:** MediaPipe 0.10.14 on the **colour** camera finds two hands in 173/181 (ep 12) and 338/373 (ep 0) frames.
  On the mono cameras it finds almost none.
- **Retargeting without MANO is feasible.** NVIDIA's `ego_recon_to_sharpa.py` reads only 21 joint positions plus
  orientations, in MediaPipe order. See `docs/research/notes/22-hand-reference-contract.md`.

## Staging for Vast (2026-10-20): see `docs/runbook-vast.md`
- **Ready off the clock.** Scripts are written but not yet run on Vast (only `ops/vast.sh offers` was tested on the
  live market):
  - `ops/vast.sh`: launch, list, logs, label and destroy through the API with curl;
  - `ops/box/`: on-start, bootstrap, HF store, stall watchdog, self-destroy;
  - `ops/jobs/smoke.sh` (box 0) and `ops/jobs/day1.sh` (box 1);
  - `pipeline/fetch_data.sh`: the whole 1.47 GB dataset;
  - `pipeline/oracle_poses.py`: the evaluation-only mocap oracle.
- **Changed in the pipeline:**
  - `setup.sh` now also installs CUDA dev headers, both hand venvs and the MediaPipe model, and can pull weights from
    the HF mirror.
  - `pipeline_ep.sh` now defaults to the validated **perc2** (it ran the unvalidated perc4 before), keeps one output
    folder per variant and seed, supports `PERC=oracle`, and resumes training from the newest `state_` checkpoint.
- **Found today:**
  - FlashCHORD resumes (`training.resume=true training.checkpoint_path=<state file>`) and checkpoints every 10,000,384 steps
    (the Sharpa recipe overrides the 5M default; corrected 2026-10-22, note 23); the replay buffer is not saved by default.
  - The Vast image `vastai/pytorch:2.11.0-cu130-cuda-13.2-mini-py313-2026-10-16` matches Colab's torch, CUDA and
    Python.
  - PRO 6000 WS on demand costs $1.45–1.65/h all-in (market on 2026-10-20 afternoon); interruptible from $0.54/h.
- **Storage:** a private HF dataset repo (`HF_STORE` in `ops/config.env`) holds the weight mirror, environment
  snapshots, depth caches and run outputs. Git holds code and summaries. Boxes never push to git.
- **Keys:**
  - Vast key and HF read token → network secrets in the Claude cloud environment.
  - HF write token and GitHub read-only token → Vast account env vars (narrow scope, expiring).
  - Owner checklist: runbook §3.

## Training budget (2026-10-22): see `docs/research/notes/23-training-budget.md`
- Analysis only, from the pinned FlashCHORD code; nothing run. The 250M-step schedule is "validated" by NVIDIA but not
  shown to be the minimum. 49 % of steps are assisted, 31 % unassisted, the last 20 % mostly eval-like frame-0 starts.
- 250M is NVIDIA's 1.97B-step PPO schedule divided by 10, plus a 50M frame-0 stage (recomputed exactly). No paper
  measures where this training plateaus; FlashSAC's own dexterous curves still rise at 50M, so 125M is the test.
- Our references play at twice NVIDIA's speed (motion_speed 1.0 at 20 fps vs 0.5 at 30 fps), so we may need more steps,
  not fewer. The 20M tissue-box result (AUC 0.918) is weak evidence: that policy trained almost only at full assist.
- **Day 1 as written cannot measure a learning curve:** `logging.mode=disabled` records no training metric, and
  `store.sh push-run` keeps only the newest policy. Fixes are listed in note 23 §8 (not made yet).
- A half schedule (all thresholds × 0.5, 125M) composes as a Hydra override (config check only). Proposed A/B:
  {250M, 125M} × 2 seeds on public eps 12, 22, 27 (18 GPU-h, about $9–29). If it holds, a 20-policy cycle drops from
  about 40 to 20 GPU-h.

## Written, not run yet (first things to test)
- `hands_mp.py` → `mkref.py` → `pipeline_ep.sh` → `score_sim.py`. `README_ref.md` lists the checks to do first:
  - pinocchio frame/finger/task counts should be 67/22/11;
  - `daqp` must be available;
  - hand overlay alignment and handedness;
  - URDF warnings;
  - contact fractions;
  - FlashCHORD `load_reference` validation;
  - Hydra quoting of a path containing `=`.
- `perc.py` (perc4): render-and-compare detection check plus reworked VO. Episode 0 with `KF_MIN=250` scored worse
  (0.087): masking leaves fewer features, so a keyframe was added nearly every frame. A rerun with `KF_MIN=120` was
  interrupted. Validate it against perc2 per episode before adopting it.

## Key facts and gotchas
- **Cameras:**
  - Videos are stored upright; do not rotate them.
  - The mono stereo pair is left = `ego_cam_c`, right = `ego_cam_b`, about 75 mm apart. Rectified focal length
    ≈ 600.2 px, baseline 0.0755 m.
  - `ego_cam_a`'s `extrinsics_to_stereo_left` maps cam_a to **cam_b**: X_b = R X_a + t.
  - Stereo frame k pairs with cam_a frame k+1, with a few clips at k+2. cam_a is rolling shutter (31.6 ms per height).
- **Timing rule (note 06):** write `fps=20.0` and exactly N frames, train with `task.motion_speed=1.0` and `sim=rl`
  (20 fps). The default `motion_speed` of 0.5 silently breaks the frame mapping.
- **Quaternions:** the public parquet `pose` is `[x, y, z, qw, qx, qy, qz]`. The kit and evaluator export use xyzw.
- **Detection:**
  - OWLv2 text prompts fail on mono images.
  - FoundationPose's register score is not comparable across masks (a rack fragment scored 143, the true cup 73).
  - Use the scan-matching detector: SAM2 proposals × DINOv2 against 42 grey renders, a 3-D size gate and an
    intensity term.
- **Symmetric objects** (lid, cups, pot body) need spin disambiguation. Note 17 found marker-based correction works
  (marker-only lid AUC 0.977).
- **Room map (note 18):** a public-frames SfM map relocalises all eval clips with about 1–2 mm accuracy, worth about
  +0.06–0.07 AUC over our VO. Not yet integrated.
- **Spoon:** the parametric model is in `spoon/`. The scan-frame rule gives **frame A by a near-tie**
  (P(B) ≈ 0.40–0.45; ≈ 0.17 if the organisers' scan lacks markers). This contradicts note 13's "commit to B". Decide
  from evidence (owner's choice); the owner can check overlays visually on request.
- **Setup gotchas:**
  - Background jobs started from an interactive terminal must use `setsid nohup … < /dev/null`, or apt gets
    SIGTTIN-stopped.
  - FoundationStereo's top-level `Utils` module shadows FoundationPose's; purge it from `sys.modules`.
  - The FoundationStereo cfg needs `vit_size`. New transformers renamed OWLv2's post-processing function.
  - `warp-lang` is required by FoundationPose.
  - Two GPU jobs sharing a card can OOM.
- MediaPipe ≥ 1.x dropped `mp.solutions`; pin 0.10.14. pin 4.1 (pinocchio) has `buildModelFromMJCF`.
- CoACD collision hulls differ by platform; build and evaluate on Linux x86_64.

## GPU plan (from `docs/gpu-rental/report.md`)
- **Vast.ai RTX PRO 6000 96 GB**, about $1.0–1.2/h on demand or $0.5–0.6 interruptible, billed per second.
  - Filters: `cuda_vers>=13.0 cpu_cores_effective>=16 cpu_ram>=65536 reliability>=0.98`, 200 GB disk.
  - Check each host's storage and bandwidth prices.
  - Destroy instances instead of stopping them.
- Fallbacks: RunPod Community $1.69/h, Nebius $1.80/h, RunPod Secure $2.49/h.
- Costs: first public end-to-end test $4–12; first submission (20 policies on 5–10 parallel machines) $35–50;
  campaign about $110.
- To verify on the first host (under $5): throughput (and Max-Q variants), two jobs on one GPU, whether training can
  resume from a checkpoint (needed before using interruptible machines), and restore time.
- **Remote access:** an agent working from a cloud session needs its own SSH key added to the owner's Vast account, and
  the cloud environment needs outbound network access to the rented host. Never commit private keys.

## Running from a Claude Code cloud session (checked against the docs, 2026-10-20)
- **Cost:** included in the owner's Claude plan; usage counts toward the plan's limits; no charge for the cloud VM.
  The VM is small (about 4 vCPU, 16 GB RAM, 30 GB disk, no GPU), which is enough to orchestrate. All GPU work runs on
  Vast.
- **SSH out is blocked (measured 2026-10-20).** The proxy resets non-TLS traffic, including SSH to a real Vast box
  through `ssh3.vast.ai`. Everything runs over HTTPS instead:
  - instances are created through the API; the on-start script clones this repo and runs the job on its own;
  - results go to the HF store; logs come through the Vast API and the label;
  - boxes self-destroy at the end;
  - **interactive access:** `ops/vast.sh exec <run_id> '<cmd>'` runs commands on a box through `rexec.py` behind a
    Cloudflare quick tunnel. The URL and token are in the HF store at `access/<run_id>.json`. This works.
- **Vast API key:** a *network secret* on the environment (host `console.vast.ai`); the `Authorization: Bearer` header
  works. HF uses the same mechanism (host `huggingface.co`). Vast account env vars hold `HF_TOKEN` and `GH_TOKEN`
  (owner swapped in narrow tokens).
- **Permission mode:** Auto mode's classifier blocks the tunnel and `ops/vast.sh create`. The owner runs this work in
  **Accept edits** mode and approves each command.
- **Idle pauses:** the VM pauses after a few idle minutes. The conversation survives, but background shell commands
  and loops do not. Long jobs must therefore run on the GPU box by themselves (nohup + self-destroy + stall watchdog) and
  must never depend on the cloud session staying awake.
- Each session starts from a fresh clone, so commit and push everything. Private repos need the Claude GitHub App
  installed on the repo, or `/web-setup` from a terminal.

## Next actions, in order
1. **Done 2026-10-20:** owner checklist (Vast key, $25 credit, HF store `aebatirel/v2d-store`, narrow HF/GH tokens) and
   the **box 0 smoke test: all checks passed, cost $0.01** (details in the work log). Still untested: the stall
   watchdog's destroy path, `setup.sh` on the Vast image, throughput on the PRO 6000.
2. **Box 1 (2026-10-20, instance 56915259, running):** setup 10 min, IMPORTS-OK, env snapshot
   `pt2.11-cu130-py313-20261020` and weight mirror in the store; perc2 ep12 perception AUC 0.997 on Vast; resume test
   passed; two trainings on one GPU ≈ 45–50k steps/s combined. The first end-to-end score (AUC 0.009) was invalid:
   mkref's table fit picked the floor, so the objects fell 60 cm in sim. Fixed in 30d3633; retraining perc2 + oracle
   since 19:20 UTC (`ops/jobs/train_pair.sh`). Fixed on the way: missing pandas etc. in setup, pinocchio 4.1 call in mkref.
3. Box 1 `ops/jobs/day1.sh`:
   - setup and environment snapshot;
   - perc2 on ep 12;
   - resume test;
   - ep 12 trained twice at once, on perception objects and on the evaluation-only mocap oracle, which separates
     tracking error from robot error;
   - evaluate and `score_sim`.

   Then ep 22 and 27 from the snapshot.
4. Perception fixes, validated on public episodes:
   - detection check (perc4 verify);
   - marker spin for lid and cups;
   - VO drift (room map or loop closure);
   - track recovery (re-registration, bidirectional tracking, full-resolution depth);
   - rest snap and table snap.
5. Spoon: fit the template to the eval videos (`spoon/fit_spoon.py` skeleton), track it, decide the frame from
   evidence; ask the owner for visual checks of overlays.
6. Eval run: perception on the 20 eval videos → references → 20 trainings in parallel → evaluator → kit
   `pack_submission.py` → owner uploads. Commit the exact code first (provenance).
7. Iterate: up to 5 submissions a week, unlimited in the final 3 days. Train several seeds per episode and keep the
   best.

## Expected score (estimates, not measurements)
- Tracking on eval videos: about 0.72–0.81, depending on the spoon.
- First submission after the robot's losses: about 0.60–0.75.
- After fixes: about 0.75–0.85.
- The first public end-to-end test replaces these guesses.
