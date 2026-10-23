# 24. Physics-aware grasp design: physics, anatomy and motor control (2026-10-23)

Owner (≈ 12:40 UTC): "design the grasps physics aware, not just simulation physics; if needed research the physics and
the physiotherapy/anatomy of a grasp". Two research briefs (grasp physics and robotics; human grasp anatomy, OT and
motor control) plus our own measurements. Primary sources are linked in the briefs' citations (copied below where they
drive a rule). [M] = measured by us, [L] = literature, [I] = our inference / hypothesis (with its test).

## 1. What our simulator and hand can do [M] (`tools/sim_physics_inventory.py`)
- MuJoCo-Warp solver inside Newton, **pyramidal cones**, impratio 20, 20 fps × 5 substeps; contact μ 1.0, torsional
  0.005 m, rolling 1e-4; Newton's SolverMuJoCo default is condim 3 → **no torsional friction** in practice [L: Newton
  source]. A pyramidal condim-3 cone is a diamond: worst-case effective μ = μ/√2 ≈ 0.71 for diagonal loads [L, derived].
- Fingers: all 22 joints PD kp 1.7 N m/rad, kd 0.1, effort 10 N m. Wrist: xyz kp 25 N/m (45 N), rotation effort PD
  kp 25 N m/rad (45 N m). Hand 1.24 kg (gravity-compensated drive), spoon and pot 0.3 kg (kit placeholder mass).
- Spoon: handle radius 1.34 cm, inertia (26.0, 25.8, 0.455) e-4 kg m², COM on the axis at the body origin; our grip
  point on ep35 is 12.6 cm from the COM towards the handle end.
- The contact-force readout (`solver.update_contacts`) is **not calibrated** for absolute use: the spoon resting on the
  table reads 1,477–2,045 N against a 2.9 N weight. Only relative shares are used.

## 2. What the task demands [M] (`pipeline/task_wrench.py`, our object reference, no ground truth)
- ep35 spoon carry: |F| = |m(a − g)| ≤ 3.4 N (weight 2.94 N), acceleration p95 1.05 m/s², COM torque ≤ 0.04 N m.
  The bowl moment about the grip: m g d ≈ 0.37 N m at d = 12.6 cm when the handle is horizontal.
- The loads are small. Failures came from how the grip transmits them, not from their size.

## 3. Diagnosis of the failures [M]
- ep35 (zero action, locked wrap): the spoon **rolls about its own handle inside the hand**, up to 72° (kp 25) / 63°
  (kp 400); with kp 400 the bowl also tips up to 50°; axial slide ≤ 1–3 cm. ep3 kp 400: roll ≤ 29°, tip ≤ 11°.
- Cause [L + I]: the uniform +0.4 rad squeeze past contact is not a static equilibrium (τ = kp·0.4 is not in
  range(Jᵀ)), so fingers keep curling and roll the thin handle like a pencil; on a 1.3 cm radius only friction resists
  roll (no form closure for surfaces of revolution, Markenscoff 1990) and its lever is tiny. 10 flexion joints hit their
  limits after the squeeze (the fingers touch the 2.7 cm handle at 72–85 % curl). The thumb barely closes (2.5 %).
