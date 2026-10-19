# 22 — FlashCHORD reference contract and a MANO-free hand path (2026-10-13)

Source: read-only code study (background agent) of nvidia-isaac/video_to_data @ 8c778f905cb3 (evaluator pin).
Nothing executed. Abbreviations: MS = flash_chord/src/flash_chord/data/mano_sharpa.py; E2S =
robotic_grounding/scripts/retarget/ego_recon_to_sharpa.py; HK = retarget/hand_kinematics.py; P = retarget/params.py;
XML = assets/xmls/sharpawave/{side}_sharpawave.xml; AX = manotorch axislayer.py (lixiny/manotorch@2f6a701).

## Parquet contract (FlashCHORD loader)
- One row; a directory must hold exactly one .parquet; hive partition values must equal the column values
  (parquet.py:34-62). All columns in data/loader.py:14-41 must be present; schema_version null/empty (:53-66).
- REQUIRED: fps (true source rate, MS:175); object_body_position (T,B,3) and object_body_wxyz (T,B,4, wxyz, unit,
  finite; MS:177-190); object_name, object_body_names (B unique), object_mesh_paths (B), object_mesh_radius (>0)
  (MS:193-212); object_urdf_paths (B) unless source_dataset in {arctic, synthbox} (assets/registry.py:179-200);
  object_articulation empty or single all-zero column (MS:213-223).
- Per side s in {left,right}: robot_{s}_wrist_position (T,3), robot_{s}_wrist_wxyz (T,4 unit), robot_{s}_finger_joints
  (T,N) + {s}_robot_finger_joint_names (matched to sim by name; MS:254-274, embodiments/base.py:588-598);
  mano_{s}_object_contact_positions/_normals (T,K,3) and _part_ids (T,K), ints in [0,B], unit normals where id>0,
  K>=1 (empty == missing; MS:154-158,279-295); robot_{s}_frames (T,F,7 pos+wxyz) + {s}_robot_frame_names (validated
  MS:301-310, unused elsewhere).
- NOT read by FlashCHORD: mano_{s}_joints, _joints_wxyz, betas, poses.
- fps: resampled to control rate x motion_speed (recipe 0.5; our timing fix uses 1.0); linear interp for positions
  and joints, SLERP for quaternions, nearest frame for contacts (MS:166-170,235-300). Units m/rad, world z-up (object
  controller gravity compensation along +z, runtime/object_control.py:36).
- Contacts: upstream = points on object surface, normals INTO the object, part id = 1 + body index, 16 slots (one per
  MANO link) (contact_utils.py:28-29, dataset_loader_base.py:156,193). Rewards: contact_wrench_support +10,
  missed_contact -1, unintended_contact -10 (curriculum/tracking_250m_mixed_reset.yaml:11-22; objectives/wrench.py:176-235).
  ALL-ZERO CONTACTS LOAD BUT ACTIVELY PENALISE GRASPING (unintended_contact fires on any touch, objectives/contact.py:206-242).

## Retargeter (E2S) — reusable without MANO
- pink FrameTask/solve_ik (daqp, dt 1/200, 100 it) on pinocchio BuildFromMJCF free-flyer, root {s}_hand_C_MC
  (HK:6-14,79-92,373-402; retarget_utils.py:26-52; HK:459-464; XML:51).
- Joint order P:7-29 = wrist, thumb1-4, index1-4, middle1-4, ring1-4, pinky1-4 == MediaPipe 0-20 (no reorder).
- Targets (pos cost, ori cost) P:191-219: hand_C_MC<-wrist 0 (0.2,0.2); thumb_MCP_VL_site<-2 (0.1,0); thumb_tip_site<-4
  (1.0,0.05); {index,middle,ring,pinky}_MP_site<-MCP 5/9/13/17 (0.1,0); index/middle/ring tips<-8/12/16 (1.0,0.1);
  pinky tip<-20 (0.5,0.1). Only joints 0,2,4,5,8,9,12,13,16,17,20 matter; orientation only for wrist + tips.
