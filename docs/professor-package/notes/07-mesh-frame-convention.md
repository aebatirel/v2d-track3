[← Index](../README.md) · [Summary](../00-summary.md) · [← 06](06-timing-audit.md) · [08 →](08-architectures-accuracy.md)

# 07 — Track 3 scan-frame convention and the unscanned wooden spoon

Status: research only. No SlamDunk code was read or changed, and no repo files other than this
note were written. Date: 2026-10-04.

Evidence tags: **[V]** verified numerically here, **[H]** hypothesis or inference, **[?]** open question.

- Scripts and raw outputs:
  `/private/tmp/claude-501/-Users-aebatirel-Documents-Code-SlamDunk/ad61ecbd-403d-49a3-817f-1f8b688b5549/scratchpad/meshframe/`
  - `analyze_meshes.py`: origin and axis candidates per mesh, URDF cross-check. Output in `.log` and `mesh_stats.json`.
  - `analyze_rest.py`: GT rest poses, which axis points up, table contact. Output in `.log` and `rest_poses.csv`.
  - `sign_stats.py`: 10 candidate sign statistics. Output in `.log` and `.json`.
  - `canon.py`: the inferred rule (R1) and a parametric spoon generator.
  - `verify_rule.py`: R1 applied to every public scan (`.log`).
  - `rule_robustness.py`: R1 under defects of the kind a reconstruction has (`.log`, `.csv`).
  - Spoon sensitivity: `spoon_sensitivity.py`, `spoon_shape_grid.py` and `spoon_noise_check.py` (plus logs).
  - `wp_compare.py`.
  - Score impact: `score_impact.py`, then `summarize_impact.py` and `lb_aggregate.py`. Outputs `score_impact_rows.csv`, `score_impact_summary.{csv,log}` and `lb_aggregate.{csv,log}`.
- Environment: `scratchpad/venv-mf` (uv, Python 3.12, numpy, scipy, trimesh 5.1.1, pygltflib, pandas, pyarrow).
  Run with `cd meshframe && ../venv-mf/bin/python <script>.py`. The full set takes about 2 min.
- Data: all 13 public Track 3 GLBs (10 objects; 3 of them also ship a `_collision.glb`), about 93 MB, downloaded from
  `huggingface.co/datasets/nvidia/video_to_data_challenge` into `scratchpad/t3/public/mesh/`. Also used: the public URDFs
  and the 20 public GT parquets.
- Scorer: the kit's `metric_code/track_3/{AUC,SP-SR,MP-SR,RPE,MPPE}.py` functions, imported unchanged. An end-to-end call to
  `score()` on a perturbed episode matched the in-process path exactly: AUC 0.90625, SP 0, MP 0, RPE 1.0, MPPE 3.516625.

## TL;DR

1. **[V] Origin and axes follow one exact rule on all 10 public scans.**
   - **Origin**: the exact area-weighted *surface* centroid. The residual |c| is at most 6e-10 m.
   - **Axes**: the eigenvectors of the exact area-weighted *surface* covariance (a uniform thin shell). The relative
     off-diagonal residual is at most 3e-9.
   - **Order**: x has the smallest variance, y the middle and z the largest. This holds on 10 of 10 scans.
   - **What it is not**: the volume centroid, the bbox centre, the vertex mean and volume-inertia axes miss by up to
     14–66 mm and 45°.
   - **Format**: metres, raw GLB coordinates, and node transforms are identity (generator "trimesh").
   - **Corroboration**: the URDF inertials are the exact uniform-surface moments of the collision mesh (mass 0.3 kg),
     expressed in this frame.
2. **Sign of z.** **[V/H]** For all 10 scans, z points so that the surface third moment (skewness) along z is positive.
   Chance alone gives 1/1024. Allowing for the ~10 statistics tested, the family-wise p is about 0.02. Two statistics
   reproduce 10/10: the third moment and the CPCA "signed square". Four one-sided statistics reproduce 9/10.
