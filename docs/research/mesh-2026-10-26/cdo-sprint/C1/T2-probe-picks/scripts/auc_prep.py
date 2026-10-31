"""GT-free preparation of the T2 AUC guard (PREREG.md s6). Reads only our own files: sweep perception tracks
(data/sweep/ep<e>/poses.npz: world_T_cam, cam_T_<obj>), library_v3 meshes, the placed candidates, and C0's
GT-free track conversions and mesh dirs (to decide whether C0's base runs may be reused). No scan, mocap, parquet.

  tracks : world_T_obj[t] = world_T_cam[t] @ cam_T_obj[t] (C0 build_c0.py recipe). For twins C0 already converted
           (11, 21, 22) C0's file is used if its recorded source sha256 equals the current sweep file and a fresh
           conversion equals it numerically; otherwise our own conversion. Others (18, 39, 40): our own.
  meshes : base = library_v3 of the 10 public objects (no spoon); single_<obj> = base with <obj>.glb replaced by the
           placed candidate.
  reuse  : C0's base/ep<e> result is reusable iff C0's base dir equals our base dir file by file (sha256) and the
           track used is C0's file (byte-identical).
Usage: auc_prep.py SCR OUT_DIR PLACED_DIR
"""
import hashlib, json, os, shutil, sys
import numpy as np

SCR, OUT, PLACED = sys.argv[1:4]
LIB = '/home/user/v2d-track3/meshes/library_v3'
OBJS = ['beige_cup', 'blue_cup', 'mini_dust_pan', 'mini_sweeper', 'plastic_dish_rack', 'water_pitcher', 'white_pot',
        'white_pot_lid', 'wooden_piece_1', 'wooden_piece_2']
CAND = {'water_pitcher': 'water_pitcher_k174_s42_lib.glb', 'mini_dust_pan': 'mini_dust_pan_k297_s42_lib.glb',
        'beige_cup': 'beige_cup_k6_s42_lib.glb'}
TWINS = {'water_pitcher': [21, 22], 'mini_dust_pan': [18, 39, 40], 'beige_cup': [11]}
C0 = f'{SCR}/cdo_c0'


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def convert(src):
    P = np.load(src, allow_pickle=False)
    W = np.asarray(P['world_T_cam'], np.float64)
    names = [k[len('cam_T_'):] for k in P.files if k.startswith('cam_T_')]
    return {n: np.einsum('tij,tjk->tik', W, np.asarray(P[f'cam_T_{n}'], np.float64)) for n in names}


rep = dict(tracks={}, mesh_dirs={}, c0_reuse={})
c0trk = json.load(open(f'{C0}/tracks/tracks.json'))
for e in sorted({e for v in TWINS.values() for e in v}):
    src = f'{SCR}/data/sweep/ep{e}/poses.npz'
    fresh = convert(src)
    c0p = f'{C0}/tracks/ep{e}/poses_world_vo.npz'
    use_c0 = False
    if str(e) in c0trk and os.path.exists(c0p) and c0trk[str(e)]['source_sha256'] == sha(src):
        z = np.load(c0p)
        use_c0 = set(z.files) == set(fresh) and all(np.array_equal(z[n], fresh[n]) for n in fresh)
    if use_c0:
        path = c0p
    else:
        d = f'{OUT}/tracks/ep{e}'
        os.makedirs(d, exist_ok=True)
        path = f'{d}/poses_world_vo.npz'
        np.savez(path, **fresh)
    rep['tracks'][e] = dict(source=src, source_sha256=sha(src), objects=sorted(fresh), frames=int(len(next(iter(fresh.values())))),
                            path=path, sha256=sha(path), c0_file=use_c0)


def fill(d, swap):
    os.makedirs(d, exist_ok=True)
    for o in OBJS:
        src = f'{PLACED}/{CAND[o]}' if o == swap else f'{LIB}/{o}.glb'
        shutil.copyfile(src, f'{d}/{o}.glb')
    return {o: sha(f'{d}/{o}.glb') for o in OBJS}


rep['mesh_dirs']['base'] = fill(f'{OUT}/base', None)
for o in CAND:
    rep['mesh_dirs'][f'single_{o}'] = fill(f'{OUT}/single_{o}', o)
c0base = {o: sha(f'{C0}/base/{o}.glb') for o in OBJS if os.path.exists(f'{C0}/base/{o}.glb')}
extra = sorted(set(os.listdir(f'{C0}/base')) - {f'{o}.glb' for o in OBJS})
same_dir = c0base == rep['mesh_dirs']['base'] and not extra
for e, t in rep['tracks'].items():
    j = f'{C0}/runs/base/ep{e}.json'
    rep['c0_reuse'][e] = dict(c0_base_dir_identical=same_dir, c0_extra_files=extra, track_is_c0_file=t['c0_file'],
                              c0_base_json=j if os.path.exists(j) else None,
                              reusable=bool(same_dir and t['c0_file']))
os.makedirs(OUT, exist_ok=True)
json.dump(rep, open(f'{OUT}/auc_prep.json', 'w'), indent=1)
print(json.dumps(rep['c0_reuse'], indent=1))
print(json.dumps({e: (t['sha256'][:16], t['c0_file'], t['objects']) for e, t in rep['tracks'].items()}, indent=1))
print(json.dumps({k: {o: s[:12] for o, s in v.items() if k == 'base' or o == k[len('single_'):]} for k, v in rep['mesh_dirs'].items()}, indent=1))
