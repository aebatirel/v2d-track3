# Object-mesh ledger: everything tried or proposed (V2D Track 3), as of 2026-10-26 ~15:30 UTC

Compiled read-only from the repo at 6762f80. WL = `docs/work-log.md` (line numbers L…). Labels: **[M]** measured, no
ground truth; **[D]** diagnostic against the public scans or mocap (the public scan stands in for the hidden scan), used
after inference; **[E]** estimate; **[H]** hypothesis. All CD-O values are cm, from the kit's `_object_chamfer_cm` at
the scorer's eval seeds, both meshes through the packer's `budget_mesh(4096)`, unless the row says otherwise. ADD = the
static registration offset, mm (`_register_object_body`, 500 kit ADD vertices); rot = rotation error of that
registration.

Context numbers:
- Board CD-O: ours 0.405 (pack 1–2) → **0.402** (pack 3; pack 4 did not re-upload CD-O).
- Leaders (Kaggle API, `scratchpad/lb.json`, 26 Oct 08:50 UTC): Panav Raaj 0.112 (17th on AUC), richchentw 0.154 (1st
  AUC), SRL 0.239, SoySauceChicken 0.253, Zihao Guo 0.264, DDD 0.302.
- Spearman(CD-O, AUC) across teams is only −0.51 (WL L3701). Pose error, not CD-O, separates the AUC top 4 from us.
- CD-O = flat mean over 36 eval (episode, object) pairs. 26 of them have a public scan; the spoon has 10 and no scan
  (WL L3705).

---

## 1. Pipeline as it stands (what the submitted meshes are)

**Submitted now (packs 3 and 4):**
- `meshes/library_v3/<obj>.glb` for every pair, except eval 8's beige cup = `meshes/library_v3x/beige_cup.glb`
  (`results/submissions/20261026-track3d/README.md`).
- The spoon is the parametric template `spoon/wooden_spoon.glb` (md5 68dcf049, the same file in v1–v4).
- The kit packer decimates each file with `budget_mesh(4096,4096)` at pack time (`ops/jobs/submit_pack.sh`).
- Library .glb files are full resolution: 3.2k–33k faces, vertex-coloured (census run here with trimesh).
- The v3x beige cup is the exception: 4096 faces (open3d) and **no colours** (trimesh `visual.kind=None`) [M, here].

**File identity across versions** (md5, checked here):

| Object | Changes |
|---|---|
| dust pan, pot | v1 → v2 |
| sweeper | v2 → v3 (flattened base) |
| boards | v3 → v4 (v4 never used) |
| beige cup | v3 → v3x |
| blue cup, rack, pitcher, lid, spoon | identical in v1 … v4 / v3x |

So 7 of the 11 objects are still submitted, in at least one pair, as the **21 Oct v1 files**: blue cup, rack,
pitcher, lid, both boards, and the beige cup in eval 10.

**How library v1/v2/v3 were built** (`pipeline/recon_mesh.py` classic mode; `meshes/library_v1/*.recon.json`; WL L787–806, L880–884):
- **Poses:** perc2 FoundationPose tracks **templated on the public scans** ("refsweep", store
  `runs/20261020-refsweep-ea14fdf`).
- **`--others`:** the public scans posed by those tracks.
- **Consequence:** not inference-legal. v1–v4 are on the deny-list (`ops/provenance/denylist.json`; WL L1521, L2908).
- **Depth:** FoundationStereo on the rectified mono pair (`ego_cam_c` left / `ego_cam_b` right, baseline ≈ 75 mm),
  run at FS_SCALE 0.5 and resized to the rectified grid (`perc2.py:117–124`). Cache `depths_fs0.5.npy`.
- **Fusion:**
  - TSDF in the object frame; voxel 4 mm, truncation 12 mm, cube ±30 cm (150³), stride 2, min_obs 3;
  - running mean of clip(sdf/τ), with free-space carving;
  - table samples (frame-0 RANSAC plane, 65° cone, 6 mm; per-frame refit ≤ 10°, 15 mm band), MediaPipe hands
    (30 mm bone capsules, 45 mm × 15 cm forearm) and other objects (12 mm) carve but never vote surface;
  - depth-edge filter 2 cm (the dust pan only: `--edge_thr -1`, a per-object exception the v5 spec removes).
- **Closing `auto`:** `fill` unless the never-observed share of the filled solid exceeds 0.5, then `near` (3 voxels).
- **Component and fragments:** keep the component nearest the origin after a 2-voxel dilation; keep fragments ≥ 5 % of
  the largest area within 15 cm.
- **Mesher:** the binary ±1 solid, Gaussian-blurred σ = 0.8 voxel, then marching cubes. The TSDF's sub-voxel values are
  discarded (`recon_mesh.py:476–483`).
- **Below-table carve:** `--below_carve 0.004` is used **only in v2's dust pan and pot**. The other v1 meshes predate
  it (no `below_carved` key in their recon.json).
- **Episodes fused (v1):**

  | Object | Public episodes |
  |---|---|
  | pot | 41, 44, 2, 27 |
  | lid | 2 |
  | rack | 12, 13, 27 |
  | blue cup | 12, 13, 21, 22 |
  | pitcher | 21, 22 |
  | beige cup | 11 |
  | dust pan | 39, 40, 18 |
  | sweeper | 18, 31 |
  | boards | 23 |

  Per-object parameters are in each `*.recon.json`.
  - The beige cup's json is **stale**: extents 5.1 × 7.1 × 16.5, while the glb measures 9.9 × 11.0 × 17.4 cm here,
    matching WL L880–884's "keep pieces" rebuild.
- **Post-steps:**
  - `flatten_base.py` on the sweeper (v3: 121 vertices within 8 mm of the lowest point along our ep18 frame-0 up,
    moved onto one plane; `mini_sweeper.flatten.json`);
  - `mesh_color.py`: grey vertex colours from our video, the median over visible frames, for FoundationPose's
    appearance term;
  - `make_assets.py`: colourless simulator copy, 0.3 kg placeholder, COM and inertia from the surface;
    `--pieces DIR` gives one `<collision>` per convex piece.