3. **Signs of x and y.** **[H]** The pair (x, y) → (−x, −y), i.e. a 180° roll about z, is **not determined by the data**.
   - "Third moment > 0 on y, x = y × z" fits every scan whose |skew_y| ≥ 0.018. Its 3 failures all have |skew_y| < 0.01,
     which is consistent with a noisy (sampled) estimate.
   - "Third moment > 0 on x" fails on wooden_piece_2, whose skew_x is −0.54.
   - A spoon is mirror-symmetric across its width (y), so **under the best-supported hypothesis the spoon's roll sign is
     effectively a coin flip**, decided by tiny asymmetries in the organisers' scan.
4. **Score impact** (kit scorer, public GT motions; leaderboard = 7 spoon-in-slot-1 + 3 spoon-alone episodes out of 20):
   - **Wrong roll (180° about z)**, upper bounds with perfect tracking: ΔSP-SR −0.48, ΔMP-SR −0.50, ΔMPPE +4.2 cm,
     ΔAUC −0.13. With 1 cm / 5° tracking noise: ΔSP-SR −0.48, ΔMPPE +3.2 cm.
   - **Wrong z sign**: similar, and AUC is hit harder (−0.28).
   - **Continuous residuals are minor**: 1 cm centroid error gives ΔRPE +0.35 cm, ΔMPPE +0.27 cm, ΔAUC −0.01. A 5° axis
     error gives ΔMPPE ≤ +0.19 cm.
   - The scorer's slot-0 first-pose alignment does **not** protect the single-spoon episodes. Errors vanish at t=0 but grow
     with motion: on moving hosts a wrong roll costs 20 cm MPPE.
5. **Recommendation.**
   - Canonicalise our spoon reconstruction with rule R1 (section 3) before any spoon policy is trained.
   - Expect +z to run from bowl to handle. Pick the roll by the hybrid y/x skew tie-break. For a symmetric spoon this
     falls through to x, giving +x toward the convex back of the bowl.
   - **Ask the organisers for the spoon frame.** That one bit is worth about 0.5 SP-SR on the board.
   - Do **not** hedge with a 90° roll: it is worse in expectation on every metric.
   - The same rule matters for *every* object built from our own reconstruction (the FAQ asks for own meshes). For the
     cups and the lid, near-equal eigenvalues make the in-plane axes ill-conditioned (section 4).

## 1. What the published frames are

### 1.1 File facts [V]

- **Structure**: every GLB has 2 nodes, a root `world` and one mesh node, both with no matrix/TRS. There is one
  primitive, float32 positions in **metres**, and `asset.generator = https://github.com/mikedh/trimesh`.
- **Collision meshes** (mini_sweeper, wooden_piece_1/2): the generator reads "UV transfer from <name>_original.glb".
  These meshes are *not* re-centred. Their surface centroids sit 0.7–2.0 mm off the origin, and the URDF `<inertial>
  origin` equals exactly that collision-mesh surface centroid (e.g. sweeper (−0.0007, −0.4399, −1.9300) mm). The URDF
  inertia tensor equals 0.3 kg × the uniform-surface inertia of the collision mesh about that centroid, to 1e-12.
- **Visual (or single) meshes**: these define the link frame. For every single-mesh URDF the inertial origin is 0 and
  the products of inertia are 0.
- **Not converted to Y-up**: the GT poses place the raw GLB coordinates correctly. At rest, every object standing on
  the table has its lowest mesh vertex at z = 0.598–0.606 m (table ≈ 0.60 m; the lid on the pot gives 0.688, the pot in
  the rack 0.618; origins sit at 0.605–0.738 m). So no glTF Y-up→Z-up conversion is applied. Any loader we use must also keep raw coordinates. trimesh does. Blender's glTF
  importer does not by default.

### 1.2 Origin and axes against candidates [V] (`analyze_meshes.log`)

| candidate | miss across the 10 scans (min–max) |
|---|---|
| exact area-weighted surface centroid (= trimesh `mesh.centroid`) | **≤ 6e-10 m** |
| volume centroid (trimesh `center_mass`; no scan is watertight) | 1.7–60.5 mm |
| vertex mean (raw or welded) | 0.5–14 mm |
| bbox centre | 4.4–65.8 mm |
| exact area-weighted surface covariance eigenvectors | **0.000°** (off-diagonal/diagonal ≤ 3e-9) |
| vertex covariance eigenvectors | 0.3–43.7° |
| trimesh volume inertia (`principal_inertia_transform`) | 0.1–45° |

