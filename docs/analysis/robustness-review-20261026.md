# Robustness review and loss budget of the whole flow — 26 Oct 2026 (first pass)

The owner asked (26 Oct): "let's think about how to make this more robust. Let's think in pieces on our whole flow
and think where we are losing what." This is the first pass, meant to be discussed one stage at a time.

**Scope and method:**
- CPU only. No GPU was rented and nothing was uploaded.
- No eval ground truth exists for us, and none was read. Public mocap numbers are quoted from earlier recorded runs.
- Labels:
  - **[M]** measured (source given);
  - **[E]** estimate or derivation from measured numbers;
  - **[H]** hypothesis, with the experiment that would falsify it.
- The helper `robustness-review-20261026/loss_budget.py` re-derives the score split for any pack from its
  `summary.txt` and the leaderboard AUC. Its output on pack 4 is `loss_budget_pack4.json`. On pack 3 it reproduces
  the forensics numbers (implied spoon accuracy 0.813, hidden loss 0.094).

> **Update 27 Oct: public-mocap check of the reference calculation, verified.**
> See `robustness-review-20261026/refcheck/README.md`.
> - **Correct:** scale (1.004), frame indexing, conventions, our scorer vs the kit, the uploaded file.
> - **Wrong:** mkref's table snap on objects resting on other objects (R1); the frame-0 alignment lottery (R2); the
>   registration lottery (R3: the submitted sweeper flips at Kaggle's eval-19 / eval-30 seeds on 3–4 of 24 stand-in
>   scans); mesh registration cost (R4); resting objects moving in our tracks (R5); a half-frame lag (R6, ≈ +0.003);
>   resting heights (R7).
> - **Corrections to this review:**
>   - §9's "the scorer's seeds sit in the majority" holds only for a full-resolution host;
>   - the loss model's multiplicative form is biased low by ≈ 0.02, so the implied spoon accuracy may be 0.73–0.76,
>     not 0.80;
>   - the 0.979 factor is right in size (0.976–0.985) but holds only where the reference scores ≳ 0.93.
> - **New top item for the ranked list:** a registration-stability gate on every submitted mesh (CPU, GT-free).

---

## 0. Summary for the owner

**Where the 0.189 we lose goes (pack 4: AUC 0.8106, our mean sim_vs_ref 0.912):**

| Bucket | Track 3 AUC lost | Kind | Main episodes |
|---|---|---|---|
| Policy does not follow our reference | **0.088** | [M] sum of (1 − sim_vs_ref) / 20 | 10 (0.028), 32 (0.011), 20, 25, 16, 14, 1, 30 |
| Our reference differs from the truth (perception, anchor, mesh) | **≈ 0.10** | [E] (0.082 eval-specific + ≈ 0.02 that public twins also lose) | the 10 spoon episodes ≈ 0.069; pitcher (20) ≈ 0.009; boards (25) ≈ 0.008 |
| Luck of the single packed draw | **+0.027 in our favour** | [M] on 9 episodes with known 5-evaluation means | 14 (+0.25), 33 (+0.15), 25 (+0.10) |

**Three findings change what "robust" has to mean for us:**

1. **Our 0.811 sits on lucky draws.** [M]
   - On the 9 episodes whose 5-evaluation mean is recorded, the packed rollouts are on average +0.027 Track 3 above
     their policies' means.
   - The rules say positions are "provisional until reproducibility verification", and the evaluator's rollouts vary
     between runs (eval 25 s42: 0.62–0.90).
   - [E] If the organisers re-run our checkpoints, expect about 0.79, not 0.81.
   - Robustness here means policies whose five rollouts agree, not more draws.

2. **The sponsor runs a further held-out evaluation after close, on undistributed data**
   (`docs/research/track3-requirements.md`).
   - Every fix marked * in the flow chart was applied by hand, to the episodes where forensics saw the problem:
     re-proposal, track guard, identity rule, arc foot, carve.
   - On held-out data only what runs by default runs. Turning each fix into an automatic, GT-free trigger is
     therefore the robustness work that matters, beyond the leaderboard.

