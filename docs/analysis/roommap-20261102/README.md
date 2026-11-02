# Room map vs perc2's camera: step-1 result (2 Nov 2026, room-map session)

PREREG: `PREREG.md` (pushed at be2f920 before any map or score existed). Labels: [M] measured, [E] estimate,
[H] hypothesis. All inference GT-free; mocap read only by `score_registered.py` after inference. Cost $0
(this container, 4 CPU, ~3.5 h wall).

## Verdict under the pre-registration
- G0 (map quality): **pass** on all 20 eval clips and 19 public episodes: 100 % of frames relocalised, gate rejections
  ≤ 0.7 %, min 442 rig inliers.
- G1 (eval camera-term bound ≥ 0.01): **fail**, mean 0.0029 [M].
- G2 (public leave-out vs control C): **fail** on clause 1, ep22 ΔAUC −0.0164 < −0.01. The other clauses pass: mean
  ΔAUC +0.0070 ≥ 0.0028 needed, mean ΔMPPE −0.081 cm.
- => Step 2 (eval recomposition / reference rebuilds / retrains) does **not** proceed under this PREREG.

## Eval (a): perc2's camera drifts little on 19 / 20 clips [M, GT-free]
`results/eval_drift.md`: object-position gap between perc2's camera and the map, p95 2–9 mm on 19 clips. Only ep35
reaches 17.9 mm (camera 25 mm / 0.85 deg; bound 0.056). The gap arrives in steps at keyframe hops (12 mm by frame
30), not as smooth drift. Note 18's own stereo VO drifted 20–83 mm on 12 / 20 clips; perc2's keyframe PnP on
FoundationStereo depth is far better, so note 18's +0.10 estimate does not apply.

## Public (b): leave-out maps, control C recomposed with map cameras, vs mocap [M]
`results/public/gate_map_vs_C.json`, per episode in `results/public/ep*/`.

| | n | mean ΔAUC | ΔMPPE (cm) | episodes |
|---|---|---|---|---|
| all | 19 | +0.0070 | −0.081 | 6 better, 10 worse (> 0.0005) |
| all but ep24 (bound ≤ 0.002) | 18 | −0.0008 | −0.008 | min ep22 −0.0164, max ep39 +0.0092 |
| ep24 (bound 0.176) | 1 | **+0.1477** (0.834 → 0.982) | **−1.383** | perc2 camera 37 mm / 1.66 deg off, 17 keyframes |

- Where perc2 drifts (ep24), the map recovers it: 84 % of the GT-free bound is realised. This confirms that the map
  poses are right at the cm level and that the GT-free bound detects real drift.
- Where perc2 does not drift (bound ≤ 0.002, object gap ≤ 9 mm), swapping cameras is noise of about ±0.005, one episode
  −0.016 (ep22). RPE never changes (Δ 0.000), as expected for a common camera term.
- [H] Why there is no small-scale gain: perc2's PnP uses near-field FoundationStereo depth (≤ 2 m: table, objects),
  so its few-mm camera errors are partly shared with the object poses and cancel in world coordinates; the map is
  independent and does not get that cancellation. Falsifier: a public episode with small bound where the map wins
  consistently across repeats.

## What this suggests (not pre-registered; a new PREREG would be needed)
- A **selective** rule: use the map camera only where the GT-free camera-term bound is large (e.g. ≥ 0.02), else
  keep perc2's. On public that picks ep24 only (+0.148, i.e. +0.0078 on the 19-episode mean) and avoids the noise.
  The rule was formed after seeing public scores, and its public support is one episode, so it needs fresh evidence
  (e.g. repeats / other perception runs) before adoption.
- On eval it would pick **ep35 only** (bound 0.056). Expected ≈ +0.047 perception AUC on ep35 (0.84 × bound) [E]
  → ≈ +0.002 board AUC after the measured ~0.74 perception-to-board transfer [E], and only through an ep35 reference
  rebuild + retrain (≈ $3–6 [E]).
- Perception side: a GT-free camera guard in perc2 (compare its chain to the map, switch when they disagree by
  > 1 cm) would have fixed ep24's public control. Handed to perception-tracking as information.

## Runs (all on this container; code at the commits named)
- Map run3: `python3 pipeline/roommap.py extract|features|match|map --t3 T3 --work /home/user/rm --name run3`
  (be2f920 + a67523c): 370/370 images, 18,589 points, 1.11 px, 22 min (4 threads).
- Eval relocalisation: `T3=... bash ops/jobs/roommap_reloc.sh /home/user/rm run3 eval OUT 4 <20 eps>`, ~55 min wall,
  1.5–1.7 s/frame/worker. Drift: `pipeline/roommap_compose.py <evperc poses.npz> <reloc npz> OUT --meshes 9a+`.
- Public: `T3=... bash ops/jobs/roommap_public.sh /home/user/rm 4` (fold maps 288–304 images, 1.09–1.11 px, 20–45 min
  each) + `scripts/public_gate.sh` / `scripts/public_gate.py`.
- HF store: `runs/20261102-roommap-6438495/` (map run3, eval relocalisations); public relocalisations under
  `runs/20261102-roommap-6438495/reloc/public_lo/`.
- Control: runs/20261102-ptrk{A,B}-7fbc3215 results/ptrk/C (ep23 has no control). Eval perception:
  runs/20261025-evperc-4f596df. Open: whether every pack-12c reference used evperc's camera chain (the camera
  depends only on the videos and the cached FoundationStereo depth).