The variance is ascending x < y < z in all 10 scans. This is equivalent to descending shell inertia (I_xx > I_yy > I_zz
in every URDF). The rule was applied to the delivered triangles themselves. Had it been computed on an "original" mesh
and then decimated, the residuals would be about 1e-3, not 1e-10. The kit's CD-O code cites the V2D team's
`evaluate_mesh_quality.py::area_weighted_surface_moments`, the same exact per-triangle integrals. A search of the public
`nvidia-isaac/video_to_data` snapshot (commit 7c0d3b9) found no Track 3 asset-generation code. The team's other PCA code
(`_pca_basis`, `calculate_mass_properties`) uses `eigh` plus a det-fix on the last column and has no moment-based sign.

### 1.3 Per-object geometry and rest pose [V] (`analyze_meshes.log`, `sign_stats.log`, `analyze_rest.log`)

| object | extent x/y/z mm | surface std x/y/z mm | λy/λx | λz/λy | skew x | skew y | skew z | axis up at rest |
|---|---|---|---|---|---|---|---|---|
| beige_cup | 104/111/170 | 27.1/27.6/55.8 | **1.04** | 4.08 | −0.090 | +0.121 | +0.231 | −z |
| blue_cup | 103/100/172 | 27.1/27.7/57.6 | **1.05** | 4.33 | +0.067 | −0.009 | +0.194 | −z |
| mini_dust_pan | 45/170/178 | 9.0/39.6/49.0 | 19.3 | 1.54 | +0.136 | −0.001 | +0.474 | +x |
| mini_sweeper | 48/114/142 | 6.7/24.4/40.4 | 13.4 | 2.74 | +0.272 | +0.055 | +0.366 | +z |
| plastic_dish_rack | 117/176/510 | 22.9/47.0/147.9 | 4.22 | 9.91 | +1.072 | +0.032 | +0.319 | +x |
| water_pitcher | 141/272/415 | 33.6/63.7/84.3 | 3.59 | 1.75 | −0.014 | +0.577 | +0.904 | +z (cos 0.79) |
| white_pot | 132/189/358 | 35.2/52.1/75.4 | 2.19 | 2.10 | +0.309 | −0.009 | +0.940 | +x |
| white_pot_lid | 47/188/190 | 7.5/45.9/48.9 | 37.8 | **1.13** | +2.832 | +0.008 | +0.035 | +x |
| wooden_piece_1 | 27/139/227 | 4.4/36.9/69.6 | 70.1 | 3.55 | +0.980 | +0.018 | +0.015 | +x |
| wooden_piece_2 | 26/139/227 | 4.9/37.0/69.2 | 57.0 | 3.49 | **−0.536** | +0.004 | +0.0003 | −x |

Skews are exact analytic area-weighted standardized third moments about the centroid. Values ≤ 0.01 in magnitude are
fragile. "Up" is the body axis most aligned with world +z over the first 5 visible frames. Its |cos| is ≥ 0.975 except
for the pitcher, whose PCA axes are tilted by its handle and spout.

## 2. Sign convention: what the data can and cannot say

**z: skew_z > 0 in 10/10.** [V for the pattern, H for the rule.] Statistics tested on all three axes:
- exact surface third moment;
- CPCA signed square;
- vertex third moment;
- vertex mean;
- bbox centre;
- vertex count by side;
- area fraction by side;
- volume centroid;
- farthest extreme;
- net area normal.

Only the two surface-moment statistics give a consistent sign on any axis, and that axis is z (10/10). Four one-sided
statistics (bbox centre, farthest extreme, vertex count, area fraction) give 9/10, all failing on wooden_piece_2, whose z
is essentially symmetric (+0.0003). Under random
signs, p = 2⁻¹⁰. After allowing for about 10 statistics tested, p ≈ 0.02. These are also the two textbook PCA
sign-disambiguation heuristics, which raises the prior. In physical terms, +z points to the "thin tail":
- the pot's handle end;
- the dust pan's handle end;
- the cups' base, because the open, flared rim carries more area (cups rest −z up);
- the sweeper's handle (up).

