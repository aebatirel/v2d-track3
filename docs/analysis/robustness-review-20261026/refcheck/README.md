# Is our reference calculation correct? Public-mocap check, 26–27 Oct 2026 (verified)

Owner's question (26 Oct): "can't we first make sure our calculation of the reference is correct with public data?"

**Method:**
- CPU only, $0: the stored public runs in the HF store and the public mocap, scored with the kit's own functions
  (`pipeline/score_registered.py`, the public scan standing in for the hidden scan).
- Five checks, each re-derived by an independent skeptic with its own code: `chain/`, `systematics/`, `timing/`,
  `mapping/`, `scorer/`, plus `verify_*/` and each folder's `VERIFY.md`.
- Below are only the findings that survived verification, with the verifier's corrected numbers.
- **[M]** measured here; **[O]** oracle (uses mocap: shows what an error costs, not a deployable fix); **[H]** hypothesis.
- No eval ground truth exists or was read. Workflow `wf_3df2ac75-ee1`; repo at e2f0a6b during the runs.

**Coverage, the main caveat:**
- 10 of the 20 public episodes have a reference built with our own meshes.
- Only ep11 and ep21 use today's full recipe; the other eight are 21–24 Oct references.
- Episodes 0, 13, 22, 23, 40–45 have perception only.

## 1. What is correct [M]

| Check | Result |
|---|---|
| Metric scale (the kit does not correct it) | our length / true length = **1.004** (0.97–1.02), by two methods. The "depth makes everything 15 % small" worry is falsified. |
| Frame indexing | frame *i* of perception, reference and rollout = mocap row *i* in all 20 episodes and all 747 stored rollouts; no drift |
| Conventions | mocap w-first, our xyzw, object slot order: right everywhere (747/747) |
| Our scorer vs the kit | identical to 4–6 decimals on all 747 public rollouts; the kit's own packer plus official metric files reproduce it |
| The uploaded pack-4 file | bit-exact: rows = rollout poses, meshes = `budget_mesh(library_v3)` (v3x beige cup for eval 8) |
| Support fill, grasp lock | do not change the object path (≤ 1e-4 mm) |
| Hand timing in the references we train on | the robot hand reaches each moving object on time or early (median 9 frames early) |
| Reference vs its perception, 10 episodes, our meshes | 0.915 → 0.902 mean; within ±0.01 on 5 of 10 |

## 2. What is wrong in the reference calculation [M, verified]

| # | Problem | Cost (public) | Eval episodes exposed | Fix status |
|---|---|---|---|---|
| R1 | **mkref's per-object table snap** (`pipeline/mkref.py` ≈ l. 963–967, ±2 cm) also moves objects that rest on another object. ep26: pot pushed 2.6 cm down into the rack in every frame (mocap: 2 cm up). | pot −0.095 to −0.123; snap mean −0.016 over 10 refs (−0.036 over the 9 objects it can move) | 28 (pot into rack), 1 (lid on pot), 14 (cup into rack) | [H] gated snap (skip objects resting on another object); CPU test |
| R2 | **Frame-0 alignment lottery.** The kit aligns the whole scene once, on the anchor object's frame-0 pose. Our frame 0 is the FoundationPose `register()` output, about 2× noisier in orientation than tracked frames (median 1.07° vs ≈ 0.5°). In rollouts, frame 0 is recorded after the first control step (the eval-20 cup falls 14.7 mm in it; the ep31 sweeper turns 11°). | anchor-only frame-0 tilt oracle [O]: +0.03 mean on refs, **+0.18 on ep21** (pitcher, 6°); ±0.01–0.07 per episode | all; largest where the anchor turns or tilts (20, 30, 32, spoon anchors 32/33/35–37) | simple GT-free fixes (frame 0 := frame 1, mean of 0–4) are a lottery: mean +0.000 to +0.006, half the episodes worse. [H] a settled start removes the first-step transient. |
| R3 | **Registration lottery.** The kit registers our submitted mesh to the hidden scan with a fixed seed; the hidden scan is very likely decimated. Near-symmetric meshes can flip 180°. | at Kaggle's own eval seeds, with decimated public scans as stand-ins: the **submitted sweeper flips for eval 30 (3 of 24 hosts) and eval 19 (4 of 24)**, each flip ≈ −0.68 episode AUC (−0.034 Track 3); eval-25 board 2 flips at 1 of 24 | 19, 30 (sweeper is the anchor), 25 | not knowable from here whether Kaggle flips them. [H] a GT-free registration-stability gate, and a sweeper mesh that breaks the near-symmetry. |
| R4 | **Our meshes cost at registration** | pitcher −0.19 to −0.24 (its tracking is fine: 0.91–0.96 with the scan); ep31 rack −0.13 to −0.17 (mostly via the sweeper as anchor); blue cup −0.055 (≈ 1 cm anchor offset along its axis moves the whole scene when it is slot 0); lid −0.06 | 20 (pitcher), 30 (rack via the sweeper), the cup episodes 10 / 14 / 20 / 32 / 33, 1 (lid) | mesh work; any swap must pass R3's stability gate (see §4) |
| R5 | **Resting objects move in our tracks.** ep11 blue cup drifts 5.4 cm while the truth never moves; ep24 board 2 creeps 2.7 cm before it is touched. This also fires the grasp lock's onset anchor early (board 2 held 82 frames early). The anchor also counts a cup's spin about its own axis (fires at frame 1). | freeze oracle [O]: ep11 +0.069, ep24 +0.019–0.022 | 10 / 8 (cups), 25 (boards), 30 | [H] "freeze objects no hand touches" falsified as a general rule (helps drifting objects only); onset anchor: measure swing, not spin |
| R6 | **Half-frame lag.** Our path is ≈ 0.5 frame (23–27 ms) late in every stage, 25 of 25 moving objects, independent of tracker iterations. Already measured on 6 Oct (`docs/research/notes/20-sync-spoon-contact.md` §A6). | pure timing ≈ +0.003 (refs and rollouts); the larger first estimate (+0.007) was half frame-0 alignment noise | all | small; needs retraining to reach the board |
| R7 | **Resting heights off by centimetres** | boards float 2.4–4 cm at the final rest (ep24); ep26 pot 29 mm too deep (half perception, half R1); blue cup 8–13 mm low in all 5 cup episodes; lid 7–9 mm into the pot; snapped racks 7–10 mm high; sweeper 9–11 mm low (v3 too) | 25, 28, 14, 1, 10, 20, 30 | part of R1, R4 |

