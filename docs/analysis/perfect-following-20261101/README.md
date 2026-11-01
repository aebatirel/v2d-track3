# Perfect following: steps 1–2 (CPU preflight + H5p7 error timelines), 1 Nov 2026 ~20:20 UTC

Session: perfect-following (session_01D9UJC8Nz9EEFNmz2yzimzN), branch `claude/perfect-following-20261101`.
No ground truth read anywhere: only our packed eval references, the pre-lock (support-filled) references, our library
meshes and the official rollouts of H5p7 (`runs/20261031-h5p7-1a7cdff`, pack-7 policies, 10 fresh draws each).
Labels: [M] measured, [E] estimate, [H] hypothesis, [I] inference.

Files:
- `preflight.py` / `preflight.json`: per episode and object: pre-lock hold phases (MANO), whether the ROBOT hand of each
  pre-lock phase grips (≥ 2 tip sites within 3 cm of the posed mesh) in the packed reference, frames where the object
  moves with no robot tip within 3 cm, motion outside every hold, cup twist at rest / held, wrist jitter.
- `../../../tools/simref_timeline.py`: sim_vs_ref exactly as `pipeline/qa.py` (checked: ep14 r1 0.8635 both) plus the
  leaderboard's symmetric version (cups: any spin about body z, kit `_symmetry_point_errors`), per-frame errors, onsets
  (first frame from which the symmetric ADD stays > 3 cm for 8 frames).
- `h5p7_timelines.py` / `h5p7_timelines.json`: all 200 draws, per draw plain / symmetric / per body / onsets, and the
  median symmetric ADD per 10 frames.

## Plain vs symmetric sim_vs_ref [M] (H5p7, 10 draws; eval 10 is the old pack-7 policy, pack 11's is 0.903)
Symmetric minus plain is ≤ +0.009 everywhere (ep32 0.852 → 0.856, ep14 0.727 → 0.730, ep8 0.973 → 0.975, the rest
≤ +0.002). Cup spin is not where the RL rollouts lose sim_vs_ref.

## Episode × problem table
Onsets: frames where the error takes off (draws with an onset / 10). "Grip" = robot hand grips in the packed reference.

| Eval | sim_vs_ref plain / sym | Where it is lost [M] | Flags [M] | Proposed fix |
|---|---|---|---|---|
| 14 | 0.727 / 0.730 | cup onset f42–46, 9/10; bimodal | human hand-over L18–51 → R35–77 → L78–118 (two-hand f35–51); robot right grips 0 % of its phase, left carries throughout | two-hand / hand-over lock (repair c); public ep13 test first |
| 16 | 0.850 / 0.850 | spoon onset f112–120, 10/10; 7–8 cm after f130 | right hold ends f107; spoon keeps moving with no robot tip f122–173; human L42–64 (two-hand f42–64) dropped | "no mover, no motion" after release (repair b); left phase |
| 32 | 0.852 / 0.856 | cup onset f19, 10/10; median 14 cm at f20–30, recovers by f40 | perceived cup glitch inside the left hold: swings 15 cm sideways f15–33, then jumps back (322 cm/s at f33); robot wrist does not follow | hand-frame low-pass / glitch rejection inside holds (repair b) |
| 25 | 0.878 / 0.878 | piece_1 onset f41, 10/10; piece_2 f173, 10/10 | piece_2 moves 26.6 cm outside any hold; carved slot | repair b on piece_2; slot geometry |
| 20 | 0.893 / 0.894 | pitcher onsets scattered (28–170), 6/10 | pitcher f0 fall (known, b1 pieces) | b1 + 1024 (already tried at stock: missed gate by 0.0004) |
| 30 | 0.897 / 0.897 | sweeper onsets f36–52, 6/10 | sweeper moves f3–27 and f242–263 with no robot tip; 200° rotation outside holds | f0 settle / repair b |
| 10 | 0.903 (pack 11) | — | blue cup moves f1–26 with no robot tip | done in pack 11 |
| 15 | 0.906 / 0.906 | spoon, 2 failed draws (onset f28, f118) | hand-over R34–53 → L39–107; robot grips neither phase with ≥ 2 tips | hand-assignment check |
| 1 | 0.912 / 0.912 | pot onset f129–164, 10/10 (2–7 cm late) | pot moves 14 cm outside holds | repair b candidate |
| 28 | 0.919 / 0.919 | pot onsets f36–67, 5/10 | pot touches rack | — |
| 33 | 0.923 / 0.925 | cup + spoon onset f91–93, 6/10 | spoon L80–87 dropped; cup L hold restarts f91 | small |
| 19 | 0.929 / 0.929 | 2 draws | sweeper f0 fall (support_fill) | support_fill |
| 3 | 0.933 / 0.933 | pot onset f66–68, 10/10 (6 cm at f70–80) | — | look at the f66 grasp |
| 5 / 6 / 8 / 35–38 | 0.965–0.998 | — | 35 / 36 drop left phases but still 0.99 | none |

## What this says [I]
- The losses are mostly at specific frames in all draws (deterministic): 14, 16, 32, 25, 1, 3. Those are reference
  problems the policy cannot follow, not draw variance.
- Three kinds dominate: a hand-over carried by one hand (14, maybe 15/16), a perceived object moving with no robot hand
  (16 after release, 25, 30, 1), and a perception glitch inside a hold (32).
- Cup twist (repair a) is not a sim_vs_ref loss in RL rollouts.
