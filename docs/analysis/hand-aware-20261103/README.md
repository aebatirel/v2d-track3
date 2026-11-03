# Hand-aware tracking lane, phase 1 (public only), 3 Nov 2026: result FAIL

Branch `claude/hand-aware-20261103`. Labels: [M] measured, [D] public vs mocap, [E] estimate, [I] inference,
[H] hypothesis. Mocap was read only by scoring and diagnostics. Spend: **$0** (CPU in the cloud session; no rental).

## Verdict
**The pre-registered hand-masked ray correction (HRC, config F1) fails every holdout gate.** Nothing goes to eval.
Rigid-in-grasp with our hands failed earlier as a probe. HOLD / MagicHOI / HaWoR were judged not to transfer
(LITERATURE.md).

## Holdout (13 episodes; PREREG.md + addendum 1 gates + addendum 2 frozen F1; results/holdout/gate_F1.json) [D]
| | control C | HRC F1 | gate | pass |
|---|---|---|---|---|
| whole-episode mean AUC (10-seed), Δ | — | **−0.0042** (noise \|C−Cr\| 0.0015) | ≥ +0.005 and ≥ 2 × noise | no |
| worst episode ΔAUC | — | **ep24 −0.0466** | ≥ −0.01 | no |
| held mean ADD (cm) | 1.893 | 1.812 (−4.3 %) | ≥ 10 % lower, or | no |
| held AUC | 0.9078 | 0.9072 | ≥ +0.01 | no |
| held median ADD (cm, report) | 0.922 | 0.924 | — | — |
| ΔMPPE / ΔRPE (cm, report) | — | +0.060 / +0.096 | — | — |

Per episode (10-seed AUC, C → F1; corrections):
| ep | C | F1 | Δ | corrected spans (max / mean shift) | SP / MP-SR C → F1 |
|---|---|---|---|---|---|
| 23 | 0.6800 | 0.6775 | −0.0025 | board 1 f92–101 (4.6 / 4.3 cm); board 2 f146–245 (24.1 / 9.9 cm) | 0 / 0 → 0 / 0 |
| 24 | 0.7601 | 0.7135 | **−0.0466** | board 2 f43–77 (23.6 / 20.9 cm) | 0.9 / 0.9 → 0.9 / **0.0** |
| 26 | 0.9766 | 0.9703 | −0.0063 | rack f74–80 (4.2 / 3.9 cm), never held in mocap | 1 / 1 → 1 / 1 |
| 40 | 0.9782 | 0.9786 | +0.0004 | dust pan f111–116 (3.7 / 3.2 cm) | 1 / 1 → 1 / 1 |
| 2, 12, 22, 27, 31, 39, 42, 44, 45 | | | 0.0000 | none | unchanged |

Ray-correction sizes (for a later eval phase): the corrections that fired on holdout were 3–24 cm. The only large
correction that helped was on dev (ep18 sweeper, up to 11.5 cm).

## Why it failed [I, post hoc; not a new test]
- On the flat boards the residual measured something other than the board. During f43–77 of ep24 the mocap ray error
  of board 2 is −1.5 to −2.5 cm (scripts/ray_diag.py), but HRC shifted it by ≈ 21 cm. With a 25 cm band, pixels
  inside a thin, obliquely seen board's silhouette fall on the surfaces behind it (the other board, the table). This is
  the same thin-object failure that placement-from-depth showed (sweeper −0.14). Dev had no board episode, so dev
  could not reveal it.
- The near gate (hand within 15 cm, ±15 frames) fired on a rack that was never held (ep26).
- Where the mechanism is right (ep18 sweeper excursion, ep13 cup after release), the gain is real but rare. On the 13
  holdout episodes no such excursion occurred outside the boards.

## What was measured along the way
1. **Where the loss is** (control C, m14p meshes; scripts/held_diag.py; held_diag_C.json) [D]: 70 % of the public AUC
   loss is in mocap-held frames. Largest held losses: ep23 board 2 0.41, pitcher 21 / 22 0.20 / 0.16, ep24 boards
   0.17, ep18 sweeper 0.13, ep11 cup 0.10, ep13 cup 0.07.
2. **Rigid-in-grasp with our MediaPipe hands fails** (scripts/rigid_probe.py; probe on the Test-B track Ct, eps 12 /
   18 / 24 / 27) [D]:
   - palm frame × constant: −0.12 to −0.79 per episode;
   - translation-only blend: −0.014 to −0.083.
   - Our hand estimate is noisier than the FoundationPose track. Track-in-hand spread 2–8.6 cm.
3. **Timing is not the held-phase story** (scripts/shift_probe.py) [D]: +0.5 frame +0.005 (the known S2 advance).
4. **Held errors lie along the camera ray** (scripts/score_dump.py, ray_diag.py) [D]: ep13 cup +2.7, ep18 sweeper
   +14.6, ep21 pitcher −4.3, ep11 cup −3.6, ep24 board −2.2 cm. Oracle ceiling for removing it in held frames:
   +0.0195 [E] (scripts/ray_ceiling.py).
5. **A GT-free hand-masked depth residual sees only some of it** (scripts/ray_residual.py, ray_validate.py) [D]:
   - ep18 sweeper corr 0.99 (25 cm band);
   - ep13 cup 0.82;
   - ep11 cup 0.18 (depth agrees with the track while mocap says 2 cm off);
   - ep21 pitcher −0.83 (template error).
6. **Dev** (results/dev/): F1 +0.0045 over 7 episodes (ep18 +0.024, ep13 +0.0074, others 0).

## Things not to repeat
- Hand-as-pose-source (MediaPipe palm frame).
- Depth-residual ray correction on thin or flat objects, or gated only by hand proximity.

## What might still work [H, not tested]
- An **object-class-gated** HRC (sweeper / cups only, excluding boards, rack and pitcher), pre-registered on public.
  Expected value is small: on this holdout it would have changed only ep40 (+0.0004), so ≈ 0 unless excursions are
  common on eval. Not recommended without new evidence.
- The remaining held losses are boards (ep23 merge, ep24 thin margin), the pitcher (template bias) and ep11-type
  errors invisible to depth. None of these is a hand problem that depth can see. Better meshes and templates (the
  existing mesh lanes) and the board identity / merge logic are the levers [I].

## Files
- PREREG.md (addenda 1, 2); LITERATURE.md; scripts/ (all code used); results/holdout/ (gate JSON, per-episode 10-seed
  scores for V / C / Cr, HRC logs, track hashes); results/dev/.
- Code: pipeline/hrc.py @ e60ff9e (frozen F1). Hands: MediaPipe 1.2.0 tasks API (Apache-2.0),
  hand_landmarker.task float16 v1 (sha256 fbc2a300…), pipeline/hand_refine.py.
- Control tracks: C = store runs/20261102-ptrkA-7fbc3215 and -ptrkB-… results/ptrk/C (ep23 = ptrkD Cr + identity_fix);
  noise Cr = runs/20261102-ptrkD-95cecd7/results/ptrk/Cr. Meshes: perception-tracking meshes/m14p_public (43cbbfb6).
  Kit kit.zip sha256 7e1fdd00….
