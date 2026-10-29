I wrote the v5 spec, to be committed as `docs/mesh-v5-spec.md`. The two decisions that matter most rest on numbers from scan-contaminated inputs, so they are provisional. The fallback mesher, which serves 17 of the 26 known-object pairs, has not been scored on compliant inputs yet. The repo is unmodified, the run was CPU only ($0), no depth was fetched, and 14 GB of disk is free.

**Two small checks I ran for this spec** (commands in `COMMANDS.txt`):
- **E0, below-table votes [D]:** obsnew had built but never scored the meshes without below-table votes ("nobc"). Gated observation-first meshes, with library_v2 standing in for the fallback, scored against v2:
  - **Below-table votes kept:** −0.0159 cm CD-O and −1.63 mm registration offset, but board 1 gains a flip on 1 seed in 6 and board 2 on 2 in 6, so it is rejected.
  - **Votes removed, counter kept:** −0.0154 cm and −1.25 mm with no new flips. It passes the rule.
  - **Cost:** the dust pan gets worse (0.342 vs 0.252 cm). A "rest clip" (carve below the table only during observed rests, against a robust plane) is pre-registered as E1 to recover it.
- **E0c, protecting per-episode meshes [M vs D]:** I compared 19 single-episode meshes with the library mesh (a ground-truth-free chamfer). That chamfer ranks them like their scan CD-O (Spearman 0.86).
  - The unexplained-evidence gate alone lets through two bad blue-cup meshes: ep11 at 1.173 cm against v2's 0.523, and ep21 at 0.749.
  - Adding "chamfer to the seed ≤ 0.5 cm" accepts 4 meshes, all better than v2.
  - The 0.5 threshold was chosen after seeing these numbers and the reference was the contaminated v2. It stays a hypothesis until the twin rehearsal (E8).

**Global decisions:**
- **Acceptance rule:** shape changes must not worsen eval-weighted CD-O or registration and must add no flip on any of ≥ 6 seeds. Physics-only changes (support flattening) may be neutral within seed noise (≤ +0.001 cm and ≤ +0.1 mm). Scans never pick anything per object. The dust pan's private edge-filter setting is removed; E3 picks one global value.
- **Mesher:** observation-first `4c12_adj_g2_f0_cont@lc25`, 2 mm voxels, below-table votes removed.
  - Ground-truth-free gates choose per object: seen-free ≤ 0.5 cm³, unexplained evidence ≤ 0.05, topology, a flip check against our own mesh, and the seed-consistency check per eval episode.
  - Fallback is today's `recon_mesh` at 4 mm with only our own meshes as other objects.
- **Not ported:** silhouette (grayscale camera, inert), below-table hits that only block closing, episode weighting, the local-fallback tier, finger masks, held-only fusion.
- **Decimation:** open3d quadric to 4096 faces, then a topology check, then pymeshlab in stages. Collision geometry is built from the full-resolution mesh.
- **Support rule:** flatten the underside only at observed unassisted rests where the object cannot stand, with acceptance checks.
- **Interaction rules:** none change the submitted mesh, and nothing is carved from the collision copy in v5.0. Only an interaction-weighted split inside our convex decomposition runs, plus an overlap report. The safe carve set is specified but parked.
- **Collision:** our own convex pieces, one `<collision>` element per piece.
- **Spoon:** the template fitted to the episode's own evidence if its gates pass, else the unfitted template; the fused spoon mesh is evidence only.
- **Provenance:** a manifest per artifact and a deny-list (by path and sha256) covering library v1–v4, scan-templated tracks and every prototype output. The v5 seeds come from tracks that were themselves seeded by library_v2 (on the deny-list), so every v5 and eval mesh carries that one-step taint. Accepting that is decision O1, tied to question 3 of the organiser email.
- **Per-episode re-fusion:** a new stage 2m in `pipeline_ep.sh` between hands and `mkref`. The spec gives the exact steps, a port list file by file, and the frozen parameters.

**GPU plan (all estimates, at $1.4–1.9/h):**

| Batch | What | When | Cost |
|---|---|---|---|
| G1 | Re-track 16 public episodes with own meshes | Now; can run before the ports | ≈ $2–3 |
| G2 | The GPU test, two boxes (details below) | After CPU experiments E1–E10 and the freeze | ≈ $13–18 |
| G3 | The 20 eval episodes | Separate go-ahead | ≈ $63–86 per seed |

- **Re-tracking first?** Yes, but not for the test itself. The four test episodes already have own-mesh tracks; the v5 library needs tracks for the lid, beige cup and pitcher, which have none.
- **G2 content:** ep18, ep12 and ep27 at 250M steps, seed 42, 6 evaluations each, against the existing baselines (no new baseline GPU needed); an ep24 smoke run for build memory and throughput with the most pieces; and v5-seeded perception on all 20 public episodes.
- **G2 is a regression guard, not a gain test.** Two seeds differ by about 0.04, so one seed only reads large effects. The pass/fail rules are written in the spec.
- **Credit:** Vast credit was $6.28 at 17:06 UTC with the spoon box still running, so even G1 needs a top-up.

**What is measured vs hoped:**
- **Measured, but on contaminated inputs [D]:** the mesh-metric gains above, the decimation results, the hull-overlap reduction from our pieces, and the ep18 jump from 0.345 to 0.715 with a sweeper that could stand (one seed, changed together with stable-pose settling).
- **Not measured yet:** the compliant fallback mesher, training throughput with pieces, how well v5 meshes work as tracking seeds, any AUC gain, and the spoon fit on a real spoon.

**Owner decisions needed:** O1 (the bootstrap provenance above); O2 (submit the library mesh when a per-episode mesh fails every gate); O3 (use the seed only as a QA reference for the gates); O4 (collision pieces differ from the submitted mesh); O5 (spoon questions); O6 (the GPU spend); O7 (the spoon template's frame convention was fitted to the public scans' frames; it carries no shape and does not affect the score).

Files are in `/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/v5/spec/`:
- mesh-v5-spec.md
- COMMANDS.txt
- results_e0.jsonl
- e0_global.json
- e0c_summary.json