3. **The largest lever cannot be measured.**
   - The spoon's ≈ 0.07 hidden loss is solved for, not measured: there is no public spoon mocap.
   - It moved from 0.813 to 0.800 implied accuracy between packs 3 and 4 while nothing about the spoon changed. That
     drift is the model's error bar.
   - Any spoon work needs a proxy measurement first (§2.4), or it is spending on a number we cannot see.

**Recommended first discussion piece:** stage 8 (choice and pack) together with stage 7 (learner variance).
- Reasons: they are cheap (evaluations cost seconds), GT-free, and they protect both the leaderboard and the
  verification re-run.
- Then the automatic-trigger list (§10), which matters for the held-out evaluation.

---

## 1. Input

**What goes wrong:**
- Nothing measured yet.
- Eval videos match the kit roster (eval 1: 335 frames).
- Object names and slot order come from the kit for eval episodes too.

**Cost:** ≈ 0 [E].

**Fragility:**
- The slot order decides the scorer's anchor object (the lowest slot without a symmetry axis). Our pipeline must
  reproduce it exactly. It does today, but nothing asserts it.

**Robust fix:**
- An input manifest check at the start of every job: frame counts per camera, the roster's names and order, and the
  anchor object the scorer will use, written into the run.

---

## 2. Perception

The most failure-prone stage historically. Every public failure started at frame 0.

### 2.1 Frame-0 detection

**What goes wrong [M]:**
- Proposals on the wrong thing:
  - ep26: the rack was matched to floor tape → AUC 0.065 → 0.988 with the compactness prior;
  - ep11: beige cup → 0.102 → 0.898 with the on-table rule;
  - eval 30: the sweeper on the wrist, fixed by re-proposal.
- Below-table registrations: ep0's lid, 0.496 → 0.964 with the track guard.

**Cost on eval today:** unknown, inside the ≈ 0.10 hidden bucket [E].

**Fragility:**
- Each rule was added after a failure was seen.
- The re-proposal rule was applied to eval 30 only.
- The rules interact (prior, on-table rule, re-proposal, guard), and their joint effect on all 20 public episodes
  was last measured as a set of A/Bs on different days.

### 2.2 Stereo depth and 6-DoF tracking (our library meshes)

**Public registered AUC vs mocap, 8 episodes, today's defaults:** mean 0.782 [M] (work log 25 Oct 01:44 UTC).

| Episode | AUC | Note |
|---|---|---|
| ep0 | 0.964 | |
| ep11 | 0.898 | |
| ep12 | 0.966 | |
| ep18 | 0.938 | |
| ep21 | 0.684 | pitcher |
| ep23 | **0.041** | board identity swap |
| ep24 | 0.812 | boards |
| ep31 | — | not listed |

Without ep23 the mean is about 0.89.

**Mesh sensitivity [M] (damaged-scan test, 21 Oct):**

| Damage | Mean AUC |
|---|---|
| clean | 0.987 |
| convex hull | 0.947 |
| bottom missing | 0.904 |
| 3 mm noise | 0.825 |
| 5 mm thicker | 0.608 |

Scale errors cost nothing.

**Fragility:**
- **GPU nondeterminism in perception [M]:**
  - eval 25's two perception runs named the boards oppositely ("close to a coin flip");
  - ep12 0.967 vs 0.966 between identical runs.
  - A rerun of perception can change an eval reference silently.

### 2.3 Camera odometry

**What goes wrong:** no isolated measurement in the repo. The 21 Oct answer to the owner listed "camera drift" as an
open item.

**Cost:** unknown [E: small on the public twins, which score 0.94–0.97 per object when detection is right].

### 2.4 Identity of look-alike objects

**What goes wrong:**
- Boards, measured [M]:
  - ep23 is near zero from a frame-0 swap;
  - eval 25 was swapped in its stored reference;
  - the knob rule (`pipeline/identity_fix.py`) flagged it and repaired ep24's 24 Oct track, 0.029 → 0.706.
- Cups: the blue and beige cups differ in colour, so no swap has been seen.

**Fragility:**
- The identity rule is wired only into `eval_idfix.sh` (eval 25). Other jobs do not call it.

### 2.5 The spoon (10 of 20 episodes, 32.5 % of object weight)

**Inferred accuracy:** ≈ 0.80–0.81 [E].
- `loss_budget.py`: per-object public accuracy midpoints, solved so that the total equals the leaderboard.
- That is about 0.069 of hidden loss in the spoon episodes.

