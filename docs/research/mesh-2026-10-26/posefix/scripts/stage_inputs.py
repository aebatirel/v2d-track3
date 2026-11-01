"""posefix stage 0 (GT-free): build the pack 9a+ mesh folder and stage the public perception tracks.

9a+ = library_c0 white_pot / white_pot_lid / plastic_dish_rack, C1 T1 beige cup (ep11_beige_cup_sep_g1), C1 T2 dust
pan (mini_dust_pan_k297_s42_lib), library_v3 for every other object. Tracks: the stored converted tracks of the CD-O
sprint AUC guard (cdo_c0/tracks, cdo_c1/t2|t3/auc/tracks), checked array-equal to world_T_cam @ cam_T_<obj> of
data/sweep/ep<e>/poses.npz (our own inference output). Reads no parquet, scan or mocap.
Usage: python -I stage_inputs.py OUT_JSON
"""
import hashlib, json, os, shutil, sys
import numpy as np

R = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
SP = f'{S}/posefix'
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
C1 = f'{R}/docs/research/mesh-2026-10-26/cdo-sprint/C1'
SRC = {'white_pot': f'{R}/meshes/library_c0/white_pot.glb',
       'white_pot_lid': f'{R}/meshes/library_c0/white_pot_lid.glb',
       'plastic_dish_rack': f'{R}/meshes/library_c0/plastic_dish_rack.glb',
       'beige_cup': f'{C1}/T1-beige-lathe/meshes/ep11_beige_cup_sep_g1.glb',
       'mini_dust_pan': f'{C1}/T2-probe-picks/meshes/mini_dust_pan_k297_s42_lib.glb'}
for n in ('blue_cup', 'mini_sweeper', 'water_pitcher', 'wooden_piece_1', 'wooden_piece_2'):
    SRC[n] = f'{R}/meshes/library_v3/{n}.glb'
TRK = {e: f'{S}/cdo_c0/tracks/ep{e}/poses_world_vo.npz' for e in [0, 2, 11, 12, 13, 21, 22, 26, 27, 31, 41, 42, 43, 44, 45]}
TRK.update({e: f'{S}/cdo_c1/t2/auc/tracks/ep{e}/poses_world_vo.npz' for e in [18, 39, 40]})
TRK.update({e: f'{S}/cdo_c1/t3/auc/tracks/ep{e}/poses_world_vo.npz' for e in [23, 24]})


def h(p, k='sha256'):
    return hashlib.new(k, open(p, 'rb').read()).hexdigest()


out = {'meshes': {}, 'tracks': {}}
md = f'{SP}/mesh9a'
os.makedirs(md, exist_ok=True)
for n, p in sorted(SRC.items()):
    shutil.copyfile(p, f'{md}/{n}.glb')
    out['meshes'][n] = dict(source=p.replace(R + '/', ''), md5=h(p, 'md5'), sha256=h(p))
for e in EPS:
    src = f'{S}/data/sweep/ep{e}/poses.npz'
    P = np.load(src)
    W = np.asarray(P['world_T_cam'], np.float64)
    names = [k[len('cam_T_'):] for k in P.files if k.startswith('cam_T_')]
    Q = np.load(TRK[e])
    eq = all(np.max(np.abs(np.einsum('tij,tjk->tik', W, np.asarray(P[f'cam_T_{n}'], np.float64)) - Q[n])) < 1e-12
             for n in names) and sorted(Q.files) == sorted(names)
    nan = {n: int((~np.isfinite(Q[n]).all((1, 2))).sum()) for n in names}
    out['tracks'][e] = dict(source=src, source_sha256=h(src), stored=TRK[e], stored_sha256=h(TRK[e]),
                            objects=names, frames=int(len(W)), equal_to_source=bool(eq), nonfinite_frames=nan,
                            world_T_cam0_is_identity=bool(np.allclose(W[0], np.eye(4))),
                            hands=f'{S}/gmg/runs/20261031-b4ext6-90c8cce/hands/public/ep{e}/hands.npz',
                            hands_sha256=h(f'{S}/gmg/runs/20261031-b4ext6-90c8cce/hands/public/ep{e}/hands.npz'),
                            bundle_episode=f'{S}/gmg/runs/20261031-b4ext6-90c8cce/bundle/public/ep{e}/episode.json',
                            bundle_episode_sha256=h(f'{S}/gmg/runs/20261031-b4ext6-90c8cce/bundle/public/ep{e}/episode.json'))
    print(e, names, len(W), 'equal' if eq else 'DIFF', nan)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
