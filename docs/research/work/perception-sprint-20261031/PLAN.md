# Perception fixes to the freeze: plan (31 Oct 2026 ~11:30 UTC; nothing launched, nothing built)

Owner's question (~09:10 UTC): "Is there anything we can do to improve perception? Are we doing anything for that?"
Inputs: `offset/`, `heldpose/`, `mask10/` READMEs here; `../leak-decomp-20261030/tracker-fix/{SCREEN,PLAN}.md`, `ep11/DIAG.md`,
`T1/`, `T5/`; `../masses-eval-20261031/PLAN.md` (masses retrain, options O1–O4, rule §5). Labels: [M] measured, [E] estimate,
[H] hypothesis, [guess]. This plan reads no ground truth and no eval score; every eval fact is from our own tracks.

## 0. Spot-checks: each report's own scorer re-run on 2 public episodes (`spot/`: `spot.py`, JSON, logs; CPU, $0) [M]
| report | number re-scored | episodes × arms | result |
|---|---|---|---|
| offset | ΔR_lib V1/V2/V3 (ep12 −0.0640/−0.0671/−0.0645 Po; ep39 0/−0.1046/−0.1281) | 12, 39 × Po, refineP | 12/12 match |
| heldpose | ΔR_lib S10g/r/t (ep39 −0.0537/−0.2921/−0.0821; ep11 +0.0185/+0.0349/−0.0513) | 39, 11 × Po, refineP | 12/12 match |
| mask10 | ΔR_lib V1/V2/V3 (ep11 +0.0676/+0.0676/+0.0764; ep12 0/0/0) | 11, 12 × Po, refineP | 12/12 match; also V4p ep11 +0.0698 lib / +0.078 \* both arms (= stored) |

Same scorer code on the stored refine outputs, so this checks reproducibility and bookkeeping, not the method itself.

## 1. What passed, ranked by expected leaderboard value
| # | fix | public result [M] | eval targets (GT-free evidence) | LB if it works [E] | next step, cost [E] |
|---|---|---|---|---|---|
| 1 | **S12 nest hold + physics seat** (`pipeline/nest.py`, `tools/nest_physics.py`); eval form **V4p** (hold the outer cup at its frame-0 support height, keep its tracked slide, seat the inner cup by MuJoCo) | ref level, ep11: V1 +0.0676, **V3 +0.0764** (pre-registered, pass); V4p +0.0698 (post hoc); other 19 eps byte-identical | **eval 10 only** (only two-cup roster). Track: blue cup +3.1–3.7 cm during the nest, +1.6–2.2 cm after hands leave, camera ≤ 0.4 cm (SCREEN §4). V4p: blue +0.06 cm, slide kept, beige +3.2 cm over blue; lowest collision point +1.68 → −0.20 cm (f0: −0.11); >2 mm penetration frames 81 → 23. Pre-registered V1/V3 hold at f44 (inside the slide): blue stays +1.53 cm | +0.004 to +0.012, central **+0.007**, cap +0.017; prob.-weighted ≈ +0.003 [guess: P(gate) 0.5 × P(eval rule) 0.8] | ep11 rollout gate, then eval-10 retrain in the masses boxes (§3); **≈ $10 ($7–14)** |
| 2 | T5 robust VO (2 m depth-clip fix) | ep24 P_o\* 0.81 → 0.994 | none confirmed; eval 35 unresolved (burst during the spoon pickup) | ≈ +0.001 (p 0.1–0.35 × 0.005–0.008) | $0 CPU camera check on 2–3 eval-35 depth frames; rebuild only if a ≥ 1 cm jump is found (+≈ $3) |
| 3 | (lead, not a fix) cup lost mid-carry on evals 14, 32, 33: track sinks 3–6 cm, up to 2 cm under the table, 5–42 frames | none (no public test) | 14 f41–45, 32 f18–33, 33 f49–90 (SCREEN §2B) | unknown [H] | $0: check whether the sink survives into the packed `glockt` references; nothing else before the freeze |
| – | masking re-track (option a, `perc2_mask_others.patch`) | CPU mock / ICP proxy: masked outer cup loses its axial anchor, slides 4–6 cm down | eval 10 (duplicates S12); 32, 33, 5, 1 ≤ +0.003 | ≤ +0.003 | not before the freeze (predicted to fail alone [H]; $0.8–1.2 GPU + its own gates) |
| ✗ | S11 constant-offset ICP (offset) | falsified: means −0.006 to +0.0005, ep12 −0.064, ep39 −0.128; also fails with true shapes | – | 0 | dropped |
| ✗ | S10 held pose = wrist × grasp (heldpose) | falsified: proxies −0.018; tracker 0.47 cm vs prediction 2.95 cm in holds | (would touch 10 spoon evals) | negative | dropped; rigid-hold variant needs a fresh pre-registration (only ep11 supports it) |
| ✗ | S6 whole-episode static hold | fails no-harm rule by 0.0003; freezes nothing on eval 10 | – | 0 | dropped |
Outside this lane: the template lever L2 (eval-20 pitcher mesh, +0.012–0.017 [E] only if the better mesh is also submitted) is
the mesh session's. Packed eval references predate S2 [E: no job script calls refine; `refine/RESULTS.md`], so any rebuilt
reference also carries S2 (+0.006 mean at reference level).

