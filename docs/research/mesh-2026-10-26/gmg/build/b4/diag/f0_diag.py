"""B4 round-2 diagnostic (GT-free): where do the pixels of an object's chosen frame-0 det proposal go? Inputs: frame-0
depth (HTTP range read of our stereo depth), det masks, tracks, calib, the v5 bundle's meta (table plane), the v5 run's
MediaPipe hands. Counts per filter of extract_joint.Frames.samples."""
import json, sys, numpy as np, ast
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from recon_mesh import rectified_K
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
ep = int(sys.argv[1]); head = sys.argv[2]
raw = open(head, 'rb').read()
# npy header
hl = int.from_bytes(raw[8:10], 'little'); hdr = ast.literal_eval(raw[10:10 + hl].decode())
D0 = np.frombuffer(raw[10 + hl:10 + hl + 1000 * 1600 * 4], dtype=hdr['descr']).reshape(1000, 1600).astype(np.float32)
K = rectified_K(f'{S}/data/calib.json')
R = f'{S}/gmg/runs/20261031-b4ext5-a776e8e'
m = json.load(open(f'{R}/bundle/public/ep{ep}/episode.json'))
P = np.load(f'{S}/data/sweep/ep{ep}/poses.npz')
d = np.load(f'{S}/data/store/ep{ep}/det_f0.npz')
shp = tuple(int(x) for x in d['mask_shape']); M = np.unpackbits(d['masks'], axis=-1)[..., :shp[2]].astype(bool); sc = 1600 / shp[2]
from gmg import extract_joint as EJ, hands_cpu
c = dict(edge=0.02, zmin=0.05, zmax=1.5, band=0.008, cube=0.30, vox=0.004)
Dt = EJ.filtered_depth(D0, c['edge'])
nc, cc = np.asarray(m['table_frames']['0'][0]), float(m['table_frames']['0'][1])
W_C = P['world_T_cam'].astype(np.float64)
from unittest import mock
from gmg import guard
with mock.patch.object(guard, 'load_npz', lambda path, role, keys=None: np.load(path)):
    segs = hands_cpu.segments(f'{R}/hands/public/ep{ep}/hands.npz', W_C[:1], 0.03, 0.045, 0.15)
for o, ci in m['crop'].items():
    bi = ci.get('det_mask')
    if bi is None:
        continue
    vv, uu = np.nonzero(np.kron(M[bi], np.ones((int(sc), int(sc)), bool)))
    d0 = D0[vv, uu]; dt = Dt[vv, uu]
    valid_raw = np.isfinite(d0) & (d0 > c['zmin']) & (d0 < c['zmax'])
    valid = np.isfinite(dt) & (dt > c['zmin']) & (dt < c['zmax'])
    z = np.where(valid, dt, 0)
    Pc = np.stack([(uu - K[0, 2]) * z / K[0, 0], (vv - K[1, 2]) * z / K[1, 1], z], 1)
    hgt = Pc @ nc + cc
    table = valid & (hgt <= c['band'])
    hand = np.zeros(len(Pc), bool)
    A0, B0, rad = segs[0]
    for s in range(len(A0)):
        ab = B0[s] - A0[s]; ap = Pc - A0[s]
        h = np.clip(ap @ ab / max(ab @ ab, 1e-12), 0, 1)
        hand |= np.linalg.norm(ap - h[:, None] * ab, axis=1) <= rad[s]
    hand &= valid & ~table
    Ti = np.linalg.inv(P[f'cam_T_{o}'][0].astype(np.float64))
    Po = Pc @ Ti[:3, :3].T + Ti[:3, 3]
    incube = np.all(np.abs(Po) < c['cube'], 1)
    kept = valid & ~table & ~hand & incube
    hk = hgt[valid & ~hand]
    print(f'ep{ep} {o}: proposal {bi} pixels {len(vv)}; raw valid {valid_raw.sum()}, after edge filter {valid.sum()}, '
          f'table band {table.sum()}, hand capsules {hand.sum()} (hand segments {len(A0)}), outside cube '
          f'{(valid & ~table & ~hand & ~incube).sum()}, kept {kept.sum()} (bundle seed_in_proposal '
          f'{ci.get("seed_in_proposal")}); height above table of valid non-hand pixels: p10/50/90 '
          f'{np.round(np.percentile(hk, [10, 50, 90]) * 1e3, 1) if len(hk) else None} mm')
