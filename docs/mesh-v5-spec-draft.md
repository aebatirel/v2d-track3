# Mesh pipeline v5: global decisions and port specification

2026-10-22. Status: **proposed**; nothing is ported yet. Repo at writing: `fc775d4` (branch `main-bsky37`), unmodified.
Freeze 2026-11-04.

Labels: **[M]** measured with method inputs only (no scan, no mocap). **[D]** diagnostic: public scans or mocap, read
after inference and used only for global method choices. **[E]** estimate. **[H]** hypothesis, always with the
experiment that would falsify it.

Sources:
- The five reports of the v5 evidence round, under `scratchpad/interact/v5/`:
  - `metric/`: the acceptance metric;
  - `obsnew/`: observation-first fusion on all objects, episode weighting, decimation;
  - `spoon/`;
  - `xcarve_adv/`: adversarial test of the interaction rules;
  - `s5coll/`: collision path.
- The judged plan and its critique: `docs/research/work/interaction-meshes-2026-10-22/`. The critique's corrections
  are binding here.
- Two small CPU checks run for this spec, **E0** and **E0c** (§11.1), in `scratchpad/interact/v5/spec/`. Commands are
  in `spec/COMMANDS.txt`.

> **Read this first.** Every [D] number of this round was produced on **scan-contaminated inputs**:
> - scan-templated `loc/perc` tracks;
> - library_v2 as region of interest, `--others` and band mask.
>
> These numbers therefore choose the *shape* of the method only provisionally. §11 lists the confirmatory runs on
> compliant inputs. Their acceptance rules are written down here, before they run.

---

## 1. Decisions at a glance

| # | Decision | Main evidence | Status |
|---|---|---|---|
| D1 | **Acceptance rule.** Rule A for shape changes and Rule B for physics-only changes (§2). Flips are checked on ≥ 6 seeds, including every eval seed. Scans decide global choices only. | metric report | adopted |
| D2 | **Mesher = observation-first `4c12_adj_g2_f0_cont@lc25`.** 2 mm voxels in a region of interest. The per-frame below-table votes are **removed**; below-table hits are kept as a counter (NB). | **E0** [D]: −0.0154 cm CD-O, −1.25 mm registration offset, no new flip vs library_v2. With below-table votes the boards gain flips (wp1 1/6, wp2 2/6). | provisional until E1 and E2 |
| D3 | **Per-object switches only through frozen ground-truth-free gates:** G1 ≤ 0.5 cm³, G2 ≤ 0.05, topology, flip check against our own reference mesh, and (per eval episode) consistency with the seed ≤ 0.5 cm. | obsnew; metric `xreg`; **E0c** [D]: G2 alone admits 2 bad single-episode meshes, G2 + consistency admits 0 | adopted; consistency needs the owner's OK (O3) |
| D4 | **Fallback mesher** = today's `recon_mesh` at 4 mm, with compliant `--others`. | Fallback to v2 (as a stand-in) gives −0.016 cm / −1.6 mm [D]. Fallback to today's rules at 2 mm gives +0.083 / +0.8 [D]. | **unmeasured on compliant inputs → E2** |
| D5 | **Not ported:** silhouette, `nbk`, episode weighting (R_w, R_sel), the local-fallback tier, finger masks, held-only fusion, today's rules at 2 mm as fallback, per-object parameters (the dust pan's `--edge_thr -1`). | §4.7 | rejected |
| D6 | **Decimation:** open3d quadric to 4096 faces, then a topology check, then pymeshlab QEC in halving stages. Collision geometry is built from the full-resolution mesh. | 15/15 watertight with topology kept [M]; CD-O −0.004 cm vs kit [D] | adopted |
| D7 | **Support rule** (`rest_support.py`): at observed unassisted rests, flatten the underside only when the object cannot stand there. Strict acceptance checks. | ep18 0.345 → 0.715 with the hand-flattened sweeper (one seed, confounded) [D]; v3/v4 are metric-neutral and pass Rule B | adopted (Rule B) |
| D8 | **Interaction rules:** none on the submitted mesh and no carving on the collision copy in v5.0. Only the interaction-weighted *split* inside the convex decomposition runs, plus an overlap report. The WS+R1+R3 rule set is specified but parked. | xcarve_adv; s5coll | adopted |
| D9 | **Collision geometry:** our own convex pieces from the full-resolution mesh (≤ 64 vertices each), one `<collision>` element per piece. | s5coll | adopted; G2 measures training throughput |
| D10 | **Spoon:** the template fitted to the episode's own evidence (T_fit) if its gates pass, else the template T0. The fused spoon mesh is used as evidence only. | spoon report | adopted; owner questions O5 |
| D11 | **Provenance manifest and deny-list,** including transitively derived artifacts. G0 is a hard fail. | critique 10 | adopted |
| D12 | **Per-eval-episode re-fusion** = new stage 2m in `pipeline_ep.sh` (§10). | owner decision 11:20 | to build |
| D13 | **GPU:** G1 re-tracks 16 public episodes (≈ $2–3), G2 tests on ep18/12/27 plus an ep24 smoke run (≈ $13–18), then G3 is the 20 eval episodes. | §12 | needs the owner's go-ahead |

**Expected effect, in plain words.**
- On the known objects, the measured mesh gains are small [D].
  - About −0.015 cm eval-weighted CD-O over the 26 known pairs, against a library mean of 0.49 cm.
  - About −1.3 mm registration offset.
- The ranking metric (ADD-AUC) moves through two channels:
  - registration, which is worth very little at these sizes [E];
  - physics, for example objects that can stand. The one measured case is ep18, +0.37 with a sweeper that could stand
    [D, one seed, confounded].
- So the main reasons for v5 are rule compliance (own meshes, re-fused per eval episode) and sim validity, not CD-O.

---

## 2. How scans may be used: the acceptance rules

### 2.1 Metric
`scratchpad/interact/v5/metric/mesh_metric.py` is ported as `tools/mesh_diag.py`, diagnostic only. It is the only
code in the repo allowed to open scans.

| Quantity | How it is computed |
|---|---|
| CD-O | the kit's `_object_chamfer_cm` |
| Registration | the scorer's `_register_object_body` |
| Mesh as the scorer sees it | both meshes go through the kit packer's `budget_mesh(4096, 4096)` |
| Seeds | every eval seed of the object (1_000_003·episode + 101·slot) plus extra seeds up to ≥ 6 |
| ADD_static | over the kit's 500 ADD vertices |
| Flip | rotation error > 90°, declared symmetries excluded |
| Weights | eval pairs: spoon 10, pot 6, blue cup 5, rack 5, beige cup 2, sweeper 2, dust pan 2, lid 1, pitcher 1, boards 1 each |

Weighted deltas are divided by the 26 known-object pairs. The script reproduces critique N1 and N2 within 0.005 cm and
0.4 mm [D].

### 2.2 Rule A: shape changes
Shape changes include the fusion rule, closing, below-table handling, decimation and the episode set. A global change
is accepted only if all three hold, measured at the scorer's eval seeds:
1. Σ w·ΔCD-O / 26 ≤ 0.
2. Σ w·ΔADD_static / 26 ≤ 0. For own-frame meshes, use the registered-AUC form in §2.4.
3. No object gains a flip on any seed (≥ 6 per object).

Objects whose scan-free ambiguity excess is often below 4 mm are the sweeper, the boards, the lid (median 3.2 mm) and,
by its template, the spoon (2.0 mm). For them, flips are also checked against the raw, unbudgeted scan.

### 2.3 Rule B: physics-motivated changes that touch the submitted mesh (new)
Rule B covers, for example, support flattening. A change is accepted if all four hold:
1. Σ w·ΔCD-O / 26 ≤ +0.001 cm.
2. Σ w·ΔADD / 26 ≤ +0.10 mm.
3. No new flip.
4. Its own CPU physics check improves (§6).

Why these bounds:
- The per-object seed spread is 0.002–0.008 cm CD-O and 0.5–1 mm ADD [D].
- At weight 2/26 that becomes 0.0002–0.0006 cm and 0.04–0.08 mm. The bounds are about twice that, so Rule B accepts
  changes that are neutral within noise.
- Under Rule B, v3 (+0.0001 cm / +0.03 mm, flips 2 → 1) and v4 (+0.0004 / −0.01) pass. Under Rule A both are
  rejected.

Changes that touch only the collision copy cannot change CD-O or registration. They are judged by the S5 acceptance
tests (§8).

