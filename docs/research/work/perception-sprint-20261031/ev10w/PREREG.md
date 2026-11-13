# ev10w: widened eval-10 blue-cup cavity — pre-registration (31 Oct 2026, 12:58 UTC)

Written before any ev10w geometry was built and before any ev10w number existed. Before writing it I had read the
Embodiment session's write-up and per-range numbers for mesh set A (`meshes/carve/ev10`, commit 2a11301 on
`origin/claude/determined-wright-3joens`). I had not run anything myself. Labels: [M] measured, [E] estimate,
[H] hypothesis.

## Hypothesis
**H-nest-a [H]:** widen the carved blue cavity below h = −40 mm to the beige carve's outer radius + ~1 mm. Here h is
the height the diagnostic uses: h = −z in the blue cup's file frame, so up is +h. Keep the 3.6 mm floor and a wall that
MuJoCo can still collide with. The packed gl10A2 reference's nest should then be (nearly) intrusion-free.

## Instruments (fixed now)
- **Intrusion:** `tools/intrusion.py` from commit 2a11301, run through that commit's `intrusion_diag.py` wrapper.
  - Defaults: pitch 2 mm, surf 0.5 mm. Provenance deny-list hits are recorded, not enforced.
  - The only code change is the path to `intrusion.py`, which is now a scratch copy. The tool is not added to this
    repo.
  - **I(f)** = max over the two ordered pairs (beige-in-blue, blue-in-beige) of `intr_vol` in cm³.
  - **Max depth** = max over both pairs of `depth_m` (union-surface depth, an upper bound).
- **Floor gap:** their `gap.py` analysis "A", with the carve directory as a parameter. The value is the beige cup's
  lowest point minus the blue cup's inner-floor height, counted only while that point is over the floor.