- Soft contacts give "gradual slip that cannot be avoided" [L: MuJoCo docs]; the evaluator's pyramidal cones and
  impratio cannot be changed by us (they are the evaluator's physics), so the grip itself must leave margin.

## 4. Physics rules [L]
1. Task wrench from the reference: F = m(a − g), M = I_w α + ω × I_w ω about the COM, plus the lever to the grip.
2. Design friction μ_d = μ/(√2·SF) (pyramidal worst case, safety factor SF 1.5): 0.47 for μ = 1.
3. Force distribution: contact forces in linearised cones with Σ G_i f_i = SF·W(t) (Kerr–Roth; LP with 8-edge pyramids),
   minimum normal preload on every kept finger contact, finger torques Jᵀf within kp × (room to the joint limit).
4. Squeeze target per joint Δq = Jᵀf / kp (statics), not a uniform angle. Schedule it with the load (it is known in
   advance from the reference).
5. Moments (the bowl) through couples of normal forces spread along the handle (index vs pinky ≈ 6 cm), not torsion.
6. Release: grip force to zero before moving joints; withdraw along a separating direction (LP over the near-contact
   normals, repelling screws, Ohwovoriole–Roth 1981); place before release.
7. Validation: replay the actual carry; time-scaled (1.25×), wrist noise ±5 mm / ±2.5°, finger noise ±0.05 rad; gate on
   in-hand drift < 1 cm and < 5° (DexGraspBench-style 5 cm / 15° is too loose for trajectory following).

## 5. Anatomy and motor-control rules [L]
- Power grip for carrying (Napier 1956; the medium wrap is the most used grasp for carrying, Feix 2014). Handle
  oblique across the palm, hand–handle angle 65 ± 7° (Young 2013), from the hypothenar to the index base.
- Finger force share in a cylinder grip ≈ index 30, middle 30, ring 22, little 18 % (Amis 1987); the thumb presses
  back in the palm plane; ring and little give stability.
- A 2.6 cm handle is a small-diameter wrap (optimum ≈ 33 mm, Sancho-Bru 2003): expect more flexion (OT data for a
  3.18 cm spoon: MCP 52–67°, PIP 52–71°, DIP 40–51°, McDonald 2016).
- Close MCP first or together with the IPs, never IP-first (IP-first "roll-up" pushes objects out of the palm,
  Muzykewicz 2013); DIP ≈ 0.76 × PIP (Hahn 1995); thumb closes last, over the fingers.
- Grip force follows load force, feed-forward, with a 30–50 % safety margin (Johansson & Westling 1984; Flanagan &
  Wing 1993/1997); vertical moves: grip peaks with load; horizontal moves: grip high throughout.
- Place: slower than lift; after the object touches the support, grip and load fall together; then release:
  grip force ≈ 0 before any joint moves, thumb opens first, DIP/PIP lead the MCP so the fingertips unroll off the
  handle (matches our measured release fix); withdraw only when contacts are clear, along the open side.

## 6. Implementation (`pipeline/grasp_force.py`, `grasp_lock.py --force_design 1`)
- Contacts at the locked grasp (per link the closest collision sample within 4 mm, hull-SDF normal), numerical contact
  Jacobians (Newton FK), per-frame LP (scipy HiGHS) → finger torques → Δq(t) = Jᵀf/kp, anticipatory lead 2 frames,
  smoothed; squeeze ramps with the load (support carries it on the table).
- Release direction: mean of the near-surface normals of the opened hand if it clears all of them, otherwise the LP.
- `--oblique_deg` (wrap_grasp.wrap_pose): handle crossing the palm obliquely.
- Unit check [M]: two-contact pinch, 0.3 kg, μ 1, SF 1.5 → 4.68 N per contact (analytic SF·mg/2/μ_d = 4.68), torque
  0.234 N m at a 5 cm lever.
- First run, eval ep35 [M]: 10 contacts (index PP/MP/DP, middle DP, ring PP/MP/DP, pinky PP, thumb PP/DP), all frames
  feasible, total normal force 27–37 N (preload 1.5 N each), squeezes ≤ 0.2 rad (most ≤ 0.1), 1 joint at its limit.

## 7. Open items / hypotheses
- H1: the force-designed squeeze removes the in-hand roll (falsified if the ep35 zero-action roll stays > 20°).
- H2: the oblique grip (25°) adds contacts and margin (A/B on ep35).
- H3: with a secure grip, the kp 400 wrist helps ep35 as it did ep3 (0.462 → 0.658).
- Missing anatomy pieces: thumb opposition (abducted thumb pressing back over the fingers) is not built yet; the thumb
  is closed from its zero pose only. MCP-first closing order not enforced (closing is simultaneous).
- Validation protocol with noise and time scaling (section 4.7) not yet run.