**How v3x beige was built:** the v5 chain on box `20261025-cups-46b8389` (`library_v3x/beige_cup.v5.json`), along the
re-tracked ep11 own-mesh track:
- `recon_mesh.py obs` (2 mm; 4/6/12 mm truncations);
- `mesh_post.py` `4c12_adj_g2_f0_cont@lc25` on `nobc` grids → branch O (G1 0.02 cm³, G2 0.028, X 0 flips);
- solid 173 cm³, watertight, 2 bodies;
- `mesh_decimate.py` (open3d) to 4096 faces;
- 32 collision pieces;
- support rule skipped (no observed unassisted rest).

**Simulator-only geometry in the latest pack** (it never touches CD-O or registration):
- `support_fill.py` (SF=1; fills of 0.5–2 cm, arc foot) per episode reference;
- `meshes/carve/ev25` (board slot, 21 + 11 pieces) and `meshes/carve/ev10` (hybrid lathe cups, 49 / 53 pieces), via
  `ASSET_PIECES` in `ops/jobs/pack_eval.sh`.
- The robustness review §5 notes that the shared `/content/assets` is keyed by object name and set by hand, with no
  check that a checkpoint is evaluated on the copy it was trained on.

**Where data lives** (`ops/config.env` `HF_STORE=aebatirel/v2d-store`; `ops/box/store.sh`; runbook §2):

