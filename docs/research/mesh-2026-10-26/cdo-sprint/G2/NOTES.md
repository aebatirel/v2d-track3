# G2 generation batch: working notes (resume from here)

Spec: `../C4-audit/PREREG.md` section 7 (addendum 2, e573235), sections 2-3. Times UTC. Scratch S =
`/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`, bulk under `S/g2/`.

- 2026-11-02T20:17Z start. Read STATUS.md, CLAUDE.md, PREREG s2/s3/s7, gen-probe README, the 29 Oct log (work log
  ~4707-4830), gen/*.sh|py, crops.py, sim3_fit.py, audit_multiseed.py, mesh_metric.evaluate, C1 T2 place.py, C1 T3 fit.py.
  Vast credit $127.84; one other instance (20261102-ptrkF-58a0f37, not ours).
- 20:22-20:25Z crops (local CPU, GT-free): `bash scripts/make_crops.sh S/g2/inputs` = crops.py as on 29 Oct (every 3rd
  frame, --n 2, --hands where hands.npz exists, our sweep tracks, calib, library_v3 silhouette seed). 11 pairs, all
  accepted, 22 crops: pot ep41 (k279, k285), ep43 (k300, k303), ep44 (k0, k3); blue cup ep22 (k156, k159), ep21 (k15,
  k18), ep12 (k156, k159; no hands.npz for ep12, so no hand gate there, rest gate only); rack ep31 (k285, k282), ep12
  (k24, k21), ep26 (k144, k138); pitcher ep22 (k33, k174), ep21 (k171, k33). crops.py's rankings in
  `inputs/ep<E>_<obj>_crops.json`, hashes in `inputs/inputs_crops_sha256.txt`.
  vs 29 Oct: same picks for ep41 pot and ep22 blue cup; ep22 pitcher now k33 + k174 (was k174 + k171), ep26 rack
  k144 + k138 (was k144 + k96). Scores differ by < 0.2 % with unchanged tracks and library_v3 (likely the local
  trimesh/OpenCV versions); the current ranking is used as pre-registered.
  Visual check of the montage (S/g2/crops_montage.jpg): all 22 show the right object; GrabCut cut notches into some
  masks (ep12 blue cup base, ep31 rack, pot floor) and ep21 pitcher k33 has skin-coloured pixels at its base.
- 20:25Z observed points for the box's Sim(3) fits: `scripts/obs_sub.py` (40k points of S/obs_all/ep<E>_<obj>.npz,
  default_rng(0)), hashes `inputs/inputs_obs_sha256.txt`. Input tar S/g2/g2_inputs.tar sha256 de9fc1c9...
- Box queue: `../../gen/box_g2.sh` (SAM 3D alongside Hunyuan3D-2.1, then TRELLIS.2 1536 alone, 1024 fallback; Sim(3)
  on the CPUs; SHA256SUMS at the end). Screen: `../C4-audit/scripts/screen6.py` (6 seeds 3001-3006, roster emptied).