**Sensitivity [M] (`docs/research/spoon-2026-10-25/`):**
- A 10° frame-0 roll costs 0.09–0.28 in the five spoon-anchored episodes (32, 33, 35, 36, 37).
- Measured random roll is 2–6°, so ≈ 0.03–0.15 per anchored episode [E].
- Registration of our template: 0 flips in 300, median error 1.0°.

**What cannot be seen:**
- a systematic template or tracker bias;
- depth along the camera axis (no exo cameras: ego a is 4 cm from c);
- tracking while the spoon is hidden in the pot or cup (3, 5, 6, 33).

### What would make perception robust and automatic

1. **One perception config, frozen, with all rules on by default, scored once on all 20 public episodes.**
   - Today's evidence is 8 episodes from 25 Oct plus older single-rule A/Bs.
   - It gives one per-object accuracy table for the current pipeline, which replaces the "midpoints" in the
     hidden-loss model.
   - Uses public mocap; ≈ $2–3 GPU.
2. **Identity rule as a default step** in every perception job, GT-free: it already exists, and is a no-op when no
   swap is found.
3. **Perception repeatability gate:** run perception twice per eval episode (or keep both runs). If identity, anchor
   object or frame-0 anchor pose disagree beyond about 1 cm / 2°, flag the episode and use a deterministic
   tie-break, for example the identity rule's score and the rest-averaged pose.
   - **[H1]** Nondeterminism changes identities or anchor poses on some episodes.
     **Falsified if** three repeated perception runs on the 20 public episodes agree on identity everywhere and on
     the anchor's frame-0 pose within 1 cm / 1°. (GPU ≈ $3; public mocap tells which run is right.)
4. **Spoon proxy measurement before any spoon spend.**
   - **[H2]** Our tracker's frame-0 roll and tilt error on public *thin, elongated* objects (sweeper handle, dust pan
     handle) predicts the spoon's.
   - Measure the anchor-pose error vs mocap per object class on the public episodes (CPU, stored tracks + mocap).
   - **Falsified if** the sweeper and dust-pan frame-0 errors are under 2° yet the board still implies spoon
     accuracy ≤ 0.85. The loss would then sit elsewhere: hidden-phase tracking, or a pitcher or boards worse than
     their twins.

---

## 3. Hands

**What goes wrong [M]:**
- ep12: hand identity swaps at hand-overs (greedy linker). Viterbi fixed ep12 but followed spurious hands
  elsewhere, so greedy stays.
- ep24: during grasps the 3-D lift squashes the hand into the held object, because stereo depth at the hand pixels
  hits the board.
- The fit scale sits at its lower clamp (hand 12 cm wrist → middle tip). Unexplained.
- ep35: late first detection gave a 60 cm/s lead-in (fixed: `--lead_in_speed 0.2`).

**Cost:** hands are not scored. Their errors show up as policy loss, through a reference the robot cannot follow,
and cannot be separated today [E].
- Suspect: the two-handed holds of 32 and 33 (0.011 + 0.003 of policy loss, larger on average draws).

**Fragility:**
- No automatic hand-quality gate.
- `ref_report` flags WRIST-JUMP but nothing acts on it.

**Robust fix (GT-free):**
- a per-episode hand QA score (palm steps > 4 cm, bone-length consistency, frames inside objects) written into
  every run;
- episodes above a threshold get the contact retarget's stricter settings.

**Public measurement:**
- The public parquets carry no hand mocap: `observation.objects` holds object poses and a visibility flag only
  (dataset `track_3/README.md`, checked 26 Oct). Hands cannot be scored against truth on any episode.
- The GT-free proxy above is therefore the only measurement of this stage.

---

## 4. Reference (retargeting, contact anchoring)

**What goes wrong [M]:**
- The object path is preserved: reference vs mocap 0.993–1.000 on ep12, ep27 and ep2 when perception is right.
- Losses come from geometry the reference asks for:
  - the hull census (forensics §3) finds the reference pushing objects into the collision copies: 14 (72 cm³),
    1 (51), 28 (39), 8 (38), 30 (29), 25 (12), 10 (112);
  - resting heights are off: boards float 2–2.5 cm on ep24; the pot sits 29 mm deep in the rack on ep26.

