# Track 3, team egoCUBE (CMU), 5th overall: talk notes, 2026-11-13

Source: 9 phone photos of the team's CoRL V2D tutorial talk, shared by the owner in chat on 13 Nov. The photos are not
in git (faces, contact details). Below is their claim as transcribed, not verified. Our numbers are labelled [M]
measured, [E] estimate, [H] hypothesis. Their results slide (final metrics) was not among the photos; the captions say
"we scored 5th place overall".

## Their pipeline (as shown)
Agents ("Claude Opus 5.5 for all of our agentic reasoning") are used at runtime inside the pipeline; starred blocks
below. The agents get numeric feedback (mask IoU, stereo agreement scores) to reason with.

1. **Per video:** stereo video → FoundationStereo depth → masks with SAM 3 + agent ★ → hands with ACE-Ego-Hand (MANO)
   → camera and gravity with DROID-SLAM + GeoCalib.
   - The agent writes SAM 3 prompts, including prompts for distractors such as the watch and the forearm, so they can
     be tracked and excluded.
2. **Object mesh:**
   - (1) agent picks views ★;
   - (2) MV-SAM3D, 5 meshes per video (seeds);
   - (3) fit, pick ★: fit size, keep the nearest to stereo, refit on all videos;
   - (4) primitives ★: the agent writes a Blender program of parts;
   - (5) coverage: frames from all videos;
   - (6) AgentSTAR ★: render vs mask, iterated;
   - (7) final mesh with colours from the video.

   Their examples are recording 25, frame 30 (boards) and recording 20, frames 190 and 0 (pitcher), so the meshes come
   from eval videos.
3. **Motion and RL:** FoundationPose tracking ★ → retargeting (free robot hands; objects settled on the table) →
   collision shapes ★ ("agent rebuilds the pieces that stop objects in simulation") → FlashCHORD RL.

### Mesh ablation (their table, CD-O in cm)

| Configuration | CD-O |
|---|---|
| SAM 3D | 0.596 |
| MV-SAM3D | 0.527 |
| + stereo fit | 0.436 |
| + best mesh across videos | 0.342 |
| + primitive mesh + AgentSTAR | **0.269** |

- They found off-the-shelf primitive fitters (PrimitiveAnything, SuperFrusta/ResFit) fail on the lid, pot and
  pitcher.
- Their parts carry names (pitcher: spout, handle, body, marker_a/b and their mounts), so an agent can add or remove
  parts or "make the slot gaps equal".
- Seeded AgentSTAR runs take about 4 h per object (the AgentSTAR paper states 10 h from scratch).
- The talk does not say which data the CD-O column was measured on, or whether "best mesh across videos" was chosen
  without the scan.

### Simulation fixes by agent ("Don't manually write heuristics")
- Spoon into the rack's holder: the default convex pieces fill the holder slot; the rebuilt collision pieces leave it
  hollow. This is our evals 15 and 16.
- Pot and lid: the pot model was scaled too big, so the lid fell in; a right-sized pot puts the lid on the rim. This
  is our eval 1 (lid inside the pot's hulls, 51 cm³ [M]).

### Symmetry
- FoundationPose added rotations about the symmetry axes of the pot, rack, cup and spoon "even when no such rotations
  existed in the video". This broke tracking, and the implausible trajectories broke simulation.
- They used the visible mocap markers to correct the tracks. "Adding object symmetries is a cheap way to counter"
  off-the-shelf trackers.

### Next steps (theirs)
- Seeded vs non-seeded AgentSTAR.
- Monocular depth, to lift internet-scale video.
- Humanoid deployment and sim-to-real.

## Compared with us and with the winner

| Topic | egoCUBE (5th) | Winner (1st) | Us |
|---|---|---|---|
| Head pose | DROID-SLAM + GeoCalib | SIFT + PnP key-frame map | VO. A room map (note 18) relocalised all eval clips to 1–2 mm, but it was dropped on 22 Oct: it used GT constants, and a GT-free rebuild was estimated at only +0.01 |
| Masks | SAM 3 + agent prompts, incl. distractors | GDINO + SAM 2, every frame | frame-0 SAM2 × DINOv2; the wrist/watch mis-tracks cost us evals 30, 33 and 14 |
| Hands | ACE-Ego-Hand (MANO) | MediaPipe | MediaPipe |
| Meshes | MV-SAM3D → stereo fit → best across videos → agent primitives (0.269) | parametric + nvdiffrast, RecGen pitcher; board CD-O 0.217 | library_v3; board CD-O 0.402 [M]. Kit-of-parts pot/lid/rack beat it (0.342/0.220/0.456) but were never shipped |
| Symmetric objects | marker correction | not stated | marker spin researched (note 17: marker-only lid AUC 0.977), listed as a fix, never integrated |
| Sim validity | agent rebuilds collision pieces per episode | physically consistent reference (rest on support, delayed release) | hand-made carves shipped for evals 25 and 10; eval-1 carve awaiting its official check on 30 Oct; eval-14 carve failed |
| Learner | FlashCHORD | FlashSAC + metric-aligned reward, best of up to 320 rollouts | FlashSAC (two recipes), selection by multi-draw mean |

## What this adds to our hypotheses
- **H-W1 is now backed by two teams.** Both fixed physical validity of the simulated scene automatically:
  - the winner on the reference side;
  - egoCUBE on the collision side.

  Our largest policy losses sit exactly there (evals 1, 14, 15, 16, 30, 10). We fixed some by hand, per episode.
- **H-E1, marker-based symmetry correction.** Already researched by us (note 17) and on our 21 Oct fix list
  (STATUS), never built.
  - Falsifier: on public episodes with the pot, lid, cups or rack, marker-corrected tracks do not raise mean AUC by
    ≥ +0.01 against the current tracks.
- **H-E2, an agent at runtime with numeric feedback** for view selection, distractor prompts and collision repair.
  - It also answers our own concern that hand-applied fixes do not carry to the sponsor's held-out evaluation:
    automated decisions do.
  - Falsifier: an agent given the same per-episode evidence (IoU, stereo scores, sim drop events) does not reproduce
    our hand fixes on the 20 public episodes.
- **H-E3, multi-view SAM 3D + stereo size fit + selection across videos.** Our generator probe ran single-image SAM 3D
  once per object and failed on placement and scale (ADD 18–34 mm). Their stereo fit is the step that fixed scale for
  them (0.527 → 0.436).

## Post-mortem point
Three of the ideas the top teams shipped were already in our notes:
- marker spin for symmetric objects (note 17);
- a drift-free map-based head pose (note 18);
- part-built meshes (the mesh session's kit-of-parts).

A fourth, the rotation-heavy default keypoint reward (22 Oct), we half-fixed: FDR point match, but σ stayed at
10 cm.

Our time went to policy recipes, carves and multi-draw variance studies. The top two teams spent theirs on making the
scene physically valid and the reference accurate.
