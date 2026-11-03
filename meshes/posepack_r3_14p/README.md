# meshes/posepack_r3_14p — round-3 pose-pack mesh on 14p (3 Nov 2026)

`wooden_piece_2.glb` is a byte copy of the HF store file aebatirel/v2d-store
runs/mesh-20261103-g3-2417282/stage2/wooden_piece_2_g3_sam3d_ep24_k6_s2025_lib.glb, md5 e88567d2d9f06dc79749a03be89cd080 (G3
manifest index 43: docs/research/mesh-2026-10-26/cdo-sprint/C4-audit/posecv_manifest_g3.json @ 847ef82a, branch
claude/bold-albattani-6qmxsv). It goes on eval 25, slot 1. Transform none: library_v3 body frame, placed GT-free with
place.py.
- SAM 3D generation from public ep24 frames. It comes from the G3 pool, which is GT-informed best-of-N by public-scan
  CD-O. 50-seed scan audit [D]: CD-O 0.1623, W30 0, anchor 5.5 mm, ADD 5.53 mm.
- **Adopted for the pose boards** by tracking-perception's public 10-seed nested leave-one-episode-out CV vs 14p
  (docs/analysis/ptrk-20261102/PREREG_round3_audit.md; results/cv_round3.json @ f391360): held-out +0.0053 (ep23 +0.0046,
  ep24 +0.0060). **Note: ep24 is also its generation source**, so that held-out episode is not independent of the mesh.