**Cost:** part of the policy loss in 14, 28, 30 and 1 (together ≈ 0.016 [M]); the share due to geometry is [E].

**Fragility:**
- The hull census is a forensics tool. It does not run in the pipeline.

**Robust fix:**
- Run `tools/hull_census.py` and the support-fill stability report as a **gate inside mkref**, on every reference.
- Above a threshold, the episode is routed to the carve / support-fill step automatically (§5).

**Public measurement (CPU):**
- resting height and in-container depth, reference vs mocap, at rest frames on the 20 public episodes;
- this calibrates the gate's threshold on data with truth.

---

## 5. Simulator assets (meshes, collision copies, support fill, carve)

**What goes wrong [M]:**
- open shells: the beige cup fell 6/6 at rest;
- filled cavities: the blue cup is solid over its lower 37 %, and CoACD hulls fill slots and holders;
- the pitcher lacks half its base (arc foot added);
- the 0.3 kg placeholder mass.
- The carves fixed eval 25 in simulation (board 2: 104° → 0.5°, CPU) and made eval 10's cups stand (floor 0.448).

**Cost:**
- eval 10's policy loss is 0.028 [M]. Its geometry now stands, and the stacking is still not learned.
- Placements 14, 28, 30, 1: ≈ 0.016 [M] total policy loss, part of it geometry [E].
- On the hidden side, our submitted meshes cost registration accuracy: the pitcher twin scores 0.57 with our mesh
  vs 0.95 with the scan [M]. CD-O is 11th.

**Mesh library lineage (checked 26 Oct by md5 of `meshes/library_*/*.glb`):**

| Library | Date | What changed | Status |
|---|---|---|---|
| v1 | 21 Oct | first reconstructions from the public videos | dropped: pot and dust pan reached 3.5–5.5 cm below the table |
| v2 | 21 Oct | pot and dust pan rebuilt (`--below_carve`) | identical to v3 except the sweeper |
| v3 | 22 Oct | v2 + the sweeper's underside flattened (it fell over) | **submitted** |
| v3x | 25 Oct | v3 + the v5 beige cup | submitted for eval 8 |
| v4 | 24 Oct | v3 + flattened boards | dropped: ep24 perception 0.795 → 0.029 |
| v5 | 25 Oct | full rebuild without the public scans (owner directive 24 Oct) | not adopted: lid, both boards and pot failed to build; CD-O worse than v2 for 4 of 5 objects; only the beige cup improved |

- v1–v4 were fused along tracks templated on the public scans, with the scans carving the other objects (work log
  22 Oct; organiser email question 3, still not sent). v5 is the scan-free rebuild, and it came out worse. So "v3 is
  older" is not the problem. The unresolved questions are v3's provenance and whether a scan-free library can match it.
- **Stale defaults:** `ops/jobs/glock_public.sh` (public twins) defaults to `library_v2`, `ops/jobs/perc_sweep.sh`
  hard-codes `library_v2`, and `ops/jobs/own_eval.sh` defaults to `library_v1`. The eval, pack and video jobs default
  to v3. Today v2 differs from v3 only in the sweeper, so public twins of evals 19 and 30 (ep18, ep31) may have
  been validated on a sweeper we do not submit. Fix: one `meshes/current.json` manifest (the adopted mesh per object,
  with provenance), read by every job; a job refuses another library unless it is named explicitly.

**Fragility (new finding):**
- **The pack builds one `/content/assets` per pack, keyed by object name, from `ASSET_PIECES`, which is set by
  hand** (`ops/jobs/pack_eval.sh` lines 20–33).
- Nothing checks that a checkpoint is evaluated on the collision copy it was trained on.
- It is harmless today only by coincidence. The standard-learner references that use the shared folder (1, 10, 19,
  25, 28, 30) share no carved object. Grasp-lock references carry their own copies.
- **It would break** with:
  - a rack carve for 14, 28 and 30: the same object, needing different cuts per episode;
  - a standard learner on any blue-cup episode (14, 20, 32, 33), which would silently get eval 10's hybrid cup.
- Fix before extending the carve: per-episode asset folders named in the reference, plus a hash of the collision
  pieces stored with the checkpoint and checked at pack time.
