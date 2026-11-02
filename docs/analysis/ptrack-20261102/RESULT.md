# Result: point-track second opinion, public episodes — FAIL, hypothesis falsified (2 Nov 2026)

Pre-registration: PREREG.md (commit 9203ccd, pushed before any variant scoring). Code 9203ccd (`pipeline/ptrack.py`),
CPU in the session container, $0. Control: ptrkD Cr. Scorer: `pipeline/score_registered.py`, public scans.
Files: `results/gate_PT-lag_vs_Cr.json`, `results/gate_PT-all_vs_Cr.json`, `results/precision.txt`,
`results/runs/<variant>/ep<N>.json` (flags, spans, counts), `results/scores/` (per-episode scores).

## Gate [D], 20 / 20 episodes, no crashes
| arm | mean ΔAUC | min ΔAUC | better / worse | mean ΔMPPE cm | frames > 3 cm (C → V) | gate |
|---|---|---|---|---|---|---|
| PT-lag (primary) | −0.0578 | −0.366 (ep42) | 0 / 6 | +0.266 | 955 → 1115 | FAIL (all 3 clauses) |
| PT-all (report-only) | −0.1319 | −0.754 (ep42) | 2 / 10 | +0.920 | 955 → 1609 | FAIL |
- PT-lag losses: ep42 −0.366, ep22 −0.269, ep21 −0.247, ep40 −0.163, ep12 −0.062, ep41 −0.049; no gain anywhere.
- PT-all gains only on ep11 (+0.053, blue cup) and ep40 (+0.010).
- ep23: 0.000 change, as expected (identity swap, ep23_identity.md).

## Why [D / I]
- **Detector precision is low:** of 17 flagged spans (PT-all), only 5 cover frames where the control's own error
  (symmetric ADD vs mocap, span median) exceeds 2 cm, and one of those is ep23's identity case. In most flags
  FoundationPose was right (0.4–1.5 cm) and the point tracks were wrong.
- [I] Failure mode of the point tracks: KLT points on weakly textured white / light-wood surfaces slip onto the hand
  or background during grasps and fast motion; the rigid fit then reports false motion ("lag") or false rest ("jump").
  Repairs rarely hand back (most spans have no end), so one false flag replaces the rest of the clip.
- On the GT-free development episodes (ep0, ep18 dust pan) the points agreed with FoundationPose, i.e. on public
  episodes FoundationPose + guard is already more reliable than a model-free KLT check.

## Verdict and next step
- Not adopted, not handed over. Falsifier fired (mean ΔAUC ≤ 0; repaired episodes down by > 0.01).
- BootsTAPIR GPU arm: **not requested.** The coordinator's condition (true-positive flags limited only by KLT dropouts)
  is not met: the main problem is false flags where FoundationPose is right, and the public headroom outside ep23 is
  small. A learned tracker would raise point quality but the case for it is weak [I]; it would need its own PREREG.
- By-products: ep23 diagnosed as an identity swap (fixed by the existing identity_fix.py); perc2's ep0 frame-0 lid
  mask lies on the pot handle [M].
