[← Index](../README.md) · [Summary](../00-summary.md) · [← 20](20-sync-spoon-contact.md)

# 21 — Round-4 synthesis: architecture v3 (2026-10-07)

Builds on [16-synthesis-round3.md](16-synthesis-round3.md) (corrections there still apply). Sources: notes 17 (marker
tracking), 18 (room map), 19 (collision hulls), 20 (sync, spoon, contact). Skeptic passes exist
for 17, 18 and 19; **note 20 has no independent verification** (its verifier and the round
critic failed on network outages). Markers: [V] verified, [E] estimate, [H] hypothesis.
All work CPU-only on public data; GT read only for analysis/evaluation.

## 1. What round 4 settled
| Topic | Result | Status |
|---|---|---|
| Camera / world drift | A room SfM map built from **public frames only** (pycolmap, 525 images, 21 min CPU) relocalises **all 20 eval clips at 100 % coverage** (≥ 527 rig inliers); metric via the b/c rig; registered to mocap. Public accuracy ~1-2 mm, no drift; table height 0.6017 m vs GT 0.6012. Gain vs our measured frame-to-frame stereo VO ≈ **+0.06-0.07 board AUC** (skeptic-corrected from +0.10); ~0 vs a 3× better VO. Eval pooling unnecessary. Neighbour-VO check catches rare 7-10 mm glitches. ~13 min CPU for all 20 eval clips | [V] 18 + verify |
| Camera timing | b and c hardware-synchronous; **cam a is not same-index**: a[k+1] ≈ b[k] in 36/39 clips (exceptions p21, p22 mid-clip drop, e20 b/c drop); cam a rolling shutter (≈31.6 ms/height). Pair GT row k with b/c k+0.5 or a[k+1] + row model; ignoring the cam-a offset costs up to 0.11 AUC/object | [V] 18, 20 (20 unverified) |
| Markers | **Not a primary tracker** (lost at first grasp; marker-only AUC 0.15-0.76) except the pot lid (AUC 0.977). As a **correction layer** on a model-based tracker: cup fixes in 53-98 % of carried frames, ADD 16-24 → 6-18 mm, trajectory AUC +0.03-0.12; **cup spin by temporal vote over fix frames** (9/10 right, abstain rule → no wrong decisions). Board ≈ +0.02-0.10, central +0.04. Conditional on an emulated tracker prior | [V] 17 + verify (gains [E]) |
| Collision hulls | Inflation removable **purely on the asset side** (loader accepts several `<collision>` meshes per link, decomposes each separately; closed convex pieces pass unchanged). Two causes: voxel preprocessing (non-watertight scans) and CoACD tolerance 0.025·L. Recommended set REC (rack + pot split ≤120 mm, blue cup 2 parts, others watertight/welded) → +0.5/+1.0 mm over the exact-collider floor vs +5.4/+2.3 public. Rack split fixes eval 14/15/16/28/30 and restores the spoon tower opening. Constraints: debris hulls crash MuJoCo (screen on Linux, re-draw), **CoACD output differs macOS vs Linux and even x86_64 vs aarch64** → build assets on the evaluator's platform; eval builds 1 world (RAM fine), 4096-world training of split rack episodes needs 0.1-1 TB RAM → train with fewer worlds or unsplit hulls. Hull-aware reference projection still needed (residual 2-4 mm settle) | [V] 19 + verify |
| Anchor window | Automatic GT-free pipeline (stereo + 2.5-D template search → frame-0 mask → motion-ended window) works (bias 0.15° / 0.14 mm median); the window question is worth only ~0.001 AUC; **wrong slot-0 identity (twin planks, eval 25) is the real danger** (AUC 0.73 even with exact tracking) | [V] 20 (unverified) |
| Spoon frame | Still unresolved: P(frame B) ≈ 0.34 under the mid-axis skew rule, 0.88-1.00 under x-skew rules, ≈ 0.45-0.5 overall. Measured marker triangle 53.0/153.2/194.2 mm, round handle 18.8-21.3 mm. → organiser question | [E] 20 (unverified) |