## 2. Value model [E]
- LB = dR × t / 20. dR for eval 10 = the twin's truth-scored rollout gain: orcB gap P 0.595 → O 0.940 = 0.345 (one seed), of
  which 30–70 % recovered → 0.10–0.24; t (twin → eval) 0.74–1.0. Central 0.17 × 0.85 / 20 = +0.0072.
- Board rule: the board scores the submitted rollout, so a swap pays only if the new rollout beats the packed one. Eval 10's
  packed draw sits only +0.006 above its policy's mean (0.4563 vs 0.450 ± 0.007, H5), worth ≈ 0.0002 LB: the lucky-draw
  penalty is negligible here; the risk is that the gate or the eval rule fails (then 0).
- V3 instead of V4p on eval 10 leaves the blue cup 1.3–1.5 cm high: assume 30–60 % of V4p's effect [guess], central ≈ +0.003.
- Masses on eval 10 alone (arm A below): masses PLAN g(.05) 0.006 → ≈ +0.0002. Arm A is an attribution control.
- All perception work left before the freeze is worth ≈ +0.007 if the gate passes, 0 if not; with masses O2 (+0.0055 at
  L = 0.05) still far from the +0.046 that 5th place needs.

## 3. Delivery: rebuild only eval 10's reference; train it in the masses retrain's grasp-lock box
**Gate N (public ep11 rollout gate; box `<date>-n11g-<sha>`; pattern `ops/jobs/oracle_twins.sh`, arm override instead of oracle).**
- Recipe gl10A2 as orcB (grasp lock, SF 0, REPLAN 1, EVOLVE 0, PIECES `meshes/carve/ev10`), Phase-1 P_o bundle, seeds 42 and
  43, NREP 10. Physics = the eval retrain's: props masses if the transfer check ADOPTs, else 0.3 kg (no verdict at launch:
  0.3 kg and the A0/B0 design) (pre-registered now).
- Arms differ only in the refined track fed to mkref: **ctrl** = `--steps S2`; **V4p** = `S12 --s12_mode support` +
  `nest_physics --mode inner` + S2. Optional third arm **V3** (+1 wave, +$1.4–2.2).
- G0 before training (stop, no training, if it fails): V4p's built reference vs mocap ≥ ctrl's + 0.03 lib.
- **PASS iff** seed-mean registered ADD-AUC vs mocap (`score_registered.py --meshes library_v3`) of V4p − ctrl ≥ **+0.05**,
  and V4p's sim_vs_ref ≥ 0.70. Falsified below +0.05. If V4p fails and V3 ran and passes, eval 10 uses V3.
**Eval-10 arms (clean attribution: per seed, arms differ in one factor; same box, commit, recipe, seed list).**
- Masses ADOPT → in box G2 (33 + 15, LIB v3; their references name their own asset copies, so eval 10's `/content/assets`
  with ev10 pieces clashes with nothing there [E, masses PLAN §1–2]; G1 cannot take it: library_v3x beige cup) as waves
  3–4: **A** = props masses + packed reference (fingerprint-checked, masses PLAN §1) and **B** = props masses + rebuilt
  reference (stored pack-6 `perc2/ep10` track → V4p refine, sha256-checked against the committed CPU output → mkref →
  gl10A2 reference build), seeds 42 and 43. B − A = perception (S2 + S12 + rebuild); A − H5 level = masses + seed + code.
- Masses NOT ADOPTED → own box after the gate passes: **A0** = 0.3 kg + packed ref, **B0** = 0.3 kg + rebuilt ref.
- Readings beside the rule: every arm's draws scored against BOTH references (old and new) and the packed rollout against
  the new reference (CPU, $0).
**Eval-10 swap rule (pre-registered here; GT-free; confirmation N = 10 pristine draws on C1, ≥ 8 scored, as masses §5.4).**
- Swap to B iff (1) gate PASS; (2) B's mean sim_vs_ref vs its own reference ≥ 0.4563 (the packed draw vs its own);
  (3) B's mean vs the new reference ≥ the packed rollout scored vs the new reference. Draw 1 by position, never by score.