**x/y pair (180° roll about z): unresolved.** [H]
- **"skew_x > 0, y = z × x"** fits 7/10. It fails on beige (−0.090), pitcher (−0.014) and **wooden_piece_2 (−0.536)**.
  The last failure is far outside any estimator noise, so the rule is rejected unless that asset was hand-edited.
- **"skew_y > 0, x = y × z"** fits 7/10. All three failures (blue −0.009, pot −0.009, dust pan −0.001) have
  |skew_y| < 0.01, as do two successes (lid +0.008, wooden_piece_2 +0.004). Every scan with |skew_y| ≥ 0.018 has
  skew_y > 0 (5/5, p = 1/32 by chance). This is consistent if the organisers estimated the sign from a sample of about 1e4–1e5 points (skewness
  standard error about 0.01–0.025). **This is the best-supported hypothesis, but it is weak.**
- **"Larger-|skew| of x/y is positive"** fits 9/10 but also fails on wooden_piece_2.
- **Hybrid**: "use skew_y > 0 if |skew_y| ≥ 0.02, else skew_x > 0" also fits 9/10 and fails only on wooden_piece_2. The
  threshold was chosen after seeing the data; any value in (0.0092, 0.032) gives the same result.
- **Up at rest**: up is +x for 5 of the 6 flat objects (wooden_piece_2 is −x). This is confounded with skew_x, because
  protruding features face up at rest.

wooden_piece_1 and wooden_piece_2 match each other to 1.6–1.9 mm Chamfer under all 8 axis-sign maps (`wp_compare.py`), so
their shapes cannot explain the different sign. Handedness (det = +1) is assumed, not testable: it cannot be determined
from the final mesh alone.

**Consequence for the spoon.** Its y axis (width) is a mirror-symmetry axis, so skew_y ≈ 0. Under the best hypothesis the
organisers' y sign, and hence the roll, is noise-determined, giving **P(correct) ≈ 0.5**. If instead the skew_x rule held,
the spoon's x would be determined (see section 3). Overall confidence in any roll choice is 50–60%.

## 3. Rule R1, specified so we can apply it to our spoon

Input: a closed, metric triangle mesh of the spoon. Faces F index vertices V.

1. Per triangle (a, b, c) compute the area A_t and s = a + b + c.
2. **Origin**: c₀ = Σ A_t·s/3 / Σ A_t.
3. **Covariance**: C = Σ A_t·(aaᵀ + bbᵀ + ccᵀ + ssᵀ)/12 / Σ A_t − c₀c₀ᵀ.
4. **Axes**: (λ, E) = `numpy.linalg.eigh(C)`, eigenvalues ascending. Then x = E[:,0] (thickness), y = E[:,1] (width) and
   z = E[:,2] (length).
5. **Signs**:
   - **z**: flip so that m₃(z) > 0, where m₃(n) is the exact third moment
     Σ A_t·h₃(f_a, f_b, f_c)/10 / Σ A_t with f = (v − c₀)·n, and h₃ is the complete homogeneous cubic,
     the sum of all 10 monomials of degree 3.
   - **Roll tie-break**: if |skew_y| ≥ 0.02, flip y so that m₃(y) > 0 and set x = y × z. Otherwise flip x so that
     m₃(x) > 0 and set y = z × x. Record which branch fired; the second branch is a ~50/50 guess (section 2).
6. **Write out**: store the mesh as V' = (V − c₀)·Rᵀ with R = [x; y; z] rows. Use metres, write a GLB with identity
   nodes, and a URDF with identity origins.
7. **Verify** on the saved file: |c₀| < 1e-6 m, off-diagonal/diagonal < 1e-6, ascending diagonal, signs as chosen.

`canon.py::canonical_frame()` implements steps 1–5; `xy_rule="hybrid"` is the step-5 tie-break. `verify_rule.py`
shows it reproduces all 10 published frames:
- origin and axes exactly;
- z sign 10/10;
- the (x, y) pair 7/10 with `skew_x`, 7/10 with `skew_y` and **9/10 with `hybrid`** (fails on wooden_piece_2; this is a
  post-hoc fit).