## 2. Architecture v3 (primary path, with fallbacks)
1. **Time & camera.** Room-map relocalisation (public-only map) for every keyframe + stereo VO between keyframes; per-clip cam-a lag calibrated against the map; gravity = map up tilted by the measured 0.54° lean; W free. *Fallback:* stereo VO + frame-0 room registration (note 11).
2. **Objects.** Model-based 6-DoF tracker (FoundationPose with the public scans as templates, stereo depth; GPU) = primary. **Marker correction layer**: guided windows, robust 2/3-marker fits, quality-weighted carry, per-segment spin vote with abstain. Pot lid can run marker-only. *Fallback for spin:* placement priors in mocap yaw (note 11) via W.
3. **Slot-0 anchor.** GT-free frame-0 mask → motion-ended window → pooled anchor from all fixes in the window; explicit **identity resolution** for twin objects (planks: marker layout / staging side rule) before anchoring; static-end fallback for eval 20/32.
4. **World-frame smoother.** Rest snap + tilt snap (never harmful), robust per-object batch smoothing, hull-aware projection against the evaluator's own (Linux-built) hulls.
5. **Assets.** R1 watertight/welded collision meshes for all objects; rack (and pot, blue cup) splits from REC after a Linux debris screen; spoon collision authored from exact pieces (capsule chain + ≤4 convex bowl pieces); explicit inertials (0.3 kg default unless organisers allow otherwise).
6. **References & policy.** Repaired human-hand references as default (grasp synthesis per segment only where its carry test passes); pre-loaded frame-0 grasp for eval 20 (and 32); timing gate (motion_speed 1.0, fps 20, row check); wrist headroom fix (stiff_tracking variant or 10 Hz exact rows, pending organiser answer); adaptive best-of-N seeds; keep the first evaluation per checkpoint.
7. **Spoon.** Parametric template fitted to stereo (with markers), canonicalised by the organisers' rule; frame bit per organiser answer, otherwise commit to one and document.

## 3. Remaining unknowns — all need a GPU or the organisers
- Real model-based tracker error on public clips (replaces the emulated prior behind the marker gains).
- e_track: policy failure rate at real speed, wrist variants, seeds (notes 14 E1-E3).
- Split-asset behaviour in the real evaluator at world_count 1 (contacts, build time, crashes).
- Organiser answers (below). **Research is at diminishing returns without GPU time; next phase = build + GPU experiments.**

## 4. Organiser questions (add to note 16 §5)
- Collision geometry and inertials of our sim assets: ours to set? Multiple collision meshes / split parts acceptable?
- Evaluation world count (kit runner uses 1; evaluate_policy default 4096) and the evaluator's platform/architecture (CoACD hulls differ by platform).
- Spoon frame/sign rule and whether its scan includes markers.
- Ranking metric (AUC only?), timing (motion_speed 1.0 / fps 20), wrist variant, re-run tolerance.

## 5. GPU day-1 runbook (for when the user rents; ≥48 GB, Linux x86_64, driver ≥ 580)
1. E1 smoke (~1 GPU-h): FlashCHORD Sharpa recipe, motion_speed 1.0, sim.fps 20, public ep 44, 5-10M steps; throughput, peak memory; evaluate 3× at world_count 1 + once at 64 (determinism).
2. Linux asset build: REC hull set + debris screen; settle test of public twin states at world_count 1.
3. Real tracker run (FoundationPose + stereo) on public eps 12/21/13/22/26/0 → feed into the marker layer (note 17 scripts) and the kit scorer.
4. E2 (12-24 GPU-h): one 250M seed on twins 44/21/13/26/23/31 with GT and with our references; read metrics_output from 130M.


---
[← Index](../README.md) · [Summary](../00-summary.md) · [← 20](20-sync-spoon-contact.md)