- **Ranges** (theirs): f0–46, f47–99, f100–117, f118–160.
- **References:**
  - **(a)** The packed gl10A2 reference `ref_gl_ilc.parquet` (md5 1a5003d9…).
  - **(b)** "V4p": the same parquet with only the two cups' poses replaced by V4p's
    (`scratchpad/mask10/eval10/posthoc/V4p/poses.npz`, 161 frames, same frame index as the reference's 161).
    - V4p's world is mapped into the reference world by one rigid transform G. G is fitted by least squares (Kabsch)
      on both cups' mesh points over f0–52, where V4p equals the stored track before the S12 window starts at f53.
    - The fit residual is reported. If the median point residual exceeds 5 mm, the V4p reading is reported as
      unreliable and does not gate. The verdict then says so.

## Gates
**G1, intrusion (gating).** PASS iff ev10w has I(f) ≤ 2.0 cm³ on every frame f100–160 of reference (a), AND on every
frame f100–160 of reference (b).
- The 2 cm³ threshold is the Embodiment session's guess. I adopt it as is; it is not calibrated.
- If (b) cannot be built or is unreliable, G1 is decided on (a) alone, and that is stated.

**G2, settle (gating, from the mesh session's M3).**
- **Scene:** plain MuJoCo 3.8.1 (fcvenv), set up as in `tools/nest_physics.py --mode inner`.
  - The blue cup is static at its reference pose.
  - The beige cup is free, starting at its reference pose with zero velocity. It uses the collision pieces and
    `inertia.json`.
  - Gravity is world −z. Timestep 2 ms, settle time 2.0 s, MuJoCo default contact parameters. There are no hands and
    no table.
- **Frames:** each assembled frame f100–160 of reference (a), settled independently.
- **Measures**, in the blue cup's frame:
  - dz = the beige centre's settled height minus its start height along the blue cup's axis (mm);
  - tilt = the angle between the beige cup's axis before and after the settle (deg).
- **A frame passes** iff |dz| ≤ 4 mm and tilt ≤ 5°.
- **Gate:** ev10w passes on ≥ 90 % of f100–160, AND on at least as many frames as ev10 does. That second condition is
  what "not worse than ev10" means here.
- **Also reported, not gating:**
  - medians and maxima per range;
  - the same settle on reference (b);
  - a FlashCHORD-harness settle at a few frames (hands parked, both cups free on the support, training sim
    parameters), if it is feasible on this container.

**Diagnostic gate M2, run on ev10 before building.**
- Inputs: reference (a), f100–160.
- **Azimuthal measure:** each intruding sample (both pairs, expressed in the blue frame) is binned into 12 sectors
  about the blue cavity axis. Then:
  - "One-sided" for a frame = at least 75 % of its intruding volume lies in one 180° half-plane. A uniform ring gives
    about 50 %.
  - "Mostly one-sided" = more than half of the intruding frames are one-sided.
- **Rigid shift:** the minimal rigid motion of the beige that brings I(f) ≤ 2 cm³ (and to 0).
  - Search space: translations up to 1 cm along 42 icosphere directions plus 10°/3° cones, the tool's own push search,
    combined with tilts of 0–3° in 1° steps at 8 azimuths about the beige centre.
  - "Clears" = a motion within 1 cm / 3° reaches I ≤ 2 cm³.
  - The fraction of frames cleared is reported per range.
  - The search may be run on every second frame if it is slow; that will be stated.
- **Verdict NOT-GEOMETRY** (do not widen all round; report a track error to the V4p / perception side) iff the f100–160
  intrusion is mostly one-sided OR a ≤ 1 cm / 3° shift clears it on more than half of the intruding frames.
  - The only exception: a widening below the seat line alone passes both G1 and G2.
  - The seat line is where the beige taper meets the blue taper on the reference, measured from the radii.
- **Taper:** both cups' wall taper (dr/dh of the outer radius, and its angle) is measured from the carved pieces before
  building. It sets the expected sink per mm of widening, about dr / tan(taper).

## Build rule (fixed now; one build is evaluated as "ev10w")
- **Shape:**
  - If M2 does not say NOT-GEOMETRY: in the blue cup's lathe frame, for every height bin with h < −40 mm, the cavity
    radius becomes r_c'(h) = max(r_c(h), R_g(h) + 1 mm).
    - R_g(h) = the maximum radial distance from the blue cavity axis of the ev10 beige pieces' surface samples in that
      bin, over frames f100–160 of reference (a).
    - The floor stays at its ev10 height (3.6 mm above the base); the outer wall and the base hulls are unchanged.
  - If M2 says NOT-GEOMETRY: the widening is applied below the seat line only (same formula), and the result is
    labelled as the exception case.
- **Wall:** at least 1.5 mm everywhere; where the formula would leave less, the cap binds and that is reported. The
  minimum wall over the widened band is reported.
- **Tool:** `pipeline/lathe_collision.py` with an opt-in option; the default output stays byte-identical, proved by
  rebuilding ev10 and diffing. Beige: an unchanged copy of the ev10 beige pieces.
- **Any later change is a new version** (ev10w2, …), reported as post hoc. It is not substituted for ev10w.

## Reported, not gating
- f0–99 intrusion on (a) and (b), which must not get worse than with ev10.
- Max depth and floor gap per range (target ≤ ~1 mm for a clean nest).
- The minimum wall over the widened band.
- Rest robustness in the carve.json `rest_robustness` style: FlashCHORD harness, no drive, start frames 0–10 → f38,
  maximum tilt of the blue cup resting alone; and the nested pair resting hands-free from f120. Both must stay upright
  as they do with ev10. Run if feasible.
- Mass, COM and inertia of the new blue collision (`inertia.json`) vs ev10.
- M4: each piece run through FlashCHORD's own CoACD call (`convex_decompose`, default params) must come back as one
  hull of equal volume. Otherwise the 3 mm wall does not survive as delivered.
- `radii.py` on V4p.
- ev10 on V4p, so that V4p's own effect is separate from the cavity's.

## Use
ev10w is used later only if PASS (G1 and G2): as an extra arm of an ep11 rollout gate (and then eval 10). The packed
eval-10 policy keeps `meshes/carve/ev10`, which this work does not modify. FAIL or NOT-GEOMETRY means ev10w is not
used, and the finding goes to the V4p / perception side.