**Expected outcome on a wooden spoon** [V on a parametric model, H for the real spoon].
- **Model**: `canon.spoon_mesh`, 30 cm long, a 7.5 × 5.4 cm bowl 12 mm deep, a 16–22 mm handle.
- **Eigenvalues**: λy/λx ≈ 6 and λz/λy ≈ 81, so the axes are well conditioned. Over 144 shape variants the minima are
  1.5 and 30.
- **Origin**: lies on the long axis 37–50% of the length from the bowl tip (nominal 42%).
- **z (skew +0.38)**: points from the **bowl toward the handle end** in 138/144 variants. The 6 exceptions are paddle-like
  shapes (narrow 4 cm bowl, 3.2 cm handle, 4 mm-deep bowl) with |skew| < 0.04. If our mesh gives |skew_z| < ~0.1, flag
  it.
- **x under the `skew_x` branch**: points to the **convex back of the bowl** (skew_x +0.28), in 139/144 variants.

## 4. Residual ambiguity and sensitivity

- **Discrete**: the z sign (if the z rule is wrong) and the roll sign. Each costs about 0.5 SP-SR on the board (section 5).
- **Near-degenerate eigenvalues** [V] (`rule_robustness.log`):
  - **Cups**: λy/λx = 1.04–1.05. The in-plane x/y axes swing by 37°, 79° and 90° under a 3 cm missing patch or a 2%
    anisotropic scale error.
  - **Lid**: λz/λy = 1.13; it swings 33° under a missing patch.
  - For these objects R1 cannot recover the published yaw from a reconstruction. The yaw is set by tiny scan asymmetries
    and must come from registration to the public scan (texture or geometry), if that is allowed **[?]**.
  - The spoon is well conditioned.
- **Defects on well-conditioned public objects** [V]:
  - The origin moves 1–10 mm for a missing underside or a 3 cm patch.
  - The axes move < 1° typically, up to 11° (sweeper, missing patch).
  - Smooth 1 mm noise and 2% scale error change the origin by ≤ 0.25 mm and the axes by ≤ 0.2°.
- **Spoon reconstruction errors** [V, parametric] (`spoon_sensitivity.log`):

  | spoon error | origin moves | axes rotate |
  |---|---|---|
  | handle length ±1 cm | 4.7 mm along z | 0.06° |
  | bowl width ±10% | 3 mm | |
  | bowl depth ±50% | 3.7–4.7 mm | 0.65° |
  | handle +20% wider | 5.5 mm | |
  | handle bent 5 mm | | 0.9° |
  | handle tilted 3° | 3.5 mm | 2.4° |
  | missing bowl underside (17.5% of area) | 18.7 mm | **x/y sign flips** |
  | missing last 3 cm of handle | 14 mm | |

- **Triangle noise biases the area centroid** [V] (`spoon_noise_check.py`). Per-vertex iid noise inflates area unevenly.
  On a 0.8 mm-edge mesh, 0.5–1 mm noise moves the origin by 12–19 mm. On 4.6 mm edges it moves 1.6–6.5 mm. So **smooth
  and isotropically remesh (≥ 2–3 mm edges) before canonicalising**, and check that the area ratio against a smoothed copy
  is close to 1.
- **[?] The spoon scan may not follow this pipeline.** All 10 public scans do, and the README says every tracked object
  has a scan in its own frame, but the confidential spoon scan is unseen.

## 5. Score impact of frame mismatch (kit scorer, public GT motions)

**Mechanism** [V, analytic and numeric]. Let M = ref_T_ours be our frame expressed in the scan frame. Our pose is
T(t)·M, and the scorer warps every body by A = T_ref0 · (T_ours0)⁻¹ of slot 0.

- **Spoon in slot ≥ 1** (eval episodes 3, 5, 6, 15, 16, 32, 33):
  - The error is constant in the body frame.
  - Position error = |t_M| and orientation error = ∠R_M.
  - Spoon MPPE = mean over keypoints k of |R_M·k + t_M − k|, with k = ±5 cm on each axis. A 180° flip gives 6.67 cm
    (3.33 per 2-object episode).
  - RPE grows by exactly |t_M|; rotation errors do not affect it.
