# C4: multi-seed mesh registration audit of packs 13e/13f, and an adoption rule for pack 13g (pre-registered)

Written 2026-11-02 ~19:50 UTC. It is committed and pushed **before any multi-seed number exists** for any mesh, shipped or
candidate. Requested by keen-heisenberg (coordinator, 19:33 UTC), with the owner asking to "push further". This is under
the owner's approval of GT-informed selection by public-scan score ("Okay I give you permission for all", 19:00 UTC).
CPU only, $0.

Labels: [D] diagnostic, scored against the public scan; [M] measured without ground truth; [E] estimate; [H] hypothesis.

## 1. Why
The scorer registers each submitted mesh to the hidden scan (kit `AUC.py _register_object_body`: scale-normalised,
trimmed ICP from 25 starts). It then expresses our poses through that registration. A mesh that registers into a wrong
basin turns correct poses into wrong ones:
- SP-SR needs a mean orientation error <= 0.5 rad;
- MP-SR needs < 30 deg.

Until now each mesh was scored on the scorer's eval seeds plus a few extras. The goal here is a seed-independent
registration quality. Following the coordinator, the scorer's eval seed must not be used as a criterion, because that
would tune to the scorer's randomness.

## 2. Audit protocol (fixed now)
- **Script.** `scripts/audit_multiseed.py`, a wrapper around `scripts/mesh_metric.py` `evaluate()`:
  - kit `_register_object_body` and `_object_chamfer_cm`;
  - candidate and public scan both go through the kit `budget_mesh(4096, 4096)`;
  - the mesh_metric symmetry handling (cups: spin about the axis is free; lid: 0/180 deg).
- **Seeds.** **50 seeds, 3001..3050.** No eval seed (the roster is emptied for these runs) and no earlier extra seed.
- **Per mesh, over the 50 seeds:**
  - CD-O median and mean (cm);
  - FLIP rate (symmetry-aware rotation error > 90 deg);
  - W30 rate (rotation error > 30 deg, the MP-SR threshold);
  - anchor error median and p90 (mm);
  - rotation error median and p90 (deg);
  - GT-free self-ambiguity (amb_mm vs amb_floor_mm), as mesh_metric computes it.
- **Meshes, in order.**
  1. Every mesh shipped in 13f, one per object. 13f differs from 13e only in the blue cup and the dust pan.
  2. The two 13e meshes that 13f replaced (C0 blue cup 9e3a74fd, T2 dust pan 19765405).
  3. library_v3 of each object.
  4. Candidates: per object, the 3 lowest-CD-O existing meshes in `review/library_index.json`, by their earlier [D]
     records. Excluded: the shipped mesh and its unplaced generator source; anything with recorded CD-O < 0.10 cm (scan
     template guard); duplicates by md5. The list is frozen in `candidates.json`, written before any run.
- **Placement of generated candidates.** Generated meshes (`gen/*`, `diag/sam3d_lib_vis/*`) are first placed in the
  library_v3 frame with the GT-free C1/T2 `place.py`, as for every generated mesh we shipped. The placed copy is
  what gets audited.
- **Wooden spoon (10 pairs).** There is no public scan, so the spoon cannot be audited against a reference. It gets the
  GT-free self-ambiguity of the shipped spoon (library_v3, md5 68dcf049) only, and no adoption.

## 3. Adoption rule for pack 13g (fixed now)
Baseline S = the 13f mesh of the object. A candidate C is **adoptable** only if it passes all three of these checks:
- it is not a byte copy of a public scan (md5 check against all scan files);
- its CD-O median is >= 0.10 cm (template guard);
- it was built from our own video or generator outputs.

It is then **adopted** if either test holds:
- **(A) shape:** `CDO_med(C) <= CDO_med(S) - 0.020` **and** `W30(C) <= W30(S) + 0.05`;
- **(B) registration:** `W30(C) <= W30(S) - 0.20` **and** `CDO_med(C) <= CDO_med(S) + 0.005` **and**
  `ANC_med(C) <= ANC_med(S) + 2.0 mm`.

