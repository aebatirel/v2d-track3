# Score and loss map, 27 Oct 2026

`main:` below means `origin/main-bsky37`. Labels: [M] measured, [E] estimate or model output, [D] derived by arithmetic from measured numbers. No eval ground truth exists in the repo, so every eval number is either our own metric (sim_vs_ref, the rollout scored against our own reference) or a model estimate of the true score.

## 1. Leaderboard state

| Board | Our best | Pack | Last recorded rank | Source |
|---|---|---|---|---|
| AUC | **0.81391** | 6 (26 Oct 17:15 UTC) | **5th** | `main:results/submissions/20261026-track3f/*.kaggle-receipt.json`, `main:STATUS.md` (27 Oct 06:15) |
| SP-SR | 0.85 | 4, 5, 6 | not recorded after pack 3 (0.80 was 5th, tied) | receipts 3d/3e/3f; `main:results/submissions/20261025-track3c/README.md` |
| MP-SR | 0.65 | 4, 5, 6 | not recorded (0.60 was 4th) | same |
| RPE | 3.94176 cm | 6 | not recorded (4.59 was 4th) | 3f receipt |
| MPPE | 2.92493 cm | 6 | not recorded (3.29 was 4th) | 3f receipt |
| CD-O | 0.40188 cm | 3 (not re-uploaded since) | 11th | 3c receipt and README |

**Teams above us on AUC** [M], as recorded at 26 Oct 11:00 UTC in `main:results/submissions/20261026-track3d/README.md`:

| Rank | Team | AUC |
|---|---|---|
| 1 | richchentw | 0.932 |
| 2 | SoySauceChicken | 0.902 |
| 3 | Zihao Guo | 0.865 |
| 4 | DDD | 0.82716 (since 26 Oct 03:36 UTC) |
| 5 | us | 0.81391 |
| 6 | SRL | 0.752 |

- The leaders' scores on the other boards are only known from the stale 25 Oct 07:20 UTC snapshot (`main:docs/research/leaderboard-20261025-0720utc.json`):
  - richchentw: SP 1.00, MP 1.00, RPE 1.34, MPPE 1.24;
  - Zihao Guo: 1.00, 0.85, 1.94, 1.83;
  - SoySauceChicken: 0.90, 0.80, 1.97, 1.64.
- CD-O leaders are 0.112 (Panav Raaj) and 0.154 (richchentw) (`origin/claude/bold-albattani-6qmxsv:docs/research/mesh-2026-10-26/README.md`).

**Submissions:**
- We made 6 uploads to each pose board: 24 Oct ×1, 25 Oct ×2, 26 Oct ×3. CD-O was uploaded twice (packs 1 and 3). Source: receipts in `main:results/submissions/*`.
- The recorded rule is "5 submissions/week per competition, unlimited in the final 3 days; 2 final picks" (`main:docs/research/track3-requirements.md:37`).
- We made 6 uploads in 3 days and all succeeded, so the recorded rule may be stale or count differently. The repo keeps no count of submissions left.

**Freeze and verification:**
- The leaderboard freezes 2026-11-04 17:00 EST, which is 22:00 UTC; winners are announced at CoRL on 12 Nov (`track3-requirements.md`).
- Positions stay provisional until reproducibility is verified, and the sponsor runs a further held-out evaluation.
- The owner said the deadline is the owner's concern (`origin/claude/bold-albattani-6qmxsv:STATUS.md:22`).

**Luck exposure:**
- Pack 6's packed rollouts average 0.9164 sim_vs_ref [M]. The same policies' 5-evaluation means average 0.883 [D, computed here from the `main:docs/work-log.md` means]. So the packed draws sit +0.033 above expectation.
- At the measured transfer of 0.74–0.78 (`refcheck/README.md` §3; pack 4→6: +0.0043 sim_vs_ref gave +0.0034 AUC [D]), a re-run of our checkpoints would score about 0.79 [E]. This matches robustness review H5.

