"""For each grasp-lock eval reference in the local store mirror: object URDF paths (absolute /content/...) vs the pulled
files, URDF mesh references, masses, and the solver's gate (frames where a hand is near a moving object; solve.py
logic: --move 0.02, 10 deg, --gate 0.10) to estimate solve time. Reads our reference parquet only (no ground truth)."""
import json, os, re, sys
import numpy as np, pyarrow.parquet as pq
tab, store = sys.argv[1], sys.argv[2]
d = json.load(open(tab))['episodes']; rows = []
for e in sorted(d, key=int):
    r = d[e]
    if r['mode'] != 'glock':
        continue
    run = f"{store}/runs/{r['source_run']}"
    t = pq.read_table(f"{run}/{r['reference']}"); g = lambda c: t.column(c)[0].as_py()
    urdfs = g('object_urdf_paths'); names = g('object_body_names'); T = len(g('robot_left_wrist_position'))
    miss, masses, meshes_missing = [], [], []
    for u in urdfs:
        loc = run + u[len('/content'):] if u.startswith('/content/') else None
        if r['shared_assets']:
            continue                                   # /content/assets: built on the box (make_assets)
        if not loc or not os.path.exists(loc):
            miss.append(u); continue
        x = open(loc).read(); masses.append(re.findall(r'mass value="([^"]+)"', x)[0])
        for m in re.findall(r'filename="([^"]+)"', x):
            if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(loc), m))):
                meshes_missing.append(m)
    B = len(names)
    OP = np.array(g('object_body_position'), float).reshape(T, B, 3); OQ = np.array(g('object_body_wxyz'), float).reshape(T, B, 4)
    rad = np.array(g('object_mesh_radius'), float)
    travel = np.linalg.norm(OP - OP[:1], axis=-1).max(0)
    ang = np.array([np.degrees(np.arccos(np.clip(np.abs(np.sum(OQ[:, j] * OQ[:1, j], -1)), 0, 1)) * 2).max() for j in range(B)])
    moving = (travel > 0.02) | (ang > 10)
    near = {}
    for s in ('right', 'left'):
        fr = np.array(g(f'robot_{s}_frames'), float).reshape(T, -1, 7)[:, :, :3]
        dd = np.linalg.norm(fr[:, :, None] - OP[:, None], axis=-1).min(1) - rad[None]
        near[s] = (dd[:, moving] < 0.10).any(1) if moving.any() else np.zeros(T, bool)
    anyh = near['right'] | near['left']
    # replans that plan (commit 10 frames, horizon 60): a window [t, t+60] with an active hand
    act = sum(1 for t0 in range(0, T - 1, 10) if anyh[t0:t0 + 61].any())
    rows.append(dict(ep=int(e), T=T, objects=names, asset_root=r['asset_root'], urdf_missing=miss, meshes_missing=sorted(set(meshes_missing)),
                     masses=masses, moving=[n for n, m in zip(names, moving)], near_right=int(near['right'].sum()), near_left=int(near['left'].sum()),
                     near_any=int(anyh.sum()), planned_replans=act, replans=len(range(0, T - 1, 10)),
                     urdf_roots=sorted({os.path.dirname(os.path.dirname(u)) for u in urdfs})))
    print(json.dumps(rows[-1]))
json.dump(rows, open(sys.argv[3], 'w'), indent=1)