### 2.4 Own-frame meshes
Compliant v5 meshes live in the frame of the `perc2m` tracks, which is library_v2's frame, not the scan frame. So the
identity target behind ADD_static no longer holds. For them:
- **CD-O [D]:** frame-free, unchanged.
- **Registered perception AUC [D]**, replacing ADD_static:
  - Run `score_registered.py EP poses_world_vo.npz --meshes DIR --reg_seeds eval` on every public episode of the
    object, with the same tracks for the base and the new mesh. Only the registration differs.
  - `--reg_seeds eval` is a new flag: it runs the kit registration at every eval seed of the object, not only at the
    public episode's own seed.
  - Rule A clause 2 becomes Σ w·ΔAUC_reg ≥ 0.
- **Flip:** a seed where an object's registered AUC drops by more than 0.2 against the base mesh at the same seed.
  `--frame_tf` from mocap is not needed.

### 2.5 No per-object choices from scans
- The per-object "best variant" tables are information only.
- A parameter may differ between objects only through a frozen ground-truth-free gate.
- The dust pan's `--edge_thr -1`, used in the library and obsnew builds, is a per-object exception picked with
  registered AUC [D]. It is **removed**, and E3 picks one global value.

---

## 3. Provenance (G0)

### 3.1 Tiers
- **P0, allowed anywhere:**
  - raw episode media: stereo mono video, colour video, `calib.json`;
  - our FoundationStereo depth caches (`cache/depth/{public,eval}/ep<N>`);
  - MediaPipe hands, lifted with our depth and our camera VO, from a perception run of tier P0 or P1;
  - object names and slot order (parquet first row, or the kit roster);
  - kit and FlashCHORD code;
  - the spoon template (`spoon/spoon_template.py`, `params.json`; dimensions from our own stereo measurements of eval
    clips, notes 13 and 20).
- **P1, bootstrap-derived; allowed only if the owner accepts it (O1):**
  - tracks made by `perc2` with `MESH_DIR=meshes/library_v2` (`perc2m`), and everything computed from them;
  - library_v2 is on the deny-list and entered these tracks only as the tracking template;
  - every v5 mesh, every eval track seeded by v5, and so every eval mesh, inherits P1.
- **DENY, never an inference input:** see §3.2.

An artifact's tier is the worst tier among its inputs. A DENY input aborts the step.

### 3.2 Deny-list (`ops/provenance/denylist.json`)
**By path glob:**
- `**/t3/mesh/**`, `**/loc/t3/mesh/**`, `**/t3/urdf/**`: public scans and the organisers' collision meshes and URDFs;
- `meshes/library_v1/**` … `meshes/library_v4/**`: built with scans as `--others` and on scan-templated tracks;
- `**/loc/perc/**`: scan-templated tracks;
- `**/loc/refs/**`: references and hands built on `loc/perc` poses;
- every `perc2/ep*` output made without `MESH_DIR` (perc2 templated on scans);
- `**/oracle/**`: the mocap oracle;
- `scratchpad/interact/**`: every prototype grid, mesh and piece set (obs, minimal, joint, judge, review2, code,
  v5/obsnew, v5/spoon, v5/xcarve_adv, v5/s5coll). They used library_v2 as ROI and `--others`, or `loc/perc` tracks;
- runs made with `ASSET_SRC=public` (`20261022-r5ks*`).

**By sha256:** every public-scan file (`<obj>.glb`, `<obj>_visual.glb`, `<obj>_collision.glb`), every library_v1–v4
mesh, every `loc/perc/ep*/poses.npz`. This catches renamed copies.

**By code:**
- Only `tools/mesh_diag.py`, the `score_*.py` scorers and perc2's block after `# ---------- scoring` may read scans or
  the parquet `pose` field.
- A repo test checks that `pipeline/` never imports `tools/mesh_diag`.
- The same test greps for `'pose'` reads outside those places.

### 3.3 Manifest
Every mesh, track set, grid and asset directory gets `<file>.prov.json`:
```json
{"artifact": "...", "sha256": "...", "kind": "mesh|tracks|grid|assets|pieces",
 "tier": "P0|P1", "code_commit": "abc1234", "command": "...", "host": "...", "created_utc": "...",
 "params": {...},
 "inputs": [{"role": "depth|poses|hands|others|roi|seed|video|calib", "path": "...", "sha256": "...",
             "tier": "P0", "manifest": "path or null"}]}
```
`pipeline/provenance.py` provides:
- `write(out, inputs, params)`;
- `check(inputs) -> tier`. It raises on any DENY match (glob or sha). It also raises when a mesh, track or grid input
  has no manifest: unknown provenance counts as DENY.

### 3.4 Enforcement points (hard fail)
| Code | Check |
|---|---|
| `recon_mesh.py` | `--poses`, `--others`, `--roi`, `--seed` |
| `perc2.py` | Under `SPLIT=eval` or `COMPLIANT=1`: `MESH_DIR` is required, each `MESH_DIR/<obj>.glb` must pass `check`, and `scan_path()` must not be reached before the scoring block. |
| `mkref.py` | Under the same flags: `--assets` is required; the `t3/mesh` fallbacks (`visual_mesh_path`, `contact_mesh_path`) are refused. |
| `make_assets.py`, `collision_decomp.py`, `rest_support.py` | input mesh |
| `ep_mesh.py`, `ops/build_library.sh` | all of the above, plus writing the manifests |
| packing wrapper | Every submitted mesh has a manifest with tier ≠ DENY. Prints the tier table. Records the commit URL. |

### 3.5 The bootstrap problem: owner decision O1
No compliant seed exists for the 10 known objects. Every track we have descends from the scans:
- `loc/perc` used scan templates;
- `perc2m` used library_v2, which was built on `loc/perc` with scans as `--others`.

Options:
- **(a) Accept P1 (recommended).** Our final chain never opens a scan. Scans influenced only the first tracking
  template. This is exactly question 3 of the pending organiser email
  (`docs/organiser-email-draft-2026-10-22.md`).
- **(b) Washout iteration.**
  - Re-track all public episodes with v5 seeds and rebuild v5: about $2–3 GPU and 3 h CPU.
  - Still P1 by the letter, but the scans' influence is two steps removed.
  - It also tests v5 as a tracking template, which G2b does anyway (§12).
- **(c) A scan-free bootstrap,** e.g. model-free object tracking from a first-frame partial scan. Days of work; not
  planned.

---

## 4. Mesher (S1)

The same code runs for the library (all public episodes of an object, summed) and per eval episode (that episode only).

### 4.1 Pass 0 (exists)
`recon_mesh.py` in classic mode:
- voxel 4 mm, truncation 12 mm, `--close auto`;
- `--below_carve 0.004`, table band 15 mm;
- hand capsules 30 mm, forearm 45 mm × 15 cm;
- `--edge_thr` = the global value from E3;
- stride 2, `--others` none.

The output is M0, used for two things only:
- the region-of-interest box;
- the other-object labels in pass 1.

### 4.2 Evidence fusion: `recon_mesh.py --mode obs --save_grid`
A port of `v5/obsnew/scripts/obsfuse4.py`, without the band-mask deltas.

**Grid:** M0's bounds plus 40 mm, voxel 2 mm (0.9–3.2 M voxels [M]).