Further rules:
- **More than one adoptable candidate:** take the lowest W30; then the lowest CDO_med; then the lowest ANC_med.
- **No candidate qualifies:** the 13f mesh stays.
- **Shipped meshes with W30(S) >= 0.20 and no qualifying candidate** are reported as priorities for a new build. A new
  build needs its own pre-registered plan.
- **No leaderboard result** is used for any choice. The eval seeds are not used. Every number comes from this one
  50-seed run per mesh, with no re-runs. If a run crashes, it is re-run once and the crash is logged.

## 4. Predictions (to be checked)
- [H1] Cups and the lid have W30 near 0, because the kit declares their symmetries.
- [H2] The board occupancy plates show FLIP > 0.10, from their near-180-deg symmetry (1 of 6 seeds flipped before).
- [H3] The rack candidate `rack/ep31_*` has the same anchor offset as the shipped dev1 fit (about 9 mm).
- [H4] No candidate passes rule (B) for any object. Our meshes rarely flip except on the boards.

## 5. Outputs
- `results/audit.jsonl`: one record per mesh with all seeds.
- `results/audit_table.md`: the table sent to the coordinator.
- `results/adoption.json`: the rule applied.
- `NOTES.md`: timestamped log.

## 6. Addendum 1 (2026-11-02 20:03 UTC by commit time, before any build or score of these variants): less-symmetric board 2
**Why.** Audit part 1: the shipped wooden_piece_2 (Tier B occupancy plate) flips on 34% of 50 seeds [D]. The coordinator
(20:01 UTC) asked for a GT-free, less-symmetric board-2 variant, adoptable only under rule (B).

**GT-free inputs (measured before this addendum):**
- library_v3 wooden_piece_2 has 4 protrusion clusters beyond its plate slab. One is the marker ball the occupancy fit
  also has; there are two more balls on the same face and a 32 mm ridge on the other face.
- The occupancy plate keeps only the one ball.
- Both meshes are ours and share a frame (ICP 0.73 mm / 0.59 deg).

**Build (`scripts/board_graft.py`).** Base = the shipped `wooden_piece_2_ep24_occ.glb`.
1. Take library_v3 faces whose centroid lies more than (t/2 + 1 mm) from the occupancy plate's mid-plane and inside
   its outline expanded by 10 mm.
2. Cluster them (single linkage, 10 mm, on face centroids). Drop clusters with < 20 faces, and any within 12 mm of an
   occupancy-plate protrusion (already present).
3. **v1** = base + the clusters that are *supported*: >= 30 ep24 observed board-2 points (`obs_all/ep24_wooden_piece_2.npz`,
   GT-free) within 3 mm of the cluster surface.
4. **v2** = base + all clusters.

Faces are concatenated; no boolean is used.

**Evaluation.** Exactly section 2: the same script, seeds 3001-3050 and summary.

**Adoption.** Rule (B) only, against the shipped board 2: W30 <= W30(S) - 0.20, CD-O median <= S + 0.005,
anchor median <= S + 2.0 mm. If both pass: lowest W30, then lowest CD-O. If v1 == v2 (all clusters supported), audit once.

**Predictions.**
- [H5] v2 flips on < 10% of seeds, because library_v3 itself is expected to be near 0.
- [H6] v1 keeps at least one of the two extra balls (ep24 sees face -1).
- [H7] CD-O changes by < +0.005 cm, since the features are small.

## 7. Addendum 2 (2026-11-02, written before any generation or rental): G2 generation batch for the weakest shipped meshes
**Why.** The coordinator relayed the owner at 20:13 UTC: "go crazy, let's win this". Credit is $127.97. The task is new
candidate generation for the weakest shipped meshes, with GPU spend <= $25, stopping if total Vast credit falls below
$15. Board 2 is handled separately (addendum 3, CPU).

**Objects and inputs (GT-free).**
- Objects: white_pot (6 pairs), blue_cup (5), plastic_dish_rack (5), water_pitcher (1).
- Inputs are `scripts/crops.py` RGBA crops from public episodes that contain the object. There are up to 3 episodes per
  object and up to 2 crops per episode, under crops.py's own ranking. The plan per object:
  - pot: ep41 / 43 / 44;
  - blue cup: ep22 / 21 / 12;
  - rack: ep31 / 12 / 26;
  - pitcher: ep22 / 21.
  The real episode list is fixed by what crops.py accepts, and it is logged.
