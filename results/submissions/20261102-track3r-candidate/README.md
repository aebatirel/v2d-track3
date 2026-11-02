# Track 3 pack-13f candidate, 2 Nov 2026 — pack 13e + Tier B+ blue cup and dust pan meshes

**STATUS: PENDING frame sign-off. Not ready, not uploaded.** The mesh lane (bold-albattani) must sign off on the frame
report below. keen-heisenberg's session uploads, on the owner's word there.

**Disclosure: ground truth entered the mesh selection** (Tier B+, see meshes/tierBplus_pack13f/README.md).
- Each mesh is the best generator output by CD-O against the public object scans. It was placed without ground truth and
  scored once [D].
- Neither is a scan copy or template; no_oracle accepts both.
- Same owner approval as Tier B (relayed 19:00 UTC).
- Inclusion timing: the coordinator decided to include them (19:22 UTC, reversing a 19:12 hold) after pack 12e's board
  result showed that meshes also move the pose boards. That decided whether to include them, not which variant to pick.
- All of 13e's disclosures carry over: eval-15 clause-c waiver, Tier B meshes, plate symmetry on eval 25, 12c blue-cup
  selector.

## Record
- File: `build_13f/track3_submission.parquet`, 9,120 rows, 1,281,353 bytes.
  sha256 `fa1e31f570e14537538ec1ab760d540cd1a584dfd0e78364e33adea5411f89db`.
- CD-O file: `build_13f/track3_submission.cd-o.parquet`, 294,912 rows, sha256 `f6e76b280b33c960…`.
- Code: https://github.com/aebatirel/v2d-track3/commit/158dd3724f5473ae4993d8a423e1ec76bdf1b011 (on every row).
- Base: pack 13e (`results/submissions/20261102-track3q-candidate/build_13e`, sha256 0ea45fcd…), first reproduced byte for
  byte from its packer inputs. Built by tools/pack_swap_meshes.py with the guard on:
  `--only-episodes "blue_cup:10,14,20,32,33;mini_dust_pan:19,38"`.

## Content
- Against 13e, only `code_commit_url` (all rows) and `object_mesh_b64` on 7 payload rows differ:
  - blue_cup, slot 0 of evals 10, 14, 20, 32, 33;
  - mini_dust_pan, eval 19 slot 1 and eval 38 slot 0.
- CD-O rows change for exactly those 7 pairs. Offline validate_submission passes. 0 MESH WARNINGs.
- Meshes: `meshes/tierBplus_pack13f/`, byte copies at 4a3b67f. Transform none. The kit's budget_mesh cuts both
  400k-face files at packing.

## Frame report [M] (base = the mesh being replaced; mm)
- **blue_cup** (base C0 9e3a74fd):
  - centroid 3.41; AABB centre 10.28;
  - extent [92.95, 103.61, 167.27] → [100.22, 120.1, 180.98], ratio up to 1.159 (**FLAG** > 15%);
  - surface median / p95 / max 1.60 / 6.98 / 22.92;
  - ICP 4.59 mm / 2.93°; kit proxy 2.74 mm / 2.92° (axial symmetry).
- **mini_dust_pan** (base C1 T2 pick 19765405):
  - centroid 6.84 (**FLAG**); AABB centre 11.42;
  - extent [41.17, 164.19, 167.67] → [46.71, 157.01, 166.64];
  - surface 1.94 / 10.36 / 14.25;
  - ICP 2.38 mm / 1.85°; kit proxy 1.37 mm / 1.58°.

## Known risks (mesh lane)
- **Blue cup:** the kit-registration anchor error roughly doubles (2.1–3.6 → 4.5–7.3 mm [D]), so the blue-cup pairs may
  score lower on the pose boards than with the C0 cup.
- **Dust pan:** anchor about unchanged (4.7 / 6.0 → 6.0 / 5.8 mm).
- **Expected CD-O [E]:** 12e measured 0.26775; 13f ≈ 0.2627.