- **Per-episode decisions:** support fill, arc foot and carve were each switched on for the episodes where
  forensics saw a failure.

**Robust fix:**
- An automatic, GT-free asset step per episode:
  1. stability certificate at every observed rest (exists: `support_fill.py`);
  2. hull-census conflict above about 10 cm³ → swept-volume carve of the container's collision copy (exists for
     slots and cups; generalise);
  3. CPU FlashCHORD check (`tools/carve_fc_test.py`) as the pass/fail gate, with a rule fixed in code instead of
     per episode.
- **[H3]** The automatic step reproduces today's hand-made choices: it carves 10 and 25, adds the arc foot to 20,
  and leaves 3, 5, 6, 15, 16, 19 and 20's cup alone.
  - **Falsified if**, run blind on the 20 eval references and the 20 public ones (CPU, ≈ 2–3 h), it misses one of
    today's fixes or fires on an episode whose rollouts show no geometry problem.

**Public measurement:**
- Same simulator check with our mesh vs the public scan on the public twins (CPU harness, driven along the mocap
  path).
- The difference isolates the asset loss from the policy loss per object class.

---

## 6. Learners (grasp lock eval_both / frozen; standard learner)

**What goes wrong [M]:**
- two-handed carries (32, 33);
- release into holders (16, 15);
- grip slip in carries (3);
- learning the stack (10);
- **high rollout variance** of some policies:

| Policy | 5-evaluation results | Spread |
|---|---|---|
| eval 33 s43 | 0.277–0.935 | sd 0.255 |
| eval 25 s42 | 0.62–0.90 | sd 0.103 |
| eval 14 | — | sd 0.17 |
| eval 5 (older s42) | one collapse in 5 | — |

**Cost:** ≈ 0.05 of the 0.088 policy loss sits in episodes whose geometry is clean (32, 33, 16, 15, 3, 19, 20) [E].

**Fragility:**
- The 0.9 gate decides whether the standard learner runs at all.
- Grasp-lock checkpoint curves jump about 0.10 between checkpoints [M], so the best checkpoint is partly chance.
- One seed per episode for most episodes.

**Robust fix:**
- Drop the gate: both learners everywhere (already proposed in the flow chart).
- Prefer policies with low rollout spread (§7).
- **[H4]** A bimodal policy collapses because of a specific start-state sensitivity, so more seeds of the same
  recipe give a tighter policy only by luck.
  - **Falsified if** the eval-32 seeds 44–46 now running show spreads (sd over 5) comparable to s42 (0.045). Then
    tight policies are common and the choice rule can simply prefer them.

---

## 7. Choice (highest 5-evaluation mean)

**What goes wrong [M]:**
- With n = 5, a mean's standard error is sd / √5. For eval 33 s43 that is ≈ 0.11.
- Two choices made today were within noise:
  - eval 10: s42 0.453 vs s43 0.452;
  - eval 33: s43 0.785 vs s42 0.773, while s43 collapses in 1 of 5 and s42 has sd 0.053.
- A 1-in-5 collapse rate has a 95 % interval of about 0.5–72 %.
- The rule winner of eval 10 was unavailable: its checkpoint had been pruned (fixed in `store.sh`).

**Cost:** small in expectation [E]. The risk is in the variance at a re-run: s43's chance of a sub-0.3 draw is real.

**Fragility:**
- the winner's curse (the maximum of noisy means is inflated);
- no tie-break rule;
- no check that the winner's files exist before the boxes are destroyed.

**Robust fix (cheap: an official evaluation takes about 15 s):**
- **Adaptive n:** evaluate each candidate 5 times. When the top two are within 2 standard errors, evaluate both
  to n = 20.
- **Pre-registered tie-break:** the lower sd, or the higher 20th percentile.
- **Verify, while the box is alive,** that the winner's checkpoint, reference and assets are in the store (sha256)
  before self-destroy.
- **[H5]** The expected value of our current pack is about 0.79, not 0.81.
  - GT-free measurement: 10 official evaluations of each of the 20 packed checkpoints. That is ≈ 200 × 15 s ≈ 1 h
    GPU, ≈ $1.5–2.
  - **Falsified if** the 20-episode mean of those means is ≥ 0.905 (the packed mean 0.912 minus 0.007).
  - This measures our exposure at verification and finds every high-variance episode at once.