- Scale 1.2x about the wrist (wrist itself unscaled) (HK:233-234; E2S:93).
- Orientation target = joints_wxyz; wrist post-multiplied by inv((0.5,-0.5,0.5,0.5)) == {s}_hand_wrist_site quaternion
  (HK:237-243,453-457; XML:55). Wrist-site axes: x proximal, y dorsal, z radial (right) / ulnar (left) (XML:90).
  Consistent with manotorch anatomical frames [back, up, left] (read_mano.py:159-172; AX:39-55,100-104). Tips reuse the
  distal joint frame (P:50-72).
- Frame 0: free-flyer set from joint-0 quaternion WITHOUT the offset; then warm start (E2S:504-535).
- Outputs: wrist pos q[:3], wxyz q[3:7][[3,0,1,2]], fingers q[7:] (22), frames (67), frame_task_names (11 keys)
  (E2S:553-606; HK:67-77,404-415).
- Reads only mano_{s}_joints/_joints_wxyz from the loaded parquet (E2S:327-331,485-502); no MANO FK, no Isaac Lab.
  Deps: numpy, torch, scipy, trimesh, viser, tqdm, pyarrow, pinocchio(+MJCF, hppfcl), pink, daqp, loop_rate_limiters.
  Frame count from len(mano_right_trans) (E2S:331); object_root_position passed in (:355-371). Fixed list sizes:
  contacts 16, fingers 22, frames 67 (data_logger.py:75-103,172-211). Contacts pass through unchanged (E2S:573).

## How much the hand reference matters
Dense reward weights: object keypoints 20 vs hand keypoints 0.25 and hand joints 0.25 (binding.py:88-96,352-365). But
the policy outputs residuals on the reference wrist/fingers (hand_pose.py:275-307; scales 0.05 m / 0.15 rad);
reference-minus-current wrist/fingers are observations (observation.py:558-598); termination if palm > 0.15 m from the
reference wrist (termination/tracking.yaml:2-5; termination.py:615); resets copy reference robot pose at random frames,
fingers x0.7 (reset.py:97-122); contacts give +10/-10 terms.

## Absent hand
No mask/NaN support; both sides hard-coded and finite (MS:29,257-271); sim always builds two hands. One-handed episode:
park the other hand on a finite trajectory away from objects, part ids 0; the 0.15 m wrist termination applies to it.

## Recipe (hypothesis, unverified)
1. MediaPipe 21 keypoints -> metric 3-D in the object world (z-up, m). Handedness: MediaPipe assumes mirrored input
   -> swap labels for egocentric non-mirrored frames (verify).
2. joints_wxyz: wrist x = norm(p0 - p9); zr = p5 - p17 (right) / p17 - p5 (left); z = zr orthogonalised vs x;
   y = z x x. Tips 4,8,12,16,20: x = norm(p[tip-1] - p[tip]); z = wrist z orthogonalised; y = z x x. Others = wrist quat.
3. Write a loaded ManoSharpaData (mano_{s}_trans = wrist positions; other MANO fields zero; 16 zero contact slots;
   object fields + object_urdf_paths); run ego_recon_to_sharpa.py --input_dir --output_dir --save [--smooth_reference].
4. Recompute contacts after IK from robot sites in robot_{s}_frames (contact_labels.py:105-193: 0.018 m threshold,
   min run 2 frames, object-motion gate per ego_recon_to_dexmate_sharpa.py:140-141); part id = nearest body + 1; normals
   into object; pad to 16; overwrite mano_{s}_object_contact_*.
5. Check with flash_chord.data.loader.load_reference and robot_*_frame_task_errors (frame 0 especially).
Unverified: MANO canonical axes (inferred), thumb-tip frame skew, tip-site y sign, frame-0 IK convergence,
URDF root == hand_C_MC, package versions, robot-probe contacts vs organisers' contacts. The bundled tissue_box_simple
processed parquet (on Colab) can confirm conventions.