| What | Where | In git? |
|---|---|---|
| Depth caches | store `cache/depth/{public,eval}/ep<N>/depths_fs0.5.npy` (0.3–0.9 GB each) | no |
| Scan-templated public tracks | store `runs/20261020-refsweep-ea14fdf/` | no |
| Own-mesh (library_v2-seeded, tier P1) public tracks | `runs/20261021-auto18-966eb96/perc2m` (ep12, 18, 27); `runs/20261021-auto24-966eb96/perc2m` (ep24); `runs/20261025-g1-022fece/{perc2m,refs/perc2m}` (16 episodes, old detection); `runs/20261025-sweep-a894083` (all 20 public, today's detection, base mean registered AUC 0.868) | no |
| Eval tracks | `runs/20261025-evperc-4f596df/results/evalperc/` | no |
| library_v5 (the only compliant library) | `runs/20261025-lib5-c476e68/results/library_v5`; beige cup `runs/20261025-cups-46b8389` | no (beige cup only, as v3x) |
| 22 Oct study grids, meshes and scripts (`interact/…`, `v5/obsnew`, `v5/spoon`, `fit_spoon_cpu.py`) and approach-2 lathe outputs (`approach2/out/lathe2`) | scratchpad of session 8c892c5e (not present in this container) | code copies only: `docs/research/work/interaction-meshes-2026-10-22/prototypes/`, `approach2-scripts/` |
| Public scans | HF dataset `nvidia/video_to_data_challenge` `track_3/*`, via `pipeline/fetch_data.sh` → `/content/t3/mesh` | no |
| Kit | a copy in this session's `scratchpad/kit/v2d_submission_kit` | no |

---

## 2. Per-object table (11 objects)

Eval pairs come from the kit roster (`data/track_3_evaluation_objects.json`, read here); 36 in all. The scene anchor is
the first object without a symmetry axis (kit rule; WL L611–656). The anchor's frame-0 orientation rotates every
object's later frames.

### 2a. CD-O by version and method [D]

Sources: `metric-summary.md` for v1–v4; WL L3607 for v5 (E2); approach 2 §2.3 for primitives;
`exp-fusion-all-objects.md` and spec App. B for O-fusion and single episodes; WL L962, L982 for v1.

| Object | Pairs (evals) | v1 | v2 = v3 (submitted) | v5 / v3x (compliant) | Primitive fit | O-fusion, scan-contaminated tracks | Best single episode |
|---|---|---|---|---|---|---|---|
| white_pot | 6 (1, 3, 5, 6, 8, 28); anchors 1, 3, 5, 6, 8 | 0.58 | **0.437** | v5 failed (lid M0 missing) | lathe 0.319 (ADD 6.7 → 4.7); solid lathe 0.545 | 0.727 (holes; G2 0.27 fails); fb12 0.367 | ep27 0.322 |
| blue_cup | 5 (10, 14, 20, 32, 33) | 0.523 | **0.523** | v5 O 0.540 | lathe **0.307** (ADD 10.0 → 9.1); solid 0.344 | 0.677 (all episodes) / 0.521 (v1 episodes); nobc 0.670 | ep13 0.407; ep11 1.173 |
| plastic_dish_rack | 5 (14, 15, 16, 28, 30); anchors 14, 15, 16, 28 | 0.555 | **0.555** | v5 F4 0.818 | lathe gate fails (MAD 6.8 mm) | 1.664 with lc25 (3.757 degenerate); v1 episodes 0.887; old rules at 2 mm on v1 episodes 0.742 | ep31 0.888 |
| beige_cup | 2 (8, 10) | 0.856 | **0.856** (eval 10) | **0.730** v3x (eval 8) | lathe 0.292 on v3x (ADD 5.4 → 8.2, fails ADD alone); 0.347 on v3 | def 0.732 / nobc 0.725 | (one episode only) |
| mini_sweeper | 2 (19, 30); anchors 19, 30 | 0.316 | 0.316 → **0.317** (flattened) | v5 F4 0.526 | gate fails | 0.282 / 0.275 (0 flips) | ep31 0.271 |
| mini_dust_pan | 2 (19, 38); anchors 38 | 0.52 | **0.331** | v5 O 0.368 | false lathe pass (needs a coverage gate) | def 0.252 / nobc 0.342; fb12 0.226 | ep18 0.246 |
| white_pot_lid | 1 (1) | 0.421 | **0.421** | v5 failed (broken ep0 track) | gate fails (slab 0.134) | 0.377–0.385, 4 mm only 0.365–0.368, but ADD 8.1 → 12.6 mm (E0; the critique measured 7.6 → 14.0) | – |
| water_pitcher | 1 (20); anchor 20 | 0.894 | **0.894** | v5 F4 0.890 (≈ v3 clone) | lathe gate fails (MAD 8.8 mm) | 4.545 degenerate → 0.848 with lc25 | ep21 0.819 |
| wooden_piece_1 | 1 (25); anchor 25 | 0.222 | **0.222** | v4 0.227; v5 failed | box + slot 0.177 | nobc 0.177 (6c12 0.163); def 0.216 with 1/6 flips | – |
| wooden_piece_2 | 1 (25) | 0.216 | **0.216** | v4 0.221; v5 failed | box + slot 0.230, **2/6 new flips** (ADD 157 mm) | nobc 0.228; def 0.326 with 2/6 flips | – |
| wooden_spoon | 10 (3, 5, 6, 15, 16, 32, 33, 35, 36, 37); anchors 32, 33, 35, 36, 37 | template | template, **≈ 0.18 inferred [E]** | – | template family 0.10–0.12 [M-synthetic] | fused single-episode proxies 0.25–0.46 | – |

Notes on the table:
- **Weighted proxy over the 26 scanned pairs** (library v1 / v2 / v3 / v4): 0.539 / 0.491 / 0.491 / 0.492.
- **The spoon's 0.18 is inferred** from (0.405·36 − 0.491·26)/10, assuming the hidden scans match the public scans
  (WL L3705).
- **Derived consistency check:** the eval-8 beige swap predicts 0.405 + (0.730 − 0.856)/36 = 0.4015, and the board
  read 0.40188. This is one data point that the public scan is a good stand-in.
- **"Best single episode"** is information only: no GT-free statistic picked it reliably (3 of 6).

### 2b. Registration, flips and known defects

ADD (mm), max rot (°) and flips come from `metric-summary.md` for library_v2 (v3 for the sweeper).

| Object | ADD / max rot / flips | Self-ambiguity excess, scan [D] / ours [M] (< 3 mm ⇒ flip risk: 36/92 vs 2/89) | Known defects (source) |
|---|---|---|---|
| pot | 6.7 / 2 / 0 of 8 | 8.05 / 5.5–15.3 | **v1 base 5.5 cm below the table** (fixed in v2). Walls 15–20 mm against real 4 mm. Bottom 56–61 % solid. Lid sits 2.8 cm below the rim at eval 1 (thick wall; WL L3249). Hand fused in at v0 (8.8°). v1 had 2 bodies; v2 has 1, 625 cm³ (v1 868). Extents 13.1 × 19.0 × 36.2 vs scan 13.2 × 18.9 × 35.7. |
| blue cup | 10.0 / 2 / 0 of 7 | 5.56 / 4.48 | **Cavity: lower ≈ 37 % solid** (400 cm³ against 136 cm³ in the scan; O fusion 22 %). The beige cup sits inside its solid in 46 of 81 eval-10 frames (WL L3592). CoACD fills it (stack overlap up to 112 cm³). |
| rack | 6.0 / 2 / 0 of 7 | 7.00 / 8.46 | 5 bodies. Tower has no floor. 36 % of the basket is holes. Fins 2 cm low. 11.0 × 16.1 × 49.7 vs scan 11.7 × 17.6 × 51.2 (simvalid F3, F8; WL L820). Our references push the cup (eval 14, 54 / 72 cm³), the pot (28, 24 cm³) and the sweeper (30) into it. |
| beige cup | 6.5 / 4 / 0 of 6 | 5.61 / 6.25 | One episode; 42 % unknown; 268 TSDF components. Largest-piece-only cut it in half (registered AUC 0.417). **Open bottom, tapering to a 1 cm cone tip:** the COM is 26–28 mm outside its support and it falls 6/6 at rest (v3 and v3x). |
| sweeper | 25.1 (v2) / 25.6 (v3) / 178 (flip) | 0.37 / 1.81–3.83 | Rounded, unobserved bristle underside: 0.3 cm² footprint with the COM 3.3 cm outside; v3 flattened it to 9.7 cm². **Flip status ambiguous:** 22 Oct says it flips at eval 30's seed (1/6 eval, 2/6 all); 26 Oct with the current kit says eval 19 and 30 seeds sit within 0.7–0.9° and 4/40 random seeds flip (WL L4130). v1 flip rate on ep18/31 tracks was 0.12–0.25. |
| dust pan | 5.6 / 3 / 0 of 6 | 5.54 / 4.19–6.54 | **v1: 3.5 cm slab below the table** (closing filled the never-seen underside), fixed in v2. Plate 11–13 mm thick against real 3–5 mm. 1 cm step at the lip. |
| lid | 8.1 / 2 / 0 of 6 | 3.54 / 2.77–7.40 | 12–13 mm thick against real 2–7 mm; underside ≈ 7.7 mm too low [D]. **Starts 7.6 mm inside the pot** at eval 1 (344 of 3,000 samples; WL L3200). Lid on pot overlaps 20–25 cm³ (mesh) and 31–51 cm³ (hulls). Kit treats it as 180°-symmetric. |
| pitcher | 7.6 / 3 / 0 of 6 | 6.66 / 10.44 | **"Twisted thin shell"** (eval videos). Half its base is missing: the observed rest up is 38° from the mesh's base axis, with a 0.2 cm² contact and the COM 4 cm outside. 19 % of the plan view is see-through; the interior is 24–43 % solid. **Pitcher reference vs mocap 0.571 on ep21** (cup 0.979), i.e. registration and track (audit-starts §2.4). The forensics/scoreboard "0.95 with the scan" counterpart was not traced to a source. |
| board 1 | 2.4 / 1 / 0 | 0.36 / 0.29–1.86 | **No slot.** Assembled overlap 10.5–10.9 cm³: a 1.0 × 11.3 × 1.2 cm column (both missing notches). Rounded edges, so no stable standing pose (0.1 cm² footprint). 4 spurious holes. Flip rate 0–25 % across recon parameters (v3 0.12, v6 0.25, v7 0.12). |
| board 2 | 3.6 / 1 / 0 | 0.24 / 0.25–2.37 | 12.0 mm thick against 9.1 mm in the scan; the same missing slot. The near-identical boards made perception swap their names on eval 25 (approach 1 §2.6). |
| spoon | 0/300 flips, median 1.0°, p95 2.5° [M-synthetic, `spoon_regflip.json`] | 2.00 (template) | Parametric loft: 3,224 faces, 5 mm bowl shell, 3 marker spheres, 0.3 kg placeholder. Three stable rests ≈ 14° apart in roll. Frame-0 roll uncertainty 2–6° ⇒ 0.03–0.15 AUC per spoon-anchored episode [E] (`docs/research/spoon-2026-10-25/`). Real-spoon shape error is unmeasured. |

**Registered perception AUC, our mesh vs the scan** [D], same scan-templated tracks:

| Object(s) | Episodes | Ours / scan |
|---|---|---|
| pot, v1 | 41, 42, 43, 44, 45 | 0.987 / 0.999, 0.958 / 0.986, 0.979 / 0.993, 0.986 / 0.999, 0.964 / 0.966 |
| pot, v2 | 41, 44, 2, 27 | 0.998, 0.997, 0.991, 0.994 |
| rack + pot | 27 | 0.993 / 0.994 |
| pot + lid | 2 | 0.983 / 0.977 |
| boards | 23, 24 | 0.997 / 0.999, 0.864 / 0.840 |
| dust pan, v1 → v2 | 39, 40, 18 | 0.992 → 0.982, 0.971 → 0.963, 0.920 → 0.917 |
| sweeper | 18, 31 | 0.920 / 0.956, 0.801 / 0.876 |
| beige cup | 11 | 0.857 / 0.914 |
| cup + pitcher (recon v3) | 21 | 0.917 / 0.975 |

(WL L822–825, L880–884, L962–966, L982–983, L743.)

**Sensitivity of the registered AUC to mesh damage** [D] (`pipeline/mesh_sensitivity.py`, 6 episodes, WL L659–680),
mean AUC:

| Damage | Mean AUC |
|---|---|
| clean | 0.987 |
| ×1.10 scale | 0.987 |
| side slab 20 % removed | 0.986 |
| convex hull | 0.947 |
| bottom 20 % removed | 0.904 |
| 3 mm vertex noise | 0.825 |
| 5 mm inflation | **0.608** |

With 5 mm inflation the board and the sweeper register flipped 180° (ep23 0.052, ep18 0.247). 2–3° of registration
error costs 0.015–0.06 AUC, most when the object anchors the scene (WL L732–737).

---

## 3. Ledger of experiments (chronological)

### 21 Oct: first reconstructions and library v1/v2
| # | Method / change | Measured | Verdict |
|---|---|---|---|
| 1 | Discovery: the kit registers our mesh to the hidden scan for all 5 pose metrics; local replica `score_registered.py` (WL L611–656) | 20-ep perception 0.8828 → 0.8824 registered; ep12 0.998 → 0.940 (rack anchors) | tool adopted |
| 2 | recon v0 TSDF on ep41 pot (WL L682–699) | CD-O 0.981 → **0.564**, rot 2.35 → 1.12°, AUC 0.9979 (scan 0.9985) after: table/hand samples carve-only (dropping table samples entirely: 27.5°, 0.711), cube ±30 cm; hand masking no effect | adopted (H1 held on ep41) |
| 3 | v0 on 27/2/23/39/18 (L701–706) | ep2 pot 102° (rim/handle split), ep23 board flipped 175° (boards fused), ep39 123° (tabletop fused), ep18 sweeper 41°, ep27 8.8° (hand) | led to v1–v3 |
| 4 | v1 hand capsules + others carve + merge 2 vox; v2 per-frame table refit; v3 closing `near` (L707–714) | ep39: 131° → **6.4°** (refit) → CD-O 0.58, 2.0°, AUC 0.953 | adopted |
| 5 | v3 on 41/39/23/21 with 8-seed flip test (L715–725) | boards flip rate 0.12/0.12 (179°); pot 0.70 (worse than v0) | flip risk found |
| 6 | v4 depth-edge filter 2 cm (L732–735) | ep39 0.953→0.880 (thin plate loses depth); boards flips 0/0 | mixed; per-object |
| 7 | Ablation ep41 (L736–738) | **closing mode decides**: fill 0.998 vs near 0.986; hands/edge filter ≈ 0 | `--close auto` |
| 8 | v5 close auto (thr 0.5) (L740–743) | ep41 0.998, ep23 0.997 (boards CD-O 0.22/0.22, flips 0/0), ep39 0.880 | adopted |
| 9 | v6 edge 5 cm / v7 edge off (L784, L806) | v6 board 2 flip 0.25; v7 board 1 flip 0.12, ep39 0.953 | flips fragile to small params |
| 10 | Multi-episode fusion → **library v1**, 11 objects (L802–884) | see §2; flips 0 except sweeper 0.12–0.25 | adopted then |
| 11 | Keep-largest-piece rule (L873, L882) | cut ep11 beige cup in half (0.417) → keep ≥5 % within 15 cm: 0.857/0.914 | replaced |
| 12 | Table-plane cone 45° → 65° (L889–909) | real bug (ep39/40 planes 48–50° from camera up) but did **not** remove the dust-pan slab (L910–926) | kept; not the cause |
| 13 | `--below_carve 0.004` → **library v2** (dust pan, pot) (L916–966, L982) | lowest point −3.3…−5.5 → −0.2…−0.6 cm; dust pan CD-O 0.52→0.33 (AUC −0.01, missed own bar, accepted: v1 not simulable); pot 0.58→0.44, AUC ep41 0.987→0.998 | adopted (v2) |
| 14 | Newton splits vertex-coloured meshes (174 fragments/board → CoACD >10 min, OOM) (L949–967) | colourless sim copy: 64 worlds 4.2 s / 0.61 GB | adopted (`make_assets.py`) |
| 15 | "Our bumpy meshes give more CoACD hulls" (L940–947) | 17 vs 10 hulls; not the cause | falsified |

### 22 Oct: physics validity, interaction designs, v5 evidence round (all CPU, scan-contaminated inputs unless [M])
| # | Method | Measured | Verdict |
|---|---|---|---|
| 16 | `flatten_base.py` sweeper underside (8 mm) → **library v3** (L1401–1425) | footprint 0.3 → 9.7 cm², CPU tilt 17.6° → ≤0.7°; **ep18 0.345/0.368 → 0.715 ± 0.240** (one seed, confounded with stable-pose settling) (L1442); later 0.889 (FDR s43) | adopted (v3) |
| 17 | `flatten_base` board edges → **library v4** (L1451–1460) | board 2 stable face 27 cm²; board 1 marginal; CD-O +0.0004 (Rule B pass). GPU W1 stopped at perception 0.029 (L2614), **later shown to be the board-identity swap, not v4** (approach 1 §2.6) | dropped 24 Oct on a misattributed reason; never trained |
| 18 | ep24 with the organisers' meshes (L1612–1670) | s42 0.389 / s43 0.245 vs ours 0.307 / 0.306; board 2 never lifted with either | mesh not ep24's limit (then) |
| 19 | Interaction census (`wf_8a372398-57b`, L1505–1512) | overlap is a mesh property (same at mocap poses); boards 10.8 cm³ column CV 0.02; lid ring 20–25 cm³; nested cups 42.7 cm³ | diagnosis |
| 20 | Design XCarve (R1 closing-loses, R2 insertion split, R3 evidence ratio) | slot fill 80/52 % → 11/0 %; CD-O +0.006/+0.007; board 2 **new flip** ADD +103 mm; R2 cuts 1.3–1.5 cm³ real wood under 5–10 mm bias | rejected for submitted mesh |
| 21 | Joint min-cut (lid/pot ep2) | lid CD-O 0.565 → 0.726 (+0.14…+0.18); cut board 2 in two without prior | rejected |
| 22 | Observation-first "Design O" (2 mm ROI, 4→12 mm cascade, adj closing, continuous MC) | lid 0.415→0.368–0.385, dust pan 0.333→0.251, board 1 0.223→0.189, **pot 0.440→0.727**; critique: ADD worse (lid 7.6→14.0, pot 6.8→11.5 mm); 4096-face files not watertight | became v5 backbone |
| 23 | Silhouette free space (`maskfuse`) | ego_cam_c is effectively grayscale; ≤1.2 cm³, |ΔCD-O| ≤ 0.013 on most objects; **but** 89 % of board-slot voxels vs 1 % of wood (judged plan §1) | not ported (D5) |
| 24 | Per-frame `below_carve` on 2 mm grids | erased real board-2 wood (126 cm³) and most rack material (83 vs 353 cm³); boards gain flips (wp1 1/6, wp2 2/6) | removed in v5 (`nobc`); costs dust pan 0.252→0.342 |
| 25 | `nbk` (below-table hits only block closing) | dust pan 0.345 vs 0.252 | rejected |
| 26 | Episode weighting R_w (pre-registered) | beats all-episode on 1/4 objects | falsified; R_sel exploratory |
| 27 | Single vs all-episode fusion [D] | one single episode beats all-episode on **6/6** objects (blue 0.407 vs 0.677, pot 0.322 vs 0.725, …) | [H] cross-episode misalignment; test never run |
| 28 | Decimation study (15 meshes) | kit `budget_mesh` watertight on 6/144; open3d quadric 15/15 watertight, CD-O −0.004; pymeshlab 15/15 | `mesh_decimate.py` |
| 29 | Spoon proxies (sweeper/dust pan, `exp-spoon.md`) | finger-scale hand masks falsified (4/4); held-only fusion flips 2–5/6; **seed band** (samples > 6 mm outside seed carve only) mean 0.312 → 0.274; template family 0.10–0.12 synthetic; 0/800 flips | template (fitted if gates pass) chosen; fit never run on real data |
| 30 | E0 / E0c (spec §11) | `nobc` set −0.0154 cm / −1.25 mm, no new flips; GT-free chamfer-to-library ranks single-ep meshes like CD-O (Spearman 0.86); G2+C≤0.5 admits only good ones (threshold set post hoc) | spec D2/D3 (provisional) |
| 31 | S5 own convex pieces (`s5coll`) | ep24 hull overlap 16.8 (v4 CoACD) → 6.7 (full-res) → 4.1 (pieces) → 3.0 cm³ (weighted); FlashCHORD keeps pieces (256/256, ≤ 0.024 mm); sweeper on 30 pieces stands, CoACD's 19 topple; single box sinks 9.6 mm in 2 s | ported (`collision_decomp.py`), off by default |

### 23–24 Oct: support, starts, v5 port, G1
| # | Method | Measured | Verdict |
|---|---|---|---|
| 32 | `support_fill.py` (COM ≥ 3 mm and ≥ 3° tip; fills 0.5–2 cm; free-space check) (L2435–2464) | ep18 brush still fell with 1 cm fill (94 mm/85°); bug: fill under another rest pose → fixed (L2557); STATUS 24 Oct: "support fill (neutral)" | kept on (SF=1), neutral |
| 33 | Pitcher base completion, 8 convex sectors (audit-starts F1) | single prism foot wobbles; 8 sectors stand ≤ 5 mm / 0° for 60 frames (CPU) | → arc foot (#40) |
| 34 | `mkref --start_overlap`; `tools/sim_settle.py` (L3240–3264) | eval 1: lift clears lid only at ≈ 3 cm (thick pot wall); SETTLE box destroyed in setup; audit: ep2 overlap costs only 0.042 | both off by default; never A/B'd |
| 35 | Capped beige cup (STATUS 24 Oct night plan) | CPU: mesh poor overall (42 % unknown, 268 fragments) "a cap would not fix it" (L3259) | rejected unrun |
| 36 | v5 port (provenance, mesh_decimate, collision_decomp, make_assets --pieces, mesh_post, mesh_gates, recon_mesh obs, rest_support, ep_mesh) (L3311–3385) | each reproduces the study bit-identically on saved grids; rest_support reproduces the v3 sweeper patch within 0.5°; ep_mesh pieces union 1.32× solid (> 1.25 gate) | code in repo; not wired into pipeline_ep.sh (no stage 2m) |
| 37 | G1: re-track 16 public eps with library_v2 templates ($1.1) (L3340–3405) | registered perception mean 0.810; failures ep0 lid (pot mask), ep11 cups (lap), ep23 boards (swap) | tracks used for v5 (partly broken) |

### 25 Oct: library v5, beige cup, arc foot, approaches 1–2, spoon
| # | Method | Measured | Verdict |
|---|---|---|---|
| 38 | **Library v5 build** (`20261025-lib5-c476e68`, ≈ $4.2) (L3547–3558, L3604) | pot, lid, boards failed (broken G1 tracks / missing M0); **E2: v5 worse than v2 on 4/5** (sweeper 0.526 vs 0.316, rack 0.818 vs 0.555, dust pan 0.368 vs 0.331, blue 0.540 vs 0.523; pitcher 0.890 vs 0.894); 0 flips | not used (except beige) |
| 39 | **v5 beige cup** along re-tracked ep11 (cups box) (L3514–3527, L3559, L3684) | CD-O 0.730 vs 0.856, 0 flips, AUC on ep11 track 0.937 vs 0.933; ep11 twin **0.525 → 0.570** (beige own 0.03–0.06 → 0.141; still falls 50 mm/29°) | **adopted** (v3x, eval 8 only; eval 8 sim_vs_ref 0.82 → 0.97, together with the track guard); eval 10's v3x run killed (njmax, 2.4–8.9k steps/s, L3974–3978) |
| 40 | **Arc foot** in `support_fill.py` (circle fit in 0–2 cm band, ≥120° arc, RMS ≤ 25 % r (v1 15 % rejected pitcher), 8 sectors, sim only) (L3627–3650) | CPU pitcher 4.7 mm/1.2° (was 158 mm/81°); **ep21 twin 0.657 ± 0.093 → 0.772 ± 0.009** (pitcher 0.414 → 0.591) (L3949) | **adopted** (eval 20 0.287/0.336 → 0.892) |
| 41 | Cup cavity probe (L3592–3600) | blue cup solid over lower 37 %; v3/v5 beige hollow | → hybrid carve (#47) |
| 42 | Approach 1, motion-constrained meshes (`approach1-…md`) | slot cut in collision copy: CPU proxy 101°→0.5°; 6/16 two-object eval refs interaction-infeasible (4–84 cm³, 7–12 mm deep); submitted-mesh carving harmful/neutral (22 Oct); **identity swap on eval 25** (ep24 0.029 → 0.706 after rule) | collision-copy carve + identity rule adopted |
| 43 | Approach 2, primitives (`approach2-…md`, RULES.md frozen before [D]) | lathe package −0.103 cm wCD-O, −0.41 mm ADD, 0 flips → board ≈ 0.331 [E]; beige lathe stands (margin 32.6 mm); blue cavity 35.4 % → 0.2 %; box-slot boards 10.7 → 0.05 cm³ at ep24 but only −4.7 cm³ at eval 25; pitcher/lid/rack/sweeper fail gate | lathe for submission **parked** (organiser question); lathe pieces used for ev10 collision |
| 44 | Spoon: anchor sensitivity, registration flips, A-f0 rest-averaged anchor (spoon-2026-10-25) | 10° roll costs 0.09–0.28 on spoon-anchored evals; flips 0/300; A-f0 mean +0.001 (< +0.01) | A-f0 not adopted |

### 26 Oct: collision-copy carves (submitted meshes unchanged)
| # | Method | Measured | Verdict |
|---|---|---|---|
| 45 | `interaction_carve.py slot` eval 25 (L4021–4050) | proxy 1.17 cm/103.7° → 0.06 cm/0.5°; hull overlap 11.8 → 0.17 cm³; FlashCHORD CPU 7.47 cm/47.9° → 0.12 cm/0.4°; removed 9.3/9.7 cm³ | — |
| 46 | GPU eval 25 carve, std learner (L4185–4189) | s42 **0.792 ± 0.103** vs 0.712 ± 0.189 (s43 0.474) | **adopted** (pack 4) |
| 47 | `lathe_collision.py` eval 10: lathe / lathe-s8 / hybrid (blue = CoACD hulls clipped below inner floor + 3 mm lathe walls; beige = lathe ring base, shrink 8 mm) (L4085–4120) | lathe-on-lathe nest overlap 113 cm³ (no shrink) vs 18 (8 mm): **our reference nests deeper than the shapes allow**; rest: beige falls 6/6 → 0/6; nest error 4.45 → 0.44 cm; pre-registered standing rule failed as written (check frame); lathe-only blue rocks/falls 1/2 | hybrid used |
| 48 | GPU eval 10 hybrid, std learner (L4211–4218) | 0.453 / 0.452 vs floor 0.448 (was 0.334): cups stand, stacking not learned | adopted s43 (pack 4) |
| 49 | Grasp lock on carved cups (L4303–4325; ev10-stack README) | A 0.454, B 0.438, never lifts; open-loop plan carries cup but hits blue rim (≤ 9.65 kN), 6–7 cm sim misalignment | falsified |
| 50 | Hull census (`tools/hull_census.py`, forensics §3) | conflicts > 10 cm³: eval 10 112, 14 72, 1 51, 28 39, 8 38, 30 29, 25 12 cm³; 32/33 clean | placement carves proposed |
| 51 | Sweeper flip re-check (L4130) | 22 Oct eval-30 flip not reproduced; 4/40 random seeds flip | cleared (but see §6) |

---

## 4. Ideas proposed but never run

| Idea | Where proposed | Status / blocker |
|---|---|---|
| Lathe meshes as the **submitted** CD-O meshes (blue cup, pot, maybe beige) | approach 2 §6.2–6.3; STATUS 25 Oct | CPU rescoring test pre-registered (pass if registered AUC per object ≥ base − 0.005, no flip), never run; parked on organiser Q2; lathe outputs not in git |
| GPU strongest tests: cups lathe+nest (ep11, $21–29), pot+lid lathe+rim (ep2/27, $28–38), B1 box boards (ep24, $28–38) | approach 2 §6.3 | not rented |
| Approach-1 T-b (lid collision carve on ep2), T-c (outer-cup cavity carve on ep11), G-1/G-a/G-b/G-c | approach 1 §6 | not run (G-1 superseded by the eval-25 identity rerun) |
| Placement carves for rack/pot (evals 14, 28, 30, 1), swept-volume | forensics §5 item 4; robustness §5 #6 ($15–20) | needs per-episode asset folders + checkpoint/asset hash first |
| Automatic GT-free asset step (certificate → census → carve → FlashCHORD gate), [H3] | robustness review §5 | not built |
| Registration-stability gate on every submitted mesh (40 seeds + scorer seeds, perturbed self-copies) | robustness review §9 | not built (one-off scripts only) |
| v5 E1 (rest clip), E2b (episode filter), E3 (global edge filter), E4–E10; G2 ($13–18) and G3 ($63–86) | `docs/mesh-v5-spec-draft.md` §11–12 | only E2 (partial) ran |
| Per-eval-episode re-fusion (stage 2m; owner decision 22 Oct 11:20) | spec §10.1; WL L1519 | `ep_mesh.py episode` exists, not wired (no `MESH_REFUSE` in `pipeline_ep.sh`) |
| v5-seeded re-tracking / washout iteration (O1 b) | spec §3.5, §12 | not run |
| Spoon T_fit (template fitted to episode evidence; joint fit over 10 eval eps; seed band) | spec §9; exp-spoon.md | `spoon/fit_spoon.py` is a skeleton; `fit_spoon_cpu.py` lived in the deleted scratchpad; owner O5 open |
| GT-free ICP alignment of per-episode grids before summing | exp-fusion-all-objects.md [H] | not run |
| "A constant tracking bias cancels in the scorer's registration" | WL L727–730 | not tested |
| Mesher from TSDF zero level without blur at 4 mm (classic/F4 still blurs σ 0.8) ; 2 mm voxels + 4–5 mm τ for plates; Directional TSDF / RoutedFusion | simvalid critique X3; simvalid synthesis | O branch uses `cont` MC; classic path unchanged |
| Pitcher lathe refit to depth/masks; "better pitcher geometry for registration" (H3: reference AUC ≥ 0.6) | approach 2 §1; audit-starts F1 H3 | not run |
| Analytic `<box>`/`<cylinder>` colliders (never decomposed by CoACD) | note 19 §1; approach 2 §3 | not run |
| `enable_multiccd` test for standing on few pieces | s5coll [H] | not run |
| Mass = volume × density class (0.3 kg placeholder everywhere) | note 09 S5 | not run |
| Generative completion: SAM 3D Objects, TRELLIS.2, Hunyuan3D-2.1; 2DGS via gsplat in object frame; BundleSDF / organisers' `v2d_bundlesdf` | note 03 §7; note 05 §I; note 09 R3.2/S5; WL L673–680 | **never run** (licences: BundleSDF/nvdiffrast NC, Hunyuan territorial) |
| Cross-episode library with Sim(3) registration of partials + revolution/generative completion of unseen regions | note 05 §I (falsifier: single vs multi Chamfer, kill if < 20 %); note 09 R3.2 | our v1 is multi-episode without inter-episode registration; #27 suggests single episodes win |
| Organiser email (Q1 collision ≠ visual, Q2 completion/primitives, Q3 bootstrap, Q4 spoon) | `docs/organiser-email-draft-2026-10-22.md` | never sent |

---

## 5. Measurement tools and how to run them

| Tool | What | Command | Needs |
|---|---|---|---|
| `docs/research/work/mesh-v5-evidence-2026-10-22/mesh_metric.py` | kit CD-O + registration ADD/rot/flips at eval seeds (+ extras to ≥6), eval-pair weights, GT-free ambiguity | `mesh_metric.py run --out R.jsonl --manifest M.tsv` / `table --res R.jsonl` / `amb label=obj=path` | **paths hard-coded** to the dead scratchpad (`SCR=…8c892c5e…`, `KIT=$SCR/loc/kit`, `SCANS=$SCR/loc/t3/mesh`, lines 41–44): edit first; public scans (`fetch_data.sh`); kit |
| `pipeline/recon_eval.py` | per-episode CD-O, registration over N seeds (flip = >30°), optional registered AUC | `recon_eval.py EP RECON_DIR [--poses poses_world_vo.npz] --t3 /content/t3 --kit KIT --seeds 8` | scans, kit, tracks |
| `pipeline/score_registered.py` | official-style registered AUC/SP/MP/MPPE (public scan stand-in, anchor = surface centroid guess) | `score_registered.py EP {results_dir|poses_world_vo.npz} --meshes DIR` | mocap parquet, scans, kit; `--reg_seeds eval` from the spec is **not implemented** |
| `pipeline/mesh_sensitivity.py` | damaged-scan sensitivity | `mesh_sensitivity.py EP POSES OUT --modes clean,hull,...` | as above |
| `pipeline/mesh_gates.py` | GT-free X flip, C consistency, G6, topology (kit functions, our meshes only) | `mesh_gates.py {flip|consistency|g6} CAND REF [OBJ] --kit KIT` | kit only (no scans) |
| `pipeline/recon_mesh.py` classic | 4 mm TSDF mesher | `--poses a.npz,b.npz --depth a.npy,b.npy --hands h1,h2 --others "n=mesh;..." --calib calib.json --obj X --out X.glb --stride 2 [--below_carve 0.004 --close auto --edge_thr 0.02]` | depth caches (store), tracks (store), hands, calib |
| `recon_mesh.py obs` → `mesh_post.py` → `mesh_decimate` | v5 evidence grids / O mesh / gates | `recon_mesh.py obs --obj X --out G.npz --roi M0.glb --ep POSES DEPTH HANDS 2 OTHERS`; `mesh_post.py OUT G.npz --mode nobc` | same; ~1.5–13 min/object-episode CPU |
| `pipeline/ep_mesh.py`, `ops/build_library.sh` | whole v5 chain (library or `episode` mode) | `G1RUN=20261025-g1-022fece bash ops/build_library.sh` (box; 48 cores ≈ 2.7 h) | store tracks + depth; open3d 0.20.0, pymeshlab 2025.7.post1, libopengl0, warp, rtree |
| `pipeline/support_fill.py` (+ `SF_ARC`) | stability certificate, fills, arc foot | `support_fill.py REF.parquet USDA OUT_ASSETS OUT_REF.parquet` | reference parquet + table usda |
| `pipeline/interaction_carve.py slot`, `pipeline/lathe_collision.py`, `pipeline/collision_decomp.py`, `make_assets.py --pieces` | collision-copy carves / pieces | see `meshes/carve/ev{10,25}/carve.json` "commands" | FlashCHORD venv (Warp, CoACD cache), reference parquet; lathe profiles from `approach2-scripts/lathe_fit2.py` |
| `tools/carve_fc_test.py`, `tools/hull_census.py`, `tools/rest_check.py`, `tools/frame_quality_probe.py` (VOC=0) | FlashCHORD-physics CPU checks: insertion/nest tracking, reference-vs-hull conflicts, zero-action rest | per docstrings | FlashCHORD venv, references from the store |
| `docs/research/spoon-2026-10-25/spoon_regflip.py`, `spoon_anchor.py`, `tools/anchor_f0_test.py` | spoon flip MC, anchor sensitivity | per README | kit, our references |
| Not ported (only in the dead scratchpad): `tools/mesh_diag.py`, `tools/replay_rest.py`, `tools/hullovl.py`, `maskfuse.py`, `spoonfuse.py`, `fit_spoon_cpu.py` | | | rebuild from `prototypes/` or rewrite |

GT-free proxy worth reusing: kit chamfer of a candidate to an independent mesh of ours ranks meshes like scan CD-O
(Spearman 0.86, n 19; spec App. B).

---

## 6. Lessons and pitfalls

- **Inference legality.** Library v1–v4 were fused along tracks templated on the public scans, with the scans as
  `--others`. The only compliant rebuild (v5, own-mesh tracks) came out *worse* than v2 on 4/5 objects
  (WL L3607–3609). The submitted meshes are therefore not compliant by the letter (organiser Q3 never sent).
  Compliant tracks are themselves seeded by library_v2 (tier P1).
- **Broken tracks silently poison fusion.** The G1 tracks of ep0 (lid), ep11 (beige cup on the lap) and ep23 (swapped
  boards) wrecked v5's lid, pot, boards and beige cup. The X gate cannot see it (it compares to M0 of the same build).
  Re-track with today's detection plus the track guard first (sweep base 0.868), or gate episodes (E2b).
- **Thick walls and rounded edges come from the mesher, not only from closing.** Binary ±1 + σ 0.8 voxel blur at 4 mm
  discards sub-voxel TSDF values:

  | Part | Ours | Real |
  |---|---|---|
  | dust pan | 11–13 mm | 3–5 |
  | lid | 12–13 | 2–7 |
  | pot walls | 15–20 | 4 |
  | board 2 | 12 | 9 |

  51 % of the 2,940 cm³ excess volume lies within 4 mm of the scan surface. Inflation is the most damaging defect for
  registration (5 mm → AUC 0.608, flips).
- **Unobserved undersides.** The table hides them:
  - `fill` closing made slabs under the table (pot 5.5 cm, dust pan 3.5 cm), so mkref rejected the table;
  - otherwise they come out round or coned (sweeper, beige cup, pitcher, board edges), so objects fall with the assist
    off.

  Fixes that worked: `--below_carve` (v2), flatten (v3), arc foot (sim only). Per-frame below-table votes at 2 mm erase
  real wood and rack, and flip boards.
- **Cavities get filled.** The blue cup's lower 37 % is solid (400 vs 136 cm³), and CoACD fills cavities and slots
  again. So any concavity fix must reach the simulator as our own convex pieces or primitives, from the full-resolution
  mesh (a slotted 4096-face board still gave 13.5 cm³ of hull overlap).
- **Registration flips on flat or near-symmetric objects.** Boards and sweeper sit on a near-tie: 0–25 % of seeds,
  moved by small parameter changes. Primitives and symmetrising raise the risk (box-slot board 2: 2/6 flips). GT-free
  self-ambiguity excess < 3 mm predicts it (36/92 vs 2/89). The scorer's seeds are fixed, so any mesh swap can silently
  land in a flipped mode. Re-check at eval seeds and ≥ 6 extras.
- **CD-O and ADD can move in opposite directions.** Design O lid: CD-O better, ADD 7.6 → 14 mm. Beige lathe: CD-O
  0.730 → 0.292, ADD 5.4 → 8.2. ADD feeds all five pose boards, and most for anchor objects (pot, rack, sweeper,
  pitcher, board 1, dust pan, spoon). Judge both.
- **Multi-episode fusion is not free.** One single episode beat the all-episode mesh on 6/6 objects [D]. Likely
  inter-episode pose/shape misalignment [H]. No GT-free picker found (3/6).
- **Interaction carving belongs in the collision copy, never in the submitted mesh.** On the submitted mesh it was
  neutral or harmful every time:
  - lid +0.14–0.18;
  - nested cups 1.17 → 1.43;
  - new flips.

  Track bias (≈ 0.8 cm / 2.4°) is about one slot width; 36–47 % of what the planar cut removes is real wood [D].
- **Simulator plumbing traps:**
  - Newton splits vertex-coloured meshes into per-colour shapes, so the simulator copy must be colourless;
  - the kit `budget_mesh` breaks watertightness on most meshes;
  - one contact per convex pair, so few-piece feet wobble and a single box sinks 9.6 mm;
  - heavy piece counts slow training (v3x beige 32 pieces + stacked filled cup: njmax overflow, 2.4–8.9k steps/s);
  - the shared `/content/assets` keyed by object name can silently feed the wrong collision copy;
  - CPU probes must run with the object assist off (VOC=0), or stability looks better than in evaluation.
- **Diagnose before blaming the mesh.**
  - The v4 boards' perception 0.029 was an identity swap.
  - ep24 with the organisers' meshes was no better (0.317 vs 0.307).
  - Eval 10's carved cups stand, but the reference's nest is deeper than the shapes allow, and the rim collision
    (6–7 cm misalignment) blocks learning.
- **The public scan works as a stand-in.** The CD-O board moved exactly as the proxy predicted for the eval-8 beige
  swap (−0.0035). The spoon (10/36 pairs) is unmeasurable; inferred ≈ 0.18 cm [E] against 0.10–0.12 synthetic for the
  template family.
- **Housekeeping traps:**
  - stale `recon.json` (beige cup);
  - v3x beige has no vertex colours (FoundationPose appearance term; effect unmeasured);
  - `mesh_metric.py` points at a deleted scratchpad;
  - the prototype grids and lathe outputs are gone, so every 22 Oct number needs regenerating before reuse;
  - all 22 Oct [D] numbers were made on scan-contaminated inputs.