- No scan, mocap, parquet pose or *_align reaches the generation inputs.

**Generation.**
- Generators: SAM 3D Objects, Hunyuan3D-2.1 (shape) and TRELLIS.2 (1536; 1024 if it runs out of memory, labelled).
- Seeds 42, 7, 123 and 2025, so at most 6 crops x 3 models x 4 seeds = 72 meshes per object.
- Each output gets a GT-free Sim(3) fit to our observed points (`gen/sim3_fit.py`), as in the 29 Oct probe.
- Every file is hashed (SHA256SUMS), and the hash list is committed **before any scan read** of these meshes.

**Selection (GT-informed, disclosed as for Tier B).**
1. Stage 1 screen [D]: one `mesh_metric` scoring per generated mesh (Sim(3) copy), 6 seeds 3001-3006, roster emptied.
2. Stage 2: per object, the 4 lowest stage-1 CD-O medians. Each is placed in the library_v3 frame with the GT-free
   C1/T2 `place.py`. A generate-then-fit copy is added with the C1/T3 GT-free fit, if its code runs unchanged. That is up
   to 8 meshes per object.
3. Stage 3: the section-2 audit (50 seeds 3001-3050) of every stage-2 mesh.
4. Adoption: section-3 rules (A)/(B) against the then-current baseline (13f, or 13g if 13g adopts that object).

No leaderboard input is used; the winners are fixed before any upload.

**Cost.** One H100-class box (interruptible where sensible), expected 3-5 h, about $6-12 including downloads [E]; the cap
is $25. Ledger planned line before creation (LEDGER_SESSION=mesh-bold). The box self-destroys. Stage 1 may run on that
box's CPUs, but only after the hash list is committed.

**Prediction.** [H8] At least one of pot / blue cup / pitcher gets a rule-(A) win (CD-O -0.02). The rack does not: the
29 Oct generators' best rack was 0.604 vs our 0.418.

## 8. Addendum 3 (2026-11-02, before any build of these variants): board 2, round 2
**Evidence so far [D, 50 seeds]:**
- library_v3 board 2: W30 0.00, CD-O 0.2169, anchor 3.28 mm.
- Shipped occupancy plate: W30 0.34, CD-O 0.1649.
- graft_v1 (plate + 2 library balls): W30 0.18, CD-O 0.1628.