## 2. The 20 eval episodes

Notes on the columns:
- **Packed** is pack 6's sim_vs_ref (`main:results/submissions/20261026-track3f/summary.txt`) [M, our reference].
- **Mean5** is the 5-evaluation mean of the same checkpoint (`main:docs/work-log.md`, 24–26 Oct) [M].
- **Est. true** is packed × the public per-object accuracy, with the spoon solved so the total matches the leaderboard (implied spoon accuracy 0.798). It comes from `main:docs/analysis/robustness-review-20261026/loss_budget.py` rerun on pack 6 [E].
- Submitted meshes are library_v3 everywhere except eval 8 (v3x). Simulator-only collision changes are noted per row.
- Wrist: grasp-lock runs use `sharpa_hands_mid` (kp 400) (`main:ops/jobs/glock_public.sh`). Standard-learner runs (variant mcks) use the default kp 25 wrist (`main:ops/jobs/train_runs.sh`; read from the code, not from checkpoint configs).

| Eval | Objects | Packed | Mean5 | Est. true | Recipe / seed / sim mesh | Main loss | Tried |
|---|---|---|---|---|---|---|---|
| 1 | pot, lid | 0.920 | 0.912 | 0.890 | std learner (std0116, 200M), kp 25 | policy: pot spikes 9 cm in the carry; lid inside the pot's hulls (51 cm³); twin lid registration −0.06 | grasp lock 0.297 → std |
| 3 | pot, spoon | 0.942 | 0.9285 | 0.833 | grasp lock s43 (seed43-61101f5) | spoon (hidden in the pot while stirring); pot slips 10 cm in two carries | s42 0.851 → s43; packing bug fixed |
| 5 | pot, spoon | 0.960 | 0.966 | 0.848 | grasp lock s43 | spoon pose (hidden) | s42 0.855 (one collapse) → s43 |
| 6 | pot, spoon | 0.971 | 0.982 | 0.859 | grasp lock s42 (evB) | spoon pose (hidden) | one seed |
| 8 | beige cup, pot | 0.978 | 0.9705 | 0.929 | grasp lock eval_both (evb0810), v3x beige cup | little | track guard, v5 cup; frozen recipe 0.76 |
| **10** | blue + beige cup | **0.456** | 0.4539 | 0.429 | grasp lock eval_both s42 (gl10A2), hybrid carved cups `meshes/carve/ev10` | **policy: stack not learned**; RL learns to avoid the cups; floor 0.448 | carve std s42/s43 0.453/0.452; glock A/B 0.454/0.438; early checkpoints (C′ 0.4528; B′ stopped early, 0.446–0.465 per evaluation); zero-init residual 0.4459; CPU object-ILC 0.632, not robust; the plan's zero action scores 0.663 but zero-residual policies are excluded by the 22 Oct rule |
| 14 | blue cup, rack | 0.909 | **0.66** | 0.864 (0.63 at the mean) | grasp lock eval_both (evb1420) | policy variance (sd 0.17); reference pushes the cup into the rack (72 cm³); table snap (R1) | frozen 0.629, std 0.619; placement carve proposed, not run |
| 15 | rack, spoon | 0.947 | 0.941 | 0.827 | grasp lock s43 | spoon turns 46° on release; spoon hidden | s42 0.901 → s43 |
| 16 | rack, spoon | 0.908 | **0.8045** | 0.794 | grasp lock s43 | spoon flips on release into the holder (128°); spoon hidden | std 0.769; s42 0.795 |
| 19 | sweeper, dust pan | 0.928 | 0.935 | 0.886 | std learner (std1928), kp 25 | 2–4 cm off in the sweep; **sweeper registration flips at Kaggle's seed on 4/24 stand-in hosts** (each flip −0.034 Track 3; whether Kaggle flips it is unknown) | glock 0.653 → std |
| 20 | blue cup, pitcher | 0.895 | 0.892 | **0.720** | grasp lock eval_both (evb1420), arc foot (sim only) | **mesh/frame:** pitcher registration (twin: our mesh 0.571 vs scan 0.95; R4 −0.19 to −0.24); frame-0 lottery (+0.18 oracle on ep21); pouring hand off camera 1.5–1.7 s (note 23 C3) | arc foot (twin 0.657 → 0.772); lathe pitcher on Kaggle **−0.0045 [M]**, reverted; frozen 0.889, std 0.146 |
| 25 | two boards | 0.894 | **0.792 ± 0.103** | 0.733 (0.65 at the mean) | std learner s42 + slot carve `meshes/carve/ev25`, identity fix | policy variance; board accuracy ≈ 0.82; board 2 flips on 1/24 hosts; boards rest 2.4–4 cm high | identity fix; carve s42/s43 0.792/0.474; glock 0.376; frozen 0.297; v4 boards dropped |
| 28 | rack, pot | 0.929 | 0.935 | 0.892 | std learner (std1928), kp 25 | pot spike 6 cm; pot set 39 cm³ into the rack; R1 snap (ep26 twin pot −0.10 to −0.12) | glock 0.694 / s43 0.668 → std |
| 30 | sweeper, rack | 0.923 | 0.919 | 0.881 | std learner (std30, ev30rp reference) | sweeper 1.9 cm / 11° off and starts inside the rack mesh; **flip risk (3/24 hosts)**; R4 rack-via-sweeper anchor −0.13 to −0.17 on twin ep31 | detection re-proposal; glock 0.72 (bimodal) → std |
| 32 | blue cup, spoon | 0.866 | 0.803 ± 0.105 | 0.757 | frozen grasp lock s46 | **policy:** cup tips and falls during the lift (17 cm spike); spoon anchor roll | seeds 42–46: 0.779 / 0.702 / 0.397 / 0.634 / 0.803; eval_both 0.497 |
| 33 | blue cup, spoon | 0.932 | **0.785 ± 0.255** | 0.814 | frozen grasp lock s43 | two-handed hold for 270 frames; in reality the spoon scoops inside the cup; one collapse in 5; anchor roll | s42 0.773 vs s43 0.785 |
| 35 | spoon | 0.983 | 0.9915 | 0.784 | grasp lock (kp 400 wrap) | spoon perception / anchor (hidden) | — |
| 36 | spoon | 0.991 | 0.9935 | 0.791 | grasp lock | same | — |
| 37 | spoon | 0.998 | 0.998 | 0.796 | grasp lock | same | — |
| 38 | dust pan | 1.000 | 0.9997 | 0.950 | grasp lock | — | — |