Killed in verification:
- "the ep21 snap is wrong": the snap is physically about right there; the loss is R2's scoring-frame tilt;
- "ep27 lags the other way";
- "the flattened v3 sweeper fixed its height";
- "boards never flip";
- the timing gain's size;
- "the oracle deltas are upper bounds" (they are not).

## 3. The loss model the review relies on [M unless marked]

- **The 0.979 factor** (true AUC ≈ 0.979 × sim_vs_ref when the reference is sound):
  - right in size: refitted 0.976–0.985;
  - its exact recipe cannot be reproduced;
  - `mapping/calibrate.py` now recomputes it from the store.
- **It holds only where the reference scores R ≳ 0.93.** At high sim_vs_ref the truth follows T ≈ 1.025 × S × R. On
  ep21 (pitcher, R 0.78) T falls 0.17 below 0.979 × S.
- **The review's multiplicative model is biased low** by ≈ 0.02. The implied spoon accuracy is sensitive to that
  scale: 0.80 at a = 1, but **0.73–0.76** at a = 1.015–1.027 [E]. The spoon loss may be larger than assumed, or
  other eval references are worse than their public twins.
- **Leaderboard transfer, pack 3 → 4:**
  - 0.74 of the sim_vs_ref gain, against 0.94–0.97 on public pairs;
  - 2.3–2.7 σ below, one measurement;
  - reading [E]: the changed eval references look ≈ 0.74 accurate, eval 33 about 0.62 ± 0.15.
- **sim_vs_ref** (`pipeline/qa.py`) is not the kit metric: unregistered, no symmetry, 5 cm sphere points. A
  registered variant predicts the truth no better, so it stays.
- **Single-draw mesh A/Bs are unreliable.** The same rollouts with the stable v3 pitcher score 0.667–0.833 across 30
  registration seeds.
- **Pack 5's pitcher swap (−0.0045 on Kaggle).** Explained by the lathe pitcher (`library_v3p`) being
  registration-unstable in yaw: −14° to +7° over 30 seeds, against v3's −2.7° to 0°. At the eval-20 seed the swap is
  negative on 20 of 22 stand-in hosts.
  - The 26 Oct work-log lesson names another cause. This explanation is evidence, not proof: the host is unknown.

## 4. What this means for the next steps (proposals; nothing run)

1. **Registration-stability gate for every submitted mesh** (CPU, GT-free):
   - reject a mesh if more than 10 % of 30 seeds × the stand-in hosts land more than 5° from the median pose;
   - it would have rejected `library_v3p`, and it flags the sweeper (19, 30) and board 2 (25) today;
   - **[H]** a sweeper mesh with its near-symmetry broken removes the flip mode. **Falsified if** it still flips at
     the eval-19 or eval-30 seed on some stand-in host.
   - Whether to test a sweeper change on Kaggle is the owner's call: it would tune on eval results.
2. **Gated table snap** (R1):
   - rebuild the 10 public object paths on CPU and score them;
   - check the start stays stable (`tools/sim_settle.py` on ep21, ep26);
   - **falsified if** the pot's AUC on ep26 stays below 0.93 or a start becomes unstable;
   - then the eval references of 28, 1 and 14 change, which needs retraining (GPU).
3. **A settled, de-noised frame 0** for the anchor object (R2), tested on all 20 public episodes. Simple versions were
   a lottery here, so only a version that is physically motivated (a stable rest pose of our mesh) is worth a test.
   - **Falsified if** the mean does not improve or more than a third of episodes get worse.
4. **Onset anchor on swing, not spin** for cups; hold untouched drifting objects (R5). CPU replay on ep11 and ep24.
5. **Coverage:** build current-recipe references for the 10 public episodes that lack one (perception on GPU,
   ≈ $2–3), so this check covers all 20.
