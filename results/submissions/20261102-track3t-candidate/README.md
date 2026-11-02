# Track 3 pack-13f1p candidate ("pose pack"), 2 Nov 2026 — 13f1 + TSDF white pot + library_c0 rack (public pose CV)

**STATUS: PENDING frame sign-off on the white pot (mesh lane). Not ready, not uploaded.** keen-heisenberg's session uploads,
on the owner's word there. This is a pose-board variant. CD-O is expected to be slightly worse (the Tier B rack is
reverted); the best-per-board rule absorbs that.

**Disclosure: how these meshes were chosen.**
- Both swaps were adopted by tracking-perception's pre-registered **public pose cross-validation**: a 10-seed,
  leave-one-episode-out AUC on public episodes. It reads public mocap, which is development. No eval result is read.
  docs/analysis/ptrk-20261102/PREREG_posemesh.md + addendum 1 (pushed before the candidate scores);
  results/cv_posemesh.json and results/d1_check.json; branch claude/perception-tracking-20261102 @ 029145e.
- **White pot (TSDF pot fit, ep43):** a primitive pot fit to our own public-ep43 points (GT-free), in the library_v3 body
  frame.
  - Its candidacy was GT-informed: it was the best existing pot by public scan-registration ADD (bold-albattani).
  - CV: held-out mean ΔAUC +0.0206, min +0.0008 over 9 pot episodes.
- **Dish rack:** reverts to our earlier GT-free library_c0 rack (packs 9a+ to 13b; payload byte-identical to 12c's).
  - CV: held-out mean +0.0234, min 0.0 over 5 episodes.
- Every disclosure of 13f1 carries over: the Tier B / B+ GT-informed selection on the remaining Tier B meshes (pitcher,
  sweeper, wooden piece 1, blue cup, dust pan), the eval-15 clause-c waiver, the eval-25 D1 revert.

## Record
- File: `build_13f1p/track3_submission.parquet`, 9,120 rows, 1,341,323 bytes.
  sha256 `3134dfc67c18da42fd3edac8654d55ba4bd0136067ad2696287a7313a640c2ed`.
- CD-O file: `build_13f1p/track3_submission.cd-o.parquet`, 294,912 rows, sha256 `dc2a1197e2f34ebe…`.
- Code: https://github.com/aebatirel/v2d-track3/commit/116dfe701a6e230f3d7cfb6c2eeb10157af709c7 (on every row).
- Base: pack 13f1 (`results/submissions/20261102-track3s-candidate/build_13f1`, c25abef2…), reproduced byte for byte from
  its packer inputs first. Built by tools/pack_swap_meshes.py with the guard on:
  `--only-episodes "white_pot:1,3,5,6,8,28;plastic_dish_rack:14,15,16,28,30"`.
- Meshes: `meshes/posepack_13f1p/`:
  - white_pot.glb, md5 3591440e2dbf2029be908d46b29bfc96, from 30186bb;
  - plastic_dish_rack.glb, md5 bbca8ec0c26e6e37baaa145cef4e48e5 (library_c0).
  - Transform none.

## Checks [M]
- vs 13f1: only `code_commit_url` (all rows) and `object_mesh_b64` on 11 payload rows differ:
  - white_pot on 1/o0, 3/o0, 5/o0, 6/o0, 8/o1, 28/o1;
  - plastic_dish_rack on 14/o1, 15/o0, 16/o0, 28/o0, 30/o1.
  The five rack payloads equal 12c's byte for byte.
- CD-O changes exactly those 11 pairs. Offline validate_submission passes. 0 MESH WARNINGs.
- **D1 no-flip gate [D]** (docs/research/work/flipcheck-20261102/scripts/d1pairs.py): the kit's _register_object_body of
  each decoded payload against the public scan, at the eval seed and 6 more seeds, with the raw scan and with the budgeted
  scan.
  - **PASS in both modes: 0/7 flips on all 11 pairs.**
  - Pot: rot ≤ 2.6°, anchor 1.5–3.2 mm. Rack: rot ≤ 3.5°, anchor 1.3–6.3 mm.
  - Files: `build_13f1p/d1_raw.json`, `build_13f1p/d1_budget.json`.
- Frame report vs the meshes they replace (`summary.txt`):
  - white_pot vs the T3 pot: centroid 9.81 mm, ICP 5.89 mm / 2.88°, kit proxy 7.67 mm (FLAGS; shape differences between two
    different pot fits).
  - rack vs the Tier B rack: the same numbers as 12e's report, in reverse.

## Expected [E]
- Pose boards: up by the CV's held-out gains on the pot and rack pairs, if the public CV transfers to eval.
- CD-O: about +0.005 worse. The rack pairs go back from about 0.42 to about 0.45 cm [D], and the pot is about the same
  (0.3097 vs 0.3107).
