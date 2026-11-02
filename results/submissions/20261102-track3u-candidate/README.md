# Track 3 pack-13p2 candidate, 2 Nov 2026 — pose pack 13p + the eval-20 water pitcher placed from depth

**STATUS: READY. NOT uploaded from this session**: keen-heisenberg's session verifies and uploads on the owner's word
there. The mesh geometry is the already signed-off 12e/13p pitcher. Only its placement Δ changes, and the delivered file
was verified to equal 13p's payload × Δ exactly (below).

**Disclosure.** The placement is a GT-free fit:
- inputs are eval-20 stereo depth inside SAM2 video masks over rest segments, in the body frame of our packed eval-20
  reference;
- nothing on eval was scored;
- the *procedure* was selected by tracking-perception's pre-registered **public pose CV** (PREREG_posemesh.md Part 2;
  mocap of public episodes, development): held-out mean ΔAUC +0.106 (ep21 +0.133, ep22 +0.080).

All disclosures of 13p carry over: the pose-board choices by public CV, the Tier B / B+ GT-informed meshes, the eval-15
clause-c waiver, the eval-25 D1 revert.

## Record
- File: `build_13p2/track3_submission.parquet`, 9,120 rows, 1,315,113 bytes.
  sha256 `19ac10e39e6ab3b95a43caee379e297616226131aca04fd69bc9a9a83990d45c`.
- CD-O file: `build_13p2/track3_submission.cd-o.parquet`, 294,912 rows, sha256 `02678b8f554b7e4b…`.
- Code: https://github.com/aebatirel/v2d-track3/commit/b0bd91fcebf3583f947c60dc413d944d8e130c54 (on every row).
- Base: pack 13p (`results/submissions/20261102-track3t-candidate/build_13f1p`, 3134dfc6…), reproduced byte for byte from
  its packer inputs first. Built by tools/pack_swap_meshes.py with the guard on, `--only-episodes "water_pitcher:20"`.
- Mesh: `meshes/posepack_13p2/water_pitcher.glb`, md5 fb2cb7eaac66699a33d2ec772732bafd. It is a byte copy of
  claude/perception-tracking-20261102 @ 0b067405 meshes/pose_pack_13p2/eval20_water_pitcher_placed.glb. Packed as is.

## Checks [M]
- vs 13p: only `code_commit_url` (all rows) and `object_mesh_b64` on 1 row (eval 20 slot 1) differ. CD-O changes only
  that pair. Offline validate_submission passes. 0 MESH WARNINGs.
- **Placement is exactly the stated Δ.** The delivered vertices equal 13p's decoded eval-20 pitcher payload × Δ, the
  README matrix (2.89°, 0.47 cm, = place_fit_ep20.json objects/water_pitcher/delta), to 0.0005 mm max. With the inverse Δ
  the error is 28 mm.
- The frame report's flags (ICP 5.01 mm / 2.875°, kit proxy 5.03 mm / 2.89°, centroid 4.98 mm) measure that intended Δ.
- **D1 PASS in both modes** [D] (d1pairs.py; eval seed + 6): 0/7 flips.
  - Raw scan: rot 3.4° at the eval seed, ≤ 4.4°.
  - Budgeted scan: 3.6°, ≤ 4.2°.
  - The anchor error against the public scan is 11–15 mm, as for the unplaced pitcher (scan-registration anchor 14.5 mm,
    12e record).
  - Files: `build_13p2/d1_raw.json`, `build_13p2/d1_budget.json`.

## Expected [E]
- Pose boards on eval 20 up, if the public CV transfers. One episode of 20.
- CD-O is about unchanged: the kit registers the mesh to the scan, so a rigid Δ barely moves it.
