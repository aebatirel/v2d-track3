# Pre-registration: (A) mesh placement from depth, (B) tracking with the submitted meshes (2 Nov 2026, night)

Owner's word via keen-heisenberg (20:10 UTC): "do as much work as you can for tonight". Budget ≤ $8 GPU for A + B,
stop if credit < $10. Written and pushed before any variant output exists.

## Common
- **Meshes "M13":** the exact submitted pack-13f payloads.
  - Source: the `object_mesh_b64` vertices / faces of
    `results/submissions/20261102-track3r-candidate/build_13f/track3_submission.parquet` (branch
    claude/focused-pascal-2nz9s1).
  - One mesh per object; every object has a single md5 across its eval episodes. 4096 faces each.
  - Copied to `meshes/m13f_payload/` (glb).
- **Caveat [I]:** several M13 meshes were selected by CD-O against the public scans (Tier B / B+: ground truth entered
  the selection). Public scores with M13 are therefore optimistic in absolute terms. Each test compares two arms with
  the same submitted meshes, so the comparison holds, but its size may not transfer to eval.
- **Tracks:** today's control C (eval defaults, library_v3 templates, TRACK_GUARD; ptrkA / ptrkB C, ep23 = ptrkD Cr,
  no identity fix), unless an arm says otherwise.
- **Scoring:** `pipeline/score_registered.py` with the arm's submitted meshes, public scans, kit metric code, 20 public
  episodes.
- **Gate (both tests, fixed now):**
  1. mean ΔAUC ≥ +0.005;
  2. no episode below −0.01;
  3. mean ΔMPPE ≤ 0 and mean ΔRPE ≤ 0;
  4. frames with position error > 3 cm not more.

## (A) Mesh placement from depth [H] (CPU, $0; `scripts/place_fit.py`)
The tracker's library_v3 pose carries a shape-driven bias. The real surface, as seen by our depth in the tracker's body
frame, sits at a constant offset from where M13 is placed now.
- Per episode and object:
  - rest segments of our track (as in Stage 1: < 0.5 cm and < 2° per frame, ≥ 10 frames, 2 edge frames dropped);
  - every 2nd frame;
  - points: SAM2 video-mask pixels (ptrkD MRr vos_masks) ∩ the dilated projected silhouette of the tracked
    library_v3 pose, at most 1500 per frame, stereo depth back-projected;
  - each frame's points moved into the tracker's BODY frame with that frame's tracked pose, then pooled.
- One constant transform Δ is fitted by trimmed ICP: the M13 mesh to the pooled body-frame cloud, 70 % kept,
  Kabsch, ≤ 40 iterations, starting at identity.
- **Guards:** ≥ 300 points, |Δ| ≤ 3 cm and ≤ 10°, trimmed RMS must drop; otherwise Δ = identity.
- **Submitted mesh for that episode:** Δ · M13 (`--meshes DIR/episode_XXXXXX/<obj>.glb`). Tracks unchanged.
- **Arms:** A0 = M13 as packed (control), A1 = re-placed. Δ and the meshes' sha256 are pushed before scoring.
- **Eval cost if it passes [E]:** the same CPU fit on the eval references needs the eval depth caches (store
  cache/depth/eval, already present for the evals that were re-perceived) and SAM2 video masks (GPU, ≈ $2–3 for 20
  episodes, or silhouettes only). No retrain: only mesh payloads change.

## (B) Track with the submitted meshes (GPU; `ops/jobs/perc_vos.sh`, one PRO 6000 box, same code, cached depth)
- **Arms on the same box:**
  - Ct: library_v3 templates (control, re-run on this box);
  - T13: M13 as FoundationPose templates (MESH_DIR=meshes/m13f_payload).
- Both scored with M13 submitted.
- Everything else is the eval defaults (TRACK_GUARD, detection rules: their templates follow MESH_DIR, as in
  production).
- Difference from the pitcher test (−0.249): that tracked with v3p but scored with v3; here tracking and scoring use
  the same mesh.
- **Eval cost if it passes [E]:** eval perception with M13 templates (≈ $3–4), references rebuilt, and retrains of
  every changed episode (≈ $3–6 each); plan sent to the coordinator first.
- **Cost of this test:** ≈ 40 runs × ≈ 1–1.5 min plus setup ≈ 1.5–2 h on one PRO 6000 ≈ $2–3 [E].
  - Depth is prefetched per file with hf_hub_download in parallel, avoiding the 12–15-minute `hf download --include`
    listing.