---

## 8. Pack (fresh rollout, keep-by-sha)

**Incidents so far [M]:**

| Incident | Cost | Status |
|---|---|---|
| `cp -n` kept the first pack's rollouts for 3, 5, 15, 16 | ≈ −0.005 [E] on pack 3 | fixed: empty folder + sha check |
| Pruned checkpoint: the rule's winner was unpackable | ≈ 0 this time | fixed |
| `ops/vast.sh` defaulted to the day-1 commit | $0.03 | fixed: local HEAD, must be on origin |
| Video job: `hf download` with three patterns fetched nothing | $0.45 | fixed |
| The replay path (`view_policy.py`) is not the evaluation harness: eval 1 replay 0.529 vs official 0.89–0.93 | misleading videos | open |
| Interruptible boxes were paused within ≈ 10 min | $0.4 | the restart path is not pause-safe |

**Fragility:**
- The pack is assembled from environment variables (`KEEP_RESULTS`, `ASSET_PIECES`, PICKs) typed per pack. Each
  incident above was a mismatch between what a rule chose and what a script did.

**Robust fix: a manifest-driven pack.** One committed file per pack lists, for each episode:
- the chosen candidate and the rule record (work-log line);
- checkpoint sha256;
- reference md5;
- collision-asset hash;
- the source of the rollout (fresh, or kept from pack N).

The pack refuses to start on any missing file or mismatch, and writes the same manifest back with the rollout's sha
and score. Most of the checks exist in pieces; this collects them in one place.

**Replay fix:**
- record body poses inside the harness rollout (proposed 26 Oct), so videos show what was scored.

---

## 9. The kit's metric (registration and anchor alignment)

**What goes wrong:**
- Mesh ICP to the hidden scan, then the whole scene is rotated onto the anchor object's frame-0 truth.
- Errors in our frame-0 anchor pose rotate every later frame [M, kit code].
- Registration flips:
  - spoon 0/300 [M];
  - sweeper: 4 of 40 random seeds flip, but the scorer's seeds sit in the majority [M];
  - boards flipped in 0–25 % of seeds depending on small parameter changes (21 Oct) [M].

**Cost:** spoon anchor ≈ 0.03–0.15 per anchored episode [E]; the rest is inside the hidden bucket.

**Fragility:**
- **The scorer's seeds are fixed.** Any change of a submitted mesh (a new library, the lathe meshes for CD-O) can
  move a registration into a flipped mode silently.
- The sweeper and spoon checks were one-off scripts.

**Robust fix (GT-free; it cannot see the true scan, so it is a self-consistency test):**
- A **registration-stability gate** on every submitted mesh before upload.
- Register it with the kit's `_register_object_body` to perturbed copies of itself and to our other library
  versions, over 40 seeds and the scorer's seeds.
- Refuse if the scorer's seeds land outside the majority mode.

**Public measurement:**
- The same gate on public objects, where flips against the true scan can be counted, tells how well
  self-consistency predicts real flips.

---

## 10. GT-free gates that would turn today's hand-applied fixes into defaults

| Fix (today applied to) | Automatic trigger | Exists? |
|---|---|---|
| Re-proposal (30) | frame-0 pose implausible (below the table, inside a hand mask, far from the others) | rule exists; wire it in as a default |
| Track guard (8, 14, 20, 32, 33) | per-frame plausibility flag | default since 25 Oct |
| Identity rule (25) | knob-rule score; a swap ranks better than as-tracked | code exists; only in `eval_idfix.sh` |
| Arc foot / support fill (20, 8) | `support_fill` reports UNSTABLE at a rest | on via SF=1, but **SF=0 on carved runs** |
| Carve (10, 25) | hull census > 10 cm³ sustained over ≥ N frames, then the CPU FlashCHORD check | census and carve exist; no trigger |
| Standard learner (1, 19, 25, 28, 30) | always (drop the gate) | proposed |
| Second seed | 5-evaluation sd > 0.05 or collapse in ≥ 1 of 5 | not built |
| More evaluations | top two within 2 standard errors | not built |
| Registration gate | scorer seeds outside the majority mode | not built |

