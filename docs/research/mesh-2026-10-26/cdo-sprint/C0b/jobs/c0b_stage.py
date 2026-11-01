"""Stage (and optionally upload) the C0b public box inputs (PREREG C0b section 2): plan.json, calib.json, our sweep
base tracks (store run 20261025-sweep-a894083) sweep/ep<N>/poses.npz, the G1 MediaPipe hands sweep/ep<N>/hands.npz
where they exist, the kit's v2dlb/mesh_budget.py, gmg/roster_public.json (slot order), and SHA256SUMS. The public
FoundationStereo depth is already in the store (cache/depth/public/ep<N>/depths_fs0.5.npy); its size and LFS sha256
are written into plan.json and checked on the box. No scan, mocap, parquet or *_align file (asserted).
Usage: python -I c0b_stage.py SCRATCH KIT REPO OUTDIR [--upload RUN_ID]
"""
import hashlib, json, os, shutil, sys

import numpy as np

SCR, KIT, REPO, OUT = sys.argv[1:5]
up = sys.argv[sys.argv.index('--upload') + 1] if '--upload' in sys.argv else None
MR = f'{REPO}/docs/research/mesh-2026-10-26'
roster = json.load(open(f'{MR}/gmg/roster_public.json'))['episodes']
EPS = sorted(int(e) for e in roster)
CAND = {'white_pot': [2, 26, 27, 41, 42, 43, 44, 45], 'white_pot_lid': [0, 2],
        'plastic_dish_rack': [12, 13, 26, 27, 31], 'blue_cup': [21, 22], 'beige_cup': [11]}
PRIM = ('white_pot', 'white_pot_lid', 'plastic_dish_rack')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


files = {'calib.json': f'{SCR}/data/calib.json', 'kit/v2dlb/mesh_budget.py': f'{KIT}/v2dlb/mesh_budget.py',
         'roster_public.json': f'{MR}/gmg/roster_public.json'}
plan = dict(schema='c0b-public-plan/1', episodes={}, candidate_eps=CAND, all_set={}, marker_objects={},
            tracks_source='store run 20261025-sweep-a894083 results/sweep/base/ep<N>/poses.npz',
            hands_source='store run 20261025-g1-022fece refs/perc2m/ep<N>/hands.npz (where it exists)',
            depth_source='store cache/depth/public/ep<N>/depths_fs0.5.npy')
from huggingface_hub import HfApi  # noqa: E402
info = {i.path: i for i in HfApi().get_paths_info('aebatirel/v2d-store', [f'cache/depth/public/ep{e}/depths_fs0.5.npy'
                                                                       for e in EPS], repo_type='dataset')}
for e in EPS:
    pz = f'{SCR}/data/sweep/ep{e}/poses.npz'
    hz = f'{SCR}/data/sweep/ep{e}/hands.npz'
    P = np.load(pz)
    bodies = [k[6:] for k in P.files if k.startswith('cam_T_')]
    slot = list(roster[str(e)])
    assert sorted(bodies) == sorted(slot), (e, bodies, slot)
    files[f'sweep/ep{e}/poses.npz'] = pz
    has_h = os.path.exists(hz) and os.path.getsize(hz) > 0
    if has_h:
        files[f'sweep/ep{e}/hands.npz'] = hz
    d = info[f'cache/depth/public/ep{e}/depths_fs0.5.npy']
    plan['episodes'][str(e)] = dict(objects=bodies, slot=slot, hands=has_h, frames_poses=int(len(P['world_T_cam'])),
                                    depth_bytes=int(d.size), depth_lfs_sha256=d.lfs.sha256 if d.lfs else None,
                                    poses_sha256=sha(pz), hands_sha256=sha(hz) if has_h else None)
for o, el in CAND.items():
    plan['all_set'][o] = sorted(int(e) for e, objs in roster.items() if o in objs)
for o in PRIM:
    for e in CAND[o]:
        plan['marker_objects'].setdefault(str(e), [])
for e in list(plan['marker_objects']):
    plan['marker_objects'][e] = [o for o in roster[e] if o in PRIM and int(e) in CAND[o]]
for k, v in files.items():
    low = (k + ' ' + v).lower()
    assert not any(w in low for w in ('scan', 'mocap', '_align', '.parquet', '/mesh/', 'library_v')), f'forbidden {k} {v}'
os.makedirs(OUT, exist_ok=True)
json.dump(plan, open(f'{OUT}/plan.json', 'w'), indent=1)
lines = [f'{sha(f"{OUT}/plan.json")}  plan.json']
for k, v in sorted(files.items()):
    d = os.path.join(OUT, k); os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copyfile(v, d)
    lines.append(f'{sha(d)}  {k}')
open(os.path.join(OUT, 'SHA256SUMS'), 'w').write('\n'.join(lines) + '\n')
tot = sum(os.path.getsize(os.path.join(OUT, k)) for k in files)
print(f'staged {len(files) + 1} files, {tot / 1e6:.1f} MB in {OUT}; episodes {len(EPS)}; depth '
      f'{sum(x["depth_bytes"] for x in plan["episodes"].values()) / 1e9:.2f} GB; all_set {plan["all_set"]}; '
      f'marker_objects {plan["marker_objects"]}')
if up:
    HfApi().upload_folder(folder_path=OUT, path_in_repo=f'runs/{up}/inputs', repo_id='aebatirel/v2d-store',
                          repo_type='dataset', commit_message=f'C0b public inputs {up}')
    print(f'uploaded to aebatirel/v2d-store runs/{up}/inputs')