**Per-sample rules** (same as today's `integrate()`):
- table band 15 mm over a per-frame refit plane (≤ 10° correction);
- hand capsules 30 mm on every bone, forearm 45 mm × 15 cm;
- other objects: their M0 posed by this episode's tracks; samples within 12 mm carve but never vote surface;
- edge filter (E3), `zmax` 1.5 m, stride 2 (= the every-2nd-frame float16 caches used in every measurement).

**Accumulators:**
| Name | Content |
|---|---|
| `S{4,6,12}`, `W{4,6,12}` | TSDF sums and weights at truncation τ. Own samples vote; other-labelled samples only where sdf > τ. |
| `NF` | samples with sdf > 8 mm |
| `NF3` | samples of any label with sdf > 3 mm |
| `NFL3` | the same, from table, hand or other-labelled samples only |
| `NV` | number of views |
| `M0/M1/M2` | moments of the object's own samples (\|sdf\| ≤ 12 mm) |
| `NB` | frames in which the voxel lies more than 4 mm under that frame's plane. **Not added to S/W.** |
| `NBR`, `NVR` | **new, for E1:** the same as NB and NV, counted only in rest frames |

**Fix:** `table_plane` line 89 uses `np.linalg.svd(..., full_matrices=False)`. Today it allocates an N×N matrix.

### 4.3 Post-pass: `pipeline/mesh_post.py`, variant `4c12_adj_g2_f0_cont@lc25`
Ported from `obspost2.build`, `obspost5.main_part_lc` and `gate_ev`.
1. **Cascade:** use the 4 mm TSDF mean where W4 ≥ 3, else the 12 mm mean. Report the share decided only by 12 mm
   ("thickness unobserved", G5).
2. **Classes:** known = W ≥ 3; inside = known and mean < 0; seen-free = NF3 ≥ 2.
3. **Closing `adj`:** a connected component of unknown, not-seen-free voxels that does not touch the grid border is
   filled only if at least 50% of its boundary faces touch observed-inside voxels.
4. **Main part `lc25`:** merge components by an 8 mm dilation. Among the components at least 25% the size of the
   largest, keep the one nearest the grid centre. [M]: neutral on 8 objects (byte-identical meshes); it fixes the
   pitcher and the rack, where the old rule kept a ~1 cm³ fragment.
5. **Mesh:** marching cubes on the clipped continuous field (`cont`):
   - known voxels take their TSDF mean;
   - filled unknown voxels are −1;
   - outside voxels are at least +0.05.
6. **Fragments:** keep pieces with ≥ 5% of the largest piece's area and a centroid within 15 cm of it.
7. **Output:** `<obj>_O_full.glb` and a gate JSON. Every full-resolution S1 mesh of this round was watertight, some
   with 2 bodies [M].

### 4.4 Below-table handling (decided by E0)
Per-frame below-table votes are removed (`nobc`); NB stays as a counter.

| Set (gated; failing objects take library_v2 as a stand-in) | wΔCD-O cm | wΔADD mm | new flips |
|---|---|---|---|
| per-frame votes (`def`, today) | −0.0159 | −1.63 | **wp1 1/6, wp2 2/6** → reject |
| votes removed (`nobc`) | **−0.0154** | **−1.25** | none → passes Rule A |

Per object, `nobc` against `def` [D]:
| Object | nobc | def |
|---|---|---|
| beige cup | 0.725 / 6.4 | 0.732 / 5.7 |
| sweeper | 0.275 / 3.6 | 0.282 / 3.2 |
| board 1 | 0.177 / 5.5 | 0.216 / 3.2, 1 flip |
| board 2 | 0.228 / 3.1 | 0.326 / 5.5, 2 flips |
| **dust pan** | **0.342 / 7.4** | **0.252 / 3.6** |

The lid has no NB grid yet: its `def` value (0.377 / 12.6) was used in both sets.

**The cost is the dust pan.** A pan lying flat needs the space under the table carved, but per-frame planes are
uncertain by several mm:
- single-frame planes span 2.8 cm on ep23/24 [M];
- the scan posed by our tracks sits −15.6 to +5.1 mm from our plane [D];

so per-frame votes also erase real board wood.

**[H] Rest clip (E1).**
- *Rule:* during unassisted rest segments, take each segment's own robust plane (median of the per-frame refits). A
  voxel more than 6 mm below that plane in at least 50% of its in-view rest frames (NBR ≥ 0.5·NVR) is free space. The
  clip applies only to voxels that are not strongly observed inside (W4 ≥ 3 and mean4 < 0), and at most 5% of the
  solid may be clipped.
- *Prediction:* it recovers the dust pan (CD-O ≤ 0.28 cm) without board flips.
- *Falsified if* the clip set fails Rule A against `nobc` on compliant grids.

### 4.5 Gates and selection (GT-free, frozen now)
| Gate | Definition | Threshold | Evidence |
|---|---|---|---|
| G1 seen-free violation | solid voxels with NF3 ≥ 2 and NF3 ≥ 0.5·NV | ≤ 0.5 cm³ | obsnew |
| G2 unexplained evidence | share of evidence voxels (W12 ≥ 5, \|mean12\| < 0.25, M0 ≥ 5) farther than 8 mm from the solid's boundary | ≤ 0.05 | catches the pot (0.27), blue cup (0.18), rack, pitcher [M] |
| T topology (after §5) | every body watertight; body count and Euler number unchanged by decimation; ≤ 4096 faces and vertices. Bodies are reported but not limited: the classic mesher deliberately keeps nearby parts (the ep11 cup was cut in half by largest-only). | hard | N5 |
| X flip check (port of `metric/xreg.py`) | candidate registered with the kit's `_register_object_body` to our reference mesh **in the same frame** (M0 of the same build; per episode also the tracking seed, if O3 is approved), at every eval seed of the object plus extras up to 6 | no rotation > 90° (declared symmetry excluded) | boards: 23 of 31 meshes that gained a flip caught, 3 false alarms in 45 [M vs D]; blind to errors shared with the reference |
| C consistency (per episode only; owner O3) | kit chamfer (CD-O formula, Sim(3)) between the candidate and the tracking seed, seeds 11 and 22 | ≤ 0.5 cm [H] | **E0c** |
| G5 coarse-only share | report only | – | – |

**E0c [M against D].** On the 19 single-episode O meshes of this round:
- The GT-free chamfer to the library mesh ranks them like their scan CD-O: Spearman 0.86, p 3e-6.
- G2 alone accepts 6 of 19, including blue cup ep11 (CD-O 1.173 against v2's 0.523) and ep21 (0.749).
- G2 plus C ≤ 0.5 accepts 4 (blue cup e12; dust pan e18 and e40; sweeper e31). All 4 beat v2 on CD-O (−0.031 to
  −0.085 cm) and ADD.
- Caveats:
  - the reference was library_v2, which is contaminated and close to the scan;
  - 0.5 was chosen after seeing these numbers;
  - so the gate is [H] until E8 repeats this with v5 leave-one-out references.

**Selection, per object:**
1. O, if G1, G2, T, X and (per episode) C all pass.
2. Else F4, the fallback mesher (§4.6), if T, X and C pass.
3. Else the tracking seed (owner decision O2). If O2 is refused, F4 with a QA flag.

Every branch taken is written to `ep_mesh.json` and the manifest.

T and X are checked again after the support rule and the final decimation. If they fail there, the unflattened mesh
is used; if that also fails, selection moves to the next branch.

### 4.6 Fallback mesher F4
- `recon_mesh.py` classic mode with today's defaults: 4 mm, 12 mm, `--close auto`, `--below_carve 0.004`, global
  edge filter.
- `--others` = M0 of the other objects of the same build or episode, i.e. our own meshes only.
- **Its quality on compliant inputs is unmeasured.** v2 is the only stand-in, and it was built with scans as
  `--others` and per-object settings. In the contaminated round F4 would serve 17 of 26 known pairs (pot, blue cup,
  rack, pitcher), so **E2 is the most important CPU experiment.**

### 4.7 Not ported (evidence)
| Item | Why |
|---|---|
| Silhouette free space (S2, `maskfuse`) | ego_cam_c is effectively grayscale. ≤ 1.2 cm³ effect and \|ΔCD-O\| ≤ 0.013 cm on the new objects [D]; ≤ 0.004 cm on the spoon proxies [D]. Not worth 2 min per object-episode or the colour-model risk on white objects. |
| `nbk` (below-table hits block closing) | dust pan 0.345 / 6.3 vs 0.252 / 3.6 [D]; also inflates G1 |
| Episode weighting R_w | pre-registered test failed: 1 of 4 objects [D] |
| R_sel | exploratory; loses on the dust pan; its confirmation test cannot apply |
| Local-fallback tier (`fb`) between O and F4 | ungated +0.050 / +1.5 [D]. Gated, it changes only the blue cup, for the worse (+0.033 / +0.7 against v2). The fb pot fails G1 (5.31 cm³) and the stability gate (tip 49.8° → 16.8°). |
| Today's rules at 2 mm as the fallback | +0.083 / +0.8 [D] |
| Finger-scale hand masks | falsified on all 4 spoon proxies [D] |
| Held-only fusion | flips 2–5 of 6 on the sweepers [D] |
| Per-object parameters | §2.5 |
| Seed band for known objects | uses the library mesh as a shape prior (owner rule) and was tested on 2 proxies only; kept for the spoon branch (§9) |

---

## 5. Watertight decimation: `pipeline/mesh_decimate.py` (port of `obsnew/scripts/decim.py`)
```
decimate(full) -> (mesh, info)
  t0 = topo(full)                      # watertight, bodies, Euler
  if faces <= 4096 and verts <= 4096: return full
  m1 = open3d simplify_quadric_decimation(target_number_of_triangles=4096); drop degenerate faces; weld
  if topo(m1) == t0 and m1 within budget: return m1
  m2 = pymeshlab meshing_decimation_quadric_edge_collapse(preservetopology, preserveboundary, preservenormal,
       optimalplacement, planarquadric, qualitythr 0.3, autoclean), halving stages while faces > 8192,
       then target 4096, retried up to 6x with target x0.9
  if topo(m2) == t0 and m2 within budget: return m2
  raise GateFail('T')                  # this candidate is not submitted
```
- **Measured** on 15 full-resolution meshes [M]:
  - open3d: 15/15 watertight with topology kept; median 24 self-intersecting faces; p95 deviation 0.49 mm;
  - CD-O against the kit decimation −0.004 cm, ADD +0.35 mm (noise) [D, 8 meshes];
  - pymeshlab: 15/15; median 8 self-intersecting faces; p95 0.61 mm; CD-O +0.010 cm [D].
- **Why it is needed:** the kit's own `budget_mesh` leaves only 6 of 144 S1 meshes watertight [M]. A mesh already
  within 4096 faces and vertices passes the packer unchanged (weld plus zero-area padding); the decimator asserts this
  by re-running `budget_mesh`.
- **Dependencies** (`setup.sh`): `open3d==0.20.0`, `pymeshlab==2025.7.post1` and the system package `libopengl0`.
  These are the measured versions.
- The full-resolution mesh is kept as `<obj>_full.glb`. **Collision pieces are built from it, never from the 4096-face
  file:** on ep24, CoACD refills the slot of the 4096-face file (13.5 cm³ overlap vs 6.7) [M].

---

## 6. Support rule: `pipeline/rest_support.py` (port of `minimal/auto_rest.py`, uses `flatten_base.flatten`)

**Inputs:**
- the chosen full mesh (body frame);
- that build's tracks (library: all public episodes of the object; per episode: that episode);
- MediaPipe hands;
- one robust table plane per rest segment: the median of the per-frame refits (critique 22).

**Steps:**
1. **Unassisted rest segment.** All of these must hold:
   - the origin moves less than max(2 mm, 2.5 × the track's own median frame-to-frame jitter) per frame (5-frame
     median); the jitter term fixes the missed ep18 rest at 1.75 mm/frame;
   - for at least 15 frames;
   - the mesh's lowest point is within ±20 mm of the plane;
   - no hand joint within 20 mm of the surface in at least 80% of the frames. A hand lost by MediaPipe counts as near
     if it was holding within the last 6 frames.
2. **Cluster** the rests by up vector (10°).
3. **Stability:** snap to the hull facet within 5° of the observed up. The mesh is stable if the centre-of-mass margin
   is ≥ 2 mm and the support area is ≥ 1 cm².
4. **If unstable:** `flatten(up, depth 8 mm)`. Accept only if all of these hold:
   - (i) stable at that rest;
   - (ii) no other observed rest becomes unstable;
   - (iii) solid removed inside strongly observed voxels (W4 ≥ 3 and mean4 < 0) ≤ 0.5 cm³. This needs the grid; for
     F4 meshes use their own 4 mm grid;
   - (iv) X flip check against the unflattened mesh passes;
   - (v) registration of flattened to unflattened moves ≤ 2 mm and 2° (G6).
5. **Scope:** the result is used for both the submitted mesh and the collision copy, so they stay one body. The spoon
   is excluded (it is a template, §9). Objects with no observed unassisted rest are never edited.

**Evidence:**
- Measured: the XCarve prototype reproduced the hand patches automatically: sweeper up within 2.2° of v3, board 2
  within 1.1° of v4 [M].
- Measured: v3 and v4 pass Rule B [D].
- ep18, flattened sweeper with stable-pose settling: 0.715 ± 0.240, against 0.368 ± 0.069 for kri with the v2 sweeper
  [D]. One seed; mesh and settling changed together.
- Hoped: the O sweeper (0.282 / 3.2, no flips) can stand after this rule without losing its registration advantage.
  Untested.

**[H]** Hull stability predicts the simulator. *Falsified if* an accepted mesh, placed at the observed rest in
`tools/replay_rest.py` (Newton engine, 2 s), tilts by more than 5°; acceptance then switches to the replay.
- Tilt is used, not sink: a single resting box already sinks 9.6 mm in 2 s [M].
- The replay uses the final collision pieces, because standing appears to depend on how many pieces touch the table
  (sweeper: our 30 pieces stand, CoACD's 19 topple [M]).

---

## 7. Interaction rules

**Submitted mesh: no interaction carving.**
- Every XCarve and joint variant failed the metric [D].
- On the S1 grids, R1+R3 changed the pot 0.732 → 0.743 and the lid 0.377 → 0.379 [D].

**Collision copy: no carving in v5.0.**
- The remaining physics blockers are mesh–mesh interference at our tracked poses [M]:
  - lid on pot: 25 cm³ with v3 meshes;
  - board 2: 12.0 mm thick, against a 9.5 mm board-1 slot.
- The gated S3 rules cannot remove that safely:
  - Gss rejects the correct ep2 track;
  - R2 turns track bias into real cuts the gates cannot see;
  - the claim-gate margins are thin and were calibrated on scan-templated tracks.

**What runs automatically:**
1. **Interaction-weighted splitting in the convex decomposition (§8):** free space that the partner occupies within
   1 mm, under our tracks, weighs λ = 10. It never removes solid. ep24: hull overlap 4.1 → 3.0 cm³, and the only
   variant that stayed upright from both track sources [M].
2. **Overlap report** (GT-free, QA only), per contact pair, in `ep_mesh.json`:
   - mesh–mesh and hull–hull overlap at static co-located frames;
   - acceptance metric: hull overlap minus mesh overlap ≤ 1 cm³ (S5 correction).

**Parked, ready to port for v5.1** (only if G2 or the CPU replays show interference-driven failures):
- R1 + WS + R3 with ratio 2;
- K = 5 sampled frames at stride 2, reached within one episode;
- claims only where the partner voxel is observed;
- per-episode claim gates Gsse AND Gcon (contested share ≤ 0.25);
- outcome gates: carve ≤ 10% of the solid, no split, no new tunnel or cavity (one-sided Betti);
- output to the collision copy only;
- worst real material carved under bias: 0.75 cm³ (pot) [D].
- **Never:** R2 in either form, Gobs, the literal item-17 gate, summing claims across episodes, any decision that
  depends on G1.

**[H] Outside the mesh pipeline: start-state interference fixed on the pose side.**
- *Rule:* at reset, `mkref` lifts the upper object of a stacked pair along the contact normal until mesh overlap is
  below 0.1 cm³.
- *Evidence so far:* with the lid lifted 15.3 mm, default CoACD stayed seated, 2.8 mm drift [M].
- *Test:* CPU replay of ep2 f330 with v5 meshes.
- *Falsified if* the lifted lid still drifts more than 10 mm or tilts more than 5°.

---

## 8. Collision geometry: `pipeline/collision_decomp.py` (port of `s5coll/scripts/decomp.py`) and `make_assets.py --pieces`

### 8.1 Facts [code + M]
- The evaluator loads the URDFs our reference names (`mkref --assets`). Kaggle scores the submitted trajectories and
  does not re-simulate.
- Newton makes one shape per `<collision>` element; 32 elements gave 32 MuJoCo geoms [M].
- FlashCHORD's CoACD (threshold 0.05) returns each of our convex pieces as one hull, changed by ≤ 0.024 mm (256 of 256
  pieces) [M].
- MuJoCo uses at most 64 hull vertices.
- The local FlashCHORD checkout is byte-identical to the kit pin in `scene/objects.py`, `assets/mesh.py` and
  `scene/builder.py`.
- **No evaluator-side change is needed.**

### 8.2 Recipe
1. Input: `<obj>_full.glb` after the support rule, in the body frame.
2. Solid from the winding number on a grid: pitch ≥ 1.5 mm, ≤ 1.2 M points, **chunked inside-test** (without it the
   lid run was killed for memory).
3. Free space = points more than 0.75 mm outside the mesh (0.5 mm when a partner weight applies).
4. Split recursively. Candidate planes: the PCA axes of the piece, of the mesh and of the piece's excess points, at 19
   offset quantiles, with 1 mm overlap between cells. Split the piece with the largest weighted excess by the plane
   that minimises the children's summed excess.
5. Stop when every piece holds ≤ 0.3 cm³ of free space, or at the cap: **32 pieces, 64 if the solid is above
   300 cm³**. The cap rule is GT-free but new [H]: the pot needed 64 to reach 1.20× its volume; the rack, pitcher
   and cups were never decomposed this way. G2 measures the cost.
6. Each hull is reduced to ≤ 64 vertices by furthest-point insertion, so MuJoCo uses exactly this hull.
7. Optional partner weighting λ = 10 (§7), from our tracks of the same build or episode.
8. `make_assets.py --pieces DIR`:
   - one OBJ and one `<collision>` element per piece;
   - visual = the submitted (decimated) mesh;
   - mass 0.3 kg; COM and inertia from the mesh surface, as today;
   - no colours (Newton splits coloured meshes).

### 8.3 Acceptance (S5, corrected)
- Hull overlap minus mesh overlap ≤ 1 cm³ at static co-located frames. This replaces "≤ 1 cm³", which was out of
  reach because the meshes themselves overlap.
- Union of the pieces ≤ 1.25 × the solid volume. This threshold was set after seeing the measured 1.18–1.20 at 32/64
  pieces (the old 1.15 gate failed them). It is GT-free and touches only the collision copy.
- Rest replay (Newton engine, 2 s): tilt ≤ 5° at each observed rest of a single object.
- 64-world build ≤ 2× default CoACD in time and memory. Measured: 1.25× time, 1.11× memory [M].
- **Unmeasured, measured in G2:** training throughput and GPU memory at 4096 worlds. Host memory per world doubles
  (1.27 → 2.63 MB), so about 11.4 GB at 4096 worlds instead of 5.8 [E].
- `check_urdf` will warn "differs from the pose mesh"; this is expected.

### 8.4 Measured on ep24 (frames 213–273, our tracks)
| Collision set | Hull overlap, cm³ |
|---|---|
| v4, default CoACD | 16.8 |
| O 4096-face mesh, default | 13.5 |
| O full-res, default | 6.7 |
| O full-res, our pieces | 4.1 |
| O full-res, weighted pieces | 3.0 |
| mesh–mesh floor | 1.2 |

No variant kept the boards within 2 mm in the replay; results swing up to 4× between track sources.

---

## 9. Spoon (10 of 36 pairs; 32.5% of the final AUC)

Answer: **submit the template fitted to that episode's own evidence (T_fit). If its gates fail, submit the unfitted
template T0. The fused spoon mesh F is never chosen automatically.**

**Basis:**
- Single-episode fused meshes on the proxies (sweeper, dust pan) score 0.25–0.46 cm CD-O [D].
- The template family scores 0.10–0.12 cm [M-synthetic].
- Flip risk: 0 flips in 800 kit registrations of 10 candidates against 16 plausible spoons [M-synthetic]. The template
  lands a median 1.9 mm off (p90 3.3, worst 4.2).
- The spoon frame A/B question no longer matters: the kit registers our mesh to the scan before scoring [code].

**Per eval episode (stage 2m, spoon branch, CPU about 10–15 min) [E]:**
1. **Fusion** (port of `spoon/code/spoonfuse.py`; one pass accumulates both rule sets):
   - **rule `cap_bm_sb`:**
     - 30 mm hand capsules;
     - a lost holding hand is carried forward ≤ 6 frames (new code: the prototype carries only in its finger-mask
       rules);
     - the 15 mm table band is not applied inside the template's outline eroded by 5 px;
     - seed band: samples more than 6 mm outside the posed template may carve but never vote surface;
   - **rule `cap_bm`**, the same without the seed band, used only for the consistency gate;
   - other objects: this episode's M0 meshes at 12 mm, always included. Labelling only drops their surface votes; it
     never carves solid;
   - 2 mm voxels, truncations 4/6/12 mm, all frames, stride 2.
2. **Post-pass** `4c12_adj_g2_f0_cont` gives F plus its G2. QA and evidence only. **No silhouette pass:** a change from
   the spoon report, per D5; its effect there was ≤ 0.004 cm.
3. **Evidence export (new code):**
   - zero-crossing voxels of the 4 mm field with ≥ 3 votes, from the `cap_bm_sb` grid;
   - seen-free voxels (NF3 ≥ 2).
4. **Fit:** `fit_spoon_cpu.fit(E, Fp)` (with `fd_jac` and `residuals`) replaces the `spoon/fit_spoon.py` skeleton.
   - It uses an absolute finite-difference step; scipy's relative step moved nothing at x = 0.
   - The fitted rigid pose is applied to the vertices, so T_fit stays in the track frame.
5. **Gates** (GT-free, frozen now):
   - prior: no parameter beyond 3 prior standard deviations;
   - median data residual ≤ 1.0 mm;
   - both faces covered: ≥ 20% of the evidence on each side of the bowl's mid-surface [H, uncalibrated];
   - mesh topology T;
   - flip gate X against T0 at all 10 spoon eval seeds: rotation ≤ 10° and offset ≤ 3 mm;
   - self-ambiguity excess ≥ 0.9 mm;
   - template consistency: ≤ 5% of the `cap_bm` evidence farther than 8 mm from T_fit. If this fails, T0 is
     submitted and the episode is flagged for owner review.
6. **Selection:** T_fit if every gate passes, else T0.
7. Collision pieces (§8). No support flattening.

**Measured [M-synthetic]:**
- The fit helps only when the evidence covers both sides and is unbiased: CD-O 0.119 → 0.100.
- The prior gate rejects 5 of 6 top-only fits and 6 of 6 biased fits.
- The error of a real spoon outside the template family is **unmeasured**.

**Optional GPU step:** re-track the spoon with T_fit when it differs from T0 by more than 1.5 mm or 3° (≈ $0.1–0.3
per episode [E]). Off by default.

**Dry run, allowed now.** Eval ep3 and ep35 already have perception outputs in the store (`runs/20261022-spoon-40ff0cd`).
- The CPU branch can run on them with frozen parameters, to produce overlays for the owner's visual check.
- No parameter may be changed because of eval outputs. A bug fix found this way is re-validated on proxies or public
  episodes before freezing again.

**Owner questions (O5):**
- Does a template fitted to our own observations count as "our reconstruction"?
- May we fall back to the unfitted template?
- May the spoon be fitted jointly over the 10 eval episodes (one physical spoon; this guarantees both faces are seen)?
- The seed band uses the template as a shape prior. Is that OK for the spoon?

---

## 10. Where it runs

### 10.1 Per-eval-episode re-fusion: `pipeline_ep.sh` stage **2m** (`MESH_REFUSE=1`)
It runs after stage 2b (hands) and before stage 3 (`mkref`), on the box CPU, while another episode trains (`TRAIN_LOCK`).

**Inputs:**
- `$P/poses.npz`: perception run with `MESH_DIR` = the seed library;
- `$P/depths_fs0.5.npy`, used at stride 2;
- `$R/hands.npz` (raw MediaPipe);
- `calib.json`;
- roster names;
- `MESH_DIR` seed meshes, used as tracking seed, gate references X and C (if O3 is approved) and spoon template.

**Steps:**
```
pipeline/ep_mesh.sh EP  ->  /content/meshes_ep/episode_<EP6>/<obj>.glb (+ _full.glb, .prov.json),
                            /content/assets_ep/ep<EP>/ (urdf + pieces), $R/ep_mesh.json
  0. provenance.check(all inputs)                          # G0, hard fail
  1. pass 0: recon_mesh classic 4 mm, --others none, every object  -> M0[obj]
  2. per known object (in parallel):
     a. recon_mesh --mode obs --save_grid (ROI = M0 bounds + 40 mm, --others = M0 of the other objects)
     b. mesh_post 4c12_adj_g2_f0_cont@lc25, below = nobc (or E1's winner)  -> O_full + G1, G2
     c. recon_mesh classic 4 mm, --others = M0 of the others  -> F4_full
     d. selection (sec. 4.5): O | F4 | seed (O2)            # gates T, X, C applied to the decimated candidate
     e. rest_support on the chosen full mesh (sec. 6)
     f. mesh_decimate -> submitted mesh (<= 4096, watertight, topology kept)
  3. spoon branch (sec. 9) if wooden_spoon is in the roster
  4. collision_decomp (sec. 8; partner weighting from this episode's tracks) -> pieces
  5. make_assets --pieces -> /content/assets_ep/ep<EP>
  6. overlap report; ep_mesh.json (branch, gates, volumes, pieces, timings); manifests
then stage 3 runs with ASSETS=/content/assets_ep/ep<EP>
```
- **Packing:** `tools/pack_submission.py --meshes /content/meshes_ep`. The kit expects
  `episode_XXXXXX/<object_name>.glb` in rollout body coordinates [code: `pack_submission.py` line 208].
- `score_registered.py` already accepts `DIR/episode_XXXXXX/<obj>.glb`.
- **Cost [E]:**
  - O fusion takes 1.5–13 min per object and episode, single thread [M];
  - F4 1.5–4 min;
  - decomposition 2.4–5.9 min per object [M];
  - the stage therefore takes about 10–25 min of wall time per episode on a 16+-core box, mostly overlapped with the
    previous episode's training.
- **Frozen parameters:** Appendix A. They are read from `pipeline/mesh_v5.json`, committed, and never set from eval
  outputs.

### 10.2 Library v5 (tracking seeds): `ops/build_library.sh`
- **Inputs:** perc2m tracks and hands for every public episode of the object (needs G1), and depth from the store.
- **Steps:** the same steps 1–6, summed over all public episodes of an object, with these differences:
  - C does not apply; X uses M0 as the reference;
  - fallback is F4 only.
- **Episode sets:**

  | Object | Public episodes |
  |---|---|
  | pot | 0, 2, 26, 27, 41–45 |
  | lid | 0, 2 |
  | blue cup | 11, 12, 13, 21, 22 |
  | beige cup | 11 |
  | rack | 12, 13, 26, 27, 31 |
  | pitcher | 21, 22 |
  | sweeper | 18, 31 |
  | dust pan | 18, 39, 40 |
  | boards | 23, 24 |

  These are all public episodes of each object, with no hand-picked lists (episode weighting was falsified). E2b may
  add one GT-free filter.
- **`--loo EP`** builds a leave-one-out library for the twin rehearsal (critique 13).
- **Outputs:** `meshes/library_v5/<obj>.glb` (submitted-style, ≤ 4096), `<obj>_full.glb`, pieces, manifests and a
  README with the gate table. The spoon in v5 = T0.
- **Consumers:** `LIB` default → `meshes/library_v5` in `auto_runs.sh`, `train_eval.sh`, `own_eval.sh` and
  `hard_ab.sh`. Today `train_eval.sh` and `own_eval.sh` still default to v1. v1–v4 are refused unless `DIAG=1`.

---

## 11. CPU work before any GPU spend

### 11.1 Done for this spec
**E0** [D, contaminated inputs]:
- I scored the 4 `nobc` meshes that obsnew had built but never scored, then compared the global sets (§4.4).
- Commands: `spec/manifest_e0.tsv`, `spec/results_e0.jsonl`, `spec/e0_global.py` → `spec/e0_global.json`.

**E0c** [M against D]:
- GT-free chamfer of 19 single-episode O meshes against library_v2 and against the all-episode O mesh (§4.5).
- Files: `spec/e0c_consistency.py`, `spec/e0c_part{1,2}.log`, `spec/e0c_summary.py` → `spec/e0c_summary.json`.
- About 25 min of CPU, $0, no depth fetched.

### 11.2 Pre-registered experiments
These run on compliant inputs: perc2m tracks (G1 for the 16 missing episodes), M0 for ROI and `--others`, no
`loc/perc`, no library_v1–v4. Each verdict follows Rule A or B as stated.

| ID | Question | Inputs and runs | Decision rule (written now) |
|---|---|---|---|
| E1 | Below-table handling: `nobc` vs `def` vs rest clip (§4.4) | library grids of all 10 objects (need G1) | rest clip replaces `nobc` only if it passes Rule A against `nobc`. `def` returns only if it passes Rule A against `nobc`, flip clause included. |
| E2 | **Is F4 good enough?** The v5 library set against v2. | v5 library (O gated, F4 fallback) | Rule A (own-frame form, §2.4) against library_v2, which itself was never compliant. If it fails, report which objects drive it. Remedies may only be global, and each is another pre-registered run. |
| E2b | Episode consistency filter [H] | v5 library | *Rule:* drop a public episode from an object's sum when its single-episode O solid is empty or its chamfer to the leave-that-episode-out mesh exceeds 0.5 cm; one pass. Adopted only if it passes Rule A against all episodes. Motivation: the broken ep26 rack track (dropping it: 0.920 vs 1.664 [D]) and the ep0 pot that sinks 8–13 cm. |
| E3 | Edge filter `0.02` vs off, globally | v5 library | Rule A; the winner applies to every object |
| E4 | Gate pass rates on own-mesh tracks | v5 library and the 4 perc2m episodes | Report only. **Thresholds stay at the frozen values.** A change would need a new pre-registered run. |
| E5 | Support rule on v5 meshes | v5 library + 4 episodes; `tools/replay_rest.py` | Rule B, plus no replay tilt > 5° at an observed rest (§6 [H]) |
| E6 | Collision acceptance | ep24 (boards), ep2 (lid/pot, after G1), ep18 (sweeper); `hullovl.py`, `replay_rest.py` | §8.3 gates. Build cost at 64 and 1024 worlds is reported. |
| E7 | Registration effect on the pose metric, with no robot | `score_registered.py --reg_seeds eval` on all public episodes, perc2m tracks, library_v2 vs v5 | Report. Any object losing more than 0.01 mean registered AUC is investigated before G2. |
| E8 | **Twin rehearsal:** per-episode re-fusion vs v5 leave-one-out | stage 2m on twins ep2, 24, 18, 11, 12, 27, 31, 21, 39, 41 along their perc2m tracks, with `--loo` seeds | Report per (episode, object): CD-O and registered AUC [D], branch taken, C value. **C ≤ 0.5 cm is kept only if every accepted per-episode mesh is ≤ its v5-LOO CD-O + 0.03 cm.** If per-episode meshes lose to v5-LOO on at least half of the twins, the owner decides (O2) whether known objects use v5. |
| E9 | Spoon dry run | eval ep3, ep35 perception from the store | Overlays and a fit report for the owner. No parameter changes. |
| E10 | G0 unit tests | deny-list hits by path and by sha; missing manifest; `pipeline/` imports | must pass before any box starts |

**Cost [E]:** about 1.5–2 CPU days.
- Fetching depth for the 20 public episodes, one at a time (float16, every 2nd frame, ≈ 0.3–0.9 GB each), deleting
  after use, keeps disk above 5 GB.
- Grids are saved, so post-pass variants need no depth.

---

## 12. GPU plan (needs the owner's go-ahead and a top-up: the Vast credit was $6.28 at 17:06 UTC, with the spoon box still running)

Prices assumed: RTX PRO 6000 at $1.4–1.9/h; about 2.2 h per 250M-step training plus evaluations; about 15 min of
setup per box.

**Is perc2m re-tracking needed first? Yes, but not for the GPU test itself.**
- G2's four episodes already have perc2m tracks, and per-episode re-fusion needs only that episode.
- The v5 library needs tracks for every object: lid (ep0/2), beige cup (ep11) and pitcher (ep21/22) have none today.
  So do the gate checks on own-mesh tracks (critique 12) and the twin rehearsal E8.
- G1 must therefore come before E1–E8 and before G3. It can run while the code is being ported.

### G1: perc2m re-tracking (≈ 1.3 h, ≈ $2–3; the plan said $3–6)
- One box, `SPLIT=public MESH_DIR=meshes/library_v2 STOP_AFTER=hands`. `STOP_AFTER=hands` is a new one-line option
  in `pipeline_ep.sh`. It stops before `mkref`, which would read the scans when no `ASSETS` is set.
- Episodes: 0, 2, 11, 13, 21, 22, 23, 26, 31, 39, 40, 41, 42, 43, 44, 45.
- Depth is pulled from the store cache (`cache/depth/public/ep<N>`) into `/content/cache/depth/ep<N>`.
- Pushes poses, hands and perception scores to `runs/<id>/perc2m/ep<N>`.
- The same seed as the existing 4 runs keeps all 20 consistent.

### G2: the test (after E1–E8 and the freeze)
**What is compared:** for the same episode, tracks, reference flags and seed:
- **v5** = per-episode re-fused meshes (stage 2m) + support rule + own pieces;
- **base** = the existing library_v2 runs. Their 6 evaluations each are already in `results/e2e/overnight_20261022/`,
  so the base arm needs no new GPU.

| Episode (twin) | Objects | Why | Flags = the base run's | Base, registered AUC (6 evals, s42) |
|---|---|---|---|---|
| ep18 (19) | sweeper, dust pan | support rule end to end; the largest measured physics effect | kfi flags: CONTACT_RETARGET, rest settle + stable pose, start fix. kfi (same flags, hand-flattened v3) shows whether the automatic rule matches the hand patch; kri (v2, height-only settling) is the floor. | kri 0.368 ± 0.069; kfi 0.715 ± 0.240 |
| ep12 (14) | blue cup, rack (together 25% of the score) | F4/O selection on the heavy objects | k (mc) | 0.790 ± 0.023 |
| ep27 (28) | pot, rack (together 27.5% of the score) | pot through F4; rack | k (mc) | k 0.911 ± 0.017 (base 0.942 ± 0.017) |
| ep24 (25) | boards | **smoke only:** 4096-world build with the most pieces, memory, steps/s; 20M steps, 1 evaluation | k (mcs) | – (ep24 is limited by learning: organiser meshes 0.389 / 0.245) |

**Seeds and evaluations:**
- seed 42, 250M steps, checkpoint sweep 0.4/0.6/0.8 with the floor guard, 6 repeat evaluations of the chosen policy;
- scored registered against the scans with our per-episode meshes [D], plus `sim_vs_ref` [M];
- also: shapes per object, build time and memory, steps/s, and the start-of-episode drop or tilt of each object.

**Boxes and cost [E]:**
| Box | Work | Hours | Cost |
|---|---|---|---|
| A | ep18 then ep12 | ≈ 0.25 setup + 0.3 stage 2m + 2 × 2.2 ≈ 5.0 h | $7–9.5 |
| B | ep27 + ep24 smoke + **v5-seeded perception on all 20 public episodes** (tracking with v5, washout tracks for O1(b); about 1.3 h) | ≈ 4.5 h | $6–8.5 |
| **G2 total** | | | **≈ $13–18** |

**Decision rules, written now (one seed: only large effects are readable).** Two seeds differ by about 0.04, and one
policy's evaluations spread ±0.01–0.10 [D].
- **Pass → G3 uses v5:**
  - no full episode below its base − 0.05;
  - mean of ep12/ep18/ep27 ≥ base mean − 0.02 (base for ep18 = kri 0.368);
  - ep24 builds and trains at ≥ 85% of baseline steps/s without OOM.
- **Ambiguous** (an episode between base − 0.05 and base − 0.02): a second seed for that episode only (≈ $3–4).
- **Fail:** stop. Diagnose on CPU (replays, overlap report). G3 runs with v5 meshes only for rule compliance, plus
  default CoACD collision, which is one switch in `make_assets`.
- **v5-seeded perception (box B):** registered perception AUC ≥ v2-seeded perc2m − 0.01 on the 20-episode mean, and
  no episode lower by more than 0.05. Otherwise v5 is not used as the tracking seed. That stays an owner decision,
  since v2 is denied.
- **ep18 [H]:** if the support rule works end to end, v5 ep18 ≥ 0.55. *Falsified if* below 0.45 with the sweeper
  falling in the first 10 frames of most rollouts.

### G3: the 20 eval episodes (separate go-ahead)
- Per episode: perception with v5 seeds → hands → stage 2m → `mkref` → contact retargeting → 250M training → sweep
  and evaluations, through `auto_ep.sh`.
- About 2.25 GPU-h per episode with overlap → 20 × 2.25 ≈ 45 h → **≈ $63–86 for one seed** [E].
- Retries or second seeds for weak episodes add 30–60%.
- Before G3: commit the exact code and `mesh_v5.json`, then run E10.

---

## 13. Owner decisions needed
| ID | Question | Recommendation |
|---|---|---|
| O1 | Accept bootstrap-derived (P1) seeds: v5 built on perc2m tracks that were seeded by library_v2? Or (b) a washout re-track? (Organiser email Q3.) | (a); G2b produces the washout tracks anyway |
| O2 | When a per-episode mesh fails every gate, submit the v5 library mesh (the tracking seed)? | yes; otherwise F4 is submitted with a flag |
| O3 | May the tracking seed serve as a QA reference (gates X and C, never as shape)? E0c says C is what keeps bad per-episode meshes out. | yes |
| O4 | The collision copy (convex pieces) differs from the submitted mesh in representation only (organiser email Q1) | proceed; same body frame, same flattening |
| O5 | Spoon: fitted template as "our reconstruction"; unfitted fallback; joint fit over the 10 eval episodes; seed band | fitted per episode; unfitted fallback; ask before a joint fit |
| O6 | GPU: G1 ≈ $2–3 now; G2 ≈ $13–18 after the CPU freeze; G3 ≈ $63–86 per seed | G1 now (can run before the ports) |
| O7 | The spoon template's frame was chosen by the R1 rule, which was fitted to reproduce the frames of the 10 public scans. It carries no shape information and does not affect the score (registration). | accept; or re-derive the frame from the template's PCA |

---

## 14. Port list (one commit per row; code from `scratchpad/interact/` and repo copies under `docs/research/work/interaction-meshes-2026-10-22/prototypes/`)

| File | From | Content |
|---|---|---|
| `pipeline/provenance.py` (new) + `ops/provenance/denylist.json` | – | tiers, `write`, `check`, deny globs and sha256 list (§3) |
| `pipeline/recon_mesh.py` (edit) | `obsnew/scripts/obsfuse4.py`, `obs/obsfuse3.py` | thin SVD; `--mode obs` accumulators (§4.2) incl. NB, NBR, NVR not voted; `--roi`, `--margin`, `--voxel 0.002`, `--save_grid`; G0 checks; classic mode unchanged for M0 and F4 |
| `pipeline/mesh_post.py` (new) | `obs/obspost2.py`, `obsnew/scripts/obspost5.py` (`main_part_lc`), `gate_ev.py` | variant builder, below mode (`nobc` / `clip`), G1, G2, G5, continuous marching cubes, fragment filter |
| `pipeline/mesh_gates.py` (new) | `metric/xreg.py`, `spoon/code/xcheck.py`, `metric/mesh_metric.py` (`amb`), `spec/e0c_consistency.py` | X flip check, C consistency, self-ambiguity, topology, G6 |
| `pipeline/mesh_decimate.py` (new) | `obsnew/scripts/decim.py` (`m_o3d`, `m_mlq` staged, `topo`) | §5 |
| `pipeline/rest_support.py` (new) | `minimal/auto_rest.py` + `flatten_base.flatten` | §6 |
| `pipeline/collision_decomp.py` (new) | `s5coll/scripts/decomp.py` (+ the needed `vox2` functions) | §8.2, chunked inside-test |
| `pipeline/make_assets.py` (edit) | `s5coll/scripts/mkassets.py` | `--pieces DIR` |
| `pipeline/spoon_mesh.py` (new) | `spoon/code/spoonfuse.py`, `fit_spoon_cpu.py`; new evidence exporter | §9; replaces `spoon/fit_spoon.py` |
| `pipeline/ep_mesh.sh`, `pipeline/ep_mesh.py` (new) | – | stage 2m orchestration, `ep_mesh.json` |
| `pipeline/mesh_v5.json` (new) | – | frozen parameters (Appendix A) |
| `pipeline/pipeline_ep.sh` (edit) | – | stage 2m (`MESH_REFUSE=1`), `ASSETS` per episode, `STOP_AFTER=hands`, G0 env checks |
| `ops/build_library.sh` (new) | `prototypes/recon_library2.sh`, `finalize_lib.sh` | §10.2, `--loo` |
| `ops/jobs/*.sh` (edit) | – | `LIB` → library_v5; refuse v1–v4 unless `DIAG=1`; `MESH_REFUSE=1` |
| `pipeline/perc2.py`, `pipeline/mkref.py` (edit) | – | G0 under `SPLIT=eval` / `COMPLIANT=1` (§3.4) |
| `pipeline/score_registered.py` (edit) | – | `--reg_seeds eval` (§2.4) |
| `tools/mesh_diag.py` (new, diagnostic only) | `metric/mesh_metric.py`, `analyze.py`, `spec/e0_global.py` | Rules A/B tables, flips, raw-scan check |
| `tools/replay_rest.py`, `tools/hullovl.py` (new) | `s5coll/scripts/replay_rest.py` (Newton engine only), `hullovl.py` | S5 acceptance. Do not port the CPU-MuJoCo engine or `--hold`. |
| `pipeline/setup.sh` (edit) | – | open3d 0.20.0, pymeshlab 2025.7.post1, apt `libopengl0` |
| `tests/test_provenance.py`, `tests/test_mesh_post.py`, `tests/test_decimate.py` (new) | – | E10; a synthetic slot and plate reproduce the prototype numbers |

**Port acceptance:** the ported code, run on the saved obsnew grids, reproduces the prototype meshes. The check is the
same sha, or CD-O within 0.002 cm [D] for floating-point differences.

---

## 15. Measured vs hoped

| Claim | Status |
|---|---|
| O meshes beat the library on the thin objects that pass the gates (beige cup, sweeper, dust pan, lid CD-O; boards with `nobc`) | **[D], contaminated inputs**; confirm in E2 |
| `nobc` + gates + v2-like fallback improves the known-object set (−0.0154 cm, −1.25 mm, no new flips) | **[D] E0**; the fallback is a stand-in |
| A compliant 4 mm fallback is as good as v2 | **hoped**; E2 |
| G2 + C protect per-episode re-fusion | **[M vs D] E0c, n = 19, reference = v2**; E8 |
| Rest clip recovers the dust pan without board flips | **[H]**; E1 |
| open3d decimation keeps meshes watertight and costs nothing in CD-O | **[M] 15/15, [D] 8 meshes** |
| Our pieces reduce hull overlap; FlashCHORD keeps them | **[M]** (ep24 16.8 → 3.0–4.1 cm³; 256/256 pieces kept) |
| Our pieces keep objects upright better | **mixed [M]:** sweeper yes; ep24 noisy; lid neither |
| Pieces do not slow training | **unmeasured**; G2 |
| The support rule makes the sweeper stand and lifts ep18 | **[D] one seed, confounded** (0.715 with v3); G2 tests the automatic version |
| Interaction carving improves CD-O or registration | **no [D]**; not used |
| The spoon fit beats the template on real spoons | **[M-synthetic] only**; the real error is unmeasured |
| v5 seeds track as well as v2 seeds | **unmeasured**; G2b |
| v5 raises the leaderboard AUC | **hoped**; the mesh-only effect via registration is small [E]; physics effects are known for one episode |

---

## Appendix A. Frozen parameters (`pipeline/mesh_v5.json`)

**Fusion**

| Group | Values |
|---|---|
| Grid | voxel 0.002 m; ROI margin 0.04 m |
| Truncations | 0.004, 0.006, 0.012 m; min_obs 3 |
| Free-space counters | NF at 0.008 m; NF3 at 0.003 m |
| Table | band 0.015 m; per-frame refit ≤ 10° |
| Below table | 0.004 m, counter only |
| Hands | hand_r 0.03; arm_r 0.045; arm_len 0.15 |
| Other objects | other_r 0.012 |
| Depth samples | edge_thr = E3's winner (default 0.02); zmax 1.5 m; stride 2 |

**Post-pass**

| Group | Values |
|---|---|
| Variant | `4c12_adj_g2_f0_cont`, adj share 0.5 |
| Main part | lc25 (fraction 0.25, merge 0.008 m) |
| Fragments | area ≥ 5% of the largest, centroid within 0.15 m |
| Below mode | `nobc` (E1 may switch to `clip`: 6 mm under the rest plane, NBR ≥ 0.5·NVR, not strongly observed, budget 5%) |

**Gates**

| Gate | Value |
|---|---|
| G1 | ≤ 0.5 cm³ (NF3 ≥ 2 and ≥ 0.5·NV) |
| G2 | ≤ 0.05 (evidence W12 ≥ 5, \|mean12\| < 0.25, M0 ≥ 5; distance 0.008 m) |
| T | every body watertight; bodies and Euler unchanged by decimation; ≤ 4096 faces and vertices |
| X | no rotation > 90° at the eval seeds + extras to 6 |
| C | ≤ 0.5 cm, seeds 11 and 22 |

**Fallback F4:** `recon_mesh` classic: voxel 0.004, trunc 0.012, close auto, below_carve 0.004, `--others` = own M0.

**Decimation:** 4096 faces; open3d, then pymeshlab QEC (qualitythr 0.3, staged).

**Support**

| Group | Values |
|---|---|
| Rest detection | move < max(2 mm, 2.5 × jitter); ≥ 15 frames; ±20 mm to the plane; no hand within 20 mm in ≥ 80% of frames (carry 6 frames) |
| Clustering and snap | 10° clusters; 5° facet snap |
| Stability | margin ≥ 2 mm, area ≥ 1 cm² |
| Flatten | 8 mm |
| Acceptance | strong-voxel removal ≤ 0.5 cm³; G6 ≤ 2 mm / 2° |

**Collision:** free margin 0.75 mm (0.5 with a partner); tolerance 0.3 cm³ per piece; 32 pieces (64 if the solid is
above 300 cm³); ≤ 64 vertices per hull; 1 mm overlap; 19 quantiles; λ 10 within 1 mm.

**Spoon**

| Group | Values |
|---|---|
| Hands and table | capsules 0.03; carry 6 frames; band exemption inside the outline eroded 5 px |
| Seed band | 0.006 m |
| Fit gates | prior 3σ; residual ≤ 1.0 mm; both faces ≥ 20% |
| Other gates | X vs T0 ≤ 10° / ≤ 3 mm; ambiguity excess ≥ 0.9 mm; consistency ≤ 5% beyond 8 mm |
| Optional re-track | above 1.5 mm or 3° |

## Appendix B. E0 / E0c numbers

**E0** (`spec/e0_global.json`): O gated, failing objects at library_v2. Each cell: CD-O cm / ADD mm / flips on all
seeds [D].

| Object | v2 | `def` | `nobc` |
|---|---|---|---|
| beige cup | 0.856 / 6.5 / 0 | 0.732 / 5.7 / 0 | 0.725 / 6.4 / 0 |
| dust pan | 0.331 / 5.6 / 0 | 0.252 / 3.6 / 0 | 0.342 / 7.4 / 0 |
| sweeper | 0.316 / 25.1 / 2 | 0.282 / 3.2 / 0 | 0.275 / 3.6 / 0 |
| lid (`def` grid in both) | 0.421 / 8.1 / 0 | 0.377 / 12.6 / 0 | 0.377 / 12.6 / 0 |
| board 1 | 0.222 / 2.4 / 0 | 0.216 / 3.2 / **1** | 0.177 / 5.5 / 0 |
| board 2 | 0.216 / 3.6 / 0 | 0.326 / 5.5 / **2** | 0.228 / 3.1 / 0 |
| **weighted over 26** | – | −0.0159 cm / −1.63 mm, new flips | **−0.0154 cm / −1.25 mm, none** |

The blue cup under `nobc` scores 0.670 / 8.2 / 0. It fails G2 either way.

**E0c** (`spec/e0c_summary.json`): single-episode O meshes [D] with their GT-free chamfer to library_v2 [M]. Each cell:
episode: CD-O / chamfer.

| Object | Episodes |
|---|---|
| pot | e2 0.732 / 0.558; e27 0.322 / 0.498; e41 0.748 / 0.616; e44 0.796 / 0.583 |
| blue cup | e11 1.173 / 0.740; e12 0.492 / 0.335; e13 0.407 / 0.416; e21 0.749 / 0.538; e22 0.861 / 0.629 |
| rack | e13 1.069 / 0.677; e27 0.905 / 0.632; e31 0.888 / 0.743 |
| dust pan | e18 0.246 / 0.248; e39 0.305 / 0.247; e40 0.281 / 0.266 |
| sweeper | e18 0.446 / 0.352; e31 0.271 / 0.244 |
| pitcher | e21 0.819 / 0.390; e22 0.847 / 0.390 |

Spearman 0.86 (n 19).
- **G2 alone** accepts e11 and e21 of the blue cup. They are 0.65 and 0.23 cm worse than v2.
- **G2 + C ≤ 0.5** accepts blue cup e12, dust pan e18 and e40, and sweeper e31. These are 0.031–0.085 cm better than v2.
