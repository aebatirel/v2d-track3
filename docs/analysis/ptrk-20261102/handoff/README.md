# Handoff to the hand-aware session (tracking-perception, 3 Nov 2026)

Everything here is either in git or in the HF store (`aebatirel/v2d-store`, dataset repo). The wrappers were written
for this session's scratchpad layout. Adjust `S=` and the relative paths, and nothing else.

## Scoring

- **`score10seed.sh TAG MESHDIR EP`**: `pipeline/score_registered.py` with `--reg_seeds 10`. It expects the tracks at
  `tracksT/epN/poses_world_vo.npz`, the public t3 data at `t3/` and the kit at `kit/v2d_submission_kit`. The CV gate
  reads `perception_seedmean`.
- **`score_perframe.sh TAG TRACKS_ROOT MESHDIR [EPS]`**: single seed with `--per_frame`, which writes per-frame position
  error, ADD and symmetric ADD per object.
- **`run_srpublic.sh EPS`** runs `../scripts/sr_public.py`: per-object SP/MP-SR against mocap over 10 seeds, with the
  failure type. Pre-registration: `../PREREG_srpublic.md`.
- **14p meshes for public objects:** `meshes/m14p_public/` (decoded 14p payloads, MD5SUMS). Use them as MESHDIR.

## Control tracks (HF store)

| | path | notes |
|---|---|---|
| C | `runs/20261102-ptrkA-7fbc3215/results/ptrk/C/epN/` | eval defaults: library_v3, TRACK_GUARD |
| Cr | `runs/20261102-ptrkD-95cecd7/results/ptrk/Cr/epN/` | replication of C |

- Files in each: `poses.npz` (camera-frame `cam_T_<obj>`, `world_T_cam`), `poses_world_vo.npz` (world, per object
  4×4), `log.txt`, `track_guard.json`, `det_f0.npz`.
- ep23 must have the board identity fix applied: `python pipeline/identity_fix.py VIDEO CALIB DIR library_v3/wooden_piece_1.glb library_v3/wooden_piece_2.glb`.
  The control track set used in CV round 3 and srpublic is C with this fix on ep23.

## Caches (HF store)

- **Stereo depth:** `cache/depth/public/epN/depths_fs0.5.npy`. Fetch per file with `hf_hub_download`; `hf download
  --include` lists the whole repo and takes 12–15 min.
- **SAM2 video masks:**
  - public: `runs/2026110*-ptrk*/results/ptrk/<variant>/epN/vos_masks.npz`, from the TRACK_VOS variants MG / MR / MD;
  - eval: `runs/20261103-ptrkH-ad13d06/results/evos/epN/vos_masks.npz`.
  - Format: bit-packed along the last axis (`np.unpackbits(V[name], axis=-1)[:, :, :400]`), 250×400 per frame.
- **Hands:**
  - eval: `runs/*/refs/perc2mck/epN/hands_refined.npz`;
  - public: the hands_mp outputs from the reference builds (ask perfect-following for the current path).

## Where public tracks fail (measured; `../srpublic/`, `../boardface/`)

Per-frame errors (seed 0) are in `../srpublic/ep*_pf.npz`: `pos` in m, `ori` in rad, `names`.

- **ep23 board 2:** lost in the hand area at f146–244 (position > 3 cm), then merged onto board 1 in the final cross
  at f240–324 (orientation ~180°). This is a held phase followed by assembly. Overlay:
  `../boardface/overlays/public23_track_vs_mocap.jpg`.
- **ep21 / ep22 pitcher:** a steady ~3 cm body-frame position bias from f50 onward (held and pouring), orientation
  fine.
- **ep24 boards:** 2.0–2.4 cm, the thinnest MP margin, and rising after f76 while handled.
- **ep11–13 blue cup:** passes MP on the episode mean, but position error grows in the later quarters (handled
  phases). Quarter means / max:
  - ep11: 0.2 / 1.2 / 3.8 / 2.1 cm, max 5.6 cm;
  - ep13: 0.5 / 0.8 / 1.9 / 1.4 cm, max 4.2 cm;
  - ep12: max 2.3 cm.
  The beige cup and rack stay under 2.3 cm.
- **ep27:** passes; rack 0.3 cm; white pot ≤ 0.9 cm by quarter, max 3.3 cm. The coordinator listed ep27 as a failure
  case from other lanes; this lane's control track does not show one on SR.

## Rules this lane followed

- Pre-register each test before scoring.
- Use nested leave-one-episode-out CV with the gate: held-out mean ≥ +0.005 and no held-out episode below −0.01.
- Exclude a candidate's own source episodes from its held-out scoring.
- Mocap is read by scoring and diagnostics only.
