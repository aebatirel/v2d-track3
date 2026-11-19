# Pre-registration: MetricTrail (ViPE) camera tracking vs our camera, public episodes, scanned meshes (19 Nov 2026)

Written and pushed before any run or score. Post-freeze research; nothing here changes a submission.
Labels: [M] measured, [D] public vs mocap, [E] estimate, [H] hypothesis, [I] inference.

## Owner's question (19 Nov)
"For the public episodes and using the scanned public meshes, can we see if we have better perception with these
methods": the owner's SLAM recipe from another project, which is NVIDIA ViPE's **MetricTrail** pipeline:
- left grey camera only, every frame, official calibration;
- DPVO with DINOv3 features, bundle adjustment over a sliding window of the last 12 keyframes;
- Depth Anything 3 metric (`DA3METRIC-LARGE`) as the metric depth anchor (MoGe-2 in the owner's earlier version);
- no IMU, no second camera, no loop closure, no smoothing.

## What is already known (do not re-derive)
- Room-map test, 2 Nov (`docs/analysis/roommap-20261102/README.md`, branch `claude/room-map-20261102`): a drift-free
  map camera instead of perc2's camera gave mean ΔAUC +0.0070 on 19 public episodes [D], all of it from ep24
  (+0.148, perc2's camera 37 mm / 1.7° off). The other 18 episodes: −0.0008, ep22 −0.0164. Those runs tracked our
  library_v3 meshes and were scored with `score_registered.py`.
- Tracker run-to-run noise: mean |ΔAUC| 0.0012 per episode (2 Nov).
- [E, before this run] So the most a better camera can add on public data is about +0.007, mostly ep24. MetricTrail
  uses one camera and learned metric depth, so a scale error (a few %) is possible; we expect it to land between
  "≈ the map" and "worse than perc2". This test measures it.

## Design
One box, one code commit. Object tracks are produced once and **shared by every camera arm**, so camera arms differ
only in `world_T_cam`.

**Tracks (arm S):** `pipeline/perc2.py` on the 20 public episodes with the **public scans** as templates
(`MESH_DIR` unset), today's eval defaults otherwise (TRACK_GUARD on, detection rules on, KF_MIN 120, grey camera c,
cached FoundationStereo depth from the store). Output: `cam_T_<obj>` per frame (rectified-left camera) and perc2's
own camera `world_T_cam` (world = rectified-left camera at frame 0).

**Camera arms** (world poses = `world_T_cam_arm[t] @ cam_T_obj[t]`):
- **C** (control): perc2's camera (keyframe SIFT + FoundationStereo-depth PnP).
- **VD** (the owner's recipe; **the candidate**): MetricTrail mono on rectified-left camera c, every frame, known K
  (`pipeline.optional.intrinsics`), keyframe depth `dav3` (ViPE loads `depth-anything/DA3METRIC-LARGE` and scales by
  focal), DPVO `OPTIMIZATION_WINDOW=12`, no loop closure, no masking, no depth fusion.
- Report-only arms (no gate):
  - **VD2**: VD run again (MetricTrail's own run-to-run noise).
  - **VM**: VD with MetricTrail's default depth prior MoGe-2 (`moge2-l`), as in the owner's earlier version.
  - **VDH**: VD with ViPE's dynamic-object masking on, phrases `person, hand` (no DPVO patches on hands/people).
  - **VS**: MetricTrail's stereo runner on the rectified c/b pair, baseline 0.0755 m (uses our second camera).
  - **M**: the 2 Nov GT-free room-map camera (leave-out fold maps, HF `runs/20261102-roommap-6438495/world_T_cam/public/`),
    as the drift-free reference.
- Report-only depth arm **SD**: perc2 re-run with VD's per-frame DA3 metric depth in place of FoundationStereo depth
  (upsampled to perc2's grid, same 0.15–2.0 m clip), so both the object tracker and perc2's camera run on monocular
  depth. Compared with S. Answers whether mono metric depth can replace our stereo depth.

Input to MetricTrail: perc2's exact rectification of camera c (and b for VS), resized to 512 × 320 (scale 0.32),
written as PNG frame directories; `input_raster.policy=unchanged`; K = perc2's rectified K × 0.32. ViPE writes OpenCV
camera-to-world poses; they are re-based so frame 0 is the identity (perc2's world convention). The conversion logs
the rotation agreement with perc2's camera as a GT-free sanity check of axis convention; no other use of it.
ViPE pinned at commit `ead2e008bc055310121736a49ff306bba50d10dc` (2026-11-06); MetricTrail weights
`nvidia/MetricTrail` `dino_dpvo.pth` (sha256 d0aa57e1…); DINOv3 ViT-S/16 `dinov3_vits16_pretrain_lvd1689m-08c60483.pth`
(MetricTrail verifies its full sha256 at load).

Everything above is GT-free. Mocap is read only by `tools/cam_arms_score.py`, after every inference output exists.

## Scoring
Official kit Track 3 metric functions (`_warp_to_reference_start`, `_object_add`, `_add_auc`, SP/MP-SR, MPPE, RPE), 500
surface points per public scan (seed 0), exactly as perc2's own scoring block. Per episode and arm: AUC, SP-SR, MP-SR,
MPPE, RPE, per-object AUC, frames with object position error > 3 cm. GT-free diagnostics per arm: object-position gap
to C (p95, max), camera gap to M (translation p95, rotation p95), path-length ratio to M (scale check).

## Gate for VD vs C (fixed now; the same four conditions as the 2 Nov and 9 Nov tests)
1. mean ΔAUC ≥ +0.005 over the 20 episodes, and ≥ 2 × MetricTrail's own noise (mean |ΔAUC| VD2 vs VD);
2. no episode ΔAUC < −0.02;
3. mean ΔMPPE ≤ 0 (cm). (RPE is invariant to a common camera change; reported only.)
4. frames with object position error > 3 cm (summed over objects and episodes) not more than C's.

Pass on all four: the owner's recipe gives better perception on public data than our camera. Fail on any: reported
as failed. Falsifier of "better camera": VD − C mean ΔAUC ≤ 0.
If VD crashes on an episode, that episode counts as C for the gate, and the crash is reported.
No setting is changed after seeing scores. If an arm needs a code fix to run at all (crash, wrong file format), the
fix is made blind to scores, recorded in the work log, and applied to every episode of that arm.

What a pass would and would not show: a better camera for our pipeline on public clips with perfect meshes. Not a
board gain (the competition is over), and not that it beats the room map.

## Cost plan
One **RTX 5090** (32 GB, same Blackwell sm_120 as the PRO 6000 that our environment snapshot was compiled for) on Vast,
on-demand ≈ $0.55–0.75/h (19 Nov market); perc2 and MetricTrail run one after the other on a card under 60 GB.
(Changed from one RTX PRO 6000 at the owner's question "do you need that strong of a machine?", before any run.)
Setup ≈ 15 min; perc2 S ≈ 35–45 min (ViPE install ≈ 30–45 min in parallel, CPU); 5 MetricTrail arms × 20 clips ≈
60–90 min [E]; SD ≈ 35–45 min; scoring ≈ 5 min. ≈ 3–4 h ≈ **$2–3, cap $5**. The box destroys itself when the job ends;
the stall watchdog stops it after 30 min without progress.