- **Spoon in slot 0, alone** (episodes 35–37):
  - The error is 0 at t=0 and grows with motion.
  - The orientation error is ∠(R_Mᵀ ΔR R_M ΔRᵀ), where ΔR is the body rotation since the start.
  - Position error = (R_A − I)·d + R_A(R(t) − R0)·t_M, where d is the displacement since the start. A 180° error therefore
    costs 2|d⊥| of position.

**Setup**:
- Synthetic achieved = GT ∘ M on the "spoon" body.
- Hosts:
  - **slot 1**: the 13 public 2-object episodes, with the slot-1 object as the spoon proxy;
  - **slot 0**: the 13 public episodes whose slot-0 object rotates > 30° (spoon-like handling), scored alone.
- AUC vertices: public-scan samples, and a canonicalised parametric spoon for the proxy body.
- Paired smooth tracking noise is optional.
- Full tables: `score_impact_summary.log`.

**Per episode, perfect tracking**:

| M | slot 1: AUC | SP | MP | RPE cm | MPPE cm | slot 0 (moving): AUC | SP | MP | MPPE cm |
|---|---|---|---|---|---|---|---|---|---|
| none | 1.000 | 1 | 1 | 0 | 0 | 1.000 | 1 | 1 | 0 |
| roll 180° (about z) | 0.969 | 0 | 0 | 0 | 3.33 | 0.231 | 0.15 | 0 | 20.5 |
| 180° about x (wrong z sign) | 0.500 | 0 | 0 | 0 | 3.33 | 0.279 | 0.15 | 0 | 14.4 |
| 180° about y (wrong z sign) | 0.500 | 0 | 0 | 0 | 3.33 | 0.238 | 0.08 | 0 | 16.9 |
| hedge: 90° about z | 0.969 | 0 | 0 | 0 | 2.36 | 0.270 | 0.15 | 0 | 14.6 |
| 5° about x | 1.000 | 1 | 1 | 0 | 0.15 | 0.975 | 1 | 1 | 0.65 |
| 10° about x | 0.969 | 1 | 1 | 0 | 0.29 | 0.893 | 1 | 1 | 1.30 |
| 20° about x / about z | 0.906 / 1.000 | 1 | 1 | 0 | 0.58 | 0.720 / 0.640 | 0.92 | 0.54 / 0.38 | 2.6 / 3.6 |
| centroid 0.5 cm (z) | 1.000 | 1 | 1 | 0.5 | 0.25 | 1.000 | 1 | 1 | 0.33 |
| centroid 1 cm (z) | 0.982 | 1 | 1 | 1.0 | 0.50 | 0.982 | 1 | 1 | 0.66 |
| centroid 2 cm (z) | 0.930 | 1 | 1 | 2.0 | 1.00 | 0.921 | 1 | 1 | 1.32 |

Offsets along x or y behave like offsets along z (within 10%).

**With smooth tracking noise of 1 cm / 5° per object**:
- Slot-1 baseline: AUC 0.547, SP 1.0, MP 0.08, RPE 2.16, MPPE 4.51.
- **Roll flip**: SP → 0 and MPPE +1.9.
- **1–2 cm offsets**: RPE +0.28 / +0.89 cm, MPPE ±0.04.
- **≤ 10° tilts**: MPPE ≤ +0.03.
- At 2 cm / 10° the baseline SP-SR is already 0.38 and a flip removes it.

**Leaderboard delta** = (7·Δslot1 + 3·Δslot0) / 20 (`lb_aggregate.log`; moving slot-0 hosts):

| M | noise | ΔAUC | ΔSP-SR | ΔMP-SR | ΔRPE cm | ΔMPPE cm |
|---|---|---|---|---|---|---|
| roll 180° | none | −0.126 | −0.477 | −0.500 | 0 | +4.25 |
| roll 180° | 1 cm/5° | −0.072 | −0.477 | −0.073 | 0 | +3.20 |
| wrong z sign (180° about x / y) | none | −0.28 / −0.29 | −0.48 / −0.49 | −0.50 | 0 | +3.3 / +3.7 |
| hedge 90° about z | none | −0.121 | −0.477 | −0.500 | 0 | +3.02 |
| centroid 1 cm | none / 1 cm/5° | −0.009 / −0.001 | 0 | 0 / −0.01 | +0.35 / +0.10 | +0.27 / 0.00 |
| centroid 2 cm | none / 1 cm/5° | −0.036 / −0.008 | 0 | 0 / −0.04 | +0.70 / +0.31 | +0.55 / +0.05 |
| tilt 5° (x) / 10° / 20° | none | −0.004 / −0.027 / −0.075 | 0 / 0 / −0.01 | 0 / 0 / −0.07 | 0 | +0.15 / +0.30 / +0.59 |

