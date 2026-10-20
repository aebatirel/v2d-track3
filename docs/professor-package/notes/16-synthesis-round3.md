[← Index](../README.md) · [Summary](../00-summary.md) · [← 15](15-eval-video-survey.md) · [17 →](17-marker-tracking.md)

# 16 — Round-3 addendum: corrections, AUC re-ranking, next digs (2026-10-06)

Supersedes the listed lines of [10-synthesis.md](10-synthesis.md). Sources: notes 11-15 (each with an
independent skeptic pass) and the round-3 completeness critic. Markers: [V] verified,
[E] estimate, [H] hypothesis.

## 0. Leaderboard state (2026-10-06 07:44 UTC)
| Team | AUC | SP-SR | MP-SR | RPE cm | MPPE cm | CD-O cm |
|---|---|---|---|---|---|---|
| SoySauceChicken | 0.649 | 0.35 | 0.25 | 5.13 | 7.28 | — |
| Panav Raaj | 0.212 | 0.05 | 0.00 | 20.0 | 15.2 | 0.112 |

The aggregator (`MVerghese/v2d-leaderboard-data/aggregator/v2d_aggregate.py`) orders rows by the
track's first metric (add_auc); the challenge page says winner = first, runner-up = "second by
the same metric". **Working assumption: ADD-AUC alone decides [E]. Re-rank everything by AUC.**
For scale: "nothing moves" ≈ 0.45 AUC, "most-moved object dropped" ≈ 0.55 [V 02].

## 1. Corrections to 10-synthesis (must not be implemented as written there)
| 10-synthesis said | Corrected [source] |
|---|---|
| P1: rotate colour 180° with K | **Do not rotate any stored video**; clips are upright, calibration describes stored frames as given; cam_a K as given (not flipped) [V 15, 11 s33] |
| — | Mono pair naming: left = ego_cam_c, right = ego_cam_b; cam_a `extrinsics_to_stereo_left` maps to **ego_cam_b** [V 15-verify] |
| Cup spin unobservable | Observable via mocap marker spheres (only cue when upright) and a base inscription when tipped; needs a learned sphere detector; beige cup's near-3-fold markers flip ~120° with 2 detections [V 12] |
| Spoon roll ~50/50, then "commit to B" (13) | Unresolved: Track 2 scans support a mid-axis skew sign rule, but measured M1/M2 offsets favour frame A (P(B) 0.09-0.14 under that rule); rule transfer from Track 2 (box-like axes) to Track 3 (area-PCA) uncertain. **Measure M1/M2 automatically, ask organisers; no leaderboard A/B** [13, 13-verify, critic] |
| P10: frame 0 open, contact-free | Eval 20: cup in hand mid-air at f0 → needs a pre-loaded frame-0 grasp; eval 32 hand on cup at f0 [V 15] |
| Anchor = static-prefix average to onset | Static prefix is 0 frames in eval 20/32, ≤1 s in 5,6,14,19,33,35; use automatic first-contact detection, window [0, contact−3 f], else static end propagated backward [15, 15-verify] |
| Keep motion_speed default / or 1.0 freely | 1.0 is required for row alignment (06), but the soft wrist likely saturates at real speed (holding 0.3 kg uses 11.8 cm of 0.2 m residual clip; 19-25/27 tracks saturate) → drops. Options: stiff_tracking wrist variant (FAQ allows other embodiments), or 10 Hz exact-row variant (parquet fps 10 + sim.fps 10) — rules check needed [14, 14-verify] |
| CoACD collision fine | Evaluator hulls inflate contact geometry 4-15 mm: GT contact states (lid-on-pot, sweeper-in-rack, cup/pot-on-rack, nested cups) start inside hulls → ejection at reset (eval 30 slot-0 sweeper, eval 1 lid) [V 15 with coacd 1.0.11 exact call] |
| Hands-free grasp synthesis as main transfer path | Rigid grasp synthesis likely fails on 5-8/20 eval episodes (hand-overs, flips, twirls, slides, in-hand start) and is partial on ~8; only 1, 8, 37, 38 are plain grasp-and-carry. Hand path must be strong; synthesis is a per-segment option [15, 15-verify] |
| Physics deterministic | Evaluator physics not deterministic by configuration (no warp deterministic mode); keep first evaluation per checkpoint [V 14] |
| "Policy error unknown" | Modelled e_track: real speed, default wrist, 1 seed ≈ AUC 0.75-0.84 on a perfect reference; best-of-3 0.84-0.90; discrete failures (no grasp / drop) cause essentially all SR loss and 1/3-2/3 of AUC loss [E 14, 14-verify] |