"Exists" was checked in the scripts named in the work log, not by re-running them.

**[H6]** The table, run blind on all 20 public episodes end to end, does at least as well against mocap as today's
hand-tuned public runs.
- **Falsified if** the public mean drops by more than 0.01 against the best per-episode configuration recorded.
- This is also the reproducible single command the rules ask winners for.

---

## 11. Ranked list (gain, cost, time to the 4 Nov 22:00 UTC freeze: about 9 days)

Gains are Track 3 AUC estimates [E] unless marked. "Protects" means the item lowers risk at verification or on the
held-out data rather than adding leaderboard points.

| # | Item | Expected gain | Cost | Time |
|---|---|---|---|---|
| 1 | **H5: 10 evaluations of all 20 packed checkpoints** (exposure check; finds high-variance policies) | information; protects about 0.02 | ≈ $2 GPU | 1–2 h |
| 2 | **Adaptive-n choice + tie-break + winner-exists check** in the jobs (§7) | +0 to +0.01; protects | CPU code, half a day | before the next batch |
| 3 | **Manifest-driven pack + per-episode collision assets** (§5, §8) | protects; prerequisite for #6 | CPU code, 1 day | before the next pack with new carves |
| 4 | **Variance-targeted seeds** for the episodes #1 flags (likely 33, 25, 14): extra seeds, choose by mean with the tie-break | +0.005 to +0.015 in expectation; stabilises the 0.027 of luck | ≈ $2 per grasp-lock seed, ≈ $3 per standard seed | 1–2 days |
| 5 | **Automatic triggers (§10) + H3 + H6 public run** | protects held-out; ≈ 0 on the leaderboard | CPU 1–2 days + ≈ $5–8 GPU for H6 | 2–3 days |
| 6 | **Placement carve for 14, 28, 30, 1** (forensics item 4), only after #3 | +0.005 to +0.012 | CPU 2–3 h + ≈ $15–20 | 2 days |
| 7 | **Spoon proxy measurement (H2) + perception repeatability (H1)**, before any spoon spend | decides whether the +0.045 lever is real | CPU + ≈ $3 | 1 day |
| 8 | Eval 10 stacking (grasp lock on the carved cups: running now) | +0.01 to +0.025 if it learns the stack | running (≈ $10.5 batch) | today |
| 9 | Eval 32 seeds 44–46 (running now) | +0.002 to +0.01 | running | today |
| 10 | Pitcher mesh / track (20) | ≈ +0.009 | mesh work + 1 rerun | 2 days |
| 11 | One frozen perception config scored on all 20 public episodes (§2) | recalibrates the hidden-loss model | ≈ $2–3 | 1 day |

**Why this order:**
- Items 1–3 are cheap and make every later batch trustworthy.
- Item 4 turns today's luck into expected value.
- Item 5 is what the held-out evaluation will run.
- Item 7 must come before spending on the largest but invisible lever.

## 12. Open questions for the owner (one per discussion piece)

1. **Choice and pack (§7–8):** run H5 (≈ $2, 1–2 h) to see how much of 0.811 is luck?
2. **Variance:** for the final pack, prefer a slightly lower mean with a much lower spread? A pre-registered
   tie-break only, or a stated penalty on sd?
3. **Held-out evaluation:** spend 2–3 days making the fixes automatic (§10), even though it adds little to the
   public board?
4. **Spoon:** accept the proxy-first rule (H2 before any spoon re-reference spend)?

## Sources

- `results/submissions/2026102*/{README.md,summary.txt}`
- `docs/analysis/forensics-20261026/README.md`
- `docs/analysis/episode-scoreboard-20261026.md`
- `docs/research/seed-race-20261026/README.md`
- `docs/research/spoon-2026-10-25/README.md`
- `docs/research/track3-requirements.md`: the held-out evaluation, verification, determinism
- `docs/work-log.md`: entries of 21, 25 and 26 Oct cited inline
- `ops/jobs/pack_eval.sh`, `pipeline/make_assets.py`: asset handling

**Caveat on the 0.979 factor:** it comes from the forensics (57 public policy means, 10 episodes), but no script in
the repo recomputes it. Committing that calibration script is part of item 11.