The SR deltas are upper bounds: they assume the affected episodes would otherwise succeed.

**Hedging is dominated.** Suppose the true roll is 50/50 and we compare committing to one sign against a 90° hedge.
- **Spoon-body MPPE**: committing gives 0.5 × 6.67 = 3.33 cm expected, against 4.71 cm for the hedge.
- **Per 2-object episode MPPE**: committing gives 1.67, against 2.36.
- **Slot-0 MPPE** on moving hosts: about 10.3 against 14.6.
- **Expected SR**: 0.5 against 0.

**Commit to one sign.**

AUC caveat: the organisers' AUC vertex payload is not public, so the spoon AUC uses parametric-spoon samples (±10%). The
noise model is a paired Gaussian-smoothed random process (σ_t = 20 frames), not a tracker.

## 6. Recommended spoon-frame strategy

1. **Before training any spoon policy**, fix the spoon asset frame by R1 (section 3).
   - Bake it into the GLB vertices with identity nodes, in metres and raw coordinates.
   - Use a URDF with identity origins and the same uniform-surface inertial convention.
   - Express our object references in that frame.
   - The body frame may enter observations and rewards, so changing it after training could require retraining
     (**[?]** check FlashCHORD's observation definition).
2. **Make the reconstruction closed and complete before canonicalising.** Both bowl faces and the full handle must be
   present. Smooth or remesh to ≥ 2–3 mm edges and check for area inflation. Missing or noisy surfaces move the origin by
   1–2 cm and can flip the roll.
3. **z**: use skew_z > 0, which should come out bowl→handle. If |skew_z| < 0.1, treat z as uncertain too.
4. **Roll**: use the tie-break in section 3. Record the choice in the handoff as a ~50% bet worth about 0.48 SP-SR and
   about 3–4 cm MPPE on the board.
5. **Resolve the roll bit cheaply.**
   - (a) **Preferred: ask the organisers** to publish the spoon frame (its R1 sign bits, or the canonicalisation
     code/sign rule). Also ask whether public-scan frames may be used for the 9 scanned objects.
   - (b) **If they will not answer**, a two-submission A/B that differs only in the spoon roll would reveal it from the
     MPPE difference (expected Δ about 3–4 cm). This is only an option if our pipeline can re-export the same rollouts in
     a rotated body frame without retraining, and if it is acceptable under the Kaggle rules. Note that `private_fraction`
     is 0, and the sponsor holds a further hidden evaluation.
6. **Do not hedge** with intermediate rolls (section 5).
7. **Side finding for the other objects.** For the cups (eval episodes 8, 10, 14, 20, 32, 33) and the lid (episode 1),
   R1 alone cannot fix the in-plane axes. For every scanned object, matching the published frame needs registration to
   the public scan, if allowed **[?]**. Otherwise expect large constant orientation errors on MPPE and SR even with
   perfect tracking.

## 7. Falsification tests and open items

- **z-sign rule.** One scan with a confident skew_z < 0 refutes it. Candidates: any scan the organisers release later,
  or an answer from them.
- **Roll hypotheses.** The y-skew hypothesis predicts that a re-estimate from ~1e4 surface samples will sometimes flip
  blue_cup, white_pot and mini_dust_pan, but never beige_cup or water_pitcher. It cannot be tested without their code.
- **[?]** Whether wooden_piece_2's x was edited by hand. It is the only confident contradiction to an x-based rule.
- **[?]** Whether the confidential spoon scan used the same pipeline. Whether invisible reference frames exist in the eval
  set (none in the public set).


---
[← Index](../README.md) · [Summary](../00-summary.md) · [← 06](06-timing-audit.md) · [08 →](08-architectures-accuracy.md)