Sources for the causes:
- `main:docs/analysis/forensics-20261026/README.md` §2–3
- `main:docs/analysis/episode-scoreboard-20261026.md`
- `main:docs/analysis/robustness-review-20261026/refcheck/README.md` §2 (R1–R7)
- `main:docs/work-log.md` (26–27 Oct)
- current branch `docs/research/notes/23-carry-control-force.md` §C3

The est.-true column for the spoon episodes is the model's residual, not a measurement.

## 3. Loss budget (pack 6: 1 − 0.814 = 0.186 AUC lost)

| Bucket | Track 3 AUC | Kind | Where |
|---|---|---|---|
| **Robot/policy** (does not follow our reference) | **0.0835** (pack 4 review: 0.088) | [M] Σ(1 − sim_vs_ref)/20 | 10: 0.027; 32: 0.0067; 20 and 25: 0.0053 each; 16: 0.0046; 14: 0.0045; 1: 0.0040; 30: 0.0039 |
| **Reference vs truth** (perception, frame-0 anchor, mesh registration) | **≈ 0.10** (model 0.1026; 0.979 × 0.9164 − 0.8139 = 0.083 eval-specific + ≈ 0.02 public norm) | [E] | spoon episodes 0.070 (a residual sink); pitcher (20) 0.0087; boards (25) 0.0080; the rest 0.016 |
| **Draw luck** | +0.033 sim_vs_ref above the means → ≈ +0.025 AUC in our favour | [D] | 14 +0.25, 33 +0.15, 16 +0.10, 25 +0.10, 32 +0.06 |