GT-free differences that remain between graft_v1 and library_v3:
- (i) library_v3's plate slab is 12.5 mm thick; the occupancy plate uses a *default* thickness of 8.9 mm (`t_src:
  default` in its fit record, not measured);
- (ii) library_v3 has a 69-face feature on face +1 (graft cluster 1, unsupported by ep24 points: 9).

**Variants (`scripts/board_graft2.py`; base = graft_v1, our meshes only):**
- **v3** = graft_v1 + cluster 1.
- **v4** = graft_v1 with the plate re-extruded to library_v3's slab thickness:
  - vertices within the occupancy slab have their offset from the mid-plane scaled by t_lib / t_occ;
  - vertices beyond it (the ball) are shifted outward by (t_lib - t_occ)/2;
  - t_lib is the 10-90 percentile slab of library_v3 measured as in `board_graft.py`;
  - the grafted library balls are not moved, since they already sit on library_v3's faces.
- **v5** = v4 + cluster 1.

**Evaluation, adoption and predictions.**
- Evaluation: section 2, 50 seeds 3001-3050.
- Adoption: rule (B) only, against the shipped board 2. Ties: lowest W30, then lowest CD-O.
- Predictions:
  - [H9] thickness (v4) matters more than the +1 feature (v3);
  - [H10] v4 reaches W30 <= 0.14;
  - CD-O stays <= 0.1699 [H, uncertain: a thicker plate may cost CD-O].

## 9. Addendum 4 (2026-11-02, written before D1 is applied to any candidate): D1 safety gate (coordinator 20:24 UTC)
**Finding that prompted it [D, re-run just now].** At eval 25 slot 1's eval seed 25000176, the shipped Tier B board 2
(md5 bf82e385) registers:
- with the budgeted public scan as reference (mesh_metric default, used by this audit's section 2): 1.05 deg, no flip;
- with the **raw** public scan as reference: 179.18 deg, a flip. This matches the perception lane's 179.2 deg.

library_v3 board 2 does not flip in either mode. A near-symmetric mesh's single-seed outcome depends on how the reference
is sampled, and the hidden scorer's preparation is unknown.

**D1, a hard veto on top of rules (A)/(B), not a selection score.** A mesh is adoptable for an (episode, slot) only if:
- (a) the mesh_metric default seed set for the object (the scorer's eval seeds for every (episode, slot) the mesh goes
  into, plus extras up to >= 6 seeds) gives **0 flips in both reference modes** (budget and raw); and
- (b) its section-2 50-seed W30 is <= 0.10.

Rules (A)/(B) still choose. D1 only removes candidates.

## 10. Addendum 5 (2026-11-02 ~21:17 UTC, coordinator-approved, before any G2 scoring): rule (C) for G2 candidates
Applies only to G2 candidates (`candidates_g2.json`), alongside rules (A) and (B) of section 3 and the D1 veto of
section 9. Baseline S = the then-current shipped mesh of the object.
- **(C) registration:** `ADD_med(C) <= ADD_med(S) - 2.0 mm` **and** `CDO_med(C) <= CDO_med(S) + 0.005` **and**
  `W30(C) <= W30(S)` **and** D1 passes.
- ADD_med and the other metrics come from the section-2 50-seed audit, with the budgeted reference.
- Ties among candidates passing any of (A)/(B)/(C): the lowest W30, then the lowest CDO_med, then the lowest ADD_med.
- Rule (C) is NOT applied to any mesh already measured in sections 2-8. Pot `potlid/tsdf/ep43` and dust pan Pixal3D-MV
  ep39 s7 go to the perception lane's own pre-registered public-pose test instead (coordinator, 21:16 UTC).
- **Stage-2 extension for rule (C)**, also before any G2 scoring. Besides addendum 2's 4 lowest stage-1 CD-O medians per
  object, stage 2 also takes the 2 lowest stage-1 ADD medians among G2 meshes whose stage-1 CD-O median is <= the
  shipped mesh's 50-seed CD-O median + 0.005, when they are not already among the 4. They are placed and audited the
  same way.

## 11. Addendum 6 (2026-11-03 ~00:08 UTC, before the build): GT-free trim of the G2 rack's hallucinated bulge
**Finding [M, GT-free]:** the adopted G2 rack (`plastic_dish_rack_g2_hy21_ep31_k282_s123_lib_t3fit.glb`, md5 a289d009) has
a +x bulge, 0.5% of its surface, at x +37..+110 mm. Our ep31 observed points never come near it (median 36 mm away),
and the shipped dev1 primitive rack ends at x +72 mm.

**Build (`scripts/rack_trim.py`).** Delete every G2-rack face whose centroid is > 15 mm from BOTH:
- (a) our ep31 observed rack points (`obs_all/ep31_plastic_dish_rack.npz`, GT-free); and
- (b) the dev1 primitive rack surface (ours).
Faces that are unobserved but consistent with our primitive fit are kept. No hole filling.
One candidate: `rack_g2_trim15`.

**Evaluation.**
- Section 2 audit (50 seeds 3001-3050), D1 (section 9), and rules (A)/(B)/(C) against the then-current CD-O pack mesh,
  i.e. the untrimmed G2 rack (CD-O 0.4016, W30 0, ADD 4.3 mm).
- If it passes, it replaces the untrimmed rack in a pack 13h2. If not, 13h stands.

**Prediction.** [H11] The trim lowers CD-O by 0.002-0.01, below rule (A)'s 0.02 bar. It then passes only if rule (C)
or (B) applies, which is unlikely since ADD and W30 are already good. So the most likely outcome is no adoption.

## 12. Addendum 7 (2026-11-03 ~01:55 UTC, before any G3 generation or rental): G3 batch, CD-O pack 13i on 13h
**Why.** The coordinator relayed the owner at 01:47 UTC: "do as much as you can tonight". Credit is $94.58; the GPU cap is
<= $15; stop if credit < $15. We are 5th on CD-O at 0.25159; 4th is 0.24669.

**Leverage (13h meshes, 50-seed CD-O medians x pairs / 36) [D]:**
- rack 5 x 0.402; pot 6 x 0.286; blue cup 5 x 0.234;
- dust pan 2 x 0.229; beige 2 x 0.250; sweeper 2 x 0.222;
- lid, pitcher, boards: 1 pair each.

The objects G2 did not cover can give about -0.003 at most [E]. The rack and pot still carry the most weight.

**Objects and inputs (GT-free crops from public episodes via `scripts/crops.py`, its own ranking, <= 2 crops per episode):**
- G3a, the coordinator's list:
  - mini_dust_pan (eps 18 / 39 / 40);
  - beige_cup (episodes with the beige cup that crops.py accepts);
  - white_pot_lid (eps 0 / 2);
  - mini_sweeper (eps 18 / 31 / others crops.py accepts);
  - wooden_piece_1/2 (ep24 only; ep23's board-2 track is known wrong).
- G3b, added by the mesh lane because of the leverage above:
  - plastic_dish_rack on episodes / crops **not used in G2** (G2 used ep31 / 12 / 26);
  - white_pot on episodes **not used in G2** (G2 used ep41 / 43 / 44).

**Generators.**
- SAM 3D, Hunyuan3D-2.1, TRELLIS.2 (1536; 1024 if it runs out of memory) for all objects; seeds 42, 7, 123, 2025.
- Pixal3D-MV (posed, our frame, `gen/mv_views.py` view sets) for dust pan, beige, lid, sweeper and boards; seeds 42, 7,
  123, 2025.
- GT-free Sim(3) fit for the single-image models; SHA256 freeze committed before any scan read.

**Selection (same as G2, plus one more copy type).**
1. Stage 1: 6-seed screen (3001-3006).
2. Stage 2: the 4 lowest CD-O per object, placed (place.py).
3. Stage 2 copies: a T3-fit copy, and a **trim copy**. The trim deletes faces whose centroid is > 15 mm from both our
   observed points of that object (the episodes used for its crops) and the 13h mesh of the object (`scripts/rack_trim.py`
   logic, generalised).
4. Stage 3: section-2 audit (50 seeds 3001-3050), rules (A)/(B)/(C) and the D1 veto, against the **13h** mesh of each
   object:
   - pot G2 0.2861; blue cup G2 0.2335; rack G2 0.4016;
   - dust pan hy21 0.2291; beige T1 0.2501; lid 0.2177; sweeper P1 0.2220; pitcher 0.3713;
   - board 1 occ 0.1872 (W30 0.06); board 2 Tier B occ 0.1649 (W30 0.34).
5. Ties: lowest W30, then lowest CD-O, then lowest ADD.

**Exclusions and cost.**
- The already-measured rack trim (section 11) stays excluded. The trim copy type applies only to G3 stage-2 meshes, none
  of which is measured yet.
- Cost: one H100/H200-class box, on demand (no preemption). Expected about 1.5-2.5 h at about $4/h plus downloads, so
  about $7-11 [E]. Ledger planned line before creation.

**Predictions.**
- [H12] rule-A wins are most likely for the dust pan and the beige cup (generators reached 0.231 / 0.263 before);
  unlikely for the sweeper and lid.
- [H13] at least one of G3b rack / pot passes (A) or (C).
- [H14] no board candidate passes D1: generated plates flip.

## 13. Addendum 8 (2026-11-03 ~07:20 UTC, coordinator GO, before any copy is built or measured): outer-shell copies
**Why.** G3 #43 (board 2) turned out to be a hollow SAM 3D plate [M, GT-free]: an inner closed shell 1-3 mm inside the
outer one, which doubles the surface area. Generated meshes adopted elsewhere may be hollow too. Pack 13i scored CD-O
0.24177 (4th); 3rd is 0.23900.

**Copy type "outer" (`scripts/outer_shell.py`, GT-free, mesh only).**
1. Split the mesh into connected components.
2. Drop every component whose area is < 1% of the total (fragments).
3. Drop every remaining component that lies inside another: >= 90% of 500 of its vertices (seed 0) are inside that
   component's volume, by trimesh `contains` on the containing component, which must be watertight. If the containing
   component is not watertight, use its convex hull.
4. If nothing is dropped, there is no copy.

**Applied to.** Every generated mesh shipped in pack 13i, plus G3 #43 (board 2, pose CV only):
- pot G3 #0;
- dust pan G3 #9;
- board 1 G3 #24;
- blue cup G2 sam3d k159 s7 t3fit;
- rack G2 hy21 ep31 k282 s123 t3fit;
- water pitcher hy21 ep22 k174 s42 (Tier B).
Non-generated shipped meshes (sweeper P1, beige T1 lathe, lid prim, board 2 Tier B occupancy) are out of scope.

**Evaluation.**
- Section-2 audit (50 seeds 3001-3050), then D1 (section 9).
- Rules (A)/(B)/(C) against the shipped 13i mesh of the same object (the un-shelled original), using its existing
  50-seed record.
- Ties: lowest W30, then CD-O, then ADD. Winners go to pack 13j on 13i.
- #43-outer is offered to tracking-perception's pose CV only, with ep24 excluded from its held-out scoring (the
  coordinator's condition). It is not used for CD-O.

**Predictions.**
- [H15] At least the pot and blue cup (SAM 3D / TRELLIS.2 lineage) have nested shells.
- [H16] Where a copy exists, its CD-O improves by 0.005-0.03 (the inner shell's sampled points sit 1-3 mm off) and
  rule A passes for at least one object.
- [H17] Hunyuan / Pixal meshes are single-shell, so no copy.

## 14. Addendum 9 (2026-11-03 ~07:40 UTC, coordinator GO, before any new rack is generated or measured): rack round R
**Why.** CD-O is 4th at 0.24177; 3rd is 0.23900 (-0.0028). The rack (5 pairs, 13i mesh 0.4016) is the largest term. Closing
the gap needs about -0.020 on the rack, which is exactly rule A's bar. Two clean-ups of the 13i rack reached -0.016 and
-0.017; they are already measured, so they stay excluded (no new rule for measured racks).

**New candidates (GT-free inputs; none measured before this commit).**
- **R-gen (GPU, <= $10, on demand, stop if credit < $15):**
  - TRELLIS.2 (1536; 1024 if it runs out of memory), Hunyuan3D-2.1 and SAM 3D on rack crops **not used in G2 / G3**:
    crops.py ranks 3-6 of public eps 12 / 13 / 26 / 27 / 31, plus any other public rack episode crops.py accepts.
    Seeds 42, 7, 123, 2025, 31337, 777.
  - Pixal3D-MV rack from our posed view sets (`gen/mv_views.py`) on the same episodes, the same seeds.
  - GT-free Sim(3) fit; SHA256 freeze committed before any scan read.
- **R-prim (CPU):** `prim_rack.py` (the C0 / dev1 primitive rack fitter) re-run on public rack episodes that have no
  existing measured prim fit, with its existing settings; plus its existing variant flags if any. These are new files,
  never measured.

**Selection (as G2 / G3).**
1. Stage 1: 6-seed screen (3001-3006) of R-gen. R-prim fits go to stage 2 directly.
2. Stage 2: the 6 lowest stage-1 CD-O R-gen meshes, plus every R-prim fit. Each is placed (place.py; prim fits are
   already in our frame).
3. Copies per stage-2 mesh:
   - **placed**;
   - **t3fit**;
   - **trim**: faces > 15 mm from both our observed rack points and the 13i rack;
   - **outer**: section-13 fragment / nested-shell removal;
   - **trim+outer**: outer applied to trim.
   No-op copies (nothing removed) are skipped.
4. Stage 3: section-2 audit (50 seeds), the D1 veto, and rules (A)/(B)/(C) against the **13i rack** (G2 #17: CD-O 0.4016,
   W30 0, anchor 3.78, ADD 4.30). Ties: lowest W30, then CD-O, then ADD. The winner goes to pack 13j on 13i.

**Prediction.** [H18] P(some candidate reaches <= 0.3816) is about 0.4 [E]. The 13i rack's two clean-ups reached 0.3856 /
0.3844, so a fresh generation + clean-up needs to land about 0.003-0.005 better.
