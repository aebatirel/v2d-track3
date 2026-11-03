# Track 3 pack-14p1 candidate, 3 Nov 2026 — pose pack 14p + round-3 wooden_piece_2 on eval 25 (public pose CV)

**STATUS: HELD — CV leakage (generation source = CV episode). Not uploaded, no sign-off sought.** Coordinator decision
(keen-heisenberg, 07:14 UTC 3 Nov):
- the mesh (#43) was generated from public ep24, one of its two CV episodes, so its held-out gain is not independent (the
  same reason pitcher #29 was rejected);
- its scan anchor is 2–3 mm worse than library_v3's;
- it may have a doubled shell (2.2× the scan's surface area);
- the expected gain is only about +0.0003.

The build is kept as a record.

**Disclosure.**
- One pose-board mesh swap, adopted by tracking-perception's pre-registered public pose CV round 3: 10-seed nested
  leave-one-episode-out vs 14p, docs/analysis/ptrk-20261102/PREREG_round3_audit.md, results/cv_round3.json @ f391360.
  - Held-out +0.0053 (ep23 +0.0046, ep24 +0.0060).
  - **ep24 is also the mesh's generation source**, so only ep23 is independent.
  - Expected effect ≈ +0.0003 board AUC [E].
- The mesh is from the G3 pool: SAM 3D on public ep24 frames, GT-informed best-of-N by public-scan CD-O, placed GT-free.
  Manifest: C4-audit/posecv_manifest_g3.json @ 847ef82a, index 43.
- All disclosures of 14p and 13p2 carry over:
  - 14p's eval-14 retrain (perfect-following, pfR2);
  - pose-CV meshes;
  - the eval-20 placement;
  - Tier B / B+ GT-informed meshes;
  - the eval-15 clause-c waiver.

## Record
- File: `build_14p1/track3_submission.parquet`, 9,120 rows, 1,342,825 bytes.
  sha256 `9dd5cbd6bf02296d1bb8f367a6eeca1e6601ecefb732df1451862870b6bccac4`.
- CD-O file: `build_14p1/track3_submission.cd-o.parquet`, 294,912 rows, sha256 `ebc9c481daa87d86…`.
- Code: https://github.com/aebatirel/v2d-track3/commit/04b14127c6fed44b85310dddd79820b298fb51e8 (on every row).
- Base: pack 14p (perfect-following, `results/submissions/20261102-track3s-candidate/build_14p` on
  claude/perfect-following-20261101, b6c6100d…) = 13p2 + the eval-14 rollout.
  - **14p reproduced byte for byte** with the kit packer from 13p2's packer inputs plus the eval-14 rollout. The rollout
    is from the store, runs/20261102-pfR2-c1a5471/results/pf_arms/conf_ep14_p0m/r1/ep14; its parquet sha256 2c3ac7bd… and
    json 68114da3… match 14p's manifest. no_oracle accepts it.
- Built by tools/pack_swap_meshes.py with the guard on, `--only-episodes "wooden_piece_2:25"`.
- Mesh: `meshes/posepack_r3_14p/wooden_piece_2.glb`, md5 e88567d2…, replacing library_v3 825a7fe3. Transform none.

## Checks [M]
- vs 14p: only `code_commit_url` (all rows) and `object_mesh_b64` on 1 row (eval 25 slot 1) differ. CD-O changes only
  that pair. Offline validate_submission passes. 0 MESH WARNINGs.
- **D1 PASS in both modes** [D]: 0/7 flips.
  - Raw scan: eval seed 0.5°, ≤ 1.6°; anchor 4.9–7.5 mm.
  - Budgeted scan: 0.7°, ≤ 2.2°; anchor 4.3–6.8 mm.
  - For comparison, library_v3: anchor 2.3–4.9 mm (flipcheck d1gate), so the new board's scan-anchor proxy is about
    2–3 mm worse.
- Frame vs library_v3: ICP 0.55 mm / 0.17°, centroid 1.99 mm (frame consistent).
  - Full x extent 26.6 → 45.7 mm (FLAG, ratio 1.72).
  - Area-weighted 1–99% x extent: 26.1 mm, vs scan 20.6 and library_v3 18.3. So the full-extent flag comes from about 1%
    of the area.
  - **Total surface area 134,935 mm², vs 62,802 for the public scan and 61,665 for library_v3: more than 2×.** This
    suggests a doubled or inner surface. The 50-seed scan audit [D] (CD-O 0.1623, ADD 5.53 mm) and the public CV already
    include its effect.