**Caveats from the refcheck (§3):**
- The multiplicative model is biased low by about 0.02. Corrected, the implied spoon accuracy is 0.73–0.76 rather than 0.80, so either the spoon loss is larger or other eval references are worse than their public twins.
- The 0.979 factor holds only where the reference scores ≥ 0.93.

**Mechanisms measured on public twins** (`refcheck/README.md` §2):
- R2, frame-0 alignment lottery: oracle +0.03 mean, +0.18 on ep21.
- R1, table snap on stacked objects: −0.016 mean over 10 references.
- R5, resting objects drifting in our tracks: oracle +0.069 on ep11 and +0.02 on ep24.
- R6, half-frame lag: about +0.003.
- R3, sweeper flip: −0.034 Track 3 per flip on eval 19 or 30; unknowable from here.

**Mesh-attributable share** (relevant to the owner's mesh question):
- **Pose boards** [E, my extrapolation of twin costs]. If the public-twin registration costs (R4) carry over to eval:
  - pitcher on 20: ≈ 0.010–0.012;
  - rack via the sweeper on 30: ≈ 0.007–0.009;
  - blue cup in 10/14/20/32/33: ≈ 0.014;
  - lid on 1: 0.003.
  - Total ≈ 0.034–0.038, about the size of the model's non-spoon hidden loss (0.033). These may not add up, and they are not measured on eval.
- **Transfer so far:** the one mesh swap tried on Kaggle lost 0.0045 [M]. The cause was yaw instability in registration (`refcheck` §3). Blue cup, beige cup and pot swaps showed no consistent gain on the twins (`main:docs/analysis/meshswap-20261026/README.md`). Better meshes therefore need a registration-stability gate and at least 2 twins before they can be trusted.
- **CD-O:** 0.402 vs the leaders' 0.112 and 0.154. The pot, lid and rack meshes from the mesh branch would give about 0.367 [E] (`origin/claude/bold-albattani-6qmxsv:STATUS.md`).
- **Simulator collision copies:** these are part of the policy loss on 10 (0.027) and on the placements 14/28/30/1 (≈ 0.016 together; the geometry share is [E]).

**Gap to each target** (est.-true points summed over the 20 episodes):

| Target | AUC needed | Summed points | Roughly in sim_vs_ref (at ≈ 0.78 transfer) |
|---|---|---|---|
| DDD 0.827 | +0.0133 | 0.265 | ≈ 0.34 |
| 3rd 0.865 | +0.051 | 1.02 | — |
| 1st 0.932 | +0.118 | 2.36 | — |

- **To DDD:** eval 10 alone holds 0.029 (0.544 sim_vs_ref of headroom), so it would close the gap if the stack were learned.
- **To 0.865:** needs eval 10 plus either the spoon (spoon accuracy 0.95 ≈ +0.045 [E], forensics §4) or most of the policy loss on 32, 25, 20, 16, 33 and 14.
- **To 0.932:** 63 % of all remaining loss, which is more than the whole policy bucket. It needs both the hidden bucket (spoon, pitcher, boards, anchors) and nearly all policy loss closed.
- **Estimated total loss per episode:**

  | Eval | Total loss | Note |
  |---|---|---|
  | 10 | 0.0286 | |
  | 20 | 0.014 | |
  | 25 | 0.0134 | |
  | 32 | 0.0122 | |
  | 35, 36, 37 | ≈ 0.0105 each | almost all hidden spoon |
  | 16 | 0.0103 | |
  | 33 | 0.0093 | |

  The 10 spoon episodes together hold 0.095 (0.070 hidden + 0.025 policy).
- **Re-draw risk:** episodes 14, 16, 25 and 33 are packed above their means. Replacing them costs points in expectation unless the new policy's mean beats the packed draw.

## 4. Budget

**Vast credit:** $3.52, with 0 boxes running [M] (`main:STATUS.md`, 27 Oct 06:15 UTC).

**Funded and spent** [D, rebuilt from `main:docs/work-log.md`; there is no ledger file]. Top-ups by date:

| Date | Top-ups (work-log line) |
|---|---|
| 20 Oct | $25 (l. 300) |
| 21 Oct | ≈ $25 (l. 596), $10 (l. 885) |
| 22 Oct | $50 (l. 1217), $10 (l. 1589), $10 (l. 1673) |
| 23 Oct | $25 (l. 1977), $10 (l. 2459), ≈ $9–10 (l. 2552) |
| 24 Oct | $10 (l. 2798), $50 (l. 2981) |
| 25 Oct | $100 (l. 3875) |

- Total funded ≈ $335; total spent ≈ $331.
- The $100 top-up batch of 25 Oct cost $54.6.
- 26–27 Oct cost ≈ $43.7 ($47.20 → $3.52): packs 4–6 and the eval 10/25/32/33 experiments.
- **Limits:** no hard cap (CLAUDE.md, `main:docs/context-and-decisions.md`). The professor called $1,000–1,500 reasonable. The agent's own rule is that no box starts unless the credit covers its estimate plus $3.

**Owner top-up:** pending. The 27 Oct entry says "a top-up will follow" (`main:docs/work-log.md`); STATUS says it is waiting for it.

**Open owner decisions, with costs from the docs** [E]:
1. **The top-up itself.** The plan after it (`main:STATUS.md`):
   - H5, 10 evaluations of all 20 packed checkpoints: ≈ $2;
   - placement carves for 14/28/30/1: CPU work plus ≈ $15–20, after the per-episode-asset manifest is built;
   - spoon proxy measurement: CPU.
2. **Robustness review §12:**
   - run H5;
   - whether to prefer lower spread over a higher mean, and which tie-break;
   - whether to spend 2–3 days on GT-free automatic triggers for the held-out evaluation (H6 ≈ $5–8);
   - whether to adopt the proxy-first spoon rule (H1 ≈ $3; spoon re-reference ≈ $4–5 per episode).
   - Also listed: variance-targeted seeds at ≈ $2 per grasp-lock seed and ≈ $3 per standard seed.
3. **Refcheck §4:** whether to test a sweeper mesh with its near-symmetry broken on Kaggle. That would be tuning on eval results.
4. **Eval 10:** zero-residual policies are excluded by the 22 Oct rule. The next try would need a task-side change (relaxed termination in the nest phase, or more clearance); it has not been pursued or costed.
5. **Mesh branch** (`origin/claude/bold-albattani-6qmxsv:STATUS.md`):
   - swap only the submitted mesh for pot/lid/rack ($0), or also the simulator copy (a GPU re-run);
   - eval depth run: ≈ $2–4;
   - WeVisOne test: ≈ $1–1.5;
   - generative probe: ≈ $4–8, plus code permission.
6. **Note 23 (this branch):**
   - G1 wrist-gain batch: ≈ $75–100 in full, a slice ≈ $40–55, or the staged route at +$7–10 and then $15–40.
   - This affects the standard-learner episodes (kp 25 wrist); the grasp-lock policies already use kp 400.
   - The organiser email draft (5 questions, including kp 400) was never sent (`main:STATUS.md:270`).
7. **Seed race:** ≈ $12–13 per episode for 8 seeds. Interruptible boxes were preempted within about 10 minutes on 26 Oct.
8. **Submission repo and final picks:** this repo or a cleaned copy is undecided, and sharing with `Nvidia-V2D-Challenge` is not confirmed anywhere in the repo. Two final picks are still to be chosen.

Scratch files are in /tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/nextsteps/:
- pack6_budget.json
- loss_budget_pack6.py (the review's script with updated means for 10 and 32)
- rank.py
- lb_1025.json