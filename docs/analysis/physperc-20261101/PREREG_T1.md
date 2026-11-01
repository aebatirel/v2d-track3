# PREREG T1: physics-fused frame-0 tilt (written and pushed BEFORE any scoring of a transformed track)

Session physics-perception (claude/physics-perception-20261101), 1 Nov 2026 ~21:20 UTC. CPU, $0. Public episodes only.

## What was known before this test
- [M] `pipeline/refine.py` S3 (30 Oct), tilt-to-plane SNAP of every table-supported object, library_v3 meshes, prefix
  mean: ΔAUC −0.0013 (10 / 8), drops ep39 −0.077, ep40 −0.028, ep24 −0.021. REJECTED. Not repeated.
- [D] D1 (`diag/d1_tilt_9a.json`, mocap read only as a diagnostic): the stable-pose prior of our 9a+ mesh is a second
  tilt sensor with about the tracker's error (~2 deg), not a better one, and it is badly wrong where the tracker's
  attitude does not match a mesh facet (dust pan 13 deg, pitcher 60 deg, ep31 sweeper 10 deg). On the 14 anchors that
  pass the gate below, the frame-0 tilt error vs the truth is mean 1.96 deg (tracker) / 1.78 (snap, w=1) / **1.56
  (w=0.5)**; on all 23 gated objects 2.25 / 1.69 / 1.64 (w=0.75: 1.54).
- Disclosure: D1 is in-sample on the same 20 episodes. MATCH_DEG = 6 was set after seeing partial D1 output (dust pan
  13 deg, pitcher 60 deg). W = 0.5 is the a-priori equal-variance fusion weight; D1 agrees with it. So the tilt
  improvement itself is not an independent test. What this gate tests is whether the tilt change transfers to the
  scored AUC through the kit's frame-0 alignment.

## Transform (GT-free): `scripts/pp_tilt.py` (docstring has the full rule)
Inputs: our tracks (20261025 sweep), our 9a+ meshes, our bundle table plane (frame-0 depth), our hands. No parquet.
- Gate per object at f0: hand > 50 mm, lowest point within [−20, +10] mm of our table, match(tracker down axis,
  nearest stable facet) <= 6 deg.
- Fused down axis = slerp(tracker, stable facet, W); one body-frame correction C applied to every frame; pivot about the
  mesh surface centroid (no translation push).

## Arms
| arm | W | objects | role |
|---|---|---|---|
| **P1** | 0.5 | scorer anchor only (first slot without a declared symmetry, else slot 0) | **primary, gated** |
| P2 | 0.5 | every gated object | secondary, gated on its own |
| R1 | 1.0 | anchor only (S3-like snap on 9a+, control) | report only |

## Gate (each arm P1, P2), against `runs/before` (20 / 20 equal to posefix runs/before)
1. mean ΔAUC over the 20 public episodes >= +0.003;
2. no episode ΔAUC < −0.010;
3. mean ΔMPPE <= 0 and mean ΔRPE <= 0 (cm; not worse on average).
Pass = all three. Falsifier of the mechanism: mean ΔAUC <= 0 on P1 (anchor tilt does not transfer through the
alignment). Each arm is scored once with `pipeline/score_registered.py` (9a+ meshes, public scans). No re-tuning of
W, gates or object selection after scoring; any later variant gets a new PREREG.

## Expected [E]
refcheck's mocap oracle that removes the whole constant body-frame tilt of every object: +0.016 on perception. P2
removes ~25 % of the tilt of 23 gated objects: about +0.003 to +0.005 [E]; P1 less. Close to the gate.
