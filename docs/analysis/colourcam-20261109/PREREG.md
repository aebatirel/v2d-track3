# Pre-registration: colour-camera tracking, public episodes (9 Nov 2026, post-freeze)

Written and pushed before any run. Owner's question (9 Nov): "can you test color tracking on the public episodes to see
if it made a difference". Labels: [M] measured, [D] public vs mocap, [E] estimate, [H] hypothesis, [I] inference.

## Hypothesis [H]
Our tracker (FoundationPose) ran on grey camera c with grey-painted templates. FoundationPose compares rendered
appearance with the image; in grey, look-alike or pale objects lose their main cue (beige vs blue cup, white pot and
lid on a pale table). Team Purple (AUC 0.933) ran FoundationPose on colour camera a (`T_A_from_scan`, "A image =
A(f+1)", their `mesh_common.py`; inference). Evidence on our side: Grounding DINO found 10/10 objects in colour and 7/10
in grey; OWLv2 swapped the twin cups in grey (Journey Report §5, §11). Against: camera a has a one-frame offset
(a[k+1] pairs with b[k] in 36 of 39 clips), a rolling shutter and motion blur on fast moves (note 12, one frame),
and its depth has to be moved in from the stereo pair (note 03, H-fit-2, the reason we chose grey on 7 Oct).
**Running FoundationPose on colour camera a, with templates painted in colour, makes the public tracks closer to mocap
than the same pipeline on grey camera c with templates painted in grey.**

## Arms (`ops/jobs/perc_colour.sh`; one box, same code, same cached stereo depth, 20 public episodes)
All arms: today's eval defaults (library_v3 geometry, detection on camera c with library_v3 grey templates, TRACK_GUARD on,
REG 5 / TRACK 2, KF_MIN 120, camera track on camera c).
- **C**: control, exactly today's tracker (TRACK_CAM=c, library_v3 grey templates).
- **CP**: camera c; tracker templates repainted in grey for this episode from camera c along C's own track
  (`mesh_color.py --cam c`, stride 4, stereo-depth visibility test).
- **AP**: camera a (`TRACK_CAM=a`: frames a[k+1] undistorted to a pinhole at half resolution, 1014 x 760; stereo depth
  of frame k splatted into camera a; detection and re-detection masks moved into camera a through the depth);
  tracker templates repainted in colour for this episode from camera a along C's own track (`mesh_color.py --cam a`).
  **The candidate.** AP vs CP isolates the camera, since both use the same per-episode painting along the same track;
  CP vs C measures the repainting alone (report only).
- Everything is GT-free: the painting uses only our video, our depth and our own control track.

CPU checks done before this file (ep12, scratchpad, $0):
- control track drawn into undistorted a[k+1]: the cup and rack outlines sit on the objects at frames 0, 60, 100, 160;
- the torch depth splat equals a numpy splat on 428,954 pixels except 2 (rounding at depth edges);
- colour painting: blue cup RGB median (62, 76, 105), rack (217, 212, 205), 93 % / 82 % of vertices seen.

No setting is tuned after seeing scores. If AP crashes on an episode, that episode counts as CP's track for the gate
and the crash is reported.

## Scoring (after inference; mocap read only here)
`pipeline/score_registered.py` with `--meshes meshes/library_v3` (the geometry all three arms track; identical across
arms), public scans, kit metric code, kit-like single registration seed, `--per_frame` for the > 3 cm diagnostic.
20 public episodes: 0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45.

## Gate for AP vs CP (fixed now; the same four conditions as the 2 Nov tracking tests)
1. mean ΔAUC ≥ +0.005 over the 20 episodes, and ≥ 2 × the tracker's run-to-run noise. Noise reference: two identical
   control runs of this tracker on 2 Nov differed by mean ΔAUC −0.00002 and mean |ΔAUC| 0.0012 per episode
   (docs/analysis/ptrk-20261102 on branch `claude/perception-tracking-20261102`); no repeat control is run here.
2. no episode ΔAUC < −0.02;
3. mean ΔMPPE ≤ 0 and mean ΔRPE ≤ 0 (cm);
4. frames with object position error > 3 cm (summed over objects and episodes) not more than CP's.

Pass on all four: colour tracking is better on public data. Fail on any: reported as failed.
Falsifier of the hypothesis: AP − CP mean ΔAUC ≤ 0.
Reported alongside (no gate): AP vs C, CP vs C, per object type (cups, pot and lid, boards, pitcher, rack, sweeper and
dust pan), and the AP crash / mask-transfer fallback counts.

What a pass would and would not show: that the colour camera tracks better with this pipeline on public episodes. It
would not show the board gain (the competition is over; eval references would need rebuilding and policies
retraining), nor that colour explains Team Purple's lead.

## Cost plan
One RTX PRO 6000 box on demand (offers on 9 Nov: $1.26–1.62/h all-in), cached public depth, 20 episodes × 3 arms
(≈ 1–2 min per arm run, ≈ 25 min setup, store pushes every 5 episodes): ≈ 2.5–3 h, **≈ $4–5 [E], cap $8**.
The box destroys itself at the end; the stall watchdog destroys it after ≈ 30 min without progress.
Vast credit before the run: $38.37 [M].