- (3) favours B by construction (B imitates the new reference), so the twin gate carries the evidence; (2) guards
  executability. A follows the masses rule §5 unchanged (bar 0.4563). If A and B both pass, B (the only one with
  truth-scored support). Gate fails: B is discarded (≈ $2 at risk in G2), A as masses §5.
**Build items (CPU, before any GO).** N1 commit the refined tracks + sha256 (ep11 S2/V4p/V3 Po; eval-10 V4p/V3, 140 kB):
boxes need no MuJoCo for the seat. N2 an `ARM_TRACK` override in `oracle_twins.sh` (or a sibling `n11_gate.sh`), run id `-n11g`,
`tools/no_oracle.py` still guarding packs. N3 `mass_eval.sh` mode `REBUILD10=V4p` (new folders `refs/n12*`, never overwriting
packed refs; refuses unless the sha256 match). N4 CPU mkref on ep11 and eval 10, both arms: blue cup's lowest collision point
and `tools/intrusion.py` penetration in the BUILT reference (the fix must survive mkref / rest settling). N5 mock both job
strings, `bash -n`, two reviews. N6 `se3_log` guard: keep held poses float64 (mask10 §2 NaN) and assert finite outputs.

## 4. Cost [E] (RTX PRO 6000 $1.18–1.47/h; wave of 2 grasp-lock trainings 1.2–1.5 h, box overhead 0.3–1.0 h [M basis])
| item | content | hours | cost (central) |
|---|---|---|---|
| Gate N | ctrl + V4p × 2 seeds = 2 waves + 2 reference builds | 2.9–4.4 | $3.4–6.5 ($5.0) |
| Gate N, optional V3 | +1 wave | +1.2–1.5 | +$1.4–2.2 |
| Eval 10 in G2 | A + B × 2 seeds = 2 waves + B's reference build, no extra overhead | 2.6–3.4 | $3.1–5.0 ($4.2) |
| (own box instead) | same + overhead | 2.9–4.4 | $3.5–6.5 ($5.0) |
| Confirmation | A and/or B in C1 | +0.3–0.5 | $0.4–0.7 ($0.6) |
| **Total** | gate + eval 10 + confirmation (gate fails: gate only, + ≈ $2 if B already ran in G2) | | **≈ $10 ($7–14)** |
Fits the lean allocation only at its top ($24–39 for mass remainder ≈ $4–6 + O2 ≈ $17 + eval 10); otherwise from the buffer.

## 5. Schedule to the freeze (UTC; Wed 4 Nov 22:00)
- **Sat 31 Oct.** 12:10–14:15 transfer-check verdict (sets the gate's physics and the A/B or A0/B0 design). Build N1–N6,
  mock, reviews (≈ 3–4 h). Owner GO with ledger lines → ≈ 17:00–19:00 launch gate N with masses wave 1 (G1, G2 + eval-10
  waves, S1a/b). $0 CPU checks for rows 2–3 of §1 in parallel.
- **Sun 1 Nov.** ≈ 00:00–02:00 gate readout (scripted rule). G2 ends ≈ 01:00–07:00. C1 confirmation (wave-1 candidates +
  eval 10) ≈ 08:00–12:00; CPU cross-scores. If masses were not adopted and the gate passed: own eval-10 box (≈ 4 h).
- **Mon 2 Nov.** Readings per §3; B7 CPU repack → pack-9 candidate; **owner decides the upload**. Re-run any INCOMPLETE
  confirmation only (never the training).
- **Tue 3 Nov.** Buffer (HF 429 can make wave 1 serial ≈ 13 h); the Embodiment recipe-winner retrain (its lane, $10–15).
  Every box destroyed by end of day.
- **Wed 4 Nov.** Final pack by 18:00, owner upload by ≈ 21:00 (1 h margin). No new training after Tue 12:00.

## 6. Integrity and limits
- No eval result tunes anything; V4p was designed after seeing eval 10's GT-free track (no scores) and is tested only on
  ep11, which has no slide: the slide part of V4p stays [H]; the eval-10 rule checks executability, not truth.
- One public twin (ep11), one orcB seed behind the 0.345 gap; ep11's two arms were the same track (one test, no holdout).
- Mocap only in the gate's scoring (`score_registered.py`, G0's `ref_vs_mocap.py`), public, after inference; refine inputs
  pass `refine.assert_inference_input`. Existing runs and references are kept; new ids `-n11g`, folders `refs/n12*`.
