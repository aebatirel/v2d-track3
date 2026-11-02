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
