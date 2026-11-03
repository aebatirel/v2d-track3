# Pre-registration: H1, learned per-object tracker body-frame bias applied as mesh placement (3 Nov 2026)

Coordinator / owner (keen-heisenberg, 04:17 UTC; plan docs/plans/new-perception-20261103.md @ 21e5fdc2 on
claude/keen-heisenberg-engcwz). CPU, $0, public only. Written and pushed before any score of this test.

**Integrity:** B is learned from public mocap. It is a GT-informed inference constant, like Tier B meshes; eval use
needs the owner's yes. This public test is a diagnostic with leave-one-episode-out, so the held-out episode's mocap
never enters its own B.

## Set-up
- **Tracks:** C with ep23 after identity_fix (as PREREG_posemesh).
- **Baseline:** pack 13p meshes (`m13p`), already scored with 10 seeds (`cv/base13p`).
- **Kit conversion [M, code]:** converted pose = T · G with G = [Rbᵀ | ca] from `_register_object_body` (mesh →
  scan). Submitting Δ·M (vertices transformed by Δ) gives T · Δ · G. So the ideal body-frame placement is
  Δ = T⁻¹ · A · S̃ · G⁻¹, where:
  - S̃ = mocap pose moved to the scan anchor;
  - A = the world alignment between our world and mocap's.

## B per episode (`scripts/bias_fit.py`)
For each episode e and object o:
- G from the kit registration of o's 13p mesh to its public scan at the episode's kit seed (k = 0).
- **A:** rotation by chordal mean, translation by mean, over all frames of all objects of ((T·Δ·G) · S̃⁻¹).
- **Δ_o,e:** chordal-mean rotation and median translation of T⁻¹·A·S̃·G⁻¹ over the object's rest frames (our track:
  < 0.5 cm and < 2° per frame, runs ≥ 10 frames).
- A and Δ are alternated for 5 iterations, starting from Δ = I.
- **Symmetric objects:**
  - blue / beige cup: the twist about the symmetry axis (axis in the mesh frame = Rbᵀ · scan axis, the scorer's
    axis) is removed from Δ_R (swing-twist), keeping the swing;
  - lid: same, twist removed about its normal.

## Variants (leave-one-episode-out per object; objects with ≥ 2 public episodes)
For held-out e, Δ̂ = chordal mean of {Δ_o,e'} rotations and median of translations over e' ≠ e:
- **H1a:** Δ̂ (rotation + translation);
- **H1b-rot:** rotation of Δ̂ only (translation 0);
- **H1b-trans:** translation of Δ̂ only (rotation I);
- **H1c (GT-free):** the per-episode depth placement (test-A machinery, PREREG_meshAB; existing fits, `placeA` for
  meshes equal to 13f, `placeB` for pot / rack), applied only if its trimmed RMS drops by ≥ 25 % and ≥ 0.5 mm, else no
  change. It learns nothing across episodes, so it is scored on every episode directly.

Each candidate: 13p meshes with o ← Δ̂ · (o's 13p mesh) for the held-out episode; scored with `score_registered.py
--reg_seeds 10` against base13p.

## Gate (per object, per variant; fixed now)
- held-out mean gain ≥ +0.005 and no held-out episode below −0.01;
- then D1 (< 20° at every eval seed of o's eval slots) for the eval placement.

**Dispersion report (falsifier of "systematic"):** per object, the spread of Δ_o,e across episodes:
- rotation: median angular distance to the chordal mean, in °;
- translation: median distance to the median, in mm.

If the spread is as large as |Δ̂| itself (ratio ≥ 1), "systematic" is falsified for that object whatever the score.