## 2. New treasures confirmed
1. **Room-fixed mocap world + placement priors [V 11].** Mocap world gravity-aligned, yaw-fixed in the room to ~1-1.5°; W (our camera heading in mocap) measurable on all 20 eval frame-0s (LOO ~1.2-1.6°). Staging is repeatable per task (≤4° rms). Slot-0 priors (ready values in our frame in 11 §C12): cups LOO AUC 0.277 → 0.871 (random-spin baseline), two-fold anchors 0.616 → 1.0. Applies to eval 10, 14, 15, 16, 19, 20, 25, 28, 30. Not additive with marker-based spin; use as fallback/consistency check.
2. **Mocap markers as a cue [V 12, critic].** Most scans model their marker spheres; GT poses are rigid-body fits to them. Markers give cup spin (and potentially mm-level 6-DoF poses wherever ≥3 are visible). Visibility through grasps is unmeasured.
3. **Rest snap (+0.014-0.058 median AUC/episode, never harmful) and anchor tilt snap [V 11].**
4. **Track 2 scans as a free holdout for frame conventions [V 13].**

## 3. Plan re-ranked by expected AUC impact (all [E])
| Rank | Lever | Why (AUC) |
|---|---|---|
| 1 | Policy discrete failures: wrist headroom (stiff/10 Hz variant), best-of-N seeds adaptive, reference QC, pre-loaded f0 grasps, hull-aware references | e_track −0.1 to −0.3; failure ≈ −0.3-0.4 per episode |
| 2 | Object loss/re-acquisition through grasps (perception) | dropped object → ~0.55 |
| 3 | Slot-0 anchor: markers + priors + contact-gated window + tilt snap | flip ≈ −0.8 per episode; cups/pot/spoon anchors in ~13/20 episodes |
| 4 | World drift: persistent room-map relocalisation | 5 cm drift ≈ −0.20 |
| 5 | Hull inflation fix on asset side (watertight/split collision meshes) | ~10 SIM-risk episodes, +0.02-0.05 board |
| 6 | Timing gate (06) | mandatory; otherwise AUC ≈ 0.415 ceiling |
| 7 | Spoon frame (slot 0 only in 35-37) | ~0.05 board AUC at 50/50 |
| — | CD-O, MP-SR-specific polish | low if AUC alone ranks |

## 4. Next digs (round 4, CPU-feasible; GPU items listed for the user)
- D16 Marker census + marker 6-DoF tracker feasibility (per-frame PnP on public eps, visibility fractions per segment type; prototype sphere detector).
- D17 Persistent room map: SfM over pooled public frames + eval frame-0s, registered to mocap via GT-fitted reference cameras, scaled by stereo; relocalise every frame; validate with static objects.
- D18 Hull inflation: watertight repair / part split, exact CoACD 1.0.11 call, penetration of GT contact states; loader support for multiple collision meshes.
- D19 Camera time sync (a/b/c) + spoon M1/M2/M3 triangulation at rest + P(B) update + automatic first-contact detector.
- GPU (user rents): E1 smoke (~1 GPU-h: throughput, memory, 64-world determinism spread at motion_speed 1.0), E2 (12-24 GPU-h: one 250M seed on twins 44/21/13/26/23/31 incl. crude object-attached wrist arm), E3 noisy-reference and stiff-wrist arms.

## 5. Consolidated organiser questions (user sends)
1. Is the Track 3 winner ranked by ADD-AUC alone? Tie-break?
2. Spoon scan frame / sign rule; does the confidential spoon scan include its 3 markers? Do Tracks 2 and 3 share one canonicalisation script?
3. Is motion_speed 1.0 with reference fps 20 the intended setting? (Report the silent half-speed truncation.) Are the stiff_tracking wrist variant or a 10 Hz exact-row variant allowed?
4. Are URDF mass/inertia/friction and collision meshes (decomposition) ours to set for our sim assets?
5. Must post-challenge validation reproduce trajectories exactly (physics is non-deterministic)?
6. May eval videos be pooled across episodes (room map, object library)?
7. Acceptability of non-commercial components used by NVIDIA's baseline.


---
[← Index](../README.md) · [Summary](../00-summary.md) · [← 15](15-eval-video-survey.md) · [17 →](17-marker-tracking.md)